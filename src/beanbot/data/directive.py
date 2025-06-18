import os
from copy import deepcopy
from typing import Any, TypeVar

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
    Price,
    Query,
    Transaction,
)

# Type variable for beancount directives
T = TypeVar("T", bound=Directive)


class MutableDirective[T: Directive]:
    """A mutable wrapper around beancount directives with change tracking."""

    _directive_type = Directive

    def __init__(
        self,
        directive: T,
        id: str | None = None,
        changes: dict[str, Any] | None = None,
    ):
        """Initialize a mutable directive.

        Args:
            directive: The beancount directive to wrap
            id: Unique identifier for this directive
            changes: Dictionary of changes made to this directive
        """
        assert isinstance(directive, self._directive_type)

        # Use object.__setattr__ to avoid triggering our custom __setattr__
        super().__setattr__("_directive", directive)
        super().__setattr__("_id", id)
        if changes is None:
            changes = {}
        super().__setattr__("_changes", changes)

    @property
    def id(self) -> str | None:
        """Get the unique identifier for this directive."""
        return self._id

    @id.setter
    def id(self, value: str) -> None:
        """Set the unique identifier for this directive."""
        super().__setattr__("_id", value)

    @property
    def directive(self) -> T:
        """Get the wrapped beancount directive."""
        return self._directive

    @property
    def changes(self) -> dict[str, Any]:
        """Get the dictionary of changes made to this directive."""
        return deepcopy(self._changes)

    def __getattr__(self, name: str) -> Any:
        """Get an attribute from the wrapped directive.

        If the attribute does not exist, raise an AttributeError."""
        # If the attribute is changed, return the changed value
        if name in self._changes:
            return self._changes[name]

        return getattr(self._directive, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Set an attribute on the wrapped directive with change tracking."""
        if name.startswith("_") or name in ("directive", "id", "changes"):
            super().__setattr__(name, value)
            return

        # Check if this is a valid field on the directive
        if not hasattr(self._directive, name):
            raise AttributeError(
                f"'{type(self._directive).__name__}' object has no attribute '{name}'"
            )

        if getattr(self._directive, name) != value:
            # Only mark as changed if the value is different
            self._changes[name] = value
        elif name in self._changes:
            # If the value is set back to the original, remove it from changes
            del self._changes[name]

    def to_immutable(self) -> T:
        """Convert this mutable directive back to an immutable beancount directive."""
        updated_directive = deepcopy(self._directive)
        updated_directive._replace(**self._changes)
        return updated_directive

    def __repr__(self) -> str:
        """String representation of the mutable directive."""
        changes_info = f", changes: {self._changes}" if self._changes else ""
        return f"{type(self._directive).__name__}(id={self._id}{changes_info})"

    def dirty(self) -> bool:
        """Check if there are any changes made to this directive."""
        return bool(self._changes)


def get_source_file_path(directive: Directive) -> str | None:
    """
    Returns the path to the source file of this directive.
    """
    return (
        os.path.abspath(directive.meta.get("filename", "")) if directive.meta else None
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
