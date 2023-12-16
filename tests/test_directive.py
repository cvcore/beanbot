import pytest

from beanbot.data import directive
from beanbot.data.entries import BeancountEntries


bc_entries = BeancountEntries.from_path("/Users/core/Development/Finance/beanbot/tests/data/main.bean")

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
            except:
                captured = True
            assert captured, f"Original entry should not be mutable!"
        print(ent)
        print(ent_mutable)


test_make_mutable()
