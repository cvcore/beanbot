import datetime
from typing import Any, Dict, List, Optional, OrderedDict, Callable
from types import NoneType
from uuid import uuid4
from numpy import column_stack

from pandas import DataFrame
from pydantic import BaseModel
from beanbot.data.directive import MutableTransaction
from beanbot.data.entries import MutableEntriesView
import streamlit as st

from beanbot.ops.extractor import BaseExtractor

from dataclasses import dataclass

class OpenedAccount(str):
    ...

@dataclass
class ColumnConfig():
    """Class storing the column configuration.

    Args:
        id (str):
            column name as in the dataframe
        name (str):
            a friendly name of the column, to be displayed in the streamlit editor
        dtype (type):
            data type of the column, used to deterimine the ui component of the editor
        description (Optional[str], optional):
            description of the column, to be displayed
            as a tooltip in the streamlit editor. Defaults to None.
        editable (bool, defaults to False):
            when editable, set this column to true. Defaults to False.
        linked_entry_field (str, optional): name of the field in the entry that
            should be updated when the column is edited. E.g. in case of editing the `new_prediction` property of a `Transaction`, we need to remove its tags that contains a magic substring `_new_`. In this case, the `linked_entry_field` should be set as 'tags'.
        entry_setter_fn (Callable[[Any, Any], Any], optional): callback function that should
            be used to set the value of the entry field, if not given, the value will be set directly.
            This function will be given two arguments when being called. The first argument will
            contain the old value of the field to be updated. And the second one will contain an
            updated value from the streamlit web UI. Often you should take both into account when
            updating a field in a directive, e.g. when inserting a value to a list.
            The function should return the updated value of the field.
    """

    id: str
    name: str
    dtype: type
    description: Optional[str] = None
    editable: Optional[bool] = False
    linked_entry_field: Optional[str] = None
    entry_setter_fn: Optional[Callable[[Any, Any], Any]] = None


class StreamlitDataEditorAdapter:
    """Adapter class to support editing BeanBotEntries by handling necessary conversions between the dataframes and the entries."""

    def __init__(self, bb_entries: MutableEntriesView, column_configs: List[ColumnConfig], editor_config: Optional[Dict] = None) -> None:
        """Initialize the adapter with given entries.

        Args:
            bb_entries (BeanBotEntries): Beancount entries to be used for the data adapter.
            column_configs (List[ColumnConfig]): Configurations for the columns that should be displayed in the data editor. The ordering of the columns will be preserved as specified.
            editor_config (Optional[Dict], optional): Configuration options for the Streamlit data editor.
        """

        self._bb_entries = bb_entries
        self._column_configs = OrderedDict([(c.id, c) for c in column_configs])
        self._editor_config = editor_config if editor_config is not None else self._get_default_editor_config()
        self._editor_key = str(uuid4())[-8:]
        self._editor_state = {}
        self._refresh_needed = False

    def is_refresh_needed(self) -> bool:
        return self._refresh_needed

    def _make_editor_callback_method(self) -> Callable[[str], NoneType]:
        # When streamlit invokes this callback to edit a specific dataframe cell, it passes the editor
        # key as the argument, and through st.session_state the change can be accessed as e.g.:
        # {'edited_rows': {0: {'new_predictions': True}}, 'added_rows': [], 'deleted_rows': []}
        def update_editor_state(editor_key):
            self._editor_state = st.session_state[editor_key]
            print(f"[DEBUG] Editor state: {self._editor_state}")
            # edited_rows = st.session_state[key]["edited_rows"]



        return update_editor_state

    def get_dataframe(self) -> DataFrame:
        bb_entries_df = self._bb_entries.as_dataframe(
            # entry_type=MutableTransaction,
            # selected_columns=self.get_visible_columns() + ["entry_id"],  # add id field for easier queries
        )
        bb_entries_df.insert(0, "Select", False, allow_duplicates=False)

        return bb_entries_df

    def get_visible_columns(self) -> List[str]:
        return [c.id for c in self._column_configs.values()]

    def _get_st_column_configs(self) -> Dict:
        """Return a dictionary of column configuraions as required by streamlit"""
        config_dict = dict(
            entry_id=None,  # hide the id column by default, unless explicitly specified
        )

        for config in self._column_configs.values():
            column_args = dict(
                label=config.name,
                help=config.description,
            )
            if config.dtype in [float, int]:
                column_cls = st.column_config.NumberColumn
            elif config.dtype in [datetime.date]:
                column_cls = st.column_config.DateColumn
            elif config.dtype == OpenedAccount:
                column_cls = st.column_config.SelectboxColumn
                column_args["options"] = self._bb_entries.get_opened_accounts()
            elif config.dtype == str:
                column_cls = st.column_config.TextColumn
            elif config.dtype == bool:
                column_cls = st.column_config.CheckboxColumn
            else:
                raise NotImplementedError(f"Support not implemented for dtype {config.dtype}!")

            config_dict[config.id] = column_cls(**column_args)

        return config_dict

    def _get_disabled_columns(self) -> List[str]:
        return [c.id for c in self._column_configs.values() if not c.editable]

    # def get_data_editor(self) -> st.data_editor:
    #     df = self.get_dataframe()
    #     idx_to_id = {idx: row.entry_id for idx, row in df.iterrows()}
    #     return st.data_editor(
    #         df,
    #         key=self._editor_key,
    #         column_config=self._get_st_column_configs(),
    #         on_change=self._make_editor_callback_method(),
    #         disabled=self._get_disabled_columns(),
    #         args=(self._editor_key,),
    #         **self._editor_config,
    #     )

    def get_data_editor_kwargs(self) -> Dict:
        return dict(
            key=self._editor_key,
            column_config=self._get_st_column_configs(),
            on_change=self._make_editor_callback_method(),
            disabled=self._get_disabled_columns(),
            args=(self._editor_key,),
            **self._editor_config,
        )

    def _get_default_editor_config(self) -> Dict:
        return dict(
            use_container_width=True,
            height=600,
        )

    def commit_changes(self):
        edited_rows = self._editor_state.get("edited_rows", {})

        for row, row_changes in edited_rows.items():
            for col, col_change in row_changes.items():
                if self._column_configs[col].linked_entry_field is not None:
                    col_config = self._column_configs[col]
                    # entry_id = idx_to_id[row]

                    if col_config.entry_setter_fn is not None:
                        orig_value = getattr(
                            # self._bb_entries.get_entry_by_id(entry_id),
                            self._bb_entries.get_entry_by_idx(row),
                            col_config.linked_entry_field
                        )
                        upd_value = col_config.entry_setter_fn(orig_value, col_change)
                    else:
                        upd_value = col_change

                    self._bb_entries.edit_entry_by_idx(
                        row,
                        [col_config.linked_entry_field],
                        [upd_value],
                    )

        self._refresh_needed = True
