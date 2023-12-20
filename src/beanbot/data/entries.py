from __future__ import annotations

from typing import Callable, Dict, List, Optional
import uuid
from beancount.core.data import Entries
from beancount.loader import load_file
from pandas import DataFrame

from beanbot.data.directive import MutableDirective, MutableEntries, make_mutable
from beancount.core.data import Directive

from beanbot.ops.extractor import BaseDirectiveExtractor, BaseExtractor


class BeanBotEntries:
    """Class for storing the imported entries in the single place and providing an interface for easy access and modification."""

    def __init__(self, entries: Entries, errors: List, options_map: Dict, extra_extractors: Dict[str, BaseExtractor] = None) -> None:
        """Create a collection of beancount entries.

        Args:
            entries (Entries): List of directives (aka. entries) to be stored. Normally they should be read from the beancount file.
                Internally, they will be converted to mutable versions for easier modification.
            errors (List): List of errors that occurred during the import of the entries.
            options_map (Dict): Dictionary of options that were set in the beancount file.
            extra_extractors (Dict[str, BaseExtractor], optional): Dictionary of extractors that should be used to extract
                metadata from the entries.
        """

        self._entries = self._make_mutable(entries)
        self._errors = errors
        self._options_map = options_map

        self._metadata = [{'eid': uuid.uuid4()} for _ in range(len(entries))]
        self._id_to_idx = {self._metadata[idx]['eid']: idx for idx in range(len(entries))}

        self._attached_extractors = {} if extra_extractors is None else extra_extractors
        self._extract_metadata()

    def _make_mutable(self, entries: Entries) -> MutableEntries:
        return [make_mutable(entry) for entry in entries]

    @classmethod
    def load_from_file(cls, path: str) -> BeanBotEntries:
        """Load imported entries from a path."""
        entries, errors, options_map = load_file(path)
        return BeanBotEntries(entries, errors, options_map)

    # Getter methods

    def get_entry_as_dict(self, idx: int, selected_keys: Optional[List] = None) -> Dict:
        entry_dict = self._entries[idx]._asdict()
        entry_dict.update(self._metadata[idx])
        if selected_keys is not None:
            entry_dict = {key: entry_dict[key] for key in selected_keys}
        return entry_dict

    def get_entry_by_id(self, eid: uuid.UUID, force_immutable: bool = False) -> MutableDirective | Directive:
        entry = self._entries[self._id_to_idx[eid]]
        if force_immutable:
            entry = entry.to_immutable()
        return entry

    def get_entries(self, force_immutable: bool = False) -> MutableEntries | Entries:
        if force_immutable:
            return [entry.to_immutable() for entry in self._entries]
        return self._entries

    # Conversions

    def as_dataframe(self, entry_type: Optional[type] = None, selected_columns: Optional[List] = None) -> DataFrame:
        """Convert the entries to a pandas dataframe."""
        if entry_type is None:
            df = DataFrame([self.get_entry_as_dict(idx, selected_columns) for idx in range(len(self._entries))])
        else:
            df = DataFrame([self.get_entry_as_dict(idx, selected_columns) for idx in range(len(self._entries)) if isinstance(self._entries[idx], entry_type)])
        if selected_columns is not None:
            df = df[selected_columns]  # keep the ordering of the columns
        return df

    # Setter methods

    def edit_entry_by_id(self, eid: uuid.UUID, keys: List[str], values: List):
        idx = self._id_to_idx[eid]
        self.edit_entry_by_idx(idx, keys, values)

    def edit_entry_by_idx(self, idx: int, keys: List[str], values: List):
        directive = self._entries[idx]
        for key, value in zip(keys, values):
            value_type = type(getattr(directive, key))
            setattr(directive, key, value_type(value))
        self._extract_metadata(idx, remove_existing=True)

    # Adding

    def add_entry(self, entry: MutableDirective | Directive) -> uuid.UUID:
        if isinstance(entry, Directive):
            entry = make_mutable(entry)
        self._entries.append(entry)
        idx = len(self._entries) - 1
        self._metadata.append({'eid': uuid.uuid4()})
        self._id_to_idx[self._metadata[-1]['eid']] = idx
        self._extract_metadata(idx)
        return self._metadata[idx]['eid']

    # Deleting

    def delete_entry_by_idx(self, idx: int):
        del self._id_to_idx[self._metadata[idx]['eid']]
        self._metadata.pop(idx)
        self._entries.pop(idx)

    # Metadata extraction

    def attach_extractors(self, extractors: Dict[str, BaseExtractor]):
        self._attached_extractors.update(extractors)
        self._extract_metadata(use_extractors=extractors)

    def _extract_metadata(self, idx: Optional[int] = None, remove_existing: bool = False, use_extractors: Optional[Dict] = None):
        if idx is None:
            for idx in range(len(self._entries)):
                self._extract_metadata(idx, remove_existing)
            return

        if remove_existing:
            eid = self._metadata[idx]['eid'] # preserve the id
            self._metadata[idx].clear()
            self._metadata[idx]['eid'] = eid
        if use_extractors is None:
            for key, extractor in self._attached_extractors.items():
                self._metadata[idx][key] = extractor.extract_one(self._entries[idx])
        else:
            for key, extractor in use_extractors.items():
                self._metadata[idx][key] = extractor.extract_one(self._entries[idx])


    # TODO: add sorting, insert at index, etc.
