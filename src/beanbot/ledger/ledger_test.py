"""Unit tests for the Ledger class using pytest."""

import shutil
import tempfile
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from beancount.core.amount import Amount
from beancount.core.data import Posting, Transaction
from beancount.core.number import D
from beancount.loader import load_file

from beanbot.ledger.ledger import Ledger


def _find_transaction_by_details(entries, date, payee, narration):
    """Helper function to find a transaction by date, payee, and narration."""
    for entry in entries:
        if (
            hasattr(entry, "date")
            and entry.date == date
            and hasattr(entry, "payee")
            and entry.payee == payee
            and hasattr(entry, "narration")
            and entry.narration == narration
        ):
            return entry
    return None


def _transaction_exists_in_entries(entries, date, payee, narration):
    """Helper function to check if a transaction exists in a list of entries."""
    return _find_transaction_by_details(entries, date, payee, narration) is not None


def _find_first_transaction_entry(ledger_entries):
    """Helper function to find the first Transaction entry in ledger entries."""
    for entry_id, entry in ledger_entries.items():
        if isinstance(entry, Transaction):
            return entry_id, entry
    return None, None


@pytest.fixture(name="main_file")
def fixture_main_file():
    """Fixture for the main beancount file path."""
    return "data/ledger/main.bean"


@pytest.fixture(name="sample_transaction")
def fixture_sample_transaction(main_file):
    """Fixture for a sample transaction."""
    return Transaction(
        meta={"filename": main_file, "lineno": 1},
        date=date(2024, 1, 1),
        flag="*",
        payee="Test Payee",
        narration="Test transaction",
        tags=None,
        links=None,
        postings=[
            Posting(
                account="Assets:Checking:SomeBank",
                units=Amount(D("-100.00"), "EUR"),
                cost=None,
                price=None,
                flag=None,
                meta={},
            ),
            Posting(
                account="Expenses:Others",
                units=None,
                cost=None,
                price=None,
                flag=None,
                meta={},
            ),
        ],
    )


@pytest.fixture(name="ledger")
def fixture_ledger(main_file):
    """Fixture for a Ledger instance."""
    return Ledger(main_file)


def test_init_loads_ledger(ledger):
    """Test that initializing a Ledger loads the file."""
    # Check that entries were loaded
    assert len(ledger._existing_entries) > 0
    assert ledger._options_map is not None
    assert not ledger.dirty


def test_add_entry(ledger, sample_transaction):
    """Test adding a new entry to the ledger."""
    initial_count = len(ledger._existing_entries)

    entry_id = ledger.add(sample_transaction)

    # Check that entry was added
    assert isinstance(entry_id, str)
    assert entry_id in ledger._new_entries
    assert ledger.dirty

    # Check that existing entries count hasn't changed
    assert len(ledger._existing_entries) == initial_count


def test_remove_existing_entry(ledger):
    """Test removing an existing entry from the ledger."""
    # Get an existing entry ID
    existing_entry_id = next(iter(ledger._existing_entries.keys()))
    original_entry = ledger._existing_entries[existing_entry_id]

    result = ledger.remove(existing_entry_id)

    # Check that entry was removed
    assert result is True
    assert existing_entry_id in ledger._deleted_entries
    assert ledger._deleted_entries[existing_entry_id] == original_entry
    assert ledger.dirty


def test_remove_new_entry(ledger, sample_transaction):
    """Test removing a newly added entry."""
    # Add a new entry first
    entry_id = ledger.add(sample_transaction)
    assert entry_id in ledger._new_entries

    # Snapshot existing entries before removal
    existing_entries_before = ledger._existing_entries.copy()

    # Remove the new entry
    result = ledger.remove(entry_id)

    # Check that entry was removed
    assert result is True
    assert entry_id not in ledger._new_entries
    assert entry_id not in ledger._deleted_entries
    assert ledger.dirty is False
    # Ensure existing entries are untouched
    assert ledger._existing_entries == existing_entries_before


def test_remove_nonexistent_entry(ledger):
    """Test removing a non-existent entry."""
    result = ledger.remove("nonexistent_id")

    # Check that removal failed gracefully
    assert result is False


def test_replace_existing_entry(ledger, sample_transaction):
    """Test replacing an existing entry."""
    # Get an existing entry ID
    existing_entry_id = next(iter(ledger._existing_entries.keys()))

    new_entry_id = ledger.replace(existing_entry_id, sample_transaction)

    # Check that entry was replaced
    assert isinstance(new_entry_id, str)
    assert existing_entry_id in ledger._changed_entries
    assert ledger.dirty


def test_replace_nonexistent_entry(ledger, sample_transaction):
    """Test replacing a non-existent entry."""
    result = ledger.replace("nonexistent_id", sample_transaction)

    # Check that replacement failed
    assert result is None
    assert "nonexistent_id" not in ledger._changed_entries


def test_dirty_property(ledger, sample_transaction):
    """Test the dirty property."""
    # Initially should not be dirty
    assert not ledger.dirty

    # Adding an entry should make it dirty
    ledger.add(sample_transaction)
    assert ledger.dirty


@patch("beanbot.ledger.ledger.TextEditor")
def test_save_with_changes(mock_text_editor, ledger, sample_transaction):
    """Test saving changes to disk."""
    # Mock the TextEditor
    mock_editor_instance = MagicMock()
    mock_text_editor.return_value = mock_editor_instance

    # Add a new entry
    entry_id = ledger.add(sample_transaction)
    assert ledger.dirty

    # Save changes
    ledger.save()

    # Check that TextEditor was used
    mock_text_editor.assert_called()

    # Verify that edit was called with the correct ChangeSet
    mock_editor_instance.edit.assert_called_once()
    call_args = mock_editor_instance.edit.call_args
    changesets = call_args[0][0]  # First positional argument

    # Should be a list with one ChangeSet
    assert isinstance(changesets, list)
    assert len(changesets) == 1

    changeset = changesets[0]
    assert changeset.type.name == "APPEND"
    assert changeset.position is None
    assert isinstance(changeset.content, list)
    assert len(changeset.content) == 1

    # Verify the transaction string contains expected elements
    transaction_string = changeset.content[0]
    assert "2024-01-01" in transaction_string
    assert "Test Payee" in transaction_string
    assert "Test transaction" in transaction_string
    assert "Assets:Checking:SomeBank" in transaction_string
    assert "-100.00 EUR" in transaction_string
    assert "Expenses:Others" in transaction_string

    mock_editor_instance.save_changes.assert_called()

    # Check that state was updated
    assert not ledger.dirty
    assert entry_id in ledger._existing_entries
    assert len(ledger._new_entries) == 0


@patch("beanbot.ledger.ledger.TextEditor")
def test_save_no_changes(mock_text_editor, ledger):
    """Test saving when there are no changes."""
    ledger.save()

    # TextEditor should not be called when there are no changes
    mock_text_editor.assert_not_called()


def test_get_entry_id_no_collision(ledger, sample_transaction):
    """Test entry ID generation without collision."""
    entry_id, modified = ledger._get_entry_id(sample_transaction)

    assert isinstance(entry_id, str)
    assert not modified


def test_get_entry_id_with_collision_handling(ledger, sample_transaction):
    """Test entry ID generation with collision handling."""
    # First, add the entry to existing entries to create a collision scenario
    entry_id_1, _ = ledger._get_entry_id(sample_transaction)
    ledger._existing_entries[entry_id_1] = sample_transaction

    # Now try to get ID for the same entry with collision handling
    sample_transaction_orig = deepcopy(sample_transaction)
    assert sample_transaction_orig == sample_transaction
    entry_id_2, modified = ledger._get_entry_id(
        sample_transaction, handle_collision=True
    )

    # Should get a different ID and be marked as modified
    assert entry_id_1 != entry_id_2
    assert modified
    assert sample_transaction_orig != sample_transaction
    assert ledger.HASH_ATTR in sample_transaction.meta


def test_extract_lineno_ranges(ledger):
    """Test extraction of line number ranges."""
    # Check that line number ranges were extracted
    assert len(ledger._entry_lineno_ranges) > 0

    with open(ledger._main_file, "r") as f:
        total_lines = sum(1 for _ in f)
    assert total_lines >= 1

    # Check that ranges are tuples of integers
    for entry_id, line_range in ledger._entry_lineno_ranges.items():
        assert isinstance(line_range, tuple)
        assert len(line_range) == 2
        assert isinstance(line_range[0], int)
        assert isinstance(line_range[1], int)
        begin = line_range[0] if line_range[0] >= 0 else total_lines + line_range[0]
        end = line_range[1] if line_range[1] >= 0 else total_lines + line_range[1]
        assert 0 <= begin <= end < total_lines


def test_reload_ledger(ledger, sample_transaction):
    """Test reloading the ledger."""
    initial_entries_count = len(ledger._existing_entries)

    # Add some changes to make it dirty
    ledger.add(sample_transaction)
    assert ledger.dirty

    # Reload
    ledger.load()

    # Check that state was reset
    assert not ledger.dirty
    assert len(ledger._existing_entries) == initial_entries_count
    assert len(ledger._new_entries) == 0
    assert len(ledger._changed_entries) == 0
    assert len(ledger._deleted_entries) == 0


def test_get_filename_for_entry(ledger, sample_transaction, main_file):
    """Test getting filename for an entry."""
    filename = ledger._get_filename_for_entry(sample_transaction)

    # Should return the main file for now
    assert filename == main_file


class TestLedgerIntegration:
    """Integration tests for the Ledger class."""

    def test_full_workflow(self, ledger, sample_transaction):
        """Test a complete workflow of add, modify, remove, and save."""
        initial_count = len(ledger._existing_entries)

        # Add entry
        entry_id = ledger.add(sample_transaction)
        assert ledger.dirty
        assert entry_id in ledger._new_entries

        # Replace entry
        modified_transaction = Transaction(
            meta=sample_transaction.meta,
            date=sample_transaction.date,
            flag=sample_transaction.flag,
            payee="Modified Payee",
            narration="Modified transaction",
            tags=sample_transaction.tags,
            links=sample_transaction.links,
            postings=sample_transaction.postings,
        )

        # Since it's a new entry, we need to remove and add again
        ledger.remove(entry_id)
        new_entry_id = ledger.add(modified_transaction)

        assert new_entry_id in ledger._new_entries
        assert ledger._new_entries[new_entry_id].payee == "Modified Payee"

        # Remove the entry
        ledger.remove(new_entry_id)
        assert new_entry_id not in ledger._new_entries
        assert not ledger.dirty

        # Final state should be the same as initial
        assert len(ledger._existing_entries) == initial_count

    def test_real_file_add_transaction(self, main_file, sample_transaction):
        """Test actual file editing and saving with real TextEditor."""
        # Create a temporary copy of the main file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "test_main.bean"
            shutil.copy2(main_file, temp_file)

            # Create ledger with temp file
            ledger = Ledger(str(temp_file))
            initial_count = len(ledger._existing_entries)

            # Add a new transaction
            entry_id = ledger.add(sample_transaction)
            assert ledger.dirty

            from beancount.parser.printer import EntryPrinter

            printer = EntryPrinter()
            print(printer(sample_transaction))

            # Record the stable ID before saving
            stable_id_before_save = entry_id

            # Save changes (this uses real TextEditor)
            ledger.save()

            # Verify state after save
            assert not ledger.dirty
            assert entry_id in ledger._existing_entries
            assert len(ledger._new_entries) == 0
            assert len(ledger._existing_entries) == initial_count + 1

            # Reload the file with beancount and verify the transaction was added correctly
            reloaded_entries, _, _ = load_file(str(temp_file))

            # Find our added transaction in the reloaded entries
            found_transaction = _find_transaction_by_details(
                reloaded_entries,
                sample_transaction.date,
                sample_transaction.payee,
                sample_transaction.narration,
            )

            assert found_transaction is not None, (
                "Added transaction not found in reloaded file"
            )
            assert len(found_transaction.postings) == len(sample_transaction.postings)

            # Test that the stable ID doesn't change when we reload the ledger
            ledger_reloaded = Ledger(str(temp_file))

            # Find the same transaction in the reloaded ledger by content
            reloaded_entry_id = None
            for (
                entry_id_reload,
                entry_reload,
            ) in ledger_reloaded._existing_entries.items():
                if (
                    hasattr(entry_reload, "date")
                    and entry_reload.date == sample_transaction.date
                    and hasattr(entry_reload, "payee")
                    and entry_reload.payee == sample_transaction.payee
                    and hasattr(entry_reload, "narration")
                    and entry_reload.narration == sample_transaction.narration
                ):
                    reloaded_entry_id = entry_id_reload
                    break

            assert reloaded_entry_id is not None, (
                "Transaction not found in reloaded ledger"
            )

            print(printer(found_transaction))

            # Verify the stable ID is the same after reload
            assert reloaded_entry_id == stable_id_before_save, (
                f"Stable ID changed after reload: {stable_id_before_save} -> {reloaded_entry_id}"
            )

    def test_real_file_modify_transaction(self, main_file, sample_transaction):
        """Test actual file modification with real TextEditor."""
        # Create a temporary copy of the main file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "test_main.bean"
            shutil.copy2(main_file, temp_file)

            # Create ledger with temp file
            ledger = Ledger(str(temp_file))
            initial_count = len(ledger._existing_entries)

            # Get the first existing transaction entry to modify
            existing_entry_id, original_entry = _find_first_transaction_entry(
                ledger._existing_entries
            )

            assert existing_entry_id is not None, (
                "No Transaction entries found in ledger"
            )

            # Create a modified version of the entry
            modified_transaction = Transaction(
                meta=original_entry.meta,
                date=original_entry.date,
                flag=original_entry.flag,
                payee="Modified Test Payee",
                narration="Modified test narration",
                tags=original_entry.tags,
                links=original_entry.links,
                postings=original_entry.postings,
            )

            # Replace the entry
            new_entry_id = ledger.replace(existing_entry_id, modified_transaction)
            assert ledger.dirty
            assert new_entry_id is not None

            # Save changes (this uses real TextEditor)
            ledger.save()

            # Verify state after save
            assert not ledger.dirty
            assert new_entry_id in ledger._existing_entries
            assert existing_entry_id not in ledger._existing_entries
            assert len(ledger._changed_entries) == 0
            assert len(ledger._existing_entries) == initial_count

            # Reload the file with beancount and verify the transaction was modified correctly
            reloaded_entries, _, _ = load_file(str(temp_file))

            # Find our modified transaction in the reloaded entries
            found_modified_transaction = _find_transaction_by_details(
                reloaded_entries,
                modified_transaction.date,
                "Modified Test Payee",
                "Modified test narration",
            )

            # Check that original transaction is no longer present
            original_transaction_found = _transaction_exists_in_entries(
                reloaded_entries,
                original_entry.date,
                original_entry.payee,
                original_entry.narration,
            )

            assert found_modified_transaction is not None, (
                "Modified transaction not found in reloaded file"
            )
            assert not original_transaction_found, (
                "Original transaction should not be present after modification"
            )

    def test_real_file_delete_transaction(self, main_file):
        """Test actual file deletion with real TextEditor."""
        # Create a temporary copy of the main file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "test_main.bean"
            shutil.copy2(main_file, temp_file)

            # Create ledger with temp file
            ledger = Ledger(str(temp_file))
            initial_count = len(ledger._existing_entries)

            # Get the first existing transaction entry to delete
            existing_entry_id, entry_to_delete = _find_first_transaction_entry(
                ledger._existing_entries
            )

            assert existing_entry_id is not None, (
                "No Transaction entries found in ledger"
            )

            # Store details to verify deletion
            deleted_date = entry_to_delete.date
            deleted_payee = (
                entry_to_delete.payee if hasattr(entry_to_delete, "payee") else None
            )
            deleted_narration = (
                entry_to_delete.narration
                if hasattr(entry_to_delete, "narration")
                else None
            )

            # Remove the entry
            result = ledger.remove(existing_entry_id)
            assert result is True
            assert ledger.dirty
            assert existing_entry_id in ledger._deleted_entries

            # Save changes (this uses real TextEditor)
            ledger.save()

            # Verify state after save
            assert not ledger.dirty
            assert existing_entry_id not in ledger._existing_entries
            assert len(ledger._deleted_entries) == 0
            assert len(ledger._existing_entries) == initial_count - 1

            # Reload the file with beancount and verify the transaction was deleted
            reloaded_entries, _, _ = load_file(str(temp_file))

            # Verify the deleted transaction is not in the reloaded entries
            deleted_transaction_found = _transaction_exists_in_entries(
                reloaded_entries, deleted_date, deleted_payee, deleted_narration
            )

            assert not deleted_transaction_found, (
                "Deleted transaction should not be present in reloaded file"
            )

            # Verify the total number of entries decreased by 1
            assert len(reloaded_entries) == initial_count - 1
