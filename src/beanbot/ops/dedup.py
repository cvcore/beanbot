from abc import ABCMeta, abstractmethod
from typing import Tuple, List
from beancount.core.data import Transaction, iter_entry_dates, filter_txns
from beancount.parser import printer
import datetime

class BaseDeduplicator(object):
    """Base class for deduplicators"""

    def __init__(self, window_days_head, window_days_tail) -> None:
        self._window_days_head = window_days_head
        self._window_days_tail = window_days_tail

    def _comparator(self, entry: Transaction, imported_entry: Transaction) -> bool:
        """Compare two entries to see if they are duplicates."""
        raise NotImplementedError()

    def _find_duplicated_pairs(self, entries, imported_entries, window_days_head=0, window_days_tail=0) -> List[Tuple[Transaction, Transaction]]:

        window_head = datetime.timedelta(days=window_days_head)
        window_tail = datetime.timedelta(days=window_days_tail + 1)

        # For each of the new entries, look at existing entries at a nearby date.
        duplicates = []
        for imported_entry in filter_txns(imported_entries):

            for entry in filter_txns(iter_entry_dates(entries, imported_entry.date - window_head, imported_entry.date + window_tail)): # This function requires that the entries are sorted by date.
                if self._comparator(entry, imported_entry):
                    duplicates.append((entry, imported_entry))
                    break
        return duplicates

    def deduplicate(self, entries: List[Transaction], imported_entries: List[Transaction]) -> Tuple[List[Transaction], List[Transaction]]:
        """De-duplicate the imported entries. Returns a tuple of (duplicated entries, non-duplicated entries). Requires all entries are sorted by date."""

        assert all(isinstance(entry, Transaction) for entry in entries), "All entries must be transactions"
        assert all(isinstance(imported_entries, Transaction) for imported_entries in imported_entries), "All imported entries must be transactions"

        duplicated_pairs = self._find_duplicated_pairs(entries, imported_entries, self._window_days_head, self._window_days_tail)
        duplicated_entries = [pair[1] for pair in duplicated_pairs]

        non_duplicated_entries = [entry for entry in imported_entries if entry not in duplicated_entries]

        return duplicated_entries, non_duplicated_entries


class InternalTransferDeduplicator(BaseDeduplicator):
    """Deduplicator that removes all internal transfers from the imported entries"""

    def __init__(self, window_days_head, window_days_tail, max_date_difference) -> None:
        super().__init__(window_days_head, window_days_tail)
        self._max_date_difference = max_date_difference

    def _is_internal_transfer(self, entry: Transaction, imported_entry: Transaction, max_date_difference: int) -> bool:

        # Check if any two postings from entry and imported entry can form a balanced transaction
        date1 = entry.date
        date2 = imported_entry.date
        if abs(date1 - date2) > datetime.timedelta(days=max_date_difference):
            return False

        for posting in entry.postings:
            for imported_posting in imported_entry.postings:
                if posting.units.currency != imported_posting.units.currency:
                    continue
                amount1 = posting.units.number
                amount2 = imported_posting.units.number
                if (amount1 + amount2).is_zero():
                    if amount1 > 0 and date1 >= date2: # entry is the destination, date1 should be no earlier then date2
                        return True
                    if amount2 > 0 and date2 >= date1:
                        return True

        return False

    def _comparator(self, entry: Transaction, imported_entry: Transaction) -> bool:
        return self._is_internal_transfer(entry, imported_entry, self._max_date_difference)
