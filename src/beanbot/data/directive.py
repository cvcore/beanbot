"""Make mutable versions of the beancount directives for easier modification."""

from typing import Union
import beancount.core.data as bd
from recordclass import recordclass

MAP_TO_MUTABLE_DIRECTIVE = {}


def _from_immutable(cls: type, obj: bd.Directive) -> "MutableDirective":
    """patched method to recursively convert an immutable object to its mutable counterpart"""
    cls_mutable = MAP_TO_MUTABLE_DIRECTIVE[cls]
    fields_dict = dict()
    for key, value in obj._asdict().items():
        if type(value) in MAP_TO_MUTABLE_DIRECTIVE:
            fields_dict[key] = _from_immutable(type(value), value)
        elif isinstance(value, list):
            value = [v if type(v) not in MAP_TO_MUTABLE_DIRECTIVE else _from_immutable(type(v), v) for v in value]
            fields_dict[key] = value
        else:
            fields_dict[key] = value
    return cls_mutable(**fields_dict)


def make_mutable_type(immutable_type: type) -> type:
    # iteratively change the type annotations of the fields to be mutable
    # add method to convert to mutable type
    # add method to convert back to immutable type
    mutable_type = recordclass("Mutable" + immutable_type.__name__, immutable_type._fields)
    mutable_type.from_immutable = _from_immutable
    MAP_TO_MUTABLE_DIRECTIVE[immutable_type] = mutable_type

    return mutable_type


MutableOpen = make_mutable_type(bd.Open)
MutableClose = make_mutable_type(bd.Close)
MutableCommodity = make_mutable_type(bd.Commodity)
MutablePad = make_mutable_type(bd.Pad)
MutableBalance = make_mutable_type(bd.Balance)
MutablePosting = make_mutable_type(bd.Posting)
MutableTransaction = make_mutable_type(bd.Transaction)
MutableTxnPosting = make_mutable_type(bd.TxnPosting)
MutableNote = make_mutable_type(bd.Note)
MutableEvent = make_mutable_type(bd.Event)
MutableQuery = make_mutable_type(bd.Query)
MutablePrice = make_mutable_type(bd.Price)
MutableDocument = make_mutable_type(bd.Document)
MutableCustom = make_mutable_type(bd.Custom)


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


def make_mutable(obj: bd.Directive) -> MutableDirective:
    """Convert an immutable directive to its mutable counterpart"""
    return _from_immutable(type(obj), obj)
