from __future__ import annotations

from collections import defaultdict
import os
from typing import Callable, Dict, List, Optional, Set
import uuid
from beancount.core.data import Entries
from beancount.loader import load_file
from pandas import DataFrame

from beanbot.data.directive import (
    MutableDirective,
    MutableEntries,
    MutableOpen,
    make_mutable,
)
from beancount.parser.printer import EntryPrinter

from beanbot.file.text_editor import ChangeSet, ChangeType, TextEditor
from beanbot.ops.extractor import BaseExtractor


class MutableEntriesContainer:
    """Class for managing the view of mutable entries accompanied with methods for conveniently modifying them."""

    _BEANBOT_EDITED_FLAG = "__edited_by_beanbot"

    def __init__(
        self,
        entries: MutableEntries,
        errors: List,
        options_map: Dict,
        extra_extractors: Dict[str, BaseExtractor] = None,
        metadata: Optional[List] = None,
        opened_accounts: Optional[Set[str]] = None,
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

        assert all(
            [isinstance(entry, MutableDirective) for entry in entries]
        ), "All entries should be mutable directives."

        self._entries = entries
        self._errors = errors
        self._options_map = options_map

        if metadata is not None:
            assert (
                len(metadata) == len(entries)
            ), "The length of the metadata should be the same as the length of the entries."
            self._metadata = metadata
        else:  # create new metadata with entry ids
            self._metadata = [
                {
                    "entry_id": uuid.uuid4(),
                    self._BEANBOT_EDITED_FLAG: False,
                }
                for _ in range(len(entries))
            ]
            self._extract_entry_lineno_range()
        if opened_accounts is not None:
            self._opened_accounts = opened_accounts
        else:
            self._opened_accounts = self._extract_opened_accounts()

        self._id_to_idx = {
            self._metadata[idx]["entry_id"]: idx for idx in range(len(entries))
        }
        self._attached_extractors = {} if extra_extractors is None else extra_extractors
        self._extract_metadata()

    # File I/O

    @classmethod
    def load_from_file(cls, path: str) -> MutableEntriesContainer:
        """Load imported entries from a path."""
        entries, errors, options_map = load_file(path)
        entries = [make_mutable(entry) for entry in entries]
        return MutableEntriesContainer(entries, errors, options_map)

    def save(self) -> None:
        changesets = self._get_changesets()
        for filename, changes in changesets.items():
            print(f"Saving changes to {filename}:")
            for change in changes:
                print(change)
            editor = TextEditor(filename)
            editor.edit(changes)
            editor.save_changes()

    def _get_changesets(self, add_newline: bool = True) -> Dict[str, List[ChangeSet]]:
        file_changesets = defaultdict(list)
        eprinter = EntryPrinter()
        for entry, metadata in zip(self._entries, self._metadata):
            if metadata[self._BEANBOT_EDITED_FLAG]:
                filename = os.path.realpath(entry.meta["filename"])
                lineno_range = metadata["lineno_range"]
                entry_string = eprinter(entry.to_immutable())
                if add_newline:
                    entry_string += "\n"
                file_changesets[filename].append(
                    ChangeSet(
                        type=ChangeType.REPLACE,
                        position=lineno_range,
                        content=[entry_string],
                    )
                )
        return file_changesets

    def _extract_entry_lineno_range(self) -> None:
        """Extract the entries' line number ranges."""

        file_linenos = defaultdict(list)
        entries = self._entries

        for entry in entries:
            filename = os.path.realpath(entry.meta["filename"])
            lineno = entry.meta["lineno"]
            file_linenos[filename].append(lineno)

        for filename in file_linenos:
            file_linenos[filename].sort()

        next_linenos = defaultdict(dict)
        for filename, linenos in file_linenos.items():
            for idx in range(len(linenos) - 1):
                next_linenos[filename][linenos[idx]] = linenos[idx + 1]
            next_linenos[filename][linenos[-1]] = 0

        for idx, entry in enumerate(entries):
            filename = os.path.realpath(entry.meta["filename"])
            lineno = entry.meta["lineno"]
            # the linenos from beancount entries are 1-indexed
            self._metadata[idx]["lineno_range"] = (
                lineno - 1,
                next_linenos[filename][lineno] - 1,
            )

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

    def get_immutable_entries(self) -> Entries:
        return [entry.to_immutable() for entry in self._entries]

    def get_unique_values_for_key(
        self, key: str, entry_type: Optional[type] = None
    ) -> Set:
        return set(self.as_dataframe(entry_type, [key]).unique())

    def _extract_opened_accounts(self) -> Set[str]:
        return set(
            [entry.account for entry in self._entries if isinstance(entry, MutableOpen)]
        )

    def get_opened_accounts(self) -> Set[str]:
        return self._opened_accounts

    # Conversions

    def as_dataframe(
        self,
        selected_entry_type: Optional[type] = None,
        selected_columns: Optional[List] = None,
    ) -> DataFrame:
        """Convert the entries to a pandas dataframe."""
        if selected_entry_type is None:
            df = DataFrame(
                [
                    self.get_entry_as_dict(idx, selected_columns)
                    for idx in range(len(self._entries))
                ]
            )
        else:
            df = DataFrame(
                [
                    self.get_entry_as_dict(idx, selected_columns)
                    for idx in range(len(self._entries))
                    if isinstance(self._entries[idx], selected_entry_type)
                ]
            )
        if selected_columns is not None and len(df) > 0:
            df = df[selected_columns]  # keep the ordering of the columns
        return df

    # Setter methods

    def edit_entry_by_id(self, entry_id: uuid.UUID, keys: List[str], values: List):
        idx = self._id_to_idx[entry_id]
        self.edit_entry_by_idx(idx, keys, values)

    def edit_entry_by_idx(self, idx: int, keys: List[str], values: List):
        directive = self._entries[idx]
        self._metadata[idx][self._BEANBOT_EDITED_FLAG] = True
        for key, value in zip(keys, values):
            value_type = type(getattr(directive, key))
            assert value_type == type(
                value
            ), f"Got unexpected value type {type(value)}, expected {value_type}"
            setattr(directive, key, value)
        self._extract_metadata(idx)

    # Adding

    def add_entry(self, entry: MutableDirective) -> uuid.UUID:
        assert isinstance(
            entry, MutableDirective
        ), "The entry should be a mutable directive."
        self._entries.append(entry)
        idx = len(self._entries) - 1
        self._metadata.append({"entry_id": uuid.uuid4()})
        self._id_to_idx[self._metadata[-1]["entry_id"]] = idx
        self._extract_metadata(idx)
        return self._metadata[idx]["entry_id"]

    # Deleting

    def delete_entry_by_idx(self, idx: int):
        del self._id_to_idx[self._metadata[idx]["entry_id"]]
        self._metadata.pop(idx)
        self._entries.pop(idx)

    # Metadata extraction

    def attach_extractors(self, extractors: Dict[str, BaseExtractor]):
        self._attached_extractors.update(extractors)
        self._extract_metadata(use_extractors=extractors)

    def _extract_metadata(
        self,
        idx: Optional[int] = None,
        remove_existing: bool = False,
        use_extractors: Optional[Dict] = None,
    ):
        if idx is None:
            for idx in range(len(self._entries)):
                self._extract_metadata(idx, remove_existing)
            return

        if remove_existing:
            raise NotImplementedError(
                "Removing existing metadata is not yet implemented."
            )
            entry_id = self._metadata[idx]["entry_id"]  # preserve the id
            self._metadata[idx].clear()
            self._metadata[idx]["entry_id"] = entry_id
        if use_extractors is None:
            for key, extractor in self._attached_extractors.items():
                self._metadata[idx][key] = extractor.extract_one(self._entries[idx])
        else:
            for key, extractor in use_extractors.items():
                self._metadata[idx][key] = extractor.extract_one(self._entries[idx])

    # TODO: add sorting, insert at index, etc.

    def create_container_from_indices(
        self, indices: List[int]
    ) -> MutableEntriesContainer:
        """Create a new view from a list of indices."""

        selected_entries = [self._entries[idx] for idx in indices]
        selected_metadata = [self._metadata[idx] for idx in indices]
        return MutableEntriesContainer(
            selected_entries,
            self._errors,
            self._options_map,
            self._attached_extractors,
            selected_metadata,
            self._opened_accounts,
        )

    # Filtering rows
    def filter_by_criterion(
        self, criterion: Callable[[MutableDirective], bool]
    ) -> MutableEntriesContainer:
        """Filter the entries according to a criterion."""

        filtered_indices = [
            idx for idx in range(len(self._entries)) if criterion(self._entries[idx])
        ]
        return self.create_container_from_indices(filtered_indices)

    def filter_by_index(self, indices: List[int]) -> MutableEntriesContainer:
        """Filter the entries by a list of indices."""
        return self.create_container_from_indices(indices)

    def filter_by_id(self, entry_ids: List[uuid.UUID]) -> MutableEntriesContainer:
        """Filter the entries by a list of entry ids."""
        indices = [self._id_to_idx[entry_id] for entry_id in entry_ids]
        return self.create_container_from_indices(indices)
