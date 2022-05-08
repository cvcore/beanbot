#!/usr/bin/env python3

"""This module implements the Filer class which is responsible for saving / appending each new transactions into the corresponding files."""

from email.policy import default
from typing import Dict, List
from collections import defaultdict
from beancount.core import data
from beancount.parser import printer

from beanbot.common.types import Transactions
from beanbot.ops.extractor import TransactionRecordSourceAccountExtractor, TransactionSourceFilenameExtractor
from beanbot.ops.filter import PredictedTransactionFilter, BalancedTransactionFilter
from beanbot.common.collections import defaultdictstateless


class TransactionFileSaver():

    def __init__(self, default_location) -> None:
        self._account_to_filename = defaultdictstateless(lambda: default_location)
        self._sa_extractor = TransactionRecordSourceAccountExtractor()
        self._filename_extractor = TransactionSourceFilenameExtractor()
        self._pred_txn_filter = PredictedTransactionFilter()

    def learn_filename(self, transactions: Transactions):
        """Learn the filing conventions from historic transactions."""

        source_accounts = self._sa_extractor.extract(transactions)
        filenames = self._filename_extractor.extract(transactions)

        for account, filename in zip(source_accounts, filenames):
            if account == '' or filename == '':
                continue

            if account in self._account_to_filename:
                assert filename == self._account_to_filename[account], f"Detected conflicts in storage location for account: {account}.\nExpected: {self._account_to_filename[account]}\nReal:{filename}"
            else:
                self._account_to_filename[account] = filename

    def save(self, transactions: Transactions, dryrun=False):
        """Append each transactions into the end of their correponding files."""

        new_transactions = self._pred_txn_filter.filter(transactions)
        source_accounts = self._sa_extractor.extract(new_transactions)
        corr_filenames = [self._account_to_filename[sa] for sa in source_accounts]
        transactions_to_append: Dict[str, Transactions] = defaultdict(list)

        for new_txn, filename in zip(new_transactions, corr_filenames):
            transactions_to_append[filename].append(new_txn)

        for filename, transactions in transactions_to_append.items():
            self._save_transactions_to_file(transactions, filename, dryrun)

    def _save_transactions_to_file(self, transactions: Transactions, filename: str, dryrun: bool=False):
        """Save a list of `Transaction`s into `filename`"""

        if dryrun:
            print(f"*************************************\n[Dryrun] The following transactions will be saved to\n{filename}\n*************************************")
            printer.print_entries(transactions)
        else:
            with open(filename, 'a') as file:
                printer.print_entries(transactions, file=file)
