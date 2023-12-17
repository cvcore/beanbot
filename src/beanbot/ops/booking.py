#!/usr/bin/env python
# coding=utf-8


from copy import deepcopy
from beancount.core import data, interpolate, number
from beancount.core.inventory import Inventory
from typing import Dict, List, Optional, Set, Union

from beanbot.ops.conditions import is_balanced


def add_postings_auto_balance(transactions: List[data.Transaction], accounts: List[Union[data.Account, None]], options_map: Dict, add_tags: Optional[Set[str]]=None) -> List[data.Transaction]:
    """Detect unbalanced transaction from `transactions` and insert automatically postings from `accounts` to balance the transaction.
    Balanced transactions will be ignored."""

    transactions = deepcopy(transactions)

    for idx, (txn, account) in enumerate(zip(transactions, accounts)):
        if account is None or is_balanced(txn, options_map):
            continue

        new_posting = data.Posting(account, number.MISSING, None, None, None, None)
        txn.postings.append(new_posting)
        if add_tags is not None:
            if txn.tags is None:
                txn = txn._replace(tags=add_tags)
            else:
                txn = txn._replace(tags=txn.tags.union(add_tags))
            transactions[idx] = txn

    return transactions
