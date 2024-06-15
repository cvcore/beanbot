from decimal import Decimal
from typing import Dict, Optional
import regex as re
from beancount.core.data import Transaction, Posting
from beancount.core.inventory import Inventory
from beancount.core import interpolate, number


def is_residual_posting(posting: Posting) -> bool:
    try:
        is_residual = (posting.units is number.MISSING) or (
            posting.meta is not None
            and "__automatic__" in posting.meta
            and posting.meta["__automatic__"]
        )
    except AttributeError:
        is_residual = False

    return is_residual


def is_balanced(transaction: Transaction, options_map: Dict) -> bool:
    """Test and return if `transaction` is balanced"""

    # First test if transaction contains floating posting to absorb residuals
    balanced = any([is_residual_posting(posting) for posting in transaction.postings])
    residual = Inventory()
    # If not, calculate residuals explicitly
    if not balanced:
        residual = interpolate.compute_residual(transaction.postings)
        tolerances = interpolate.infer_tolerances(transaction.postings, options_map)
        balanced = residual.is_small(tolerances)

    return balanced


def is_predicted(transaction: Transaction) -> bool:
    """If transaction has tag started with `_new`, treat it as a predicted transaction."""

    return any(map(lambda tag: re.match(r"_new", tag), transaction.tags))


def is_internal_transfer(
    transaction_a: Transaction,
    transaction_b: Transaction,
    max_timediff: Optional[int] = None,
    max_unitsdiff: Optional[Decimal] = None,
) -> bool:
    """Test if transaction_a and transaction_b belongs to the same internal transfer from one own bank to the other one.

    Parameters
    ----------
    transaction_a : Transaction
        The first transaction
    transaction_b : Transaction
        The second transaction
    max_timediff : Optional[int], optional
        the maximal time difference between two transactions in days. By default 0.
    max_unitsdiff : Optional[Decimal], optional
        the maximal unit (amount) difference between two transactions. By default 0.

    Returns
    -------
    bool
        _description_
    """

    timediff = abs(transaction_a.date - transaction_b.date)

    if max_timediff is None:
        max_timediff = 0
    if max_unitsdiff is None:
        max_unitsdiff = Decimal(0.0)

    if (
        transaction_a.postings[0].account != transaction_b.postings[1].account
        and transaction_a.postings[0].units.number
        + transaction_b.postings[0].units.number
        < max_unitsdiff
        and transaction_a.postings[0].units.currency == transaction_b.units.currency
        and timediff.days <= max_timediff
    ):
        return True

    return False
