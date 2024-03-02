from __future__ import annotations

from typing import Callable, Dict, List, Optional, Set
import uuid
from beancount.core.data import Entries
from beancount.loader import load_file
from pandas import DataFrame

from beanbot.data.directive import MutableDirective, MutableEntries, MutableOpen, make_mutable
from beancount.core.data import Directive

from beanbot.ops.extractor import BaseExtractor


class MutableEntriesView:
    """Class for managing the view of mutable entries accompanied with methods for conveniently modifying them."""

    def __init__(
        self,
        entries: MutableEntries,
        errors: List,
        options_map: Dict,
        extra_extractors: Dict[str, BaseExtractor] = None,
        metadata: Optional[List] = None,
    ) -> None:
        """Create a collection of beancount entries.

        Args:
            entries (Entries): List of directives (aka. entries) to be stored. Normally they should be read from the beancount file.
                Internally, they will be converted to mutable versions for easier modification.
            errors (List): List of errors that occurred during the import of the entries.
            options_map (Dict): Dictionary of options that were set in the beancount file.
            extra_extractors (Dict[str, BaseExtractor], optional): Dictionary of extractors that should be used to extract
                metadata from the entries.
        """

        assert all([isinstance(entry, MutableDirective) for entry in entries]), "All entries should be mutable directives."

        self._entries = entries
        self._errors = errors
        self._options_map = options_map

        if metadata is not None:
            assert len(metadata) == len(entries), "The length of the metadata should be the same as the length of the entries."
            self._metadata = metadata
        else:  # create new metadata with entry ids
            self._metadata = [{'entry_id': uuid.uuid4()} for _ in range(len(entries))]
        self._id_to_idx = {self._metadata[idx]['entry_id']: idx for idx in range(len(entries))}

        self._attached_extractors = {} if extra_extractors is None else extra_extractors
        self._extract_metadata()


    @classmethod
    def load_from_file(cls, path: str) -> MutableEntriesView:
        """Load imported entries from a path."""
        entries, errors, options_map = load_file(path)
        entries = [make_mutable(entry) for entry in entries]
        return MutableEntriesView(entries, errors, options_map)

    # Getter methods

    def get_entry_as_dict(self, idx: int, selected_keys: Optional[List] = None) -> Dict:
        entry_dict = self._entries[idx]._asdict()
        entry_dict.update(self._metadata[idx])
        if selected_keys is not None:
            entry_dict = {key: entry_dict[key] for key in selected_keys}
        return entry_dict

    def get_entry_by_idx(self, idx: int) -> MutableDirective:
        entry = self._entries[idx]
        return entry

    def get_entry_by_id(self, entry_id: uuid.UUID) -> MutableDirective:
        return self.get_entry_by_idx(self._id_to_idx[entry_id])

    def get_entries(self) -> MutableEntries:
        return self._entries

    def get_unique_values_for_key(self, key: str, entry_type: Optional[type] = None) -> Set:
        return set(self.as_dataframe(entry_type, [key]).unique())

    def get_opened_accounts(self) -> Set[str]:
        return set([entry.account for entry in self._entries if isinstance(entry, MutableOpen)])

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

    def edit_entry_by_id(self, entry_id: uuid.UUID, keys: List[str], values: List):
        idx = self._id_to_idx[entry_id]
        self.edit_entry_by_idx(idx, keys, values)

    def edit_entry_by_idx(self, idx: int, keys: List[str], values: List):
        directive = self._entries[idx]
        for key, value in zip(keys, values):
            value_type = type(getattr(directive, key))
            assert value_type == type(value), f"Got unexpected value type {type(value)}, expected {value_type}"
            setattr(directive, key, value)
        self._extract_metadata(idx, remove_existing=True)

    # Adding

    def add_entry(self, entry: MutableDirective) -> uuid.UUID:
        assert isinstance(entry, MutableDirective), "The entry should be a mutable directive."
        self._entries.append(entry)
        idx = len(self._entries) - 1
        self._metadata.append({'entry_id': uuid.uuid4()})
        self._id_to_idx[self._metadata[-1]['entry_id']] = idx
        self._extract_metadata(idx)
        return self._metadata[idx]['entry_id']

    # Deleting

    def delete_entry_by_idx(self, idx: int):
        del self._id_to_idx[self._metadata[idx]['entry_id']]
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
            entry_id = self._metadata[idx]['entry_id'] # preserve the id
            self._metadata[idx].clear()
            self._metadata[idx]['entry_id'] = entry_id
        if use_extractors is None:
            for key, extractor in self._attached_extractors.items():
                self._metadata[idx][key] = extractor.extract_one(self._entries[idx])
        else:
            for key, extractor in use_extractors.items():
                self._metadata[idx][key] = extractor.extract_one(self._entries[idx])

    # TODO: add sorting, insert at index, etc.

    def create_view_from_indices(self, indices: List[int]) -> MutableEntriesView:
        """Create a new view from a list of indices."""

        selected_entries = [self._entries[idx] for idx in indices]
        selected_metadata = [self._metadata[idx] for idx in indices]
        return MutableEntriesView(selected_entries, self._errors, self._options_map, self._attached_extractors, selected_metadata)

    # Filtering rows
    def filter(self, criterion: Callable[[MutableDirective], bool]) -> MutableEntriesView:
        """Filter the entries according to a criterion."""

        filtered_indices = [idx for idx in range(len(self._entries)) if criterion(self._entries[idx])]
        return self.create_view_from_indices(filtered_indices)
