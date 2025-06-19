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
)


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
    def test_construction(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction, id="txn_1")
        assert mutable.id == "txn_1"
        assert mutable.directive == sample_transaction
        assert not mutable.dirty()

    def test_attribute_access(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        assert mutable.date == date(2024, 1, 1)
        assert mutable.flag == "*"
        assert mutable.payee == "Test Payee"
        assert mutable.narration == "Test transaction"

    def test_attribute_modification(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        mutable.narration = "Modified narration"
        assert mutable.narration == "Modified narration"
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_transaction

    def test_reset_method(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)

        # Modify some attributes
        mutable.narration = "Modified narration"
        mutable.payee = "Modified payee"
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.narration == sample_transaction.narration
        assert mutable.payee == sample_transaction.payee


class TestMutableOpen:
    def test_construction(self, sample_open):
        mutable = MutableOpen(sample_open, id="open_1")
        assert mutable.id == "open_1"
        assert mutable.directive == sample_open
        assert mutable.account == "Assets:Cash"

    def test_attribute_modification(self, sample_open):
        mutable = MutableOpen(sample_open)
        mutable.account = "Assets:Bank"
        assert mutable.account == "Assets:Bank"
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_open):
        mutable = MutableOpen(sample_open)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_open

    def test_reset_method(self, sample_open):
        mutable = MutableOpen(sample_open)

        # Modify attribute
        mutable.account = "Assets:Bank"
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.account == sample_open.account


class TestMutableClose:
    def test_construction(self, sample_close):
        mutable = MutableClose(sample_close, id="close_1")
        assert mutable.id == "close_1"
        assert mutable.directive == sample_close
        assert mutable.account == "Assets:Cash"

    def test_attribute_modification(self, sample_close):
        mutable = MutableClose(sample_close)
        mutable.date = date(2024, 6, 30)
        assert mutable.date == date(2024, 6, 30)
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_close):
        mutable = MutableClose(sample_close)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_close

    def test_reset_method(self, sample_close):
        mutable = MutableClose(sample_close)

        # Modify attribute
        mutable.date = date(2024, 6, 30)
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.date == sample_close.date


class TestMutableBalance:
    def test_construction(self, sample_balance):
        mutable = MutableBalance(sample_balance, id="balance_1")
        assert mutable.id == "balance_1"
        assert mutable.directive == sample_balance
        assert mutable.account == "Assets:Cash"

    def test_attribute_modification(self, sample_balance):
        mutable = MutableBalance(sample_balance)
        new_amount = Amount(Decimal("2000"), "USD")
        mutable.amount = new_amount
        assert mutable.amount == new_amount
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_balance):
        mutable = MutableBalance(sample_balance)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_balance

    def test_reset_method(self, sample_balance):
        mutable = MutableBalance(sample_balance)

        # Modify attribute
        new_amount = Amount(Decimal("2000"), "USD")
        mutable.amount = new_amount
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.amount == sample_balance.amount


class TestMutablePad:
    def test_construction(self, sample_pad):
        mutable = MutablePad(sample_pad, id="pad_1")
        assert mutable.id == "pad_1"
        assert mutable.directive == sample_pad
        assert mutable.account == "Assets:Cash"

    def test_attribute_modification(self, sample_pad):
        mutable = MutablePad(sample_pad)
        mutable.source_account = "Equity:Opening-Balance"
        assert mutable.source_account == "Equity:Opening-Balance"
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_pad):
        mutable = MutablePad(sample_pad)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_pad

    def test_reset_method(self, sample_pad):
        mutable = MutablePad(sample_pad)

        # Modify attribute
        mutable.source_account = "Equity:Opening-Balance"
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.source_account == sample_pad.source_account


class TestMutableNote:
    def test_construction(self, sample_note):
        mutable = MutableNote(sample_note, id="note_1")
        assert mutable.id == "note_1"
        assert mutable.directive == sample_note
        assert mutable.comment == "Test note"

    def test_attribute_modification(self, sample_note):
        mutable = MutableNote(sample_note)
        mutable.comment = "Modified note"
        assert mutable.comment == "Modified note"
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_note):
        mutable = MutableNote(sample_note)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_note

    def test_reset_method(self, sample_note):
        mutable = MutableNote(sample_note)

        # Modify attribute
        mutable.comment = "Modified note"
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.comment == sample_note.comment


class TestMutableEvent:
    def test_construction(self, sample_event):
        mutable = MutableEvent(sample_event, id="event_1")
        assert mutable.id == "event_1"
        assert mutable.directive == sample_event
        assert mutable.type == "location"

    def test_attribute_modification(self, sample_event):
        mutable = MutableEvent(sample_event)
        mutable.description = "San Francisco"
        assert mutable.description == "San Francisco"
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_event):
        mutable = MutableEvent(sample_event)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_event

    def test_reset_method(self, sample_event):
        mutable = MutableEvent(sample_event)

        # Modify attribute
        mutable.description = "San Francisco"
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.description == sample_event.description


class TestMutableQuery:
    def test_construction(self, sample_query):
        mutable = MutableQuery(sample_query, id="query_1")
        assert mutable.id == "query_1"
        assert mutable.directive == sample_query
        assert mutable.name == "test_query"

    def test_attribute_modification(self, sample_query):
        mutable = MutableQuery(sample_query)
        mutable.name = "modified_query"
        assert mutable.name == "modified_query"
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_query):
        mutable = MutableQuery(sample_query)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_query

    def test_reset_method(self, sample_query):
        mutable = MutableQuery(sample_query)

        # Modify attribute
        mutable.name = "modified_query"
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.name == sample_query.name


class TestMutablePrice:
    def test_construction(self, sample_price):
        mutable = MutablePrice(sample_price, id="price_1")
        assert mutable.id == "price_1"
        assert mutable.directive == sample_price
        assert mutable.currency == "AAPL"

    def test_attribute_modification(self, sample_price):
        mutable = MutablePrice(sample_price)
        new_amount = Amount(Decimal("155.00"), "USD")
        mutable.amount = new_amount
        assert mutable.amount == new_amount
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_price):
        mutable = MutablePrice(sample_price)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_price

    def test_reset_method(self, sample_price):
        mutable = MutablePrice(sample_price)

        # Modify attribute
        new_amount = Amount(Decimal("155.00"), "USD")
        mutable.amount = new_amount
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.amount == sample_price.amount


class TestMutableDocument:
    def test_construction(self, sample_document):
        mutable = MutableDocument(sample_document, id="doc_1")
        assert mutable.id == "doc_1"
        assert mutable.directive == sample_document
        assert mutable.filename == "receipt.pdf"

    def test_attribute_modification(self, sample_document):
        mutable = MutableDocument(sample_document)
        mutable.filename = "invoice.pdf"
        assert mutable.filename == "invoice.pdf"
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_document):
        mutable = MutableDocument(sample_document)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_document

    def test_reset_method(self, sample_document):
        mutable = MutableDocument(sample_document)

        # Modify attribute
        mutable.filename = "invoice.pdf"
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.filename == sample_document.filename


class TestMutableCustom:
    def test_construction(self, sample_custom):
        mutable = MutableCustom(sample_custom, id="custom_1")
        assert mutable.id == "custom_1"
        assert mutable.directive == sample_custom
        assert mutable.type == "budget"

    def test_attribute_modification(self, sample_custom):
        mutable = MutableCustom(sample_custom)
        mutable.type = "forecast"
        assert mutable.type == "forecast"
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_custom):
        mutable = MutableCustom(sample_custom)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_custom

    def test_reset_method(self, sample_custom):
        mutable = MutableCustom(sample_custom)

        # Modify attribute
        mutable.type = "forecast"
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.type == sample_custom.type


class TestMutableCommodity:
    def test_construction(self, sample_commodity):
        mutable = MutableCommodity(sample_commodity, id="commodity_1")
        assert mutable.id == "commodity_1"
        assert mutable.directive == sample_commodity
        assert mutable.currency == "USD"

    def test_attribute_modification(self, sample_commodity):
        mutable = MutableCommodity(sample_commodity)
        mutable.currency = "EUR"
        assert mutable.currency == "EUR"
        assert mutable.dirty()

    def test_round_trip_conversion(self, sample_commodity):
        mutable = MutableCommodity(sample_commodity)
        converted_back = mutable.to_immutable()
        assert converted_back == sample_commodity

    def test_reset_method(self, sample_commodity):
        mutable = MutableCommodity(sample_commodity)

        # Modify attribute
        mutable.currency = "EUR"
        assert mutable.dirty()

        # Reset changes
        mutable.reset()
        assert not mutable.dirty()
        assert mutable.currency == sample_commodity.currency


class TestMutableDirectiveDirty:
    def test_initially_not_dirty(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        assert not mutable.dirty()

    def test_dirty_after_modification(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        mutable.narration = "Modified narration"
        assert mutable.dirty()

    def test_not_dirty_after_reverting_to_original(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        original_narration = mutable.narration

        # Modify and verify it's dirty
        mutable.narration = "Modified"
        assert mutable.dirty()

        # Revert to original value
        mutable.narration = original_narration
        assert not mutable.dirty()

    def test_dirty_with_multiple_changes(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        mutable.narration = "Modified narration"
        mutable.payee = "Modified payee"
        assert mutable.dirty()

    def test_partially_reverted_still_dirty(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        original_narration = mutable.narration

        # Make multiple changes
        mutable.narration = "Modified narration"
        mutable.payee = "Modified payee"
        assert mutable.dirty()

        # Revert one change, should still be dirty
        mutable.narration = original_narration
        assert mutable.dirty()


class TestMutableDirectiveBase:
    def test_invalid_attribute_access(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        with pytest.raises(AttributeError):
            _ = mutable.nonexistent_attribute

    def test_invalid_attribute_modification(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        with pytest.raises(AttributeError):
            mutable.nonexistent_attribute = "value"

    def test_revert_to_original_value(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)
        original_narration = mutable.narration

        # Modify the attribute
        mutable.narration = "Modified"
        assert mutable.dirty()

        # Verify change is reflected in conversion
        converted = mutable.to_immutable()
        assert converted.narration == "Modified"

        # Revert to original value
        mutable.narration = original_narration
        assert not mutable.dirty()

        # Verify revert is reflected in conversion
        converted = mutable.to_immutable()
        assert converted.narration == original_narration

    def test_directive_property_readonly(self, sample_transaction):
        mutable = MutableTransaction(sample_transaction)

        # Modify attribute and verify directive property reflects the change
        mutable.narration = "Changed"
        directive = mutable.directive
        assert directive.narration == "Changed"
        assert directive != sample_transaction  # Should be different from original

        # Verify original directive is unchanged
        assert sample_transaction.narration == "Test transaction"
