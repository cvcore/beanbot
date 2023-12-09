import datetime
from typing import Callable, Dict, Optional


_DEFAULT_FN_SERIALIZE = {
    datetime.date: lambda d: d.isoformat(),
}


def serialize_dict(input_dict: Dict, fn_serialize: Optional[Dict[type, Callable]] = None) -> Dict:
    """Recursively serialize the fields of a dictionary by calling fn_serialize when applicable.

    Args:
        input_dict (Dict): the dictionary to be serialized
        fn_serialize (Dict[type, Callable]): a dictionary mapping types to functions that serialize the type

    Returns:
        Dict: the serialized dictionary that can be converted to json
    """
    if fn_serialize is None:
        fn_serialize = _DEFAULT_FN_SERIALIZE

    for k, v in input_dict.items():
        if type(v) in fn_serialize:
            input_dict[k] = fn_serialize[type(v)](v)
        elif isinstance(v, dict):
            input_dict[k] = serialize_dict(v, fn_serialize)

    return input_dict


_DEFAULT_FN_DESERIALIZE = {}


def deserialize_dict(input_dict: Dict, path: str = "", fn_deserialize: Optional[Dict[str, Callable]] = None) -> Dict:
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
        path_k = k if path == "" else path + "." + k
        if path_k in fn_deserialize:
            input_dict[k] = fn_deserialize[path_k](v)
        elif isinstance(v, dict):
            input_dict[k] = deserialize_dict(v, path_k, fn_deserialize)

    return input_dict
