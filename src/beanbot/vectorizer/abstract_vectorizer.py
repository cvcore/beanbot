#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from typing import Iterable
from beanbot.common.types import Transactions, VectorizedTransactions
from beancount.core.data import Account


class AbstractVectorizer(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def vectorize(self, transactions: Transactions) -> VectorizedTransactions:
        """Vectorize transactions into a vector and a label used to train a classifier"""
        pass

    @abstractmethod
    def devectorize_label(self, label: Iterable[int]) -> Account:
        """Query the corresponding account with vector labels"""
        pass

    # @abstractmethod
    # def devectorize_vec(self, vec: np.ndarray) -> str:
    #     """Devectorize the tokenized vector into the original string description"""
    #     # Note: normally no need to implement this method.
    #     pass
