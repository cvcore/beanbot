import datetime
from typing import Dict, OrderedDict
import streamlit as st

from beanbot.data.adapter import StreamlitDataEditorAdapter, ColumnConfig, OpenedAccount
from beanbot.data.entries import BeanBotEntries
from beanbot.ops import extractor


def _setter_fn_new_prediction(old_tags: set, col_change: bool) -> set:
    if col_change:  # change to new
        tags = old_tags.union({"_new_"})
    else:
        tags = {t for t in old_tags if "_new_" not in t}
    return frozenset(tags)


class BeanbotDataEditorFactory:
    def __init__(self, entries: BeanBotEntries) -> None:
        self._bb_entries = entries

        ext_new_predictions = extractor.DirectiveNewPredictionsExtractor()
        ext_descriptions = extractor.DirectiveDescriptionExtractor()
        ext_source_account = extractor.DirectiveRecordSourceAccountExtractor()
        ext_cat_account = extractor.DirectiveCategoryAccountExtractor()
        ext_cat_amount = extractor.DirectiveCategoryAmountExtractor()

        self._bb_entries.attach_extractors({
            "new_predictions": ext_new_predictions,
            "descriptions": ext_descriptions,
            "source_account": ext_source_account,
            "category_account": ext_cat_account,
            "category_amount": ext_cat_amount,
        })

        self._adapter = StreamlitDataEditorAdapter(
            self._bb_entries, 
            [
                ColumnConfig("date", "Date", datetime.date, "The date of the transaction."),
                ColumnConfig("category_account", "Category", OpenedAccount, "The transaction category."),
                ColumnConfig("category_amount", "Amount", float, "The transaction amount."),
                ColumnConfig("payee", "Payee", str, "The transaction payee"),
                ColumnConfig("narration", "Narration", str, "The transaction narration."),
                ColumnConfig("new_predictions", "New Prediction", bool, "Is the transaction category newly predicted?", linked_entry_field="tags", editable=True, entry_setter_fn=_setter_fn_new_prediction),
                ColumnConfig("source_account", "Booked On", str, "Which account is the tranaction booked on?"),
            ]
        )

    def get_ui(self) -> st.data_editor:
        return self._adapter.get_data_editor()
