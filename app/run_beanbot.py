from datetime import date
import os
from typing import Dict, List, Optional
from uuid import UUID
from beanbot.common.configs import BeanbotConfig
import pandas as pd

from beanbot.data import directive
from beanbot.data.adapter import OpenedAccount, StreamlitDataEditorAdapter
from beanbot.data.entries import MutableEntriesContainer
import streamlit as st
from beanbot.data.adapter import ColumnConfig

from beanbot.ops import extractor
from beanbot.ops.conditions import is_predicted
from beanbot.ui.factory import _setter_fn_new_prediction, _setter_fn_pred_account
import logging

logger = logging.getLogger(__name__)


TEST_FILE = os.environ.get("BEANBOT_FILE", None)
assert TEST_FILE is not None, "BEANBOT_FILE environment variable must be set!"


@st.cache_resource
def get_entries_container(file: str) -> MutableEntriesContainer:
    print(f"Loading entries from {file}")
    global_config = BeanbotConfig.get_global()
    global_config.parse_file(file)
    entries_container = MutableEntriesContainer.load_from_file(file)
    return entries_container


# @st.cache_resource
# def get_editor_args(_entries) -> Tuple:
#     print(f"Creating editor from entries")
#     editor = BeanbotDataEditorFactory(_entries)
#     return editor._adapter.get_dataframe(), editor._adapter.get_data_editor_kwargs()


@st.cache_resource
def get_adapter(
    _entries: MutableEntriesContainer, filters: Optional[Dict] = None
) -> StreamlitDataEditorAdapter:
    print("Creating adapter from entries")

    ext_new_predictions = extractor.DirectiveNewPredictionsExtractor()
    ext_descriptions = extractor.DirectiveDescriptionExtractor()
    ext_source_account = extractor.DirectiveRecordSourceAccountExtractor()
    ext_cat_account = extractor.DirectiveCategoryAccountExtractor()
    ext_cat_amount = extractor.DirectiveCategoryAmountExtractor()

    _entries.attach_extractors(
        {
            "new_predictions": ext_new_predictions,
            "descriptions": ext_descriptions,
            "source_account": ext_source_account,
            "category_account": ext_cat_account,
            "category_amount": ext_cat_amount,
        }
    )

    return StreamlitDataEditorAdapter(
        _entries,
        [
            ColumnConfig("date", "Date", date, "The date of the transaction."),
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
                "category_account",
                "Category",
                OpenedAccount,
                "The transaction category.",
                linked_entry_field="postings",
                editable=True,
                entry_setter_fn=_setter_fn_pred_account,
            ),
            ColumnConfig("category_amount", "Amount", float, "The transaction amount."),
            ColumnConfig("payee", "Payee", str, "The transaction payee"),
            ColumnConfig("narration", "Narration", str, "The transaction narration."),
            ColumnConfig(
                "source_account",
                "Booked On",
                str,
                "Which account is the tranaction booked on?",
            ),
        ],
    )


@st.cache_resource
def get_dataframe(_adapter, filters: Optional[Dict] = None) -> pd.DataFrame:
    print("Getting dataframe from adapter")
    return _adapter.get_dataframe()


def is_new_prediction(entry: directive.MutableTransaction) -> bool:
    return isinstance(entry, directive.MutableTransaction) and is_predicted(entry)


# streamlit use wide mode
st.set_page_config(layout="wide")
st.header("🫘 Beanbot Data Editor")
st.text(
    "The following data are imported from the transaction file, please check their correctness and make changes if necessary."
)

entries_container = get_entries_container(TEST_FILE)
# entries = entries_orig.filter(is_new_prediction)
adapter = get_adapter(entries_container)
dataframe = get_dataframe(adapter)


filters = {}
with st.expander("Filters"):
    filter = st.text_input("Date")
    if filter:
        filters["date"] = filter
    filter = st.text_input("Category")
    if filter:
        filters["category_account"] = filter
    filter = st.text_input("Payee")
    if filter:
        filters["payee"] = filter
    filter = st.text_input("Narration")
    if filter:
        filters["narration"] = filter
    filter = st.text_input("Booked On")
    if filter:
        filters["source_account"] = filter
    filter = st.selectbox("New Prediction", ["True", "False", ""])
    if filter:
        filters["new_predictions"] = filter
    # filter_new_pred = st.selectbox("New Prediction", ["All", "Yes", "No"])


def filter_dataframe(dataframe: pd.DataFrame, filters: Dict[str, str]) -> List[UUID]:
    df_temp = dataframe.copy()
    for column, filter in filters.items():
        f = lambda x: filter in str(x)
        df_temp = df_temp[df_temp[column].apply(f)]
        if len(df_temp) == 0:
            return []
    return df_temp["entry_id"].tolist()


if len(filters) > 0:
    filtered_rows = filter_dataframe(
        dataframe,
        filters,
    )
    filtered_entries = entries_container.filter_by_id(filtered_rows)
    adapter = get_adapter(filtered_entries, filters)
    dataframe = get_dataframe(adapter, filters)

# Show the table editor
st.data_editor(dataframe, **adapter.get_data_editor_kwargs())

# Button for confirming the changes
if st.button("Confim Changes"):
    adapter.update_entries()
    get_adapter.clear()
    get_dataframe.clear()
    # st.session_state[adapter._editor_key] = {}
    # print(st.session_state)


if st.button("Save To File"):
    # file_saver = EntryFileSaver(BeanbotConfig.get_global()['fallback-transaction-file'])
    # file_saver.learn_filename(entries_container.get_entries())
    # file_saver.save(entries_container.get_immutable_entries())
    entries_container.save()
    st.cache_resource.clear()
