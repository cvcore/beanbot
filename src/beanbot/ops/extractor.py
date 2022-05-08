#!/usr/bin/env python

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
import numpy as np
from beancount.core import interpolate
from beancount.core.data import Transaction
import regex as re
from beanbot.common.configs import BeanbotConfig
from beanbot.common.types import Postings, Transactions
from beanbot.common.configs import BeanbotConfig


class AbstractTransactionExtractor(ABC):
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions"""

    @abstractmethod
    def extract(self, transactions: Transactions) -> list:
        pass


class TransactionDescriptionExtractor(AbstractTransactionExtractor):
    """Extract descriptions from transactions"""

    def extract(self, transactions: Transactions) -> list[str]:
        replace_none = lambda s: s if s is not None else ''

        transaction_descriptions = [
            f"{replace_none(t.payee)}\r{replace_none(t.narration)}" for t in transactions
        ]

        return transaction_descriptions


class _TransactionRegExpExtractor(AbstractTransactionExtractor):
    """Extract description from Transaction using RegExp with an extra helper method `match`."""

    def __init__(self, regexp: str):
        self._regexp = re.compile(regexp)

    def match(self, string: str):
        return self._regexp.match(string)


class _TransactionAccountExtractor(_TransactionRegExpExtractor):
    """Class for extracting account information from transactions. When there is no valid extraction, return an empty string./posting"""

    def posting_filter_keep_one(self, postings: Postings) -> str:

        valid_accounts = [p.account for p in postings if self.match(p.account)]

        if len(valid_accounts) > 0:
            return valid_accounts[0]
        return ''

    def extract(self, transactions: Transactions) -> list[str]:

        return [self.posting_filter_keep_one(t.postings) for t in transactions]


class TransactionCategoryAccountExtractor(_TransactionAccountExtractor):
    """Extract accounts for categorizing the transactions"""

    def __init__(self):
        regex_category_account = BeanbotConfig.get_global()['regex-category-account']
        super().__init__(regex_category_account)


class TransactionRecordSourceAccountExtractor(_TransactionAccountExtractor):
    """Extract accounts where the transaction records are generated"""

    def __init__(self):
        source_account_regex = BeanbotConfig.get_global()['regex-source-account']
        super().__init__(source_account_regex)


class TransactionDateExtractor(AbstractTransactionExtractor):

    def _date_to_int(self, dt: date) -> int:
        return dt.year * 10000 + dt.month * 100 + dt.day

    def extract(self, transactions: Transactions) -> list:
        dates = [self._date_to_int(t.date) for t in transactions]
        return dates


class _TransactionAmountExtractor(_TransactionRegExpExtractor):
    """Class for extracting account information from transactions"""

    def _posting_amount_keep_one(self, postings: Postings) -> str:

        for p in postings:
            if self.match(p.account):
                return np.sign(p.units.number)
        return 0.

    def extract(self, transactions: Transactions) -> list[str]:

        return [self._posting_amount_keep_one(t.postings) for t in transactions]


class TransactionCategoryAmountExtractor(_TransactionAmountExtractor):

    def __init__(self):
        regex_category_account = BeanbotConfig.get_global()['regex-category-account']
        super().__init__(regex_category_account)


class TransactionRecordSourceAmountExtractor(_TransactionAmountExtractor):

    def __init__(self):
        regex_record_source_account = BeanbotConfig.get_global()['regex-source-account']
        super().__init__(regex_record_source_account)


class TransactionSourceFilenameExtractor(AbstractTransactionExtractor):
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions"""

    def extract(self, transactions: Transactions) -> list:

        filenames = []

        for txn in transactions:
            try:
                filename = txn.meta['filename']
            except KeyError:
                filename = ''

            filenames.append(filename)

        return filenames
