#!/usr/bin/env python3
# coding=utf-8

"""Module for loading test cases for the classifier."""

from copy import deepcopy
from pathlib import Path
from typing import List, Tuple, Iterable
from collections import abc
import random
from beancount.loader import load_file
from beancount.core.data import Transaction

from beanbot.common.types import Transactions
from beanbot.ops.extractor import TransactionCategoryAccountExtractor
from beanbot.tests.dataset import Dataset
from beanbot.ops import filter



class DataLoader():

    def __init__(self, filename, n_test_cases: int=5, n_removal: int=6, init_rand_seed: int=0) -> None:

        super().__init__()

        self._filename = filename
        self._n_test_cases = n_test_cases
        self._n_removal = n_removal
        self._init_rand_seed = init_rand_seed

    def _load_test_file(self) -> Tuple:

        test_file = self._filename
        entries, errors, options_map = load_file(str(test_file))

        return (entries, errors, options_map)

    def _load_transactions(self) -> Transactions:
        entries, errors, options_map = self._load_test_file()
        transactions = filter.TransactionFilter().filter(entries)

        return transactions, errors, options_map

    def _remove_entries_rand(self, transactions: Transactions, random_seed: int) -> Tuple[Transactions, List[int]]:
        """Remove randomly the ground truth label from `n_removal` entries """

        random.seed(random_seed)

        category_accounts = TransactionCategoryAccountExtractor().extract(transactions)
        valid_labels = [(idx, account) for idx, account in enumerate(category_accounts) if account != '']
        n_valid_labels = len(valid_labels)

        assert n_valid_labels >= self._n_removal, f"You cannot remove more than {n_valid_labels} entries from the ground truth transaction list!"

        transactions = deepcopy(transactions)
        removed_labels = random.sample(valid_labels, self._n_removal)
        removed_indices = [idx for idx, _ in removed_labels]
        for idx_transaction, account_to_remove in removed_labels:
            account_found = False
            for idx_posting, posting in enumerate(transactions[idx_transaction].postings):
                if posting.account == account_to_remove:
                    transactions[idx_transaction].postings.pop(idx_posting)
                    account_found = True
                    break
            assert account_found, ("Category account not found!")

        return transactions, removed_indices

    def load(self) -> Iterable[Dataset]:
        """Get test case. Format: Ground truth transactions, Test input, Indices with label removed"""

        for rand_seed in range(self._init_rand_seed, self._init_rand_seed+self._n_test_cases):
            transactions_gt, _, options_map = self._load_transactions()
            transactions_input, removed_indices = self._remove_entries_rand(transactions_gt, rand_seed)
            yield Dataset(
                transactions_gt, options_map, transactions_input, None, removed_indices
            )
