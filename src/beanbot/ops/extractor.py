#!/usr/bin/env python

from __future__ import annotations
from datetime import date
import numpy as np
from beancount.core.data import Transaction, Directive, Entries
from beancount.core import data
from beanbot.data import directive
from beanbot.helper import logger
import regex as re
from beanbot.common.configs import BeanbotConfig
from beanbot.common.types import Postings
from typing import Any, List


class BaseExtractor(object):
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions"""

    def extract_one(self, entry: Directive) -> Any:
        self._type_check(entry)
        return self._extract_one_impl(entry)

    def extract(self, entries: Entries) -> List:
        return [self.extract_one(e) for e in entries]

    def _extract_one_impl(self, entry: Directive) -> Any:
        return NotImplementedError("You need to implement this method in the subclass.")

    def _type_check(self, entry: Directive) -> None:
        """We do type checking based on the name of the extractor class. The first capitalized word of the class name is the expected type of the entry.
        Since for each type, there can be a mutable version that is compatible with the immutable version, we need to check both types.

        Args:
            entry (Directive): The entry to be checked.

        Raises:
            AssertionError: If the type of the entry is not compatible with the expected type.
        """

        expected_type_str = re.match(
            r"[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))", self.__class__.__name__
        ).group()
        expected_type_immutable = getattr(data, expected_type_str)
        expected_type_mutable = getattr(directive, "Mutable" + expected_type_str)
        assert isinstance(
            entry, (expected_type_immutable, expected_type_mutable)
        ), f"Expected type {expected_type_str}, got {type(entry)}!"


################# Extractor for Transactions #################


class TransactionDescriptionExtractor(BaseExtractor):
    """Extract descriptions from transactions"""

    def __init__(self, prefer_payee=True) -> None:
        super().__init__()
        self._prefer_payee = prefer_payee

    def _extract_one_impl(self, entry: Transaction) -> str:
        replace_none = lambda s: s if s is not None else ""
        # return f"{replace_none(entry.payee)}\r{replace_none(entry.narration)}"
        result: str = ""
        if entry.payee is not None:
            if self._prefer_payee:
                result = entry.payee
            else:
                result = f"{replace_none(entry.payee)} {replace_none(entry.narration)}"
        else:
            result = replace_none(entry.narration)

        result = result.lower()

        # remove hyphens connecting words
        # result = re.sub(r'(?<=\w)-(?=\w)', '', result)

        # remove dots between words
        # result = re.sub(r'(?<=\w)\.(?=\w)', '', result)

        # remove dots in form of abbreviations e.g. a.b.c.d
        result = re.sub(r"((?<=(\P{L}|^)\p{L})\.(?=\p{L}(\P{L}|$)))+", "", result)

        # normalize remaining symbols & whitespaces
        result = re.sub(r"(\p{Z}|\p{S}|\p{P})+", " ", result)

        # normalization: replace european texts with english ones
        result = result.replace("ä", "ae")
        result = result.replace("ö", "oe")
        result = result.replace("ü", "ue")
        result = result.replace("ß", "ss")
        result = result.replace("é", "e")

        return result


class _TransactionRegExpExtractor(BaseExtractor):
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

        if len(valid_accounts) > 1:
            logger.debug(f"Multiple valid accounts found: {valid_accounts}")
            return valid_accounts[0]
        elif len(valid_accounts) == 1:
            return valid_accounts[0]
        return ""

    def _extract_one_impl(self, entry: Transaction) -> str:
        return self.posting_filter_keep_one(entry.postings)


class TransactionCategoryAccountExtractor(_TransactionAccountExtractor):
    """Extract accounts for categorizing the transactions"""

    def __init__(self):
        regex_category_account = BeanbotConfig.get_global()["regex-category-account"]
        super().__init__(regex_category_account)


class TransactionCounterAccountExtractor(BaseExtractor):
    """Counter accounts are the ones that are not in the first position of the postings."""

    def _extract_one_impl(self, entry: Directive) -> str:
        if len(entry.postings) < 2:
            return ""
        elif len(entry.postings) > 2:
            return ", ".join([p.account for p in entry.postings[1:]])
        return entry.postings[1].account


class TransactionRecordSourceAccountExtractor(_TransactionAccountExtractor):
    """Extract accounts where the transaction records are generated"""

    def __init__(self):
        source_account_regex = BeanbotConfig.get_global()["regex-source-account"]
        super().__init__(source_account_regex)


class TransactionDateExtractor(BaseExtractor):
    def _date_to_int(self, dt: date) -> int:
        return dt.year * 10000 + dt.month * 100 + dt.day

    def _extract_one_impl(self, entry: Transaction) -> int:
        return self._date_to_int(entry.date)


class _TransactionAmountExtractor(_TransactionRegExpExtractor):
    """Class for extracting account information from transactions"""

    _EXTRACT_SIGN = False

    def _posting_amount_keep_one(self, postings: Postings) -> float:
        try:
            for p in postings:
                if self.match(p.account):
                    if self._EXTRACT_SIGN:
                        return np.sign(p.units.number)
                    return p.units.number
        except:  # noqa
            return 0.0

    def _extract_one_impl(self, entry: Transaction) -> float:
        return self._posting_amount_keep_one(entry.postings)


class TransactionCategoryAmountSignExtractor(_TransactionAmountExtractor):
    _EXTRACT_SIGN = True

    def __init__(self):
        regex_category_account = BeanbotConfig.get_global()["regex-category-account"]
        super().__init__(regex_category_account)


class TransactionRecordSourceAmountSignExtractor(_TransactionAmountExtractor):
    _EXTRACT_SIGN = True

    def __init__(self):
        regex_record_source_account = BeanbotConfig.get_global()["regex-source-account"]
        super().__init__(regex_record_source_account)


class TransactionCategoryAmountExtractor(_TransactionAmountExtractor):
    def __init__(self):
        regex_category_account = BeanbotConfig.get_global()["regex-category-account"]
        super().__init__(regex_category_account)


class TransactionRecordSourceAmountExtractor(_TransactionAmountExtractor):
    def __init__(self):
        regex_record_source_account = BeanbotConfig.get_global()["regex-source-account"]
        super().__init__(regex_record_source_account)


class TransactionCounterAmountExtractor(BaseExtractor):
    def _extract_one_impl(self, entry: Directive) -> float:
        if not isinstance(entry, Transaction | directive.MutableTransaction):
            return 0.0
        elif len(entry.postings) < 2:
            return 0.0
        elif len(entry.postings) > 2:
            return sum([p.units.number for p in entry.postings[1:]])
        return entry.postings[1].units.number


class TransactionSourceFilenameExtractor(BaseExtractor):
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions"""

    def _extract_one_impl(self, entry: Transaction) -> str:
        try:
            filename = entry.meta["filename"]
        except KeyError:
            filename = ""

        return filename


class TransactionNewPredictionsExtractor(BaseExtractor):
    """Extract the classifier state from the transaction"""

    def _extract_one_impl(self, entry: Transaction) -> bool:
        if entry.tags is None:
            return False
        for tag in entry.tags:
            if tag.startswith("_new"):
                return True
        return False


class TransactionTagsExtractor(BaseExtractor):
    def _extract_one_impl(self, entry: Transaction) -> str:
        return ", ".join(entry.tags)


################# Extractor for Balances #################


class BalanceRecordSourceAccountExtractor(BaseExtractor):
    """Extract account where the balance records are generated"""

    def _extract_one_impl(self, entry: data.Balance) -> str:
        return entry.account


class BalanceSourceFilenameExtractor(BaseExtractor):
    """Extract account where the balance records are generated"""

    def _extract_one_impl(self, entry: data.Balance) -> str:
        try:
            filename = entry.meta["filename"]
        except KeyError:
            filename = ""

        return filename


################# Extractor for Open directives #################


class OpenCategoryAccountExtractor(BaseExtractor):
    """Extract account where the balance records are generated"""

    def _extract_one_impl(self, entry: data.Open) -> str:
        return entry.account


################# Extractor for Directives #################


class BaseDirectiveExtractor(BaseExtractor):
    """Abstract Extractor class, extract a list of string descriptions from a list of Transactions.
    This class with automatically call the extractor based on the type of the entry.
    The user should not instantiate this class directly, but use the subclasses instead.
    """

    def __init__(self):
        self._extractor_cache = {}

    def extract_one(self, entry: Directive) -> str:
        """Extract a list of string descriptions from a list of Entries"""
        assert (
            self.__class__.__name__ != "BaseDirectiveExtractor"
        ), "Calling from base class is not allowed"

        entry_class_name = (
            entry.__class__.__name__
        )  # Class name of the entry, e.g. Transaction / Balance / Open ...
        if entry_class_name.startswith("Mutable"):
            entry_class_name = entry_class_name.replace("Mutable", "", 1)

        extractor_type = self.__class__.__name__  # Class name of the extractor, e.g. EntrySourceAccountExtractor / EntrySourceFilenameExtractor
        extractor_class = extractor_type.replace(
            "Directive", entry_class_name, 1
        )  # get the extractor class name to be used depending on the entry's and the extractor's class name

        if extractor_class not in self._extractor_cache:
            if extractor_class in globals():
                self._extractor_cache[extractor_class] = globals()[extractor_class]()
                print(f"[DEBUG] extractor class: {extractor_class} instantiated")
            else:
                print(f"[DEBUG] extractor class: {extractor_class} not found")
                self._extractor_cache[extractor_class] = None
                # breakpoint()

        extractor = self._extractor_cache[extractor_class]
        if extractor is None:
            return ""
        return extractor.extract_one(entry)


class DirectiveRecordSourceAccountExtractor(BaseDirectiveExtractor):
    pass


class DirectiveSourceFilenameExtractor(BaseDirectiveExtractor):
    pass


class DirectiveNewPredictionsExtractor(BaseDirectiveExtractor):
    pass


class DirectiveDescriptionExtractor(BaseDirectiveExtractor):
    pass


class DirectiveCategoryAccountExtractor(BaseDirectiveExtractor):
    pass


class DirectiveCategoryAmountExtractor(BaseDirectiveExtractor):
    pass


class DirectiveCounterAccountExtractor(BaseDirectiveExtractor):
    pass


class DirectiveCounterAmountExtractor(BaseDirectiveExtractor):
    pass


class DirectiveTagsExtractor(BaseDirectiveExtractor):
    pass


class DirectiveRecordSourceAmountExtractor(BaseDirectiveExtractor):
    pass
