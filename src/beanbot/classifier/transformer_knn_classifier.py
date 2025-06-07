#!/usr/bin/env python
# -*- coding: utf-8 -*-


from beancount.core.data import Account

from beanbot.classifier.abstract_transaction_classifier import (
    AbstractTransactionClassifier,
)
from beanbot.model.transformer_knn_classifier import TransformerKNNClassifier
from beanbot.ops.extractor import (
    TransactionDescriptionExtractor,
    TransactionCategoryAccountExtractor,
)
from beanbot.common.types import Transactions
from beanbot.ops.filter import BalancedTransactionFilter


class TransformerKNNAccountClassifier(AbstractTransactionClassifier):
    """Perform transaction classification with decision tree"""

    ADD_TAG = "_new_dt"

    def __init__(self, options_map: dict):
        super().__init__(options_map, add_tags={self.ADD_TAG})
        self._text_extractor = TransactionDescriptionExtractor()
        self._account_extractor = TransactionCategoryAccountExtractor()
        self._classifier = TransformerKNNClassifier()

    @property
    def is_fitted(self) -> bool:
        return self._classifier.is_fitted

    def load_model(self, model_path: str):
        self._classifier = TransformerKNNClassifier.load(model_path)

    def save_model(self, model_path: str):
        self._classifier.save(model_path)

    def train(self, transactions: Transactions):
        """Train the classifier with labelled transactions"""

        # TODO: in preprocessing step, check duplicate transaction
        transactions_train = BalancedTransactionFilter(self._options_map).filter(
            transactions
        )

        texts = self._text_extractor.extract(transactions_train)
        labels = self._account_extractor.extract(transactions_train)
        texts, labels = zip(*[(t, a) for t, a in zip(texts, labels) if a != ""])

        self._classifier.fit(list(texts), list(labels))

    def update(self, transactions: Transactions):
        transactions_update = BalancedTransactionFilter(self._options_map).filter(
            transactions
        )

        texts = self._text_extractor.extract(transactions_update)
        labels = self._account_extractor.extract(transactions_update)
        texts, labels = zip(*[(t, a) for t, a in zip(texts, labels) if a != ""])

        self._classifier.update(texts, labels)

    def predict(self, transactions: Transactions) -> Transactions:
        raise NotImplementedError(
            "TransformerKNNAccountClassifier does not support predicting transactions"
        )

    def predict_accounts(
        self, transactions: Transactions
    ) -> list[tuple[Account, float]]:
        """Perform prediction by balanding the transactions with predicted postings"""

        texts = self._text_extractor.extract(transactions)
        return self._classifier.predict_batch(texts)
