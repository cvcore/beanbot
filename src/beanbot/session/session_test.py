from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest
from beancount.core.amount import Amount
from beancount.core.data import EMPTY_SET, Posting, Transaction

from beanbot.data.directive import MutableDirective, to_mutable
from beanbot.ledger.ledger import Ledger
from beanbot.session.session import Session
from beanbot.utils.id_generator import IDGenerator


@pytest.fixture(name="mock_ledger")
def fixture_mock_ledger():
    """Create a mock ledger for testing."""
    ledger = Mock(spec=Ledger)
    ledger.id_generator = IDGenerator()
    ledger.has_entry = Mock(return_value=False)
    ledger.add = Mock()
    ledger.delete = Mock(return_value=True)
    ledger.replace = Mock(return_value="test_id")
    ledger.save = Mock()
    ledger.load = Mock()
    ledger.dirty = Mock(return_value=False)
    return ledger


@pytest.fixture(name="session")
def fixture_session(mock_ledger):
    """Create a session with mock ledger."""
    return Session(mock_ledger)


@pytest.fixture(name="sample_transaction")
def fixture_sample_transaction():
    """Create a sample transaction for testing."""
    return Transaction(
        meta={},
        date=date(2023, 1, 1),
        flag="*",
        payee="Test Payee",
        narration="Test Transaction",
        tags=EMPTY_SET,
        links=EMPTY_SET,
        postings=[
            Posting(
                account="Assets:Checking",
                units=Amount(Decimal("100.00"), "USD"),
                cost=None,
                price=None,
                flag=None,
                meta={},
            ),
            Posting(
                account="Expenses:Food",
                units=Amount(Decimal("-100.00"), "USD"),
                cost=None,
                price=None,
                flag=None,
                meta={},
            ),
        ],
    )


class TestSessionAdd:
    """Test the add method."""

    def test_add_directive_generates_id(self, session, sample_transaction):
        """Test adding a Directive generates a new ID."""
        entry_id = session.add(sample_transaction)

        assert entry_id is not None
        assert entry_id in session.new_entries
        assert isinstance(session.new_entries[entry_id], MutableDirective)
        assert session.new_entries[entry_id].id == entry_id

    def test_add_mutable_directive_without_id(self, session, sample_transaction):
        """Test adding a MutableDirective without ID generates a new ID."""
        mutable_entry = to_mutable(sample_transaction)
        entry_id = session.add(mutable_entry)

        assert entry_id is not None
        assert entry_id in session.new_entries
        assert session.new_entries[entry_id].id == entry_id

    def test_add_mutable_directive_with_unique_id(self, session, sample_transaction):
        """Test adding a MutableDirective with unique ID uses that ID."""
        mutable_entry = to_mutable(sample_transaction)
        custom_id = "custom_test_id"
        mutable_entry.id = custom_id

        entry_id = session.add(mutable_entry)

        assert entry_id == custom_id
        assert custom_id in session.new_entries
        assert session.new_entries[custom_id].id == custom_id

    def test_add_mutable_directive_with_existing_id_raises_error(
        self, session, sample_transaction
    ):
        """Test adding a MutableDirective with existing ID raises ValueError."""
        # First add an entry to register the ID
        first_entry = to_mutable(sample_transaction)
        first_id = session.add(first_entry)

        # Try to add another entry with the same ID
        second_entry = to_mutable(sample_transaction)
        second_entry.id = first_id

        with pytest.raises(
            ValueError, match=f"Entry with ID '{first_id}' already exists"
        ):
            session.add(second_entry)

    def test_session_dirty_after_add(self, session, sample_transaction):
        """Test session becomes dirty after adding an entry."""
        assert not session.dirty()

        session.add(sample_transaction)

        assert session.dirty()


class TestSessionDelete:
    """Test the delete method."""

    def test_delete_new_entry(self, session, sample_transaction):
        """Test deleting a newly added entry removes it from new_entries."""
        entry_id = session.add(sample_transaction)
        assert entry_id in session.new_entries

        result = session.delete(entry_id)

        assert result is True
        assert entry_id not in session.new_entries

    def test_delete_existing_entry_in_session(self, session, sample_transaction):
        """Test deleting an existing entry marks it for deletion."""
        # Simulate an existing entry loaded into session
        mutable_entry = to_mutable(sample_transaction)
        entry_id = "existing_id"
        mutable_entry.id = entry_id
        session.existing_entries[entry_id] = mutable_entry

        result = session.delete(entry_id)

        assert result is True
        assert entry_id not in session.existing_entries
        assert entry_id in session.deleted_entries

    def test_delete_entry_in_ledger_only(self, session):
        """Test deleting an entry that exists only in ledger marks it for deletion."""
        entry_id = "ledger_only_id"
        session.ledger.has_entry.return_value = True

        result = session.delete(entry_id)

        assert result is True
        assert entry_id in session.deleted_entries
        session.ledger.has_entry.assert_called_with(entry_id)

    def test_delete_nonexistent_entry(self, session):
        """Test deleting a nonexistent entry returns False."""
        session.ledger.has_entry.return_value = False

        result = session.delete("nonexistent_id")

        assert result is False
        assert "nonexistent_id" not in session.deleted_entries

    def test_delete_already_deleted_entry(self, session):
        """Test deleting an already deleted entry returns True."""
        entry_id = "already_deleted"
        session.deleted_entries.add(entry_id)

        result = session.delete(entry_id)

        assert result is True
        assert entry_id in session.deleted_entries


class TestSessionCommit:
    """Test the commit method."""

    def test_commit_new_entries(self, session, sample_transaction):
        """Test committing new entries calls ledger.add."""
        _ = session.add(sample_transaction)

        session.commit()

        session.ledger.add.assert_called_once()
        assert len(session.new_entries) == 0

    def test_commit_deleted_entries(self, session):
        """Test committing deleted entries calls ledger.delete."""
        entry_id = "to_delete"
        session.deleted_entries.add(entry_id)

        session.commit()

        session.ledger.delete.assert_called_once_with(entry_id)
        assert len(session.deleted_entries) == 0

    def test_commit_modified_existing_entries(self, session, sample_transaction):
        """Test committing modified existing entries calls ledger.replace."""
        # Create a dirty existing entry
        mutable_entry = to_mutable(sample_transaction)
        entry_id = "existing_modified"
        mutable_entry.id = entry_id
        mutable_entry.narration = "Dummy modification narration"
        assert mutable_entry.dirty()
        session.existing_entries[entry_id] = mutable_entry

        session.commit()

        session.ledger.replace.assert_called_once_with(
            entry_id, mutable_entry.to_immutable()
        )
        assert len(session.existing_entries) == 0

    def test_commit_calls_ledger_save_and_load(self, session):
        """Test commit calls ledger.save() and ledger.load()."""
        session.commit()

        session.ledger.save.assert_called_once()
        session.ledger.load.assert_called_once()

    def test_commit_clears_session_state(self, session, sample_transaction):
        """Test commit clears all session state."""
        # Add some state
        session.add(sample_transaction)
        session.deleted_entries.add("deleted_id")
        mutable_entry = to_mutable(sample_transaction)
        session.existing_entries["existing_id"] = mutable_entry

        session.commit()

        assert len(session.new_entries) == 0
        assert len(session.deleted_entries) == 0
        assert len(session.existing_entries) == 0


class TestSessionModifyNewDirective:
    """Test modifying a newly added directive before commit."""

    def test_modify_new_directive_and_commit(self, session, sample_transaction):
        """Test modifying a newly added directive and then committing."""
        # Add a new entry
        entry_id = session.add(sample_transaction)
        mutable_entry = session.new_entries[entry_id]
        assert isinstance(mutable_entry, MutableDirective)

        # Modify the entry
        original_narration = mutable_entry.narration
        new_narration = "Modified narration"
        mutable_entry.narration = new_narration

        # Verify modification
        assert mutable_entry.narration == new_narration
        assert mutable_entry.narration != original_narration
        assert mutable_entry.dirty()
        assert session.dirty()

        # Commit the changes
        session.commit()

        # Verify the modified entry was passed to ledger
        session.ledger.add.assert_called_once()
        committed_directive = session.ledger.add.call_args[0][0]
        assert committed_directive.narration == new_narration

        # Verify session is clean
        assert not session.dirty()
        assert len(session.new_entries) == 0

    def test_modify_new_directive_multiple_times(self, session, sample_transaction):
        """Test multiple modifications to a new directive before commit."""
        # Add a new entry
        entry_id = session.add(sample_transaction)
        mutable_entry = session.new_entries[entry_id]

        # Make multiple modifications
        mutable_entry.narration = "First modification"
        mutable_entry.payee = "Modified Payee"

        # Verify all modifications
        assert mutable_entry.narration == "First modification"
        assert mutable_entry.payee == "Modified Payee"

        # Commit and verify
        session.commit()

        committed_directive = session.ledger.add.call_args[0][0]
        assert committed_directive.narration == "First modification"
        assert committed_directive.payee == "Modified Payee"

    def test_modify_new_directive_postings(self, session, sample_transaction):
        """Test modifying postings of a newly added directive."""
        # Add a new entry
        entry_id = session.add(sample_transaction)
        mutable_entry = session.new_entries[entry_id]

        # Modify a posting amount
        original_amount = mutable_entry.postings[0].units.number
        new_amount = Decimal("200.00")
        mutable_entry.postings[0].units = Amount(new_amount, "USD")
        mutable_entry.postings[1].units = Amount(-new_amount, "USD")

        # Verify modification
        assert mutable_entry.postings[0].units.number == new_amount
        assert mutable_entry.postings[0].units.number != original_amount

        # Commit and verify
        session.commit()

        committed_directive = session.ledger.add.call_args[0][0]
        assert committed_directive.postings[0].units.number == new_amount


class TestSessionDirtyState:
    """Test dirty state tracking."""

    def test_clean_session_not_dirty(self, session):
        """Test a clean session is not dirty."""
        assert not session.dirty()

    def test_session_dirty_with_new_entries(self, session, sample_transaction):
        """Test session is dirty when it has new entries."""
        session.add(sample_transaction)
        assert session.dirty()

    def test_session_dirty_with_deleted_entries(self, session):
        """Test session is dirty when it has deleted entries."""
        session.deleted_entries.add("deleted_id")
        assert session.dirty()

    def test_session_dirty_with_modified_existing_entries(
        self, session, sample_transaction
    ):
        """Test session is dirty when existing entries are modified."""
        mutable_entry = to_mutable(sample_transaction)
        mutable_entry.narration = "Dummy modification narration"
        assert mutable_entry.dirty()
        session.existing_entries["existing_id"] = mutable_entry

        assert session.dirty()
