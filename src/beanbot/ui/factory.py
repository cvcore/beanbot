import datetime
from typing import Dict, OrderedDict
import streamlit as st

from beanbot.data.adapter import StreamlitDataEditorAdapter, ColumnConfig, OpenedAccount
from beanbot.data.entries import BeanBotEntries
from beanbot.ops import extractor


class BeanbotDataEditorFactory:
    def __init__(self, entry_file: str) -> None:
        self._bb_entries = BeanBotEntries.load_from_file(entry_file)

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
                ColumnConfig("new_predictions", "New Prediction", bool, "Is the transaction category newly predicted?"),
                ColumnConfig("source_account", "Booked On", str, "Which account is the tranaction booked on?"),
            ]
        )

    # def _get_column_configs(self) -> OrderedDict:
    #     return OrderedDict(
    #         [
    #             ("date", st.column_config.DateColumn("Date", help="The date of the transaction.")),
    #             ("category_account", st.column_config.SelectboxColumn("Category", help="The expense category.", options=self._bb_entries.get_opened_accounts())),
    #             ("category_amount", st.column_config.NumberColumn("Amount", help="The amount of the transaction.")),
    #             ("descriptions", st.column_config.TextColumn("Description", help="The description of the transaction.")),
    #             ("payee", st.column_config.TextColumn("Payee", help="The payee of the transaction.")),
    #             ("narration", st.column_config.TextColumn("Narration", help="The narration of the transaction.")),
    #             ("new_predictions", st.column_config.CheckboxColumn("New Prediction", help="Whether the transaction is a new prediction.")),
    #             ("source_account", st.column_config.SelectboxColumn("Source Account", help="The source account of the transaction.", options=self._bb_entries.get_opened_accounts())),
    #         ]
    #     )


    def get_ui(self) -> st.data_editor:
        return self._adapter.get_data_editor()
