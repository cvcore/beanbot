from copy import deepcopy
from typing import Any, Optional, Tuple, List
from beancount.core.data import (
    iter_entry_dates,
    Directive,
    Entries,
    Open,
    Close,
    Balance,
    Transaction,
    Note,
)
from beancount.parser import printer
import datetime
import re
from beanbot.common.types import Postings

from beanbot.ops.extractor import TransactionRecordSourceAccountExtractor


class BaseDeduplicator(object):
    """Base class for deduplicators. Currently only implement deduplication for transactions."""

    def __init__(self, window_days_head, window_days_tail) -> None:
        self._window_days_head = window_days_head
        self._window_days_tail = window_days_tail

    def _comparator(self, entry: Directive, imported_entry: Directive) -> bool:
        """Compare two entries to see if they are duplicates."""
        raise NotImplementedError()

    def _find_duplicated_pairs(
        self, entries, imported_entries, window_days_head=0, window_days_tail=0
    ) -> List[Tuple[Directive, Directive]]:
        """Find duplicated pairs of entries. Returns a list of (entry, imported_entry) pairs which forms a duplication.
        This method tries to find duplicated entries in `imported_entries` by comparing them with entries in `entries`,
        which are within a time window of `window_days_head` days before and `window_days_tail` days after the date of the imported entry."""

        window_head = datetime.timedelta(days=window_days_head)
        window_tail = datetime.timedelta(days=window_days_tail + 1)

        entries = deepcopy(entries)
        entries = sorted(entries, key=lambda x: x.date)

        # For each of the new entries, look at existing entries at a nearby date.
        duplicates = []
        for imported_entry in imported_entries:
            for entry in iter_entry_dates(
                entries,
                imported_entry.date - window_head,
                imported_entry.date + window_tail,
            ):  # This function requires that the entries are sorted by date.
                if self._comparator(entry, imported_entry):
                    duplicates.append((entry, imported_entry))
                    break
        return duplicates

    def deduplicate(
        self, entries: Entries, imported_entries: Entries
    ) -> Tuple[Entries, Entries]:
        """De-duplicate the imported entries. Returns a tuple of (duplicated entries, non-duplicated entries). Requires all input entries are sorted by date."""

        duplicated_pairs = self._find_duplicated_pairs(
            entries, imported_entries, self._window_days_head, self._window_days_tail
        )
        duplicated_entries = [pair[1] for pair in duplicated_pairs]
        non_duplicated_entries = [
            entry for entry in imported_entries if entry not in duplicated_entries
        ]

        return duplicated_entries, non_duplicated_entries


class InternalTransferDeduplicator(BaseDeduplicator):
    """Deduplicator that removes all internal transfers from the imported entries"""

    def __init__(self, window_days_head, window_days_tail, max_date_difference) -> None:
        super().__init__(window_days_head, window_days_tail)
        self._max_date_difference = max_date_difference
        self._re_internal_account = re.compile(r"^(Liabilities:Credit|Assets:Checking)")

    def _is_internal_transfer(
        self, entry: Transaction, imported_entry: Transaction, max_date_difference: int
    ) -> bool:
        assert (
            len(imported_entry.postings) == 1
        ), "Imported entry must have exactly one posting for deduplication"

        source_account_extr = TransactionRecordSourceAccountExtractor()
        account_entry = source_account_extr.extract_one(entry)
        account_imported_entry = source_account_extr.extract_one(imported_entry)

        if not self._re_internal_account.match(
            account_entry
        ) or not self._re_internal_account.match(account_imported_entry):
            return False
        # TODO: attempt adding the destination account to the postings

        # Check if any two postings from entry and imported entry can form a balanced transaction
        date1 = entry.date
        date2 = imported_entry.date
        if abs(date1 - date2) > datetime.timedelta(days=max_date_difference):
            return False

        duplicate_found = False

        for posting in entry.postings:
            for imported_posting in imported_entry.postings:
                if posting.units.currency != imported_posting.units.currency:
                    continue
                if (
                    posting.account != account_entry
                    or imported_posting.account != account_imported_entry
                ):
                    continue  # only match the source accounts
                amount1 = posting.units.number
                amount2 = imported_posting.units.number
                if (amount1 + amount2).is_zero():
                    if amount1 > 0 and date1 >= date2:  # money flow: 2 -> 1
                        duplicate_found = True
                        break
                    if amount2 > 0 and date2 >= date1:  # money flow: 1 -> 2
                        duplicate_found = True
                        break

        if duplicate_found:
            # try to search for a matching posting from the existing entry
            account_matches = False

            for posting in entry.postings:
                if posting.account == account_entry:
                    continue  # skip the source account
                if posting.account == account_imported_entry:
                    account_matches = True
                    break

            if not account_matches:
                print(
                    f"[Warning] Possible wrong posting(s) detected: {printer.format_entry(entry)}The posting should contain: {account_imported_entry}"
                )

            return True

        return False

    def _comparator(self, entry: Directive, imported_entry: Directive) -> bool:
        if isinstance(entry, Transaction) and isinstance(imported_entry, Transaction):
            return self._is_internal_transfer(
                entry, imported_entry, self._max_date_difference
            )
        return False


def _comparator(field_value_0: Any, field_value_1: Any, field_key: str) -> bool:
    if field_key == "postings":
        field_value_0: Postings
        field_value_1: Postings

        if (
            len(field_value_0) > 0
            and len(field_value_1) > 0
            and field_value_0[0].account == field_value_1[0].account
            and field_value_0[0].units == field_value_1[0].units
        ):
            return True

        return False

    # Handle the case where we have mixed input of None and empty string
    field_value_0 = "" if field_value_0 is None else field_value_0
    field_value_1 = "" if field_value_1 is None else field_value_1

    return field_value_0 == field_value_1


class SimilarEntryDeduplicator(BaseDeduplicator):
    def _compare_postings(
        self, postings: Postings, imported_postings: Postings
    ) -> bool:
        postings = sorted(postings.copy(), key=lambda x: x.account)
        imported_postings = sorted(imported_postings.copy(), key=lambda x: x.account)

        accounts = [posting.account for posting in postings]
        accounts_imported = [posting.account for posting in imported_postings]
        if len(accounts_imported) == 1 and accounts_imported[0] not in accounts:
            return False
        elif len(accounts_imported) > 1 and accounts_imported != accounts:
            return False

        amounts = [p.units for p in postings]
        amounts_imported = [p.units for p in imported_postings]
        if (
            len(amounts_imported) == 1
            and amounts[accounts.index(accounts_imported[0])] != amounts_imported[0]
        ):
            return False
        elif len(amounts_imported) > 1 and amounts != amounts_imported:
            return False

        return True

    def _compare_optional_strings(
        self, str_value: Optional[str], imported_str_value: Optional[str]
    ) -> bool:
        if str_value is None:
            str_value = ""
        if imported_str_value is None:
            imported_str_value = ""
        return str_value == imported_str_value

    def _comparator(self, entry: Directive, imported_entry: Directive) -> bool:
        if type(entry) != type(imported_entry):  # pylint: disable=unidiomatic-typecheck
            return False

        FIELDS_COMPARISON = {
            Open: ["date", "account"],
            Close: ["date", "account"],
            Balance: ["date", "account", "amount"],
            Transaction: ["date", "payee", "narration", "postings"],
            Note: ["date", "account", "comment"],
        }

        assert (
            type(entry) in FIELDS_COMPARISON.keys()
        ), "Entry type not supported for deduplication"

        fields = FIELDS_COMPARISON[type(entry)]
        for field in fields:
            field_value_0 = getattr(entry, field, None)
            field_value_1 = getattr(imported_entry, field, None)
            if field == "postings":
                if not self._compare_postings(field_value_0, field_value_1):
                    return False
            elif field in ["payee", "narration", "comment"]:
                if not self._compare_optional_strings(field_value_0, field_value_1):
                    return False
            else:
                if field_value_0 != field_value_1:
                    return False

        return True


class Deduplicator:
    def __init__(self, window_days_head, window_days_tail, max_date_difference) -> None:
        """Initialize the deduplicator with a list of deduplicators. The deduplicators are applied in the order they are given."""

        self._deduplicators = [
            SimilarEntryDeduplicator(
                0, 0
            ),  # For similar entries, we don't need a window
            InternalTransferDeduplicator(
                window_days_head, window_days_tail, max_date_difference
            ),
        ]

    def deduplicate(
        self, entries: Entries, imported_entries: Entries
    ) -> Tuple[Entries, Entries]:
        duplicates = []
        for dedup in self._deduplicators:
            duplicated_entries, imported_entries = dedup.deduplicate(
                entries, imported_entries
            )
            duplicates.extend(duplicated_entries)

        return duplicates, imported_entries
