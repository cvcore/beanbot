from __future__ import annotations

from typing import Dict, List, Optional
import uuid
from beancount.core.data import Entries
from beancount.loader import load_file
from pandas import DataFrame

from beanbot.data.directive import MutableDirective, MutableEntries, make_mutable


class BeanBotEntries:
    """Class for storing the imported entries in the single place and providing an interface for easy access and modification."""

    def __init__(self, entries: Entries, errors: List, options_map: Dict) -> None:
        self._entries = self._make_mutable(entries)
        self._ids = [uuid.uuid4() for _ in range(len(entries))]
        self._errors = errors
        self._options_map = options_map

    def _make_mutable(self, entries: Entries) -> MutableEntries:
        return [make_mutable(entry) for entry in entries]

    @property
    def entries(self) -> Entries:
        """Get the entries."""
        return [entry.to_immutable() for entry in self._entries]

    def get_entry_as_dict(self, idx: int, with_id: bool = True, selected_keys: Optional[List] = None) -> Dict:
        entry_dict = self._entries[idx]._asdict()
        if with_id:
            entry_dict["eid"] = self._ids[idx]
        if selected_keys is not None:
            entry_dict = {key: entry_dict[key] for key in selected_keys}
        return entry_dict

    def get_entry_by_id(self, eid: uuid.UUID) -> MutableDirective:
        return self._entries[self._ids.index(eid)]  # TODO: make this faster

    @classmethod
    def load_from_file(cls, path: str) -> BeanBotEntries:
        """Load imported entries from a path."""
        entries, errors, options_map = load_file(path)
        return BeanBotEntries(entries, errors, options_map)

    def as_dataframe(self, entry_type: Optional[type] = None, selected_columns: Optional[List] = None, with_id: bool = True) -> DataFrame:
        """Convert the entries to a pandas dataframe."""
        if entry_type is None:
            df = DataFrame([self.get_entry_as_dict(idx, with_id, selected_columns) for idx in range(len(self._entries))])
        else:
            df = DataFrame([self.get_entry_as_dict(idx, with_id, selected_columns) for idx in range(len(self._entries)) if isinstance(self._entries[idx], entry_type)])
        return df

    def edit_entry_by_id(self, eid: uuid.UUID, keys: List[str], values: List):
        directive = self.get_entry_by_id(eid)
        for key, value in zip(keys, values):
            value_type = type(getattr(directive, key))
            setattr(directive, key, value_type(value))

    def edit_entry_by_idx(self, idx: int, keys: List[str], values: List):
        directive = self._entries[idx]
        for key, value in zip(keys, values):
            value_type = type(getattr(directive, key))
            setattr(directive, key, value_type(value))

    def add_entry(self, entry: MutableDirective) -> uuid.UUID:
        self._entries.append(entry)
        self._ids.append(uuid.uuid4())
        return self._ids[-1]

    def delete_entry_by_idx(self, idx: int):
        self._entries.pop(idx)
        self._ids.pop(idx)
