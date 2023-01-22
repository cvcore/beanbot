#!/usr/bin/env python3
# coding=utf-8

"""Module for loading test cases for the classifier."""

from copy import deepcopy
from pathlib import Path
from typing import List, Tuple, Iterable, Optional
from collections import abc
import random
from beancount.loader import load_file
from beancount.core.data import Transaction

from beanbot.common.types import Transactions
from beanbot.ops.extractor import TransactionCategoryAccountExtractor
from beanbot.tests.dataset import Dataset
from beanbot.ops import filter


class DataLoader():

    def __init__(self, filename, ratio_removal: float=6, remove_from_tail=True, init_rand_seed: Optional[int]=None) -> None:
        """Build a DataLoader object. This object can be used to load test cases for the classifier.

        Arguments:
            filename {str} -- The filename of the test file.
            ratio_removal {float} -- The procent of transactions to remove from the test file. Range from 0 to 1.
            remove_from_tail {bool} -- Whether to remove the transactions from the tail of the file.
            init_rand_seed {Optional, int} -- The random seed to use for the random removal of transactions.
        """

        super().__init__()

        self._filename = filename
        assert ratio_removal > 0 and ratio_removal < 1, "Ratio removal must be between 0 and 1"
        self._ratio_removal = ratio_removal
        self._init_rand_seed = init_rand_seed
        self._remove_from_tail = remove_from_tail

    def _load_test_file(self) -> Tuple:

        test_file = self._filename
        entries, errors, options_map = load_file(str(test_file))
        self._safeguard_date_ascending(entries) # Some functionalities rely on the date being ascending. Make sure it is.

        return (entries, errors, options_map)

    def _load_transactions(self) -> Transactions:
        entries, errors, options_map = self._load_test_file()
        transactions = filter.TransactionFilter().filter(entries)

        return transactions, errors, options_map

    def _remove_entries_tail(self, transactions: Transactions) -> Tuple[Transactions, List[int]]:
        """Remove the ground truth label from the `n_removal` last entries """

        n_removal = int(self._ratio_removal * len(transactions))
        indices_to_remove = list(range(len(transactions)-n_removal, len(transactions)))

        return self._remove_entries(transactions, indices_to_remove)


    def _remove_entries_rand(self, transactions: Transactions, random_seed: int) -> Tuple[Transactions, List[int]]:
        """Remove randomly the ground truth label from `n_removal` entries """

        random.seed(random_seed)
        n_removal = int(self._ratio_removal * len(transactions))
        indices_to_remove = random.sample(range(len(transactions)), n_removal)

        return self._remove_entries(transactions, indices_to_remove)

    def _remove_entries(self, transactions: Transactions, indices: List[int]) -> Tuple[Transactions, List[int]]:
        """Remove the ground truth label from entries with indices in `indices`.

        Returns:
            transactions: The transactions with the removed labels,
            removed_incides_successful: The indices of the entries that were successfully removed.
        """

        category_accounts = TransactionCategoryAccountExtractor().extract(transactions)
        valid_labels = [(idx, account) for idx, account in enumerate(category_accounts) if account != '']
        n_valid_labels = len(valid_labels)

        assert n_valid_labels >= len(indices), f"You cannot remove more than {n_valid_labels} entries from the ground truth transaction list!"

        transactions = deepcopy(transactions)
        removed_labels = zip(indices, [category_accounts[idx] for idx in indices])
        removed_indices_successful = []
        for idx_transaction, account_to_remove in removed_labels:
            # account_found = False
            for idx_posting, posting in enumerate(transactions[idx_transaction].postings):
                if posting.account == account_to_remove:
                    transactions[idx_transaction].postings.pop(idx_posting)
                    # account_found = True
                    removed_indices_successful.append(idx_transaction)
                    break
            # assert account_found, ("Category account not found!")

        return transactions, removed_indices_successful

    def load(self) -> Iterable[Dataset]:
        """Get test case. Format: Ground truth transactions, Test input, Indices with label removed"""

        transactions_gt, _, options_map = self._load_transactions()
        if self._remove_from_tail:
            transactions_input, removed_indices = self._remove_entries_tail(transactions_gt)
        else:
            assert self._init_rand_seed is not None, "You must provide a random seed for the random removal of transactions!"
            transactions_input, removed_indices = self._remove_entries_rand(transactions_gt, self._init_rand_seed)

        yield Dataset(
            transactions_gt, options_map, transactions_input, None, removed_indices
        )

    def _safeguard_date_ascending(self, entries):
        assert all([entries[i].date <= entries[i+1].date for i in range(len(entries)-1)]), "Dates are not ascending!"
