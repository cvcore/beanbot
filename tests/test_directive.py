import pytest

from beanbot.data import directive
from beanbot.data.entries import MutableEntriesContainer


bc_entries = MutableEntriesContainer.load_from_file("/Users/core/Development/Finance/beanbot/tests/data/main.bean")

def test_make_mutable():
    for ent in bc_entries.entries:
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
            assert captured, f"Original entry should not be mutable!"
        print(ent)
        print(ent_mutable)


def test_make_immutable():
    for ent in bc_entries.entries:
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
            assert captured, f"entry should be immutable!"
        print(ent)
        print(ent_immutable)


def test_equity():
    for ent in bc_entries.entries:
        ent_mutable = directive.make_mutable(ent)
        ent_immutable = ent_mutable.to_immutable()
        assert ent == ent_immutable, f"entry {ent_immutable} is not identical to the original one {ent}!"
