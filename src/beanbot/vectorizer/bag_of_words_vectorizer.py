#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Callable, Iterable

import numpy as np
from beancount.core.data import Transaction, Account
from beanbot.vectorizer.abstract_vectorizer import AbstractVectorizer, VectorizedTransactions
from beanbot.ops.extractor import TransactionCategoryAccountExtractor, TransactionDescriptionExtractor, TransactionDateExtractor, TransactionRecordSourceAmountExtractor
from beanbot.ops.hashing import BiDirectionalHash
from beanbot.common.types import Postings, Transactions
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer


class BagOfWordVectorizer(AbstractVectorizer):
    """Vectorize Transactions with the Bag of Words (BoW) approach for the string description and a simple integer counter for converting the account name into integer.

    Note: This class needs be trained first with text corpus containing all possible words with the `fit_dictionary()` method before use"""

    def __init__(self, extract_date=True, extract_amount=True):

        super().__init__()

        self._cat_account_extractor = TransactionCategoryAccountExtractor()
        self._date_extractor = TransactionDateExtractor() if extract_date else None
        self._amount_extractor = TransactionRecordSourceAmountExtractor() if extract_amount else None
        self._trans_desc_extractor = TransactionDescriptionExtractor()

        # self._vectorizer = CountVectorizer(ngram_range=(3, 3), analyzer='char')
        self._vectorizer = TfidfVectorizer(ngram_range=(3, 5), analyzer='char')
        self._bd_hash = BiDirectionalHash()

        self._is_trained = False

    def vectorize(self, transactions: Transactions) -> VectorizedTransactions:

        assert self._is_trained, "You need to train the CountVectorizer first with the `fit_dictionary` method!"
        learnable_mask = np.ones((len(transactions,)), dtype=bool)

        trans_desc = self._trans_desc_extractor.extract(transactions)
        trans_desc_vec = self._vectorizer.transform(trans_desc).toarray()
        # If a text corpus contains no word in the dictionary, the vectorizer will return an all-zero vector. We mark this as not learnable
        learnable_mask &= (trans_desc_vec.sum(-1) != 0)

        # if self._date_extractor is not None:
        #     date_vec = np.array(self._date_extractor.extract(transactions))[:, None]
        #     trans_desc_vec = np.concatenate([trans_desc_vec, date_vec], axis=-1)
        # if self._amount_extractor is not None:
        #     amount_vec = np.array(self._amount_extractor.extract(transactions))[:, None]
        #     trans_desc_vec = np.concatenate([trans_desc_vec, amount_vec], axis=-1)
        #     learnable_mask &= (amount_vec[:, 0] != 0.)

        cat_accounts = self._cat_account_extractor.extract(transactions)
        cat_accounts_ind = self._bd_hash.hash(cat_accounts)
        learnable_mask &= (cat_accounts_ind != 0)

        return VectorizedTransactions(trans_desc_vec, cat_accounts_ind, learnable_mask)

    def devectorize_label(self, label: Iterable[int]) -> Account:

        return self._bd_hash.dehash(label)

    def fit_dictionary(self, transactions: Transactions):

        self._vectorizer.fit(
            self._trans_desc_extractor.extract(transactions)
        )

        self._is_trained = True
