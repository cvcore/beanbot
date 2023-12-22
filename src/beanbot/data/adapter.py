import datetime
from typing import Dict, List, Optional, OrderedDict
from uuid import uuid4
from numpy import column_stack

from pandas import DataFrame
from beanbot.data.directive import MutableTransaction
from beanbot.data.entries import BeanBotEntries
import streamlit as st

from beanbot.ops.extractor import BaseExtractor

from dataclasses import dataclass

class OpenedAccount(str):
    ...

@dataclass
class ColumnConfig:
    """Class storing the column configuration."""
    id: str
    name: str
    dtype: type
    description: Optional[str] = None


class StreamlitDataEditorAdapter:
    """Adapter class to provide easy data access methods to the Streamlit app."""

    def __init__(self, bb_entries: BeanBotEntries, column_configs: List[ColumnConfig], editor_config: Optional[Dict] = None) -> None:
        """Initialize the adapter with given entries.

        Args:
            bb_entries (BeanBotEntries): Beancount entries to be used for the data adapter.
            column_configs (List[ColumnConfig]): Configurations for the columns that should be displayed in the data editor. The ordering of the columns will be preserved as specified.
            editor_config (Optional[Dict], optional): Configuration options for the Streamlit data editor.
        """

        self._bb_entries = bb_entries
        self._column_configs = column_configs
        self._editor_config = editor_config if editor_config is not None else self._get_default_editor_config()
        self._editor_key = str(uuid4())[-8:]

    def callback_on_change(self, table_key: str):
        pass

    def get_dataframe(self) -> DataFrame:
        return self._bb_entries.as_dataframe(
            entry_type=MutableTransaction,
            selected_columns=self.get_visible_columns(),
        )

    def get_visible_columns(self) -> List[str]:
        return [c.id for c in self._column_configs]

    def _get_st_column_configs(self) -> Dict:
        """Return a dictionary of column configuraions as required by streamlit"""
        config_dict = dict()

        for config in self._column_configs:
            # TODO: move to modular constructions
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

    def get_data_editor(self) -> st.data_editor:
        return st.data_editor(
            self.get_dataframe(),
            key=self._editor_key,
            column_config=self._get_st_column_configs(),
            **self._editor_config,
        )

    def _get_default_editor_config(self) -> Dict:
        return dict(
            use_container_width=True,
            height=600,
        )
    
    def register_column_data_types(self, column_types):
        pass
