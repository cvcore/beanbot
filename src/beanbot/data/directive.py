from copy import deepcopy
from typing import Any, TypeVar, Union

from beancount import Directive
from beancount.core.data import (
    Balance,
    Close,
    Commodity,
    Custom,
    Document,
    Event,
    Note,
    Open,
    Pad,
    Posting,
    Price,
    Query,
    Transaction,
)
from recordclass import recordclass

from beanbot.data.constants import METADATA_BBID

# Type variable for beancount directives
T = TypeVar("T", bound=Directive)

# Mapping dictionaries for conversion between mutable and immutable types
_MAP_TO_MUTABLE_DIRECTIVE = {}
_MAP_TO_IMMUTABLE_DIRECTIVE = {}


def _from_immutable(cls: type, obj: Directive) -> "_MutableDirectiveImpl":
    """Convert an immutable object to its mutable counterpart recursively"""
    cls_mutable = _MAP_TO_MUTABLE_DIRECTIVE[cls]
    fields_dict = dict()
    for key, value in obj._asdict().items():
        if type(value) in _MAP_TO_MUTABLE_DIRECTIVE:
            fields_dict[key] = _from_immutable(type(value), value)
        elif isinstance(value, list):
            value = [
                (
                    v
                    if type(v) not in _MAP_TO_MUTABLE_DIRECTIVE
                    else _from_immutable(type(v), v)
                )
                for v in value
            ]
            fields_dict[key] = value
        else:
            fields_dict[key] = value
    return cls_mutable(**fields_dict)


def _to_immutable(obj: "_MutableDirectiveImpl") -> Directive:
    """Convert a mutable object to its immutable counterpart recursively"""
    cls = type(obj)
    cls_immutable = _MAP_TO_IMMUTABLE_DIRECTIVE[cls]
    fields_dict = dict()
    for key, value in obj._asdict().items():
        if type(value) in _MAP_TO_IMMUTABLE_DIRECTIVE:
            fields_dict[key] = _to_immutable(value)
        elif isinstance(value, list):
            value = [
                v if type(v) not in _MAP_TO_IMMUTABLE_DIRECTIVE else _to_immutable(v)
                for v in value
            ]
            fields_dict[key] = value
        else:
            fields_dict[key] = value
    return cls_immutable(**fields_dict)


def _make_mutable_type(immutable_type: type) -> type:
    """Create a mutable version of an immutable beancount type"""
    mutable_type = recordclass(
        "_Mutable" + immutable_type.__name__ + "Impl", immutable_type._fields
    )
    mutable_type.from_immutable = _from_immutable
    mutable_type.to_immutable = _to_immutable
    _MAP_TO_MUTABLE_DIRECTIVE[immutable_type] = mutable_type
    _MAP_TO_IMMUTABLE_DIRECTIVE[mutable_type] = immutable_type
    return mutable_type


# Create mutable implementation classes
_MutableOpenImpl = _make_mutable_type(Open)
_MutableCloseImpl = _make_mutable_type(Close)
_MutableCommodityImpl = _make_mutable_type(Commodity)
_MutablePadImpl = _make_mutable_type(Pad)
_MutableBalanceImpl = _make_mutable_type(Balance)
_MutablePostingImpl = _make_mutable_type(Posting)
_MutableTransactionImpl = _make_mutable_type(Transaction)
_MutableNoteImpl = _make_mutable_type(Note)
_MutableEventImpl = _make_mutable_type(Event)
_MutableQueryImpl = _make_mutable_type(Query)
_MutablePriceImpl = _make_mutable_type(Price)
_MutableDocumentImpl = _make_mutable_type(Document)
_MutableCustomImpl = _make_mutable_type(Custom)

_MutableDirectiveImpl = Union[
    _MutableOpenImpl,
    _MutableCloseImpl,
    _MutableCommodityImpl,
    _MutablePadImpl,
    _MutableBalanceImpl,
    _MutablePostingImpl,
    _MutableTransactionImpl,
    _MutableNoteImpl,
    _MutableEventImpl,
    _MutableQueryImpl,
    _MutablePriceImpl,
    _MutableDocumentImpl,
    _MutableCustomImpl,
]


class MutableDirective[T: Directive]:
    """A mutable wrapper around beancount directives with change tracking."""

    _directive_type = Directive

    def __init__(
        self,
        directive: T,
        id: str | None = None,
    ):
        """Initialize a mutable directive.

        Args:
            directive: The beancount directive to wrap
            id: Unique identifier for this directive
        """
        assert isinstance(directive, self._directive_type)

        # Convert to mutable implementation and create backup
        self._mutable_directive = _from_immutable(type(directive), directive)
        self._original_directive = deepcopy(directive)
        self._id = id

    @property
    def id(self) -> str | None:
        """Get the unique identifier for this directive."""
        return self._id

    @id.setter
    def id(self, value: str) -> None:
        """Set the unique identifier for this directive."""
        self._id = value

    @property
    def directive(self) -> T:
        """Get the wrapped beancount directive."""
        return _to_immutable(self._mutable_directive)

    def __getattr__(self, name: str) -> Any:
        """Get an attribute from the mutable implementation."""
        return getattr(self._mutable_directive, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Set an attribute on the mutable implementation."""
        if name.startswith("_") or name in ("directive", "id"):
            super().__setattr__(name, value)
            return

        # Set attribute on mutable implementation
        setattr(self._mutable_directive, name, value)

    def to_immutable(self) -> T:
        """Convert this mutable directive back to an immutable beancount directive."""
        updated_directive = _to_immutable(self._mutable_directive)
        if updated_directive.meta is None:
            updated_directive = updated_directive._replace(meta={})
        if self._id is not None:
            meta_copy = dict(updated_directive.meta)
            meta_copy[METADATA_BBID] = self._id
            updated_directive = updated_directive._replace(meta=meta_copy)
        return updated_directive

    def __repr__(self) -> str:
        """String representation of the mutable directive."""
        dirty_info = " (dirty)" if self.dirty() else ""
        return f"{type(self._mutable_directive).__name__}(id={self._id}{dirty_info})"

    def dirty(self) -> bool:
        """Check if there are any changes made to this directive."""
        return self._mutable_directive.to_immutable() != self._original_directive

    def reset(self) -> None:
        """Reset the changes made to this directive."""
        self._mutable_directive = _from_immutable(
            type(self._original_directive), self._original_directive
        )


class MutableTransaction(MutableDirective[Transaction]):
    _directive_type = Transaction


class MutableOpen(MutableDirective[Open]):
    _directive_type = Open


class MutableClose(MutableDirective[Close]):
    _directive_type = Close


class MutableBalance(MutableDirective[Balance]):
    _directive_type = Balance


class MutablePad(MutableDirective[Pad]):
    _directive_type = Pad


class MutableNote(MutableDirective[Note]):
    _directive_type = Note


class MutableEvent(MutableDirective[Event]):
    _directive_type = Event


class MutableQuery(MutableDirective[Query]):
    _directive_type = Query


class MutablePrice(MutableDirective[Price]):
    _directive_type = Price


class MutableDocument(MutableDirective[Document]):
    _directive_type = Document


class MutableCustom(MutableDirective[Custom]):
    _directive_type = Custom


class MutableCommodity(MutableDirective[Commodity]):
    _directive_type = Commodity


def to_mutable(directive: Directive) -> MutableDirective[Directive]:
    """Convert a beancount directive to a mutable directive."""
    if isinstance(directive, Transaction):
        return MutableTransaction(directive)
    elif isinstance(directive, Open):
        return MutableOpen(directive)
    elif isinstance(directive, Close):
        return MutableClose(directive)
    elif isinstance(directive, Balance):
        return MutableBalance(directive)
    elif isinstance(directive, Pad):
        return MutablePad(directive)
    elif isinstance(directive, Note):
        return MutableNote(directive)
    elif isinstance(directive, Event):
        return MutableEvent(directive)
    elif isinstance(directive, Query):
        return MutableQuery(directive)
    elif isinstance(directive, Price):
        return MutablePrice(directive)
    elif isinstance(directive, Document):
        return MutableDocument(directive)
    elif isinstance(directive, Custom):
        return MutableCustom(directive)
    elif isinstance(directive, Commodity):
        return MutableCommodity(directive)

    raise TypeError(f"Unsupported directive type: {type(directive).__name__}")


def make_mutable(obj: Directive) -> _MutableDirectiveImpl:
    """Convert an immutable directive to its mutable counterpart"""
    return _from_immutable(type(obj), obj)
