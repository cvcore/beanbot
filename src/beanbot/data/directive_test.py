from datetime import date
from decimal import Decimal

import pytest
from beancount.core.amount import Amount
from beancount.core.data import (
    EMPTY_SET,
    Balance,
    Close,
    Commodity,
    Custom,
    Document,
    Event,
    Note,
    Open,
    Pad,
    Posting,
    Price,
    Query,
    Transaction,
)

from .directive import (
    MutableBalance,
    MutableClose,
    MutableCommodity,
    MutableCustom,
    MutableDocument,
    MutableEvent,
    MutableNote,
    MutableOpen,
    MutablePad,
    MutablePrice,
    MutableQuery,
    MutableTransaction,
    Session,
)


class MockSession(Session):
    """Mock session for testing."""

    def __init__(self):
        self.changes = []
        self.states = {}

    def update_state(self, directive, state):
        self.states[directive] = state


@pytest.fixture(name="mock_session")
def fixture_mock_session():
    return MockSession()


@pytest.fixture(name="sample_transaction")
def fixture_sample_transaction():
    return Transaction(
        meta={"filename": "test.beancount", "lineno": 1},
        date=date(2024, 1, 1),
        flag="*",
        payee="Test Payee",
        narration="Test transaction",
        tags=EMPTY_SET,
        links=EMPTY_SET,
        postings=[
            Posting(
                account="Assets:Cash",
                units=Amount(Decimal("100"), "USD"),
                cost=None,
                price=None,
                flag=None,
                meta={},
            )
        ],
    )


@pytest.fixture(name="sample_open")
def fixture_sample_open():
    return Open(
        meta={"filename": "test.beancount", "lineno": 2},
        date=date(2024, 1, 1),
        account="Assets:Cash",
        currencies=["USD"],
        booking=None,
    )


@pytest.fixture(name="sample_close")
def fixture_sample_close():
    return Close(
        meta={"filename": "test.beancount", "lineno": 3},
        date=date(2024, 12, 31),
        account="Assets:Cash",
    )


@pytest.fixture(name="sample_balance")
def fixture_sample_balance():
    return Balance(
        meta={"filename": "test.beancount", "lineno": 4},
        date=date(2024, 1, 1),
        account="Assets:Cash",
        amount=Amount(Decimal("1000"), "USD"),
        tolerance=None,
        diff_amount=None,
    )


@pytest.fixture(name="sample_pad")
def fixture_sample_pad():
    return Pad(
        meta={"filename": "test.beancount", "lineno": 5},
        date=date(2024, 1, 1),
        account="Assets:Cash",
        source_account="Equity:Opening-Balances",
    )


@pytest.fixture(name="sample_note")
def fixture_sample_note():
    return Note(
        tags=None,
        links=None,
        meta={"filename": "test.beancount", "lineno": 6},
        date=date(2024, 1, 1),
        account="Assets:Cash",
        comment="Test note",
    )


@pytest.fixture(name="sample_event")
def fixture_sample_event():
    return Event(
        meta={"filename": "test.beancount", "lineno": 7},
        date=date(2024, 1, 1),
        type="location",
        description="New York",
    )


@pytest.fixture(name="sample_query")
def fixture_sample_query():
    return Query(
        meta={"filename": "test.beancount", "lineno": 8},
        date=date(2024, 1, 1),
        name="test_query",
        query_string="SELECT account, sum(position) GROUP BY account",
    )


@pytest.fixture(name="sample_price")
def fixture_sample_price():
    return Price(
        meta={"filename": "test.beancount", "lineno": 9},
        date=date(2024, 1, 1),
        currency="AAPL",
        amount=Amount(Decimal("150.00"), "USD"),
    )


@pytest.fixture(name="sample_document")
def fixture_sample_document():
    return Document(
        meta={"filename": "test.beancount", "lineno": 10},
        date=date(2024, 1, 1),
        account="Assets:Cash",
        filename="receipt.pdf",
        tags=EMPTY_SET,
        links=EMPTY_SET,
    )


@pytest.fixture(name="sample_custom")
def fixture_sample_custom():
    return Custom(
        meta={"filename": "test.beancount", "lineno": 11},
        date=date(2024, 1, 1),
        type="budget",
        values=["Assets:Cash", Amount(Decimal("1000"), "USD")],
    )


@pytest.fixture(name="sample_commodity")
def fixture_sample_commodity():
    return Commodity(
        meta={"filename": "test.beancount", "lineno": 12},
        date=date(2024, 1, 1),
        currency="USD",
    )


class TestMutableTransaction:
    def test_construction(self, sample_transaction, mock_session):
        mutable = MutableTransaction(sample_transaction, mock_session, id="txn_1")
        assert mutable.id == "txn_1"
        assert mutable.directive == sample_transaction
        assert mutable.session == mock_session
        assert mutable.changes == {}

    def test_attribute_access(self, sample_transaction, mock_session):
        mutable = MutableTransaction(sample_transaction, mock_session)
        assert mutable.date == date(2024, 1, 1)
        assert mutable.flag == "*"
        assert mutable.payee == "Test Payee"
        assert mutable.narration == "Test transaction"

    def test_attribute_modification(self, sample_transaction, mock_session):
        mutable = MutableTransaction(sample_transaction, mock_session)
        mutable.narration = "Modified narration"
        assert mutable.narration == "Modified narration"
        assert "narration" in mutable.changes
        assert mutable.changes["narration"] == "Modified narration"


class TestMutableOpen:
    def test_construction(self, sample_open, mock_session):
        mutable = MutableOpen(sample_open, mock_session, id="open_1")
        assert mutable.id == "open_1"
        assert mutable.directive == sample_open
        assert mutable.account == "Assets:Cash"

    def test_attribute_modification(self, sample_open, mock_session):
        mutable = MutableOpen(sample_open, mock_session)
        mutable.account = "Assets:Bank"
        assert mutable.account == "Assets:Bank"
        assert "account" in mutable.changes


class TestMutableClose:
    def test_construction(self, sample_close, mock_session):
        mutable = MutableClose(sample_close, mock_session, id="close_1")
        assert mutable.id == "close_1"
        assert mutable.directive == sample_close
        assert mutable.account == "Assets:Cash"

    def test_attribute_modification(self, sample_close, mock_session):
        mutable = MutableClose(sample_close, mock_session)
        mutable.date = date(2024, 6, 30)
        assert mutable.date == date(2024, 6, 30)
        assert "date" in mutable.changes


class TestMutableBalance:
    def test_construction(self, sample_balance, mock_session):
        mutable = MutableBalance(sample_balance, mock_session, id="balance_1")
        assert mutable.id == "balance_1"
        assert mutable.directive == sample_balance
        assert mutable.account == "Assets:Cash"

    def test_attribute_modification(self, sample_balance, mock_session):
        mutable = MutableBalance(sample_balance, mock_session)
        new_amount = Amount(Decimal("2000"), "USD")
        mutable.amount = new_amount
        assert mutable.amount == new_amount
        assert "amount" in mutable.changes


class TestMutablePad:
    def test_construction(self, sample_pad, mock_session):
        mutable = MutablePad(sample_pad, mock_session, id="pad_1")
        assert mutable.id == "pad_1"
        assert mutable.directive == sample_pad
        assert mutable.account == "Assets:Cash"

    def test_attribute_modification(self, sample_pad, mock_session):
        mutable = MutablePad(sample_pad, mock_session)
        mutable.source_account = "Equity:Opening-Balance"
        assert mutable.source_account == "Equity:Opening-Balance"
        assert "source_account" in mutable.changes


class TestMutableNote:
    def test_construction(self, sample_note, mock_session):
        mutable = MutableNote(sample_note, mock_session, id="note_1")
        assert mutable.id == "note_1"
        assert mutable.directive == sample_note
        assert mutable.comment == "Test note"

    def test_attribute_modification(self, sample_note, mock_session):
        mutable = MutableNote(sample_note, mock_session)
        mutable.comment = "Modified note"
        assert mutable.comment == "Modified note"
        assert "comment" in mutable.changes


class TestMutableEvent:
    def test_construction(self, sample_event, mock_session):
        mutable = MutableEvent(sample_event, mock_session, id="event_1")
        assert mutable.id == "event_1"
        assert mutable.directive == sample_event
        assert mutable.type == "location"

    def test_attribute_modification(self, sample_event, mock_session):
        mutable = MutableEvent(sample_event, mock_session)
        mutable.description = "San Francisco"
        assert mutable.description == "San Francisco"
        assert "description" in mutable.changes


class TestMutableQuery:
    def test_construction(self, sample_query, mock_session):
        mutable = MutableQuery(sample_query, mock_session, id="query_1")
        assert mutable.id == "query_1"
        assert mutable.directive == sample_query
        assert mutable.name == "test_query"

    def test_attribute_modification(self, sample_query, mock_session):
        mutable = MutableQuery(sample_query, mock_session)
        mutable.name = "modified_query"
        assert mutable.name == "modified_query"
        assert "name" in mutable.changes


class TestMutablePrice:
    def test_construction(self, sample_price, mock_session):
        mutable = MutablePrice(sample_price, mock_session, id="price_1")
        assert mutable.id == "price_1"
        assert mutable.directive == sample_price
        assert mutable.currency == "AAPL"

    def test_attribute_modification(self, sample_price, mock_session):
        mutable = MutablePrice(sample_price, mock_session)
        new_amount = Amount(Decimal("155.00"), "USD")
        mutable.amount = new_amount
        assert mutable.amount == new_amount
        assert "amount" in mutable.changes


class TestMutableDocument:
    def test_construction(self, sample_document, mock_session):
        mutable = MutableDocument(sample_document, mock_session, id="doc_1")
        assert mutable.id == "doc_1"
        assert mutable.directive == sample_document
        assert mutable.filename == "receipt.pdf"

    def test_attribute_modification(self, sample_document, mock_session):
        mutable = MutableDocument(sample_document, mock_session)
        mutable.filename = "invoice.pdf"
        assert mutable.filename == "invoice.pdf"
        assert "filename" in mutable.changes


class TestMutableCustom:
    def test_construction(self, sample_custom, mock_session):
        mutable = MutableCustom(sample_custom, mock_session, id="custom_1")
        assert mutable.id == "custom_1"
        assert mutable.directive == sample_custom
        assert mutable.type == "budget"

    def test_attribute_modification(self, sample_custom, mock_session):
        mutable = MutableCustom(sample_custom, mock_session)
        mutable.type = "forecast"
        assert mutable.type == "forecast"
        assert "type" in mutable.changes


class TestMutableCommodity:
    def test_construction(self, sample_commodity, mock_session):
        mutable = MutableCommodity(sample_commodity, mock_session, id="commodity_1")
        assert mutable.id == "commodity_1"
        assert mutable.directive == sample_commodity
        assert mutable.currency == "USD"

    def test_attribute_modification(self, sample_commodity, mock_session):
        mutable = MutableCommodity(sample_commodity, mock_session)
        mutable.currency = "EUR"
        assert mutable.currency == "EUR"
        assert "currency" in mutable.changes


class TestMutableDirectiveBase:
    def test_invalid_attribute_access(self, sample_transaction, mock_session):
        mutable = MutableTransaction(sample_transaction, mock_session)
        with pytest.raises(AttributeError):
            _ = mutable.nonexistent_attribute

    def test_invalid_attribute_modification(self, sample_transaction, mock_session):
        mutable = MutableTransaction(sample_transaction, mock_session)
        with pytest.raises(AttributeError):
            mutable.nonexistent_attribute = "value"

    def test_revert_to_original_value(self, sample_transaction, mock_session):
        mutable = MutableTransaction(sample_transaction, mock_session)
        original_narration = mutable.narration

        # Modify the attribute
        mutable.narration = "Modified"
        assert "narration" in mutable.changes

        # Revert to original value
        mutable.narration = original_narration
        assert "narration" not in mutable.changes

    def test_session_assignment_error(self, sample_transaction, mock_session):
        mutable = MutableTransaction(sample_transaction, mock_session)
        with pytest.raises(AttributeError, match="Forbidden: can't modify attribute"):
            mutable.session = MockSession()

    def test_directive_assignment_error(self, sample_transaction, mock_session):
        mutable = MutableTransaction(sample_transaction, mock_session)
        with pytest.raises(AttributeError, match="Forbidden: can't modify attribute"):
            mutable.directive = sample_transaction

    def test_changes_assignment_error(self, sample_transaction, mock_session):
        mutable = MutableTransaction(sample_transaction, mock_session)
        with pytest.raises(AttributeError, match="Forbidden: can't modify attribute"):
            mutable.changes = {}
