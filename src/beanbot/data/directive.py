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


# Forward declaration for Session type
class Session:
    """Base session interface for change tracking."""

    pass


class MutableDirective[T: Directive]:
    """A mutable wrapper around beancount directives with change tracking."""

    _directive_type = Directive

    def __init__(
        self,
        directive: T,
        session: Session,
        id: str | None = None,
        changes: dict[str, Any] | None = None,
    ):
        """Initialize a mutable directive.

        Args:
            directive: The beancount directive to wrap
            session: The session for change tracking
            id: Unique identifier for this directive
            committed_state: The last committed state (None for new objects)
        """
        assert isinstance(directive, self._directive_type)

        # Use object.__setattr__ to avoid triggering our custom __setattr__
        object.__setattr__(self, "_directive", directive)
        object.__setattr__(self, "_session", session)
        object.__setattr__(self, "_id", id)
        if changes is None:
            changes = {}
        object.__setattr__(self, "_changes", changes)

    @property
    def id(self) -> str | None:
        """Get the unique identifier for this directive."""
        return self._id

    @property
    def session(self) -> Session:
        """Get the session associated with this directive."""
        return self._session

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
        if name.startswith("_"):
            # Avoid infinite recursion for private attributes
            return object.__getattribute__(self, name)

        # If the attribute is changed, return the changed value
        if name in self._changes:
            return self._changes[name]

        return getattr(self._directive, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Set an attribute on the wrapped directive with change tracking."""
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        elif name in ("directive", "session", "id", "changes"):
            raise AttributeError(
                f"Forbidden: can't modify attribute '{name}' on {type(self).__name__}"
            )

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

        # Update session state
        if len(self._changes) > 0:
            self._session.update_state(self, "CHANGED")
        else:
            self._session.update_state(self, "UNCHANGED")

    def to_immutable(self) -> T:
        """Convert this mutable directive back to an immutable beancount directive."""
        updated_directive = deepcopy(self._directive)
        updated_directive._replace(**self._changes)
        return updated_directive

    def __repr__(self) -> str:
        """String representation of the mutable directive."""
        changes_info = f", changes: {self._changes}" if self._changes else ""
        return f"{type(self._directive).__name__}(id={self._id}{changes_info})"


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
