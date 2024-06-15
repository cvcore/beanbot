import pytest

from beancount.loader import load_file
from beancount.core.data import Entries

from beanbot.data import directive


@pytest.fixture
def bc_entries() -> Entries:
    BEANCOUNT_FILE = "tests/data/main.bean"
    entries, errors, options = load_file(BEANCOUNT_FILE)
    return entries


def test_make_mutable(bc_entries):
    for ent in bc_entries:
        ent_mutable = directive.make_mutable(ent)
        # try to change something
        for attr in ent_mutable._asdict().keys():
            if attr == "meta":
                continue
            setattr(ent_mutable, attr, "test")
            captured = False
            try:
                setattr(ent, attr, "test")
            except AttributeError:
                captured = True
            assert captured, "Original entry should not be mutable!"
        print(ent)
        print(ent_mutable)


def test_make_immutable(bc_entries):
    for ent in bc_entries:
        ent_mutable = directive.make_mutable(ent)
        ent_immutable = ent_mutable.to_immutable()
        # try to change something
        for attr in ent_immutable._asdict().keys():
            if attr == "meta":
                continue
            captured = False
            try:
                setattr(ent_immutable, attr, "test")
            except AttributeError:
                captured = True
            assert captured, "entry should be immutable!"
        print(ent)
        print(ent_immutable)


def test_equity(bc_entries):
    for ent in bc_entries:
        ent_mutable = directive.make_mutable(ent)
        ent_immutable = ent_mutable.to_immutable()
        assert (
            ent == ent_immutable
        ), f"entry {ent_immutable} is not identical to the original one {ent}!"
