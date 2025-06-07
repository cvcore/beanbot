"""Provides in-memory representation of a Beancount ledger."""

from collections import defaultdict
from beancount import Directive, load_file
from beanbot.utils import logger
from beanbot.data.hashing import hash_directive
from beanbot.data.directive import get_source_file_path


class Ledger:
    def __init__(self, main_file: str) -> None:
        self._main_file = main_file
        self._dirty = False
        self._entries = dict()
        self._options_map = dict()
        self._ids_by_file = defaultdict(list)

        self.load()

    def add(self, entry: Directive) -> None:
        """Add a new entry to the ledger."""
        pass

    def remove(self, entry: Directive) -> None:
        """Remove an entry from the ledger."""
        pass

    def replace(self, entry_old: Directive, entry_new: Directive) -> None:
        """Replace an existing entry with a new one."""
        pass

    def save(self) -> None:
        """Save the current state of the ledger to the main file."""
        pass

    def load(self) -> None:
        """Load the ledger from the main file."""
        entries, errors, options_map = load_file(self._main_file)

        if errors:
            logger.error("Errors occurred while loading the ledger: %s", errors)

        self._options_map = options_map

        # Process entries
        for entry in entries:
            assert isinstance(entry, Directive), "All entries must be of type Directive"
            entry_id = hash_directive(entry)
            file_name = get_source_file_path(entry)
            assert file_name is not None, "Entry must have a source file path"
            self._entries[entry_id] = entry
            self._ids_by_file[file_name].append(entry_id)

        self._dirty = False
