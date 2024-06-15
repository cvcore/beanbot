#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict
from sklearn.ensemble import RandomForestClassifier

from beanbot.classifier.abstract_transaction_classifier import (
    AbstractTransactionClassifier,
)
from beanbot.vectorizer.bag_of_words_vectorizer import BagOfWordVectorizer
from beanbot.common.types import Transactions
from beanbot.ops.filter import BalancedTransactionFilter


class DecisionTreeTransactionClassifier(AbstractTransactionClassifier):
    """Perform transaction classification with decision tree"""

    ADD_TAG = "_new_dt"

    def __init__(self, options_map: Dict):
        super().__init__(options_map, add_tags={self.ADD_TAG})
        # self._classifier = DecisionTreeClassifier()
        # self._classifier = KNeighborsClassifier(n_neighbors=1)
        # self._classifier = MLPClassifier(max_iter=1000, hidden_layer_sizes=(1000, 100), verbose=True)
        self._classifier = RandomForestClassifier(
            n_estimators=200, max_depth=20, random_state=1, verbose=True
        )
        self._vectorizer = BagOfWordVectorizer()
        self._gt_label = None

    def train(self, transactions: Transactions):
        """Train the classifier with labelled transactions"""

        # TODO: in preprocessing step, check duplicate transaction
        transactions_train = BalancedTransactionFilter(self._options_map).filter(
            transactions
        )

        self._vectorizer.fit_dictionary(transactions)
        trans_train_vec = self._vectorizer.vectorize(transactions_train)

        learnable_indices = trans_train_vec.learnable.nonzero()[0]
        train_input = trans_train_vec.vec[learnable_indices]
        train_label = trans_train_vec.label[learnable_indices]

        self._classifier.fit(train_input, train_label)

        # for debugging
        # self._gt_label = self._vectorizer.vectorize(transactions).label

    def predict(self, transactions: Transactions) -> Transactions:
        """Perform prediction by balanding the transactions with predicted postings"""

        trans_vec = self._vectorizer.vectorize(transactions)
        pred_label = self._classifier.predict(trans_vec.vec)
        pred_accounts = self._vectorizer.devectorize_label(pred_label)

        transactions = self.add_postings_auto_balance(transactions, pred_accounts)
        return transactions
