#!/usr/bin/env python

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
import numpy as np
from beancount.core import interpolate
from beancount.core.data import Transaction, Directive, Entries
import regex as re
from beanbot.common.configs import BeanbotConfig
from beanbot.common.types import Postings, Transactions


class AbstractTransactionExtractor(ABC):
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions"""

    @abstractmethod
    def extract_one(self, transaction: Transaction) -> str:
        pass

    def extract(self, transactions: Transactions) -> list[str]:
        return [self.extract_one(t) for t in transactions]


class TransactionDescriptionExtractor(AbstractTransactionExtractor):
    """Extract descriptions from transactions"""

    def extract_one(self, transaction: Transaction) -> str:
        replace_none = lambda s: s if s is not None else ''
        return f"{replace_none(transaction.payee)}\r{replace_none(transaction.narration)}"


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

    def extract_one(self, transaction: Transaction) -> list[str]:

        return self.posting_filter_keep_one(transaction.postings)


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

    def extract_one(self, transaction: Transaction) -> str:
        date = self._date_to_int(transaction.date)
        return date


class _TransactionAmountExtractor(_TransactionRegExpExtractor):
    """Class for extracting account information from transactions"""

    def _posting_amount_keep_one(self, postings: Postings) -> str:

        for p in postings:
            if self.match(p.account):
                return np.sign(p.units.number)
        return 0.

    def extract_one(self, transaction: Transaction) -> str:

        return self._posting_amount_keep_one(transaction.postings)


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

    def extract_one(self, transaction: Transaction) -> str:

        try:
            filename = transaction.meta['filename']
        except KeyError:
            filename = ''

        return filename



class BaseEntryExtractor():
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions"""

    SUPPORTED_ENTRY_TYPES = [Transaction]

    def __init__(self):
        self._extractor_cache = {}

    # TODO: put extract and extract_one into a abstract base class

    def extract(self, entries: Entries) -> list[str]:
        """Extract a list of string descriptions from a list of Entries"""
        return [self.extract_one(e) for e in entries]

    def extract_one(self, entry: Directive) -> str:
        """Extract a list of string descriptions from a list of Entries"""
        assert self.__class__.__name__ != 'BaseEntryExtractor', "Calling from base class is not allowed"
        assert type(entry) in self.SUPPORTED_ENTRY_TYPES, f"Unsupported entry type: {type(entry)}"

        entry_class_name = entry.__class__.__name__ # Class name of the entry, e.g. Transaction / Balance / Open ...
        extractor_type = self.__class__.__name__ # Class name of the extractor, e.g. EntrySourceAccountExtractor / EntrySourceFilenameExtractor
        extractor_class = extractor_type.replace('Entry', entry_class_name, 1) # get the extractor class name to be used depending on the entry's and the extractor's class name
        print(f"[DEBUG] extractor class: {extractor_class}")

        if extractor_class not in self._extractor_cache:
            self._extractor_cache[extractor_class] = globals()[extractor_class]()
            print(f"[DEBUG] extractor class: {extractor_class} instantiated")
        extractor = self._extractor_cache[extractor_class]

        return extractor.extract_one(entry)


class EntryRecordSourceAccountExtractor(BaseEntryExtractor):
    pass


class EntrySourceFilenameExtractor(BaseEntryExtractor):
    pass
