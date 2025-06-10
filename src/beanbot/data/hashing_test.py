import datetime
import hashlib
from beancount import D, Amount
from beancount.core import data
from beancount.parser import printer
from beanbot.data.hashing import stable_hash


def test_stable_hash_same_entry_same_hash():
    entry = data.Transaction(
        meta={"lineno": 1},
        date=datetime.date(2024, 6, 1),
        flag="*",
        payee="Payee",
        narration="Narration",
        tags=frozenset(),
        links=frozenset(),
        postings=[],
    )
    h1 = stable_hash(entry)
    h2 = stable_hash(entry)
    assert h1 == h2
    assert isinstance(h1, str)
    assert len(h1) == 64  # sha256 hex digest


def test_stable_hash_with_postings():
    entry = data.Transaction(
        meta={"lineno": 1},
        date=datetime.date(2024, 6, 1),
        flag="*",
        payee="Payee",
        narration="Narration",
        tags=frozenset(),
        links=frozenset(),
        postings=[
            data.Posting(
                flag="",
                account="Expenses:Food",
                units=Amount(D("100"), "USD"),
                cost=None,
                price=None,
                meta={"lineno": 2},
            ),
            data.Posting(
                flag="",
                account="Assets:Cash",
                units=Amount(D("-100"), "USD"),
                cost=None,
                price=None,
                meta={"lineno": 3},
            ),
        ],
    )
    h1 = stable_hash(entry)
    h2 = stable_hash(entry)
    assert h1 == h2
    assert isinstance(h1, str)
    assert len(h1) == 64  # sha256 hex digest


def test_stable_hash_different_entries_different_hash():
    entry1 = data.Transaction(
        meta={"lineno": 1},
        date=datetime.date(2024, 6, 1),
        flag="*",
        payee="Payee1",
        narration="Narration",
        tags=frozenset(),
        links=frozenset(),
        postings=[],
    )
    entry2 = data.Transaction(
        meta={"lineno": 1},
        date=datetime.date(2024, 6, 1),
        flag="*",
        payee="Payee2",
        narration="Narration",
        tags=frozenset(),
        links=frozenset(),
        postings=[],
    )
    h1 = stable_hash(entry1)
    h2 = stable_hash(entry2)
    assert h1 != h2


def test_stable_hash_matches_manual_hash():
    entry = data.Transaction(
        meta={"lineno": 1},
        date=datetime.date(2024, 6, 1),
        flag="*",
        payee="Payee",
        narration="Narration",
        tags=frozenset(),
        links=frozenset(),
        postings=[],
    )
    entry_str = printer.EntryPrinter()(entry)
    expected = hashlib.sha256(entry_str.encode("utf-8")).hexdigest()
    assert stable_hash(entry) == expected


def test_stable_hash_change_posting_order():
    entry1 = data.Transaction(
        meta={"lineno": 1},
        date=datetime.date(2024, 6, 1),
        flag="*",
        payee="Payee",
        narration="Narration",
        tags=frozenset(),
        links=frozenset(),
        postings=[
            data.Posting(
                flag="",
                account="Expenses:Food",
                units=Amount(D("100"), "USD"),
                cost=None,
                price=None,
                meta={"lineno": 2},
            ),
            data.Posting(
                flag="",
                account="Assets:Cash",
                units=Amount(D("-100"), "USD"),
                cost=None,
                price=None,
                meta={"lineno": 3},
            ),
        ],
    )
    entry2 = data.Transaction(
        meta={"lineno": 1},
        date=datetime.date(2024, 6, 1),
        flag="*",
        payee="Payee",
        narration="Narration",
        tags=frozenset(),
        links=frozenset(),
        postings=[
            data.Posting(
                flag="",
                account="Assets:Cash",
                units=Amount(D("-100"), "USD"),
                cost=None,
                price=None,
                meta={"lineno": 3},
            ),
            data.Posting(
                flag="",
                account="Expenses:Food",
                units=Amount(D("100"), "USD"),
                cost=None,
                price=None,
                meta={"lineno": 2},
            ),
        ],
    )
    h1 = stable_hash(entry1)
    h2 = stable_hash(entry2)
    assert h1 != h2, "Hash should differ when posting order changes"
