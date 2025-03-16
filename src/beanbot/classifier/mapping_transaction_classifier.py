#!/usr/bin/env python
# coding=utf-8

from typing import Dict

from beanbot.classifier.abstract_transaction_classifier import (
    AbstractTransactionClassifier,
)
from beanbot.common.types import Transactions
from beanbot.ops.extractor import (
    TransactionCategoryAccountExtractor,
    TransactionDescriptionExtractor,
)
from beanbot.ops.filter import BalancedTransactionFilter
from beancount.core import interpolate
from beanbot.helper import logger


class MappingTransactionClassifier(AbstractTransactionClassifier):
    """Classify transaction with simple mapping.

    This class only predicts unbalanced transactions that are previously seen and do not have any ambiguity."""

    ADD_TAG = "_new_map"

    def __init__(self, options_map: Dict):
        super().__init__(options_map, add_tags={self.ADD_TAG})

        self._desc_to_cat = {}
        self._desc_ignore = set()
        self._desc_extractor = TransactionDescriptionExtractor()
        self._cat_extractor = TransactionCategoryAccountExtractor()

    def train(self, transactions: Transactions):
        """Train the classifier using only balanced transactions"""
        transactions_train = BalancedTransactionFilter(self._options_map).filter(
            transactions
        )

        descriptions = self._desc_extractor.extract(transactions_train)
        categories = self._cat_extractor.extract(transactions_train)

        for desc, cat in zip(descriptions, categories):
            if desc in self._desc_ignore or desc == "" or cat == "":
                continue

            if desc in self._desc_to_cat:
                if cat != self._desc_to_cat[desc]:
                    # debug
                    logger.debug(
                        f"Dropping ambiguous case: Desc: {desc} Cat: {cat} PrevCat: {self._desc_to_cat[desc]}"
                    )

                    self._desc_ignore.add(desc)
                    self._desc_to_cat.pop(desc)
            else:
                self._desc_to_cat[desc] = cat

    def predict(self, transactions: Transactions) -> Transactions:
        """Perform prediction by balancing the transactions with predicted postings"""

        descriptions = self._desc_extractor.extract(transactions)
        cat_account_pred = []

        for txn, desc in zip(transactions, descriptions):
            residual = interpolate.compute_residual(txn.postings)
            tolerances = interpolate.infer_tolerances(txn.postings, self._options_map)

            if residual.is_small(tolerances):
                pred_cat = None
            else:
                try:
                    pred_cat = self._desc_to_cat[desc]
                except KeyError:
                    pred_cat = None

            cat_account_pred.append(pred_cat)

        transactions = self.add_postings_auto_balance(transactions, cat_account_pred)

        return transactions
