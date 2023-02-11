#!/usr/bin/env python

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
import numpy as np
from beancount.core import interpolate
from beancount.core.data import Transaction, Directive, Entries, Balance
from beancount.core import data
import regex as re
from beanbot.common.configs import BeanbotConfig
from beanbot.common.types import Postings, Transactions
import typing


class _BaseExtractor(object):
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions"""

    def extract_one(self, entry: Directive):
        self._type_check(entry)
        return self._extract_one_impl(entry)

    def extract(self, entries: Entries) -> list:
        return [self.extract_one(e) for e in entries]

    def _extract_one_impl(self, entry: Directive):
        return NotImplementedError('You need to implement this method in the subclass.')

    def _type_check(self, entry: Directive) -> None:
        expected_type_name = re.match(r"[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))", self.__class__.__name__).group()
        expected_type = getattr(data, expected_type_name)
        if typing.get_origin(expected_type) is typing.Union:
            expected_type = typing.get_args(expected_type)
        assert isinstance(entry, expected_type), f"Expected type {expected_type_name}, got {type(entry)}!"


################# Extractor for Transactions #################


class TransactionDescriptionExtractor(_BaseExtractor):
    """Extract descriptions from transactions"""

    def __init__(self, prefer_payee=True) -> None:
        super().__init__()
        self._prefer_payee = prefer_payee

    def _extract_one_impl(self, entry: Transaction) -> str:
        replace_none = lambda s: s if s is not None else ''
        # return f"{replace_none(entry.payee)}\r{replace_none(entry.narration)}"
        result:str = ''
        if entry.payee is not None:
            if self._prefer_payee:
                result = entry.payee
            else:
                result = f"{replace_none(entry.payee)} {replace_none(entry.narration)}"
        else:
            result = replace_none(entry.narration)
        # remove hyphens connecting words
        # result = re.sub(r'(?<=\w)-(?=\w)', '', result)
        # # remove dots between words
        # result = re.sub(r'(?<=\w)\.(?=\w)', '', result)
        # remove dots in form of abbreviations e.g. a.b.c.d.
        result = result.lower()

        result = re.sub(r'((?<=(\P{L}|^)\p{L})\.(?=\p{L}(\P{L}|$)))+', '', result)
        # remove all non-alphanumeric characters with whitespace
        # result = re.sub('[^0-9a-zA-Z]+', ' ', result).lower()
        result = re.sub(r'(\p{Z}|\p{S}|\p{P})+', ' ', result)

        # process european texts
        result = result.replace("ä", "ae")
        result = result.replace("ö", "oe")
        result = result.replace("ü", "ue")
        result = result.replace("ß", "ss")
        result = result.replace("é", "e")

        return result


class _TransactionRegExpExtractor(_BaseExtractor):
    """Extract description from Transaction using RegExp with an extra helper method `match`."""

    def __init__(self, regexp: str):
        super().__init__()
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

    def _extract_one_impl(self, entry: Transaction) -> str:
        return self.posting_filter_keep_one(entry.postings)


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


class TransactionDateExtractor(_BaseExtractor):

    def _date_to_int(self, dt: date) -> int:
        return dt.year * 10000 + dt.month * 100 + dt.day

    def _extract_one_impl(self, entry: Transaction) -> int:
        return self._date_to_int(entry.date)


class _TransactionAmountExtractor(_TransactionRegExpExtractor):
    """Class for extracting account information from transactions"""

    def _posting_amount_keep_one(self, postings: Postings) -> float:
        for p in postings:
            if self.match(p.account):
                return np.sign(p.units.number)
        return 0.

    def _extract_one_impl(self, entry: Transaction) -> float:
        return self._posting_amount_keep_one(entry.postings)


class TransactionCategoryAmountExtractor(_TransactionAmountExtractor):

    def __init__(self):
        regex_category_account = BeanbotConfig.get_global()['regex-category-account']
        super().__init__(regex_category_account)


class TransactionRecordSourceAmountExtractor(_TransactionAmountExtractor):

    def __init__(self):
        regex_record_source_account = BeanbotConfig.get_global()['regex-source-account']
        super().__init__(regex_record_source_account)


class TransactionSourceFilenameExtractor(_BaseExtractor):
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions"""

    def _extract_one_impl(self, entry: Transaction) -> str:
        try:
            filename = entry.meta['filename']
        except KeyError:
            filename = ''

        return filename


################# Extractor for Balances #################


class BalanceRecordSourceAccountExtractor(_BaseExtractor):
    """Extract account where the balance records are generated"""

    def _extract_one_impl(self, entry: data.Balance) -> str:
        return entry.account


class BalanceSourceFilenameExtractor(_BaseExtractor):
    """Extract account where the balance records are generated"""

    def _extract_one_impl(self, entry: data.Balance) -> str:
        try:
            filename = entry.meta['filename']
        except KeyError:
            filename = ''

        return filename


################# Extractor for Directives #################


class _BaseDirectiveExtractor(_BaseExtractor):
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions.
    This class with automatically call the extractor based on the type of the entry.
    The user should not instantiate this class directly, but use the subclasses instead."""

    # You should extend this list with the supported entry types, when you implement a new extractor for a new entry type.
    SUPPORTED_ENTRY_TYPES = [Transaction, Balance]

    def __init__(self):
        self._extractor_cache = {}

    def extract_one(self, entry: Directive) -> str:
        """Extract a list of string descriptions from a list of Entries"""
        assert self.__class__.__name__ != 'BaseDirectiveExtractor', "Calling from base class is not allowed"
        if type(entry) not in self.SUPPORTED_ENTRY_TYPES:
            print(f"[Warning] Unsupported entry type: {type(entry)}. Returning empty string!")
            return ''

        entry_class_name = entry.__class__.__name__ # Class name of the entry, e.g. Transaction / Balance / Open ...
        extractor_type = self.__class__.__name__ # Class name of the extractor, e.g. EntrySourceAccountExtractor / EntrySourceFilenameExtractor
        extractor_class = extractor_type.replace('Directive', entry_class_name, 1) # get the extractor class name to be used depending on the entry's and the extractor's class name

        if extractor_class not in self._extractor_cache:
            self._extractor_cache[extractor_class] = globals()[extractor_class]()
            print(f"[DEBUG] extractor class: {extractor_class} instantiated")
        extractor = self._extractor_cache[extractor_class]

        return extractor.extract_one(entry)


class DirectiveRecordSourceAccountExtractor(_BaseDirectiveExtractor):
    pass


class DirectiveSourceFilenameExtractor(_BaseDirectiveExtractor):
    pass
