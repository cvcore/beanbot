from __future__ import annotations

import datetime
from decimal import Decimal
from functools import cache
from types import NoneType, UnionType
from typing import Any, Callable, Dict, List, Optional, Tuple, _UnionGenericAlias
import uuid
from beancount.parser.grammar import ValueType
from beancount.utils.defdict import ImmutableDictWithDefault
from beancount.core.data import Directive, Posting, TxnPosting, Booking
from beancount.core.amount import Amount
from beancount.core.position import Cost, CostSpec

class _DummyType:
    pass

# The Listlike and Dictlike types will be first converted to a magic tuple (a 3-tuple containing the type info),
# then serialized as a list or dict respectively.
Listlike = _DummyType
Dictlike = Directive | ImmutableDictWithDefault | Posting | TxnPosting | Amount | Cost | CostSpec

# The Primitives types are natively json-serializable.
Primitives = str | int | float | bool | NoneType


_MAGIC_STR_SER_OBJ = "___serialized_obj___"
_MAGIC_STR_SER_LIST = "___serialized_list___"
_MAGIC_STR_SER_DICT = "___serialized_dict___"


_DEFAULT_FN_SERIALIZE = {
    datetime.date: lambda d: [d.isoformat()],
    uuid.UUID: lambda u: [str(u)],
    ValueType: lambda v: [v.value, str(v.dtype)],
    Decimal: lambda d: [str(d)],
    set: lambda s: [list(s)],
    frozenset: lambda s: [list(s)],
    Booking: lambda b: [b.name],
}


_DEFAULT_FN_DESERIALIZE = {
    "date": lambda params: datetime.datetime.strptime(params[0], "%Y-%m-%d").date(),
    "UUID": lambda params: uuid.UUID(params[0]),
    "ValueType": lambda params: ValueType(type(params[1])(params[0]), type(params[1])),
    "Decimal": lambda params: Decimal(params[0]),
    "set": lambda params: set(params[0]),
    "frozenset": lambda params: frozenset(params[0]),
    "Booking": lambda params: Booking(params[0]),
}


def _serialize_object_to_tuple(obj: Any, fn_serialize: Optional[Dict[type, Callable]] = None) -> Tuple[str, str, List]:
    assert type(obj) in fn_serialize, f"Cannot serialize type {type(obj)}"
    serialized_args = fn_serialize[type(obj)](obj)
    assert isinstance(serialized_args, list), f"Serialized arguments must be a list, got {type(serialized_args)}"
    return (
        _MAGIC_STR_SER_OBJ,
        obj.__class__.__name__,
        serialized_args,
    )


def _is_serialized_tuple(obj: object) -> bool:
    return isinstance(obj, (tuple, list)) and \
        len(obj) == 3 and \
        obj[0] in [_MAGIC_STR_SER_DICT, _MAGIC_STR_SER_LIST, _MAGIC_STR_SER_OBJ]


def serialize_object(obj: object, fn_serialize: Optional[Dict[type, Callable]] = None) -> Dict | List | Tuple:
    """Make an object json-serializable.

    Args:
        obj (object): the object to be serialized
        fn_serialize (Dict[type, Callable]): a dictionary mapping types to functions that serialize the type

    Returns:
        Dict | List | Tuple: the serialized object that can be converted to json.
    """

    if _is_serialized_tuple(obj):
        return obj

    if fn_serialize is None:
        fn_serialize = _DEFAULT_FN_SERIALIZE

    if type(obj) in fn_serialize:
        return _serialize_object_to_tuple(obj, fn_serialize)
    elif isinstance(obj, List | Listlike):
        return serialize_list(obj, fn_serialize)
    elif isinstance(obj, Dict | Dictlike):
        return serialize_dict(obj, fn_serialize)
    else:
        assert isinstance(obj, Primitives), \
            f"[WARNING] Possible loss of information when serializing {obj} of type {type(obj)}"
        return obj


def serialize_list(input_list: List | Listlike, fn_serialize: Optional[Dict[type, Callable]] = None) -> List | Tuple:
    """Recursively serialize the elements of a list by calling fn_serialize when applicable.

    Args:
        input_list (List | Listlike): the list(-like) object to be serialized. When the input is a Listlike object,
            it will be converted to a magic tuple first to allow serialization.
        fn_serialize (Dict[type, Callable]): a dictionary mapping types to functions that serialize the type

    Returns:
        List | Tuple: the serialized list that can be converted to json
    """
    if fn_serialize is None:
        fn_serialize = _DEFAULT_FN_SERIALIZE

    if isinstance(input_list, Listlike):
        input_type = input_list.__class__.__name__
        input_list = list(input_list)
        return (_MAGIC_STR_SER_LIST, input_type, serialize_list(input_list, fn_serialize))
    else:
        assert isinstance(input_list, list), f"Cannot serialize type {type(input_list)}"

    for i, e in enumerate(input_list):
        input_list[i] = serialize_object(e, fn_serialize)

    return input_list


def _convert_to_dict(input_dict: Dictlike) -> Dict:
    if isinstance(input_dict, ImmutableDictWithDefault):
        return dict(input_dict)
    else:
        return input_dict._asdict()


def serialize_dict(input_dict: Dict | Dictlike, fn_serialize: Optional[Dict[type, Callable]] = None) -> Dict | Tuple:
    """Recursively serialize the fields of a dictionary by calling fn_serialize when applicable.

    Args:
        input_dict (Dict | Dictlike): the dictionary to be serialized. A Dictlike object will be converted to a magic
            tuple first to allow serialization.
        fn_serialize (Dict[type, Callable]): a dictionary mapping types to functions that serialize the type

    Returns:
        Dict | Tuple: the serialized dictionary that can be converted to json
    """
    if fn_serialize is None:
        fn_serialize = _DEFAULT_FN_SERIALIZE

    if isinstance(input_dict, Dictlike):
        # Convert to a regular dict to allow mutation
        input_type = input_dict.__class__.__name__
        input_dict = _convert_to_dict(input_dict)
        return (_MAGIC_STR_SER_DICT, input_type, serialize_dict(input_dict, fn_serialize))
    else:
        assert isinstance(input_dict, dict), f"Cannot serialize type {type(input_dict)}"

    for k, v in input_dict.items():
        input_dict[k] = serialize_object(v, fn_serialize)

    return input_dict


def _deserialize_object_from_tuple(tup: Tuple[str, str, List], fn_deserialize: Optional[Dict[str, Callable]] = None) -> Any:
    assert tup[0] == _MAGIC_STR_SER_OBJ, f"Cannot deserialize non-serialized object {tup}"
    assert tup[1] in fn_deserialize, f"Cannot deserialize type {tup[1]}"
    return fn_deserialize[tup[1]](tup[2])


@cache
def _get_type_from_string(type_str: str, typespec: UnionType | type) -> type:
    if isinstance(typespec, (UnionType, _UnionGenericAlias)):
        type_mapping = {t.__name__: t for t in typespec.__args__}
        return type_mapping[type_str]
    elif isinstance(typespec, type) and type_str == typespec.__name__:
        return typespec

    raise ValueError(f"Cannot get type from string {type_str} with typespec {typespec}")


def deserialize_object(obj: object, fn_deserialize: Optional[Dict[str, Callable]] = None) -> Any:
    """Recursively deserialize an object by calling fn_deserialize when applicable.

    Args:
        obj (object): the object to be deserialized
        fn_deserialize (Optional[Dict[str, Callable]], optional): the deserialization functions. Defaults to None.

    Returns:
        object: the deserialized object
    """

    if fn_deserialize is None:
        fn_deserialize = _DEFAULT_FN_DESERIALIZE

    if _is_serialized_tuple(obj):
        if obj[0] == _MAGIC_STR_SER_OBJ:
            return _deserialize_object_from_tuple(obj, fn_deserialize)
        elif obj[0] == _MAGIC_STR_SER_LIST:
            type_class = _get_type_from_string(obj[1], Listlike)
            return type_class(*deserialize_list(obj[2], fn_deserialize))
        elif obj[0] == _MAGIC_STR_SER_DICT:
            type_class = _get_type_from_string(obj[1], Dictlike)
            if type_class == ImmutableDictWithDefault:
                return type_class(deserialize_dict(obj[2], fn_deserialize))
            return type_class(**deserialize_dict(obj[2], fn_deserialize))
        else:
            raise ValueError(f"Cannot deserialize object {obj} with magic string {obj[0]}")
    elif isinstance(obj, List):
        return deserialize_list(obj, fn_deserialize)
    elif isinstance(obj, Dict):
        return deserialize_dict(obj, fn_deserialize)
    else:
        assert isinstance(obj, Primitives), \
            f"[WARNING] Possible loss of information when deserializing {obj} of type {type(obj)}"

    return obj


def deserialize_dict(input_dict: Dict, fn_deserialize: Optional[Dict[str, Callable]] = None) -> Dict:
    """Recursively deserialize the fields of a dictionary by calling fn_deserialize when applicable.

    Args:
        input_dict (Dict): the dictionary to be deserialized
        path (str, optional): the path to the current field. Defaults to "".
        fn_deserialize (Dict[str, Callable]): a dictionary mapping field names to functions that deserialize the field

    Returns:
        Dict: the deserialized dictionary
    """

    if fn_deserialize is None:
        fn_deserialize = _DEFAULT_FN_DESERIALIZE

    for k, v in input_dict.items():
        input_dict[k] = deserialize_object(v, fn_deserialize)

    return input_dict


def deserialize_list(input_list: List, fn_deserialize: Optional[Dict[str, Callable]] = None) -> List:
    """Recursively deserialize the elements of a list by calling fn_deserialize when applicable.

    Args:
        input_list (List): the list to be deserialized
        fn_deserialize (Dict[str, Callable]): a dictionary mapping field names to functions that deserialize the field

    Returns:
        List: the deserialized list
    """

    if fn_deserialize is None:
        fn_deserialize = _DEFAULT_FN_DESERIALIZE

    for i, e in enumerate(input_list):
        input_list[i] = deserialize_object(e, fn_deserialize)

    return input_list
