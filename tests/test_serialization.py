from pathlib import Path
import pytest
import json

from beancount.core.data import Transaction
from beancount.loader import load_file

# Import the serialization functions
from beanbot.common.configs import BeanbotConfig
from beanbot.data.serialization import (
    serialize_object,
)

global_config = BeanbotConfig.get_global()
global_config.parse_file(str(Path(__file__).parent / "data" / "main.bean"))
TEST_FILE_SAMPLE = global_config["main-file"]


@pytest.fixture
def read_transactions():
    """Read transactions from the test file."""
    entries, errors, options = load_file(TEST_FILE_SAMPLE)
    return [entry for entry in entries if isinstance(entry, Transaction)]


def test_serialize_object(read_transactions):
    entries = read_transactions
    sobj = serialize_object(entries[0])
    json_str = json.dumps(sobj)
    print(json_str)


if __name__ == "__main__":
    pytest.main(["-v"])
