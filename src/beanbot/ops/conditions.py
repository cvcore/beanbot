from typing import Dict
import regex as re
from beancount.core.data import Transaction, Posting
from beancount.core.inventory import Inventory
from beancount.core import interpolate, number


def is_residual_posting(posting: Posting) -> bool:
    try:
        is_residual = (posting.units is number.MISSING) or \
            (posting.meta is not None and '__automatic__' in posting.meta and posting.meta['__automatic__'])
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

    return any(map(lambda tag: re.match(r'_new', tag), transaction.tags))
