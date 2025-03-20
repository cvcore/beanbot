import datetime
import logging
from typing import List
from beanbot.common.configs import BeanbotConfig
import re

from beanbot.data.adapter import StreamlitDataEditorAdapter, ColumnConfig, OpenedAccount
from beanbot.data.directive import MutablePosting
from beanbot.data.entries import MutableEntriesContainer
from beanbot.ops import extractor


def _setter_fn_new_prediction(old_tags: set, col_change: bool) -> frozenset:
    """Set the new prediction tags.
    Arguments:
        old_tags (set): the old tags
        col_change (bool): whether the column is changed
    Returns:
        new_tags (set): the new tags for the transaction"""
    if col_change:  # change to new
        tags = old_tags.union({"_new_"})
    else:
        tags = {t for t in old_tags if "_new_" not in t}
    return frozenset(tags)


def _setter_fn_pred_account(
    old_postings: List[MutablePosting], col_change: str
) -> List[MutablePosting]:
    """Set the new predicted account.
    Arguments:
        old_postings (List[MutablePosting]): the old postings
        col_change (str): the new account
    Returns:
        new_postings (List[MutablePosting]): the new postings for the transaction"""

    # dirty: refactor this part
    regex_category_account = BeanbotConfig.get_global()["regex-category-account"]
    regexp = re.compile(regex_category_account)

    for posting in old_postings:
        if regexp.match(posting.account):
            logging.debug(f"Set account from {posting.account} to {col_change}")
            posting.account = col_change
            return old_postings  # return by reference

    raise ValueError(
        f"Could not find a category account in the postings: {old_postings}"
    )


def _setter_fn_tags(old_tags: set, col_change: str) -> frozenset:
    return frozenset(set(col_change.split(",")))


class BeanbotDataEditorFactory:
    def __init__(self, entries: MutableEntriesContainer) -> None:
        self._bb_entries = entries

        ext_new_predictions = extractor.DirectiveNewPredictionsExtractor()
        ext_descriptions = extractor.DirectiveDescriptionExtractor()
        ext_source_account = extractor.DirectiveRecordSourceAccountExtractor()
        ext_cat_account = extractor.DirectiveCategoryAccountExtractor()
        ext_cat_amount = extractor.DirectiveCategoryAmountExtractor()

        self._bb_entries.attach_extractors(
            {
                "new_predictions": ext_new_predictions,
                "descriptions": ext_descriptions,
                "source_account": ext_source_account,
                "category_account": ext_cat_account,
                "category_amount": ext_cat_amount,
            }
        )

        self._adapter = StreamlitDataEditorAdapter(
            self._bb_entries,
            [
                ColumnConfig(
                    "date", "Date", datetime.date, "The date of the transaction."
                ),
                ColumnConfig(
                    "category_account",
                    "Category",
                    OpenedAccount,
                    "The transaction category.",
                    linked_entry_field="postings",
                    editable=True,
                    entry_setter_fn=_setter_fn_pred_account,
                ),
                ColumnConfig(
                    "category_amount", "Amount", float, "The transaction amount."
                ),
                ColumnConfig("payee", "Payee", str, "The transaction payee"),
                ColumnConfig(
                    "narration", "Narration", str, "The transaction narration."
                ),
                ColumnConfig(
                    "new_predictions",
                    "New Prediction",
                    bool,
                    "Is the transaction category newly predicted?",
                    linked_entry_field="tags",
                    editable=True,
                    entry_setter_fn=_setter_fn_new_prediction,
                ),
                ColumnConfig(
                    "source_account",
                    "Booked On",
                    str,
                    "Which account is the tranaction booked on?",
                ),
                ColumnConfig(
                    "entry_id",
                    "Entry ID",
                    str,
                    "The unique identifier of the transaction used for editing.",
                ),
            ],
        )
