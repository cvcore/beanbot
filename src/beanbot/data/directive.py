"""Make mutable versions of the beancount directives for easier modification."""

from typing import Union
import beancount.core.data as bd
from recordclass import recordclass


_MAP_TO_MUTABLE_DIRECTIVE = {}
_MAP_TO_IMMUTABLE_DIRECTIVE = {}


def _from_immutable(cls: type, obj: bd.Directive) -> "MutableDirective":
    """patched method to recursively convert an immutable object to its mutable counterpart"""
    cls_mutable = _MAP_TO_MUTABLE_DIRECTIVE[cls]
    fields_dict = dict()
    for key, value in obj._asdict().items():
        if type(value) in _MAP_TO_MUTABLE_DIRECTIVE:
            fields_dict[key] = _from_immutable(type(value), value)
        elif isinstance(value, list):
            value = [v if type(v) not in _MAP_TO_MUTABLE_DIRECTIVE else _from_immutable(type(v), v) for v in value]
            fields_dict[key] = value
        else:
            fields_dict[key] = value
    return cls_mutable(**fields_dict)


def _to_immutable(obj: "MutableDirective") -> bd.Directive:
    """patched method to recursively convert a mutable object to its immutable counterpart"""
    cls = type(obj)
    cls_immutable = _MAP_TO_IMMUTABLE_DIRECTIVE[cls]
    fields_dict = dict()
    for key, value in obj._asdict().items():
        if type(value) in _MAP_TO_IMMUTABLE_DIRECTIVE:
            fields_dict[key] = _to_immutable(value)
        elif isinstance(value, list):
            value = [v if type(v) not in _MAP_TO_IMMUTABLE_DIRECTIVE else _to_immutable(v) for v in value]
            fields_dict[key] = value
        else:
            fields_dict[key] = value
    return cls_immutable(**fields_dict)


def _make_mutable_type(immutable_type: type) -> type:
    mutable_type = recordclass("Mutable" + immutable_type.__name__, immutable_type._fields)
    mutable_type.from_immutable = _from_immutable
    mutable_type.to_immutable = _to_immutable
    _MAP_TO_MUTABLE_DIRECTIVE[immutable_type] = mutable_type
    _MAP_TO_IMMUTABLE_DIRECTIVE[mutable_type] = immutable_type

    return mutable_type


MutableOpen = _make_mutable_type(bd.Open)
MutableClose = _make_mutable_type(bd.Close)
MutableCommodity = _make_mutable_type(bd.Commodity)
MutablePad = _make_mutable_type(bd.Pad)
MutableBalance = _make_mutable_type(bd.Balance)
MutablePosting = _make_mutable_type(bd.Posting)
MutableTransaction = _make_mutable_type(bd.Transaction)
MutableTxnPosting = _make_mutable_type(bd.TxnPosting)
MutableNote = _make_mutable_type(bd.Note)
MutableEvent = _make_mutable_type(bd.Event)
MutableQuery = _make_mutable_type(bd.Query)
MutablePrice = _make_mutable_type(bd.Price)
MutableDocument = _make_mutable_type(bd.Document)
MutableCustom = _make_mutable_type(bd.Custom)


MutableDirective = Union[
    MutableOpen,
    MutableClose,
    MutableCommodity,
    MutablePad,
    MutableBalance,
    MutablePosting,
    MutableTransaction,
    MutableTxnPosting,
    MutableNote,
    MutableEvent,
    MutableQuery,
    MutablePrice,
    MutableDocument,
    MutableCustom,
]


ALL_MUTABLE_DIRECTIVES = (
    MutableOpen,
    MutableClose,
    MutableCommodity,
    MutablePad,
    MutableBalance,
    MutablePosting,
    MutableTransaction,
    MutableTxnPosting,
    MutableNote,
    MutableEvent,
    MutableQuery,
    MutablePrice,
    MutableDocument,
    MutableCustom,
)


def make_mutable(obj: bd.Directive) -> MutableDirective:
    """Convert an immutable directive to its mutable counterpart"""
    return _from_immutable(type(obj), obj)
