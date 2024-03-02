from datetime import date
from sqlite3 import adapt
from typing import Tuple
import pytest
from beanbot.common.configs import BeanbotConfig
import pandas as pd

from beanbot.data import directive
from beanbot.data.adapter import OpenedAccount, StreamlitDataEditorAdapter
from beanbot.data.entries import MutableEntriesView
import streamlit as st
from beanbot.data.adapter import ColumnConfig

from beanbot.ops import extractor
from beanbot.ops.conditions import is_predicted
from beanbot.ops.filter import PredictedTransactionFilter
from beanbot.ui.factory import BeanbotDataEditorFactory, _setter_fn_new_prediction, _setter_fn_pred_account
import logging

logger = logging.getLogger(__name__)


# TODO: put this to argument
TEST_FILE = "/Users/core/Development/Finance/beanbot/tests/data/main.bean"
# TEST_FILE = "/Users/core/Library/Mobile Documents/com~apple~CloudDocs/Beancount/main.bean"

@st.cache_resource
def get_entries(file: str) -> MutableEntriesView:
    print(f"Loading entries from {file}")
    global_config = BeanbotConfig.get_global()
    global_config.parse_file(file)
    entries = MutableEntriesView.load_from_file(file)
    return entries


@st.cache_resource
def get_editor_args(_entries) -> Tuple:
    print(f"Creating editor from entries")
    editor = BeanbotDataEditorFactory(_entries)
    return editor._adapter.get_dataframe(), editor._adapter.get_data_editor_kwargs()


@st.cache_resource
def get_adapter(_entries: MutableEntriesView) -> StreamlitDataEditorAdapter:
    print("Creating adapter from entries")

    ext_new_predictions = extractor.DirectiveNewPredictionsExtractor()
    ext_descriptions = extractor.DirectiveDescriptionExtractor()
    ext_source_account = extractor.DirectiveRecordSourceAccountExtractor()
    ext_cat_account = extractor.DirectiveCategoryAccountExtractor()
    ext_cat_amount = extractor.DirectiveCategoryAmountExtractor()

    _entries.attach_extractors({
        "new_predictions": ext_new_predictions,
        "descriptions": ext_descriptions,
        "source_account": ext_source_account,
        "category_account": ext_cat_account,
        "category_amount": ext_cat_amount,
    })

    return StreamlitDataEditorAdapter(_entries, [
        ColumnConfig("date", "Date", date, "The date of the transaction."),
        ColumnConfig("category_account", "Category", OpenedAccount, "The transaction category.", linked_entry_field="postings", editable=True, entry_setter_fn=_setter_fn_pred_account),
        ColumnConfig("category_amount", "Amount", float, "The transaction amount."),
        ColumnConfig("payee", "Payee", str, "The transaction payee"),
        ColumnConfig("narration", "Narration", str, "The transaction narration."),
        ColumnConfig("new_predictions", "New Prediction", bool, "Is the transaction category newly predicted?", linked_entry_field="tags", editable=True, entry_setter_fn=_setter_fn_new_prediction),
        ColumnConfig("source_account", "Booked On", str, "Which account is the tranaction booked on?"),
    ])


def get_dataframe(_adapter) -> pd.DataFrame:
    print("Getting dataframe from adapter")
    return _adapter.get_dataframe()



def is_new_prediction(entry: directive.MutableTransaction) -> bool:
    return isinstance(entry, directive.MutableTransaction) and is_predicted(entry)



# streamlit use wide mode
st.set_page_config(layout="wide")
st.header("🫘 Beanbot Data Editor")
st.text("The following data are imported from the transaction file, please check their correctness and make changes if necessary.")

entries = get_entries(TEST_FILE)
# entries = entries_orig.filter(is_new_prediction)
adapter = get_adapter(entries)
dataframe = get_dataframe(adapter)

# Show the table editor
st.data_editor(dataframe, **adapter.get_data_editor_kwargs())

# Button for confirming the changes
if st.button("Confim Changes"):
    adapter.commit_changes()
    # st.session_state[adapter._editor_key] = {}
    # print(st.session_state)
