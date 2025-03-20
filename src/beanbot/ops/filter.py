#!/usr/bin/env python3
# coding=utf-8
# Filtering the transactions

from typing import Optional
from beancount.core.data import Transaction, Entries, Directive

from beanbot.common.types import Transactions
from beanbot.data.directive import MutableTransaction, MutableEntries, MutableDirective
from beanbot.ops.conditions import is_balanced, is_internal_transfer, is_predicted
from beanbot.ops.extractor import TransactionRecordSourceAccountExtractor


class BaseFilter:
    """Base filter class that filters beancount entries according to criterions.

    This base class will pass through everything, as a default design.

    For children of `BaseFilter` class, in most cases you just need to implement
    the `_cond_impl` method. When calling filter, the implementation will automatically pass the
    entries through the filters of parent classes before calling the object's own filter implementation.
    In this way, the implementation effort of each filter can be kept minimum.
    """

    def __init__(self) -> None:
        self._inverse_condition = False

    def filter(self, entries: Entries | MutableEntries) -> Entries | MutableEntries:
        if self.__class__ == BaseFilter:
            return entries
        if hasattr(super(), "filter"):
            entries = super().filter()
        return self._filter_impl(entries)

    def _filter_impl(
        self, entries: Entries | MutableEntries
    ) -> Entries | MutableEntries:
        return [entry for entry in entries if self._test_condition(entry)]

    def _test_condition(self, entry: Directive | MutableDirective) -> bool:
        condition = self._cond_impl(entry)
        if self._inverse_condition:
            condition = not condition
        return condition

    def _cond_impl(self, entry: Directive | MutableDirective) -> bool:
        return True


class TransactionFilter(BaseFilter):
    """Filter that only passes transactions"""

    def _cond_impl(self, entry: Directive | MutableDirective) -> bool:
        return isinstance(entry, Transaction | MutableTransaction)


class NotTransactionFilter(TransactionFilter):
    def __init__(self) -> None:
        super().__init__()
        self._inverse_condition = True


class BalancedTransactionFilter(TransactionFilter):
    """Transaction filter to remove all unbalanced transactions"""

    def __init__(self, options_map) -> None:
        super().__init__()
        self._options_map = options_map

    def _cond_impl(self, entry: Directive | MutableDirective) -> bool:
        return is_balanced(entry, self._options_map)


class UnbalancedTransactionFilter(BalancedTransactionFilter):
    """The unbalanced twin of the balanced transaction filter. Leave only the unbalanced transactions in this case."""

    def __init__(self, options_map) -> None:
        super().__init__(options_map)
        self._inverse_condition = True

        # class MostRecentTransactionFilter(TransactionFilter):
        #     """If more than one transaction has the same description, keep the one with the most recent date.

        #     The results are expected to have a stable ordering, i.e. the order of output always respect the order of the original input."""

        #     def __init__(self, extractor: AbstractTransactionExtractor):
        #         super().__init__()
        #         self._extractor = extractor

        #     def filter(self, transactions: List[Transaction | MutableTransaction]) -> List[Transaction | MutableTransaction]:

        #         descriptions = self._extractor.extract(transactions)
        #         desc_to_idx = {}

        #         for txn_idx, (txn, desc) in enumerate(zip(transactions, descriptions)):
        #             date_txn = txn.date
        #             if desc in desc_to_idx:
        #                 date_prev = transactions[desc_to_idx[desc]].date
        #                 if date_txn > date_prev:
        #                     desc_to_idx[desc] = txn_idx
        #             else:
        #                 desc_to_idx[desc] = txn_idx

        #         indices_latest = sorted(desc_to_idx.values())
        #         transactions_latest = [transactions[idx] for idx in indices_latest]

        # return transactions_latest


class PredictedTransactionFilter(TransactionFilter):
    """Return transactions that have a posting predicted by the automatic classifier"""

    def _cond_impl(self, entry: Directive | MutableDirective) -> bool:
        return is_predicted(entry)


class NonduplicatedTransactionFilter(TransactionFilter):
    """Remove double-bookings for internal transactions between one bank account to the other bank account

    Arguments:
        `existing_transactions`: (optional, Transactions) if specified, compare also with existing transactions for duplicate filtering.
        `accepted_delay`: (optional, int) maximum number of delay in days for duplicate detection"""

    def __init__(
        self,
        existing_transactions: Optional[Transactions] = None,
        accepted_delay: Optional[int] = None,
    ):
        self._existing_transactions = existing_transactions
        self._accepted_delay = accepted_delay

    def _filter_impl(
        self, entries: Entries | MutableEntries
    ) -> Entries | MutableEntries:
        filtered_entries = []

        for idx, entry in enumerate(entries):
            entry_valid = True
            for entry_next in entries[idx:]:
                if is_internal_transfer(entry, entry_next):
                    print(
                        f"Found duplicate entries in new transactions:\n{entry_next}\n{entry}"
                    )
                    entry_valid = False
                    break
            if self._existing_transactions is not None:
                for entry_next in self._existing_transactions:
                    if is_internal_transfer(entry, entry_next):
                        print(
                            f"Found duplicate entries in existing transactions:\n{entry_next}\n{entry}"
                        )
                        entry_valid = False
                        break

            if entry_valid:
                filtered_entries.append(entry)

        return filtered_entries


class AccountTransactionFilter(TransactionFilter):
    """Filter that only passes transactions"""

    def __init__(self, account: str) -> None:
        super().__init__()
        self._account = account
        self._extractor = TransactionRecordSourceAccountExtractor()

    def _cond_impl(self, entry: Directive | MutableDirective) -> bool:
        if not isinstance(entry, Transaction | MutableTransaction):
            return False
        return self._extractor.extract_one(entry) == self._account
