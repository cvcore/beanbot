#!/usr/bin/env python
# coding=utf-8

from abc import ABCMeta, abstractmethod
from typing import Dict, List, Optional, Union

from pandas import options
from beancount.core import data
from beanbot.common.types import Transactions
from beanbot.vectorizer.abstract_vectorizer import AbstractVectorizer
from beanbot.ops.booking import add_postings_auto_balance


class AbstractTransactionClassifier(metaclass=ABCMeta):

    def __init__(self, options_map: Dict, add_tags: Optional[str]=None):
        self._options_map = options_map
        self._add_tags = add_tags

    @abstractmethod
    def train(self, transactions: Transactions):
        """Train the classifier using only balanced transactions"""
        return NotImplemented

    @abstractmethod
    def predict(self, transactions: Transactions) -> Transactions:
        """Perform prediction by balancing the transactions with predicted postings"""
        return NotImplemented

    def train_predict(self, transactions: Transactions) -> Transactions:
        self.train(transactions)
        return self.predict(transactions)

    def add_postings_auto_balance(self, transactions: List[data.Transaction], accounts: List[Union[data.Account, None]]) -> List[data.Transaction]:
        """Detect unbalanced transaction from `transactions` and insert automatically postings from `account` to balance the transaction.
        Balanced transactions will be ignored."""

        # TODO: dirty interface
        return add_postings_auto_balance(transactions, accounts, self._options_map, self._add_tags)
