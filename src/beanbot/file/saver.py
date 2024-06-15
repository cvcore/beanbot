#!/usr/bin/env python3

"""This module implements the Filer class which is responsible for saving / appending each new transactions into the corresponding files."""

import sys
from typing import Dict
from collections import defaultdict
from beancount.core import data
from beancount.parser import printer

from beanbot.ops.extractor import (
    DirectiveRecordSourceAccountExtractor,
    DirectiveSourceFilenameExtractor,
)
from beanbot.ops.filter import PredictedTransactionFilter
from beanbot.common.collections import defaultdictstateless


class EntryFileSaver:
    def __init__(self, default_location) -> None:
        self._account_to_filename = defaultdictstateless(lambda: default_location)
        self._sa_extractor = DirectiveRecordSourceAccountExtractor()
        self._filename_extractor = DirectiveSourceFilenameExtractor()
        self._pred_txn_filter = PredictedTransactionFilter()

    def learn_filename(self, entries: data.Entries):
        """Learn the filing conventions from historic transactions."""

        source_accounts = self._sa_extractor.extract(entries)
        filenames = self._filename_extractor.extract(entries)

        for account, filename in zip(source_accounts, filenames):
            if account == "" or filename == "":
                continue

            if account in self._account_to_filename:
                assert (
                    filename == self._account_to_filename[account]
                ), f"Detected conflicts in storage location for account: {account}.\nExpected: {self._account_to_filename[account]}\nGot:{filename}"
            else:
                self._account_to_filename[account] = filename

    def save(self, entries: data.Entries, dryrun=False):
        """Append each transactions into the end of their correponding files."""

        source_accounts = self._sa_extractor.extract(entries)
        filenames = [self._account_to_filename[sa] for sa in source_accounts]
        entries_to_append: Dict[str, data.Entries] = defaultdict(list)

        for new_txn, filename in zip(entries, filenames):
            entries_to_append[filename].append(new_txn)

        for filename, entries in entries_to_append.items():
            self._append_entries_to_file(entries, filename, dryrun)

    def _append_entries_to_file(
        self, transactions: data.Entries, filename: str, dryrun: bool = False
    ):
        """Save a list of `Transaction`s into `filename`"""

        if dryrun:
            print(
                f"*************************************\n[Dryrun] The following transactions will be saved to\n{filename}\n*************************************"
            )
            printer.print_entries(transactions, file=sys.stdout)
        else:
            with open(filename, "a") as file:
                printer.print_entries(transactions, file=file)
