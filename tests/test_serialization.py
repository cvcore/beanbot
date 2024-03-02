from copy import deepcopy
import datetime
import json

from beanbot.backend import serialization


def test_serializer():
    data = {
        "string": "string_a",
        "integer": 1,
        "float": 1.0,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"a": 1, "b": 2, "c": [1, 2, {"d": 3}]},
        "none": None,
        "date": datetime.date(2020, 1, 1),
    }

    data_expected = deepcopy(data)
    data_expected["date"] = ("___serialized_obj___", "date", ["2020-01-01"])

    data_serialized = serialization.serialize_dict(data)

    assert data_serialized == data_expected


def test_deserializer():
    data = {
        "string": "string_a",
        "integer": 1,
        "float": 1.0,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"a": 1, "b": 2, "c": [1, 2, {"d": 3}]},
        "none": None,
        "date": ("___serialized_obj___", "date", ["2020-01-01"]),
    }

    data_expected = deepcopy(data)
    data_expected["date"] = datetime.date(2020, 1, 1)

    data_deserialized = serialization.deserialize_object(data)

    assert data_deserialized == data_expected


def test_json_compatible():
    data = {
        "string": "string_a",
        "integer": 1,
        "float": 1.0,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"a": 1, "b": 2, "c": [1, 2, {"d": 3}]},
        "none": None,
        "date": datetime.date(2020, 1, 1),
    }

    data_serialized = serialization.serialize_dict(deepcopy(data))
    json_s = json.dumps(data_serialized)
    json_d = json.loads(json_s)
    data_deserialized = serialization.deserialize_dict(json_d)
    assert data_deserialized == data
