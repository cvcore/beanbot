#!/usr/bin/env python3

"""This module implements the meta classifier that uses multiple methods to classify the transaction.

It first tries to identify category with simple mapping unambiguously learned from historical data.
If it fails, will fallback to decision tree and mark the transaction as uncertain."""

from typing import Dict

from beanbot.classifier.abstract_transaction_classifier import (
    AbstractTransactionClassifier,
)
from beanbot.classifier.decision_tree_transaction_classifier import (
    DecisionTreeTransactionClassifier,
)
from beanbot.classifier.mapping_transaction_classifier import (
    MappingTransactionClassifier,
)
from beanbot.common.types import Transactions


class MetaTransactionClassifier(AbstractTransactionClassifier):
    def __init__(self, options_map: Dict):
        super().__init__(options_map)
        self._dt_classifier = DecisionTreeTransactionClassifier(options_map)
        self._map_classifier = MappingTransactionClassifier(options_map)

    def train(self, transactions: Transactions):
        """Train the classifier using only balanced transactions"""
        self._map_classifier.train(transactions)
        self._dt_classifier.train(transactions)

    def predict(self, transactions: Transactions) -> Transactions:
        """Perform prediction by balanding the transactions with predicted postings"""
        pred_transactions = self._map_classifier.predict(transactions)
        pred_transactions = self._dt_classifier.predict(pred_transactions)

        return pred_transactions
