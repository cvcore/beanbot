from abc import ABC, abstractmethod
from collections import defaultdict
import os
from typing import Any
import uuid

import beancount.core.data as d
from beancount.parser.printer import EntryPrinter
from beancount.loader import load_file, _parse_recursive
from beanbot.data.pydantic_serialization import Transaction
from beanbot.file.text_editor import ChangeSet, ChangeType, TextEditor
from beanbot.helper import logger


class BaseContainer(ABC):
    """Containers are mutable data types the can be used to store directives and modify them."""

    @classmethod
    @abstractmethod
    def load_from_file(cls, path: str, no_interpolation: bool = False): ...

    @abstractmethod
    def save(self):
        """In-place save the container modifications to a file."""
        ...

    @abstractmethod
    def edit_entry_by_idx(self, idx: int, new_entry):
        """Set a new entry at a specific index."""
        ...

    @abstractmethod
    def edit_entry_by_id(self, entry_id: str, new_entry):
        """Set a new entry by its unique identifier."""
        ...

    @property
    @abstractmethod
    def entries(self) -> list:
        """Return all entries in the container."""
        ...

    @property
    @abstractmethod
    def get_entry_by_id(self, entry_id: str) -> Any:
        """Return an entry by its unique identifier"""
        ...


_BEANBOT_UUID = "beanbot_uuid"
_BEANBOT_EDITED = "beanbot_edited"
_BEANBOT_LINENO_RANGE = "beanbot_lineno_range"


def _extract_lineno_ranges(entries: list[d.Directive]) -> list[d.Directive]:
    """Extract full line numbers from the entries."""
    file_linenos = defaultdict(list)

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
        meta = entry.meta
        meta[_BEANBOT_LINENO_RANGE] = (lineno - 1, next_linenos[filename][lineno] - 1)
        entries[idx]._replace(meta=meta)

    return entries


class TransactionsContainer(BaseContainer):
    def __init__(self, entries: list[Transaction], errors: list, options_map: dict):
        assert all(isinstance(entry, Transaction) for entry in entries)

        self._entries = entries
        self._errors = errors
        self._options_map = options_map

        # Attach required meta data to each entry
        for entry in self._entries:
            if entry.meta is None:
                entry.meta = {}
            entry.meta[_BEANBOT_UUID] = str(uuid.uuid4())
            entry.meta[_BEANBOT_EDITED] = False

        self._id_to_idx = {
            entry.meta[_BEANBOT_UUID]: idx for idx, entry in enumerate(self._entries)
        }

    @property
    def options_map(self) -> dict:
        return self._options_map

    @classmethod
    def load_from_file(
        cls, path: str, no_interpolation: bool = False
    ) -> "TransactionsContainer":
        """Load transactions from a file."""
        if no_interpolation:
            entries, errors, options_map = _parse_recursive([(path, True)], None)
        else:
            entries, errors, options_map = load_file(path)

        entries = _extract_lineno_ranges(entries)

        # Filter out non-transaction entries
        entries = [entry for entry in entries if isinstance(entry, d.Transaction)]

        # Convert beancount entries to pydantic entries
        entries = [Transaction.from_beancount(entry) for entry in entries]

        return cls(entries, errors, options_map)

    def get_beancount_entries(self) -> list[d.Directive]:
        entries = [entry.to_beancount() for entry in self._entries]
        return entries

    def _get_changesets(self, add_newline: bool = True) -> dict[str, list[ChangeSet]]:
        """Return a dictionary of changesets for each file."""
        file_changesets = defaultdict(list)
        eprinter = EntryPrinter()

        for entry in self._entries:
            if not entry.meta[_BEANBOT_EDITED]:
                continue
            filename = os.path.realpath(entry.meta["filename"])
            lineno_range = entry.meta[_BEANBOT_LINENO_RANGE]
            # Remove the additional metadata from the entry
            entry_copy = entry.model_copy(deep=True)
            entry_copy.meta.pop(_BEANBOT_UUID)
            entry_copy.meta.pop(_BEANBOT_EDITED)
            entry_copy.meta.pop(_BEANBOT_LINENO_RANGE)
            entry_string = eprinter(entry_copy.to_beancount())
            if add_newline:
                entry_string += "\n"
            file_changesets[filename].append(
                ChangeSet(
                    type=ChangeType.REPLACE,
                    position=tuple(lineno_range),
                    content=[entry_string],
                )
            )

        return file_changesets

    def save(self):
        changesets = self._get_changesets()
        for filename, changeset in changesets.items():
            logger.debug(f"Saving changes to {filename}")
            for change in changeset:
                logger.debug(change)
            editor = TextEditor(filename)
            editor.edit(changeset)
            editor.save_changes()

    @property
    def entries(self):
        return self._entries

    def edit_entry_by_id(self, entry_id: str, new_entry):
        idx = self._id_to_idx[entry_id]
        assert self._entries[idx].meta[_BEANBOT_UUID] == new_entry.meta[_BEANBOT_UUID]
        self._entries[idx] = new_entry
        self._entries[idx].meta[_BEANBOT_EDITED] = True

    def edit_entry_by_idx(self, idx: int, new_entry):
        self._entries[idx] = new_entry
        assert self._entries[idx].meta[_BEANBOT_UUID] == new_entry.meta[_BEANBOT_UUID]
        self._entries[idx].meta[_BEANBOT_EDITED] = True

    def get_entry_by_id(self, entry_id: str):
        return self._entries[self._id_to_idx[entry_id]]
