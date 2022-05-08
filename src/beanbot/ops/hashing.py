#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Any, Dict, Iterable, Union
import numpy as np

class BiDirectionalHash(object):
    """Bi-directional hashing"""

    def __init__(self):
        self._dict : Dict[Any, int] = dict()
        self._inv_dict : Dict[int, Any] = dict()

    def hash(self, obj: Union[Any, Iterable[Any]]) -> Union[int, np.ndarray]:

        if isinstance(obj, Iterable):
            return np.array([self._hash_impl(o) for o in obj])
        return self._hash_impl(obj)

    def _hash_impl(self, obj: Any) -> int:
        """Generate hash value of an object.

        Args:
            obj (Any): the object to be hashed

        Returns:
            int: the hash value
        """
        INVALID_HASH_VAL = 0

        if isinstance(obj, str):
            if obj == '':
                return INVALID_HASH_VAL
            objstr = obj
        elif obj is None:
            return INVALID_HASH_VAL
        else:
            objstr = f"{sorted(obj)}"

        if objstr not in self._dict:
            n_elem = len(self._dict)
            hash_val = n_elem + 1
            self._dict[objstr] = hash_val
            self._inv_dict[hash_val] = obj

        return self._dict[objstr]

    def dehash(self, hash_val: Union[int, Iterable[int]]) -> Union[Any, Iterable[Any]]:

        if isinstance(hash_val, Iterable):
            return list(map(self._dehash_impl, hash_val))
        return self._dehash_impl(hash_val)

    def _dehash_impl(self, hash_val: int) -> Any:
        """Get object from hash value

        Args:
            hash_val (int): the hash value. Assume the hash value already exists in this class.

        Returns:
            Any: the object
        """
        return self._inv_dict[hash_val]

    def __len__(self):
        return len(self._dict)
