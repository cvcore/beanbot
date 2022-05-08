#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List
from collections import namedtuple
from beancount.core.data import Transaction, Posting

Transactions = List[Transaction]

Postings = List[Posting]

VectorizedTransactions = namedtuple('VectorizedTransactions', [
    'vec', # np.ndarray (n_transaction, n_dim): int
    'label',  # np.ndarray (n_transaction,): int
    'learnable', # np.ndarray (n_transaction,): bool
])
