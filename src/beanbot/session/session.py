from beancount import Directive

from beanbot.data.directive import MutableDirective, to_mutable
from beanbot.ledger.ledger import Ledger


# TODO: Remove forward declarations when QueryExecutor & Query is implemented
class Query:
    pass


class QueryExecutor:
    pass


class Session:
    """Session tracks in-memory state of entries in a ledger. It allows for adding, deleting, and modifying entries
    without immediately committing changes to the ledger. This is useful for batch processing or undo/redo
    operations."""

    def __init__(self, ledger: Ledger) -> None:
        self.new_entries: dict[str, MutableDirective] = {}
        self.existing_entries: dict[str, MutableDirective] = {}
        self.deleted_entries: set[str] = set()

        self.ledger = ledger
        self.id_generator = ledger.id_generator
        assert self.id_generator is not None, (
            "Session requires a shared ID generator from the ledger."
        )

        self.executor: "QueryExecutor | None" = None  # TODO: remove forward declaration

    def add(self, entry: MutableDirective | Directive) -> str:
        """Add a new entry to the session.

        Args:
            entry: The entry to add, either a MutableDirective or a Directive.
                When using MutableDirective with an `id` specified, you must ensure that the `id`
                is unique within the session. Otherwise, it will raise an error.
                When `id` is not specified or an immutable `Directive` is provided, a new unique ID will be generated.
        Returns:
            The unique identifier for the added entry.
        Raises:
            ValueError: If the entry already exists in the session with the same ID.
        """
        # Handle MutableDirective with existing ID
        if isinstance(entry, MutableDirective) and entry.id is not None:
            entry_id = entry.id
            # Check if ID already exists in session
            if self.id_generator.exists(entry_id):
                raise ValueError(
                    f"Entry with ID '{entry_id}' already exists in session"
                )
            mutable_entry = entry
        else:
            # Generate new ID for Directive or MutableDirective without ID
            entry_id = self.id_generator.generate()

            # Convert Directive to MutableDirective if needed
            if isinstance(entry, MutableDirective):
                mutable_entry = entry
                mutable_entry.id = entry_id
            else:
                mutable_entry = to_mutable(entry)
                mutable_entry.id = entry_id

        # Add to new entries tracking
        self.new_entries[entry_id] = mutable_entry

        return entry_id

    def delete(self, id: str) -> bool:
        """Mark an entry for deletion in the session.

        Args:
            id: The unique identifier of the entry to delete.
        Returns:
            bool: True if the entry was found, False if it did not exist.
        """
        # Check if the ID is already marked for deletion
        if id in self.deleted_entries:
            return True

        # Check if it's a new entry that hasn't been committed yet
        if id in self.new_entries:
            del self.new_entries[id]
            return True

        # Check if it's an existing entry that's been loaded into session
        if id in self.existing_entries:
            del self.existing_entries[id]
            self.deleted_entries.add(id)
            return True

        # Check if it exists in the ledger but hasn't been loaded into session
        if self.ledger.has_entry(id):
            self.deleted_entries.add(id)
            return True

        # Entry doesn't exist anywhere
        return False

    def commit(self) -> None:
        """Commit all changes in the session to the ledger and save to disk."""
        # Add new entries to the ledger
        for entry_id, entry in self.new_entries.items():
            # Convert MutableDirective back to Directive for ledger storage
            directive = entry.to_immutable()
            self.ledger.add(directive)

        # Delete entries from the ledger
        for entry_id in self.deleted_entries:
            self.ledger.delete(entry_id)

        # Update existing entries in the ledger
        for entry_id, entry in self.existing_entries.items():
            if entry.dirty():
                # Convert MutableDirective back to Directive for ledger storage
                directive = entry.to_immutable()
                self.ledger.replace(entry_id, directive)

        # Save all changes to disk
        self.ledger.save()
        self.ledger.load()

        assert not self.ledger.dirty(), (
            "Ledger should not be dirty after committing session changes"
        )

        # Clear session state after successful commit
        self.new_entries.clear()
        self.deleted_entries.clear()
        self.existing_entries.clear()

    def rollback(self) -> None:
        """Discard all uncommitted changes in the session, reverting to the last committed state."""
        # Clear all new entries that haven't been committed
        self.new_entries.clear()

        # Clear all deletion marks
        self.deleted_entries.clear()

        # Reset all existing entries to their original state
        for entry in self.existing_entries.values():
            entry.reset()

    def query(self, query_string: str | None) -> "Query":
        pass

    def dirty(self) -> bool:
        """Check if there are any unsaved changes in the session.

        Returns:
            bool: True if there are unsaved changes, False otherwise.
        """
        return (
            len(self.new_entries) > 0
            or len(self.deleted_entries) > 0
            or any(entry.dirty() for entry in self.existing_entries.values())
        )

    def has_entry(self, id: str) -> bool:
        """Check if an ID exists in the session.

        Args:
            id: The unique identifier to check.
        Returns:
            bool: True if the ID exists in the session, False otherwise.
        """
        if id in self.deleted_entries:
            return False

        return (
            id in self.new_entries
            or id in self.existing_entries
            or self.ledger.has_entry(id)
        )
