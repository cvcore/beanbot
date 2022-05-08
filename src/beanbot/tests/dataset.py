#!/usr/bin/env python3

class Dataset(object):

    def __init__(self, gt_transactions, options_map, input_transactions, pred_transactions, removed_indices) -> None:

        self.gt_transactions = gt_transactions
        self.options_map = options_map
        self.input_transactions = input_transactions
        self.pred_transactions = pred_transactions
        self.removed_indices = removed_indices
