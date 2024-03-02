#!/usr/bin/env python3

from dataclasses import dataclass
from typing import Dict, List, Optional

from beanbot.common.types import Transactions
from beancount.core.data import Entries


@dataclass
class Dataset(object):
    """Class for storing a dataset

    Args:
        gt_transactions (Transactions): Ground truth transactions
        options_map (Dict): Options map returned by the dataloader
        input_transactions (Transactions): Input transactions with removed entries (to be predicted)
        removed_indices (List[int]): Indices for the removed entries
        pred_transactions (Optional[Transactions], optional): Predicted transactions. Defaults to None.
        all_entries (Optional[Entries], optional): All entries returned by the loader. Defaults to None.
    """

    gt_transactions: Transactions
    options_map: Dict
    input_transactions: Transactions
    removed_indices: List[int]
    pred_transactions: Optional[Transactions] = None
    all_entries: Optional[Entries] = None
