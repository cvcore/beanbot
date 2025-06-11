"""Provides in-memory representation of a Beancount ledger."""

import os
import random
from collections import defaultdict
from copy import deepcopy

from beancount import Directive, load_file
from beancount.parser.printer import EntryPrinter

from beanbot.data.hashing import stable_hash
from beanbot.ledger.text_editor import ChangeSet, ChangeType, TextEditor
from beanbot.utils import logger


class Ledger:
    """In-memory representation of a Beancount ledger.

    This class manages raw beancount entries, allowing for operations such as adding,
    removing, and replacing entries as a whole. It also implements a stable hashing
    mechanism to ensure that entries can be uniquely identified and tracked across
    reloads."""

    HASH_ATTR = "bbid"

    def __init__(self, main_file: str) -> None:
        self._main_file = main_file

        self._init_state()

        self.load()

    def _init_state(self) -> None:
        self._existing_entries = {}
        self._options_map = {}
        self._entry_lineno_ranges = {}

        self._new_entries = {}  # List of IDs of new entries to be added.
        self._changed_entries = {}  # Maps existing entry IDs to new entries
        self._deleted_entries = {}  # Maps existing entry IDs to the original entries

    def add(self, entry: Directive) -> str:
        """Add a new entry to the ledger.

        Returns:
            The ID of the newly added entry.
        """
        entry_id, _ = self._get_entry_id(entry, handle_collision=True)
        self._new_entries[entry_id] = entry
        return entry_id

    def remove(self, entry_id: str) -> bool:
        """Remove an entry from the ledger.

        Returns:
            True if the entry was found and removed, False otherwise."""
        found = False

        if entry_id in self._existing_entries:
            found = True
            entry = self._existing_entries.pop(entry_id)
            self._deleted_entries[entry_id] = entry

        if entry_id in self._new_entries:
            found = True
            del self._new_entries[entry_id]

        if entry_id in self._changed_entries:
            found = True
            del self._changed_entries[entry_id]

        if not found:
            logger.warning(
                "Attempted to remove non-existent entry with ID: %s", entry_id
            )

        return found

    def replace(self, entry_id: Directive, entry_new: Directive) -> str | None:
        """Replace an existing entry with a new one.

        Returns:
            If there is no entry found with `entry_id`, returns None.
            Otherwise, returns the new ID calculated for the new entry.
        """
        if entry_id not in self._existing_entries:
            logger.warning(
                "Attempted to replace non-existent entry with ID: %s", entry_id
            )
            return None

        self._changed_entries[entry_id] = entry_new
        entry_new_id, _ = self._get_entry_id(entry_new, handle_collision=True)

        return entry_new_id

    def save(self) -> None:
        """Persist the changes back to disk."""
        if not self.dirty:
            logger.debug("No changes to save.")
            return

        # Save changes to files
        changesets_by_file = self._get_changesets_by_file()
        for filename, changesets in changesets_by_file.items():
            if not changesets:
                continue
            logger.debug("Saving changes to file: %s", filename)
            self._commit_changes(filename, changesets)

        # Update ledger states
        updated_entries = self._existing_entries

        # Add new entries
        for entry_id, entry in self._new_entries.items():
            updated_entries[entry_id] = entry
        self._new_entries.clear()

        # Update changed entries
        for entry_id_old, entry in self._changed_entries.items():
            entry_id_new, _ = self._get_entry_id(entry)
            assert entry_id_new not in updated_entries
            updated_entries[entry_id_new] = entry
            del updated_entries[entry_id_old]
        self._changed_entries.clear()

        # Remove deleted entries
        for entry_id_deleted in self._deleted_entries:
            del updated_entries[entry_id_deleted]
        self._deleted_entries.clear()

        self._existing_entries = updated_entries

        # TODO: verify that after reload, the state is unchanged

    def _get_entry_printer(self):
        if not hasattr(self, "_entry_printer"):
            self._entry_printer = EntryPrinter(
                dcontext=self._options_map.get("dcontext", None)
            )
        return self._entry_printer

    def _commit_changes(self, filename: str, changesets: list[ChangeSet]) -> None:
        """Commit changes to a file."""
        editor = TextEditor(filename)
        editor.edit(changesets)
        editor.save_changes()

    def _get_changesets_by_file(self) -> dict[str, list[ChangeSet]]:
        changesets_by_file = defaultdict(list)
        printer = self._get_entry_printer()

        # Iterate over new entries and append them to corresponding files
        for entry in self._new_entries.values():
            filename = self._get_filename_for_entry(entry)
            changesets_by_file[filename].append(
                ChangeSet(
                    type=ChangeType.APPEND,
                    content=[printer(entry) + "\n"],
                )
            )

        # Replace changed entries
        for entry_id, entry in self._changed_entries.items():
            filename = entry.meta.get("filename", None)
            assert filename is not None, "Entry must have a filename in metadata."

            lineno_range = self._entry_lineno_ranges[entry_id]
            entry_string = printer(entry) + "\n"

            changesets_by_file[filename].append(
                ChangeSet(
                    type=ChangeType.REPLACE,
                    position=lineno_range,
                    content=[entry_string],
                )
            )

        # Delete entries
        for entry_id, entry in self._deleted_entries.items():
            filename = entry.meta.get("filename", None)
            assert filename is not None, "Entry must have a filename in metadata."

            lineno_range = self._entry_lineno_ranges[entry_id]

            changesets_by_file[filename].append(
                ChangeSet(
                    type=ChangeType.DELETE,
                    position=lineno_range,
                )
            )

        return changesets_by_file

    def _get_filename_for_entry(self, entry: Directive) -> str:
        # TODO: Implement logic to determine the filename for the entry
        return self._main_file

    def _extract_lineno_ranges(self) -> None:
        """Extract full line numbers from the entries."""
        file_linenos = defaultdict(list)

        # Collect all linenos from existing entries
        for entry in self._existing_entries.values():
            filename = os.path.realpath(entry.meta["filename"])
            lineno = entry.meta["lineno"]
            file_linenos[filename].append(lineno)

        for filename in file_linenos:
            file_linenos[filename].sort()

        # Create a mapping of linenos to the next lineno in the file
        next_linenos = defaultdict(dict)
        for filename, linenos in file_linenos.items():
            for idx in range(len(linenos) - 1):
                next_linenos[filename][linenos[idx]] = linenos[idx + 1]
            next_linenos[filename][linenos[-1]] = 0

        # Store the lineno ranges for each existing entry
        self._entry_lineno_ranges.clear()

        for entry_id, entry in self._existing_entries.items():
            filename = os.path.realpath(entry.meta["filename"])
            lineno = entry.meta["lineno"]
            # the linenos from beancount entries are 1-indexed, we use 0-indexed
            self._entry_lineno_ranges[entry_id] = (
                lineno - 1,
                next_linenos[filename][lineno] - 1,
            )

    def load(self) -> None:
        """Load the ledger from the main file."""

        # TODO: consider locking the file to prevent concurrent modifications
        # TODO: record file version and check if it has changed during saving
        entries, errors, options_map = load_file(self._main_file)

        if errors:
            logger.error("Errors occurred while loading the ledger: %s", errors)

        self._options_map = options_map

        self._init_state()

        # Process entries
        for entry in entries:
            assert isinstance(entry, Directive), "All entries must be of type Directive"

            entry_id, modified = self._get_entry_id(entry, handle_collision=False)

            if entry_id in self._existing_entries:
                # Handle hash collision by modifying the entry
                logger.debug("Hash collision detected for entry: %s", entry_id)
                entry_mod = deepcopy(entry)

                entry_mod_id, modified = self._get_entry_id(
                    entry_mod, handle_collision=True
                )
                assert modified, "Entry should be modified to resolve hash collision"

                self._existing_entries[entry_mod_id] = entry
                self._changed_entries[entry_mod_id] = entry_mod

            self._existing_entries[entry_id] = entry

        # Extract line number ranges for existing entries
        self._extract_lineno_ranges()

    def _get_entry_id(
        self, entry: Directive, handle_collision: bool = False
    ) -> tuple[str, bool]:
        """Generate an id for a Beancount directive.

        Args:
            entry: The Beancount directive to hash.
            handle_collision: If True, will handle hash collisions by appending a random number.

        Returns:
            A hash value and a boolean indicating if the entry was modified to resolve a collision.
        """
        hash_value = stable_hash(entry)

        if not handle_collision:
            return hash_value, False

        modified = False
        while hash_value in self._existing_entries:
            modified = True
            entry.meta[self.HASH_ATTR] = "".join(
                random.choices(
                    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                    k=3,
                )
            )
            hash_value = stable_hash(entry)

        return hash_value, modified

    @property
    def dirty(self) -> bool:
        """Check if the ledger has unsaved changes."""
        return (
            len(self._new_entries) > 0
            or len(self._changed_entries) > 0
            or len(self._deleted_entries) > 0
        )
