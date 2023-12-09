from copy import deepcopy
import datetime
import pytest

from beanbot.backend import data, serialization


def test_serializer():
    data = {
        "string": "string_a",
        "integer": 1,
        "float": 1.0,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"a": 1, "b": 2},
        "none": None,
        "date": datetime.date(2020, 1, 1),
        None: "null",
    }

    data_expected = deepcopy(data)
    data_expected["date"] = "2020-01-01"

    data_serialized = serialization.serialize_dict(data)

    assert data_serialized == data_expected

def test_deserializer():
    data = {
        "string": "string_a",
        "integer": 1,
        "float": 1.0,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"a": 1, "b": 2},
        "none": None,
        "date": "2020-01-01",
        None: "null",
    }

    data_expected = deepcopy(data)
    data_expected["date"] = datetime.date(2020, 1, 1)

    data_deserialized = serialization.deserialize_dict(
        data,
        fn_deserialize={
            "date": lambda d: datetime.datetime.strptime(d, "%Y-%m-%d").date(),
        },
    )

    assert data_deserialized == data_expected
