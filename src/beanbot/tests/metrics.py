#!/usr/bin/env python3

"""Module containing various metrics"""

from abc import ABC, abstractclassmethod
import numpy as np
from beanbot.tests.dataset import Dataset
from beanbot.ops.extractor import (
    TransactionCategoryAccountExtractor,
    TransactionDescriptionExtractor,
)

from pandas import DataFrame


class AbstractMetrics(ABC):
    @classmethod
    def calculate(cls, dataset: Dataset):
        """Calculate metrics on `dataset`. Assumes all fields have valid value."""
        for attr in dir(dataset):
            if callable(getattr(dataset, attr)) or attr.startswith("__"):
                continue
            assert (
                getattr(dataset, attr) is not None
            ), f"Dataset incomplete. Missing field {attr}"

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
        masks[dataset.removed_indices] = 1.0
        good_predictions = np.array(
            [(gt == pred) for (gt, pred) in zip(gt_accounts, pred_accounts)]
        )
        idx_bad_predictions = (1 - good_predictions).nonzero()[0]

        # Print bad cases
        if len(idx_bad_predictions) > 0:
            print("Bad cases discovered!")
            descriptions = TransactionDescriptionExtractor().extract(
                dataset.input_transactions
            )

            replace_empty = lambda s: "(empty)" if s == "" else s
            transactions_table = {
                "date": [replace_empty(t.date) for t in dataset.pred_transactions],
                "description": [
                    replace_empty(d.replace("\n", "").replace("\r", ""))
                    for d in descriptions
                ],
                "prediction": [replace_empty(a) for a in pred_accounts],
                "groundtruth": [replace_empty(a) for a in gt_accounts],
                "tags": [replace_empty(t.tags) for t in dataset.pred_transactions],
                "is_bad": [i in idx_bad_predictions for i in range(n_transactions)],
            }

            transactions_df = DataFrame(transactions_table)
            transactions_df.to_csv("bad_cases.csv")

            transactions_bad = transactions_df[transactions_df.is_bad == True]  # noqa: E712
            print(transactions_bad)

        # Only calculate matrix on masked elements
        n_good_predictions = np.sum(good_predictions * masks)
        n_predictions = np.sum(masks)
        precision = float(n_good_predictions) / n_predictions

        return precision
