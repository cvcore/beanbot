from typing import Generic, List, Optional, TypeVar, Dict, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model for consistent API pagination."""

    items: List[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(
        cls, items: List[T], total: int, page: int, size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response from items and pagination info."""
        pages = (total + size - 1) // size if size > 0 else 0  # Ceiling division
        return cls(items=items, total=total, page=page, size=size, pages=pages)


class TransactionMetadata(BaseModel):
    """Metadata about transactions collection."""

    date_range: Optional[Dict[str, Any]] = None
    account_count: int = 0
    payee_count: int = 0
    tag_count: int = 0
    currency_count: int = 0


class TransactionResponse(BaseModel, Generic[T]):
    """Enhanced response with transactions and metadata."""

    data: PaginatedResponse[T]
    metadata: TransactionMetadata = Field(default_factory=TransactionMetadata)
