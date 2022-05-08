#!/usr/bin/env python3

"""Module containing various metrics"""

from abc import ABC, abstractclassmethod, abstractmethod
import numpy as np
from beanbot.tests.dataset import Dataset
from beanbot.ops.extractor import TransactionCategoryAccountExtractor, TransactionDescriptionExtractor

class AbstractMetrics(ABC):

    @classmethod
    def calculate(cls, dataset: Dataset):
        """Calculate metrics on `dataset`. Assumes all fields have valid value."""
        for attr in dir(dataset):
            if callable(getattr(dataset, attr)) or attr.startswith("__"):
                continue
            assert getattr(dataset, attr) is not None, f"Dataset incomplete. Missing field {attr}"

        print(f"Calculating metrics on {len(dataset.removed_indices)} transactions.")
        return cls._metrics_impl(dataset)

    @abstractclassmethod
    def _metrics_impl(cls, dataset: Dataset):
        raise NotImplementedError()


class PrecisionScore(AbstractMetrics):
    """Calculate the precision score: TP / (TP + FP)"""

    @classmethod
    def _metrics_impl(cls, dataset: Dataset) -> float:
        account_extractor = TransactionCategoryAccountExtractor()
        pred_accounts = account_extractor.extract(dataset.pred_transactions)
        gt_accounts = account_extractor.extract(dataset.gt_transactions)

        n_transactions = len(pred_accounts)
        assert n_transactions == len(gt_accounts)

        masks = np.zeros(n_transactions)
        masks[dataset.removed_indices] = 1.
        good_predictions = np.array([(gt == pred) for (gt, pred) in zip(gt_accounts, pred_accounts)])
        idx_bad_predictions = (1 - good_predictions).nonzero()[0]

        if len(idx_bad_predictions) > 0:
            print(f"Bad cases discovered!\nDate\tDescription\tPrediction\tGroundtruth\tTags")
            descriptions = TransactionDescriptionExtractor().extract(dataset.input_transactions)
        replace_empty = lambda s: '(empty)' if s == '' else s
        for idx in idx_bad_predictions:
            print(f"{replace_empty(dataset.pred_transactions[idx].date)}\t{replace_empty(descriptions[idx])}\t{replace_empty(pred_accounts[idx])}\t{replace_empty(gt_accounts[idx])}\t{replace_empty(dataset.pred_transactions[idx].tags)}")


        # Only calculate matrix on masked elements
        n_good_predictions = np.sum(good_predictions * masks)
        n_predictions = np.sum(masks)
        precision = float(n_good_predictions) / n_predictions

        return precision
