import datetime
from decimal import Decimal
from typing import Any, Optional, Type, TypeVar
from typing_extensions import Annotated
from pydantic import BaseModel, Field, BeforeValidator, PlainSerializer
import beancount.core.data as d
from beancount.core.number import MISSING


# Handling of MISSING values
_MISSING_VALUE = "__MISSING__"


def _parse_missing(value: Any) -> Any:
    if value == _MISSING_VALUE:
        return MISSING
    return value


def _serialize_missing(value: Any) -> Any:
    if value is MISSING:
        return _MISSING_VALUE
    return value


T = TypeVar("T")
OptionalMaybeValue = Annotated[
    T | None | Type[MISSING],
    BeforeValidator(_parse_missing),
    PlainSerializer(_serialize_missing),
]
MaybeValue = Annotated[
    T | Type[MISSING],
    BeforeValidator(_parse_missing),
    PlainSerializer(_serialize_missing),
]


class Amount(BaseModel):
    number: OptionalMaybeValue[Decimal] = None
    currency: str | None = None

    @classmethod
    def from_beancount(
        cls, amount: d.Amount | Type[MISSING]
    ) -> "Amount" | Type[MISSING]:
        if amount is MISSING or amount is None:
            return amount
        assert isinstance(amount, d.Amount)
        return cls(number=amount.number, currency=amount.currency)

    def to_beancount(self) -> d.Amount:
        return d.Amount(number=self.number, currency=self.currency)


class Cost(BaseModel):
    """Represents a cost basis."""

    number: Decimal
    currency: str
    date: datetime.date
    label: str | None = None

    @classmethod
    def from_beancount(cls, cost: d.Cost | Type[MISSING]) -> "Cost" | Type[MISSING]:
        if cost is MISSING or cost is None:
            return cost
        assert isinstance(cost, d.Cost)
        return cls(
            number=cost.number,
            currency=cost.currency,
            date=cost.date,
            label=cost.label,
        )

    def to_beancount(self) -> d.Cost:
        return d.Cost(
            number=self.number,
            currency=self.currency,
            date=self.date,
            label=self.label,
        )


class CostSpec(BaseModel):
    """Represents a cost specification."""

    number_per: OptionalMaybeValue[Decimal] = None
    number_total: OptionalMaybeValue[Decimal] = None
    currency: OptionalMaybeValue[str] = None
    date: datetime.date | None = None
    label: str | None = None
    merge: bool | None = None

    @classmethod
    def from_beancount(
        cls, cost: d.CostSpec | Type[MISSING]
    ) -> "CostSpec" | Type[MISSING]:
        if cost is MISSING or cost is None:
            return cost
        assert isinstance(cost, d.CostSpec)
        return cls(
            number_per=cost.number_per,
            number_total=cost.number_total,
            currency=cost.currency,
            date=cost.date,
            label=cost.label,
            merge=cost.merge,
        )

    def to_beancount(self) -> d.CostSpec:
        return d.CostSpec(
            number_per=self.number_per,  # type: ignore
            number_total=self.number_total,  # type: ignore
            currency=self.currency,
            date=self.date,
            label=self.label,
            merge=self.merge,
        )


class Posting(BaseModel):
    account: str
    units: MaybeValue[Amount]
    cost: OptionalMaybeValue[Cost | CostSpec] = None
    price: OptionalMaybeValue[Amount] = None
    flag: str | None = None
    meta: dict[str, Any] | None = None

    @classmethod
    def from_beancount(cls, posting: d.Posting) -> "Posting":
        if isinstance(posting.cost, d.Cost):
            cost = Cost.from_beancount(posting.cost)
        elif isinstance(posting.cost, d.CostSpec):
            cost = CostSpec.from_beancount(posting.cost)
        else:
            cost = None

        return cls(
            account=posting.account,
            units=Amount.from_beancount(posting.units),
            cost=cost,
            price=Amount.from_beancount(posting.price)
            if posting.price is not None
            else None,
            flag=posting.flag,
            meta=posting.meta,
        )

    def to_beancount(self) -> d.Posting:
        return d.Posting(
            account=self.account,
            units=to_beancount(self.units),
            cost=to_beancount(self.cost),
            price=to_beancount(self.price),
            flag=self.flag,
            meta=self.meta,
        )


class Transaction(BaseModel):
    date: datetime.date
    flag: str
    payee: Optional[str] = None
    narration: str
    tags: set[str] = Field(default_factory=set)
    links: set[str] = Field(default_factory=set)
    postings: list[Posting]
    meta: Optional[dict[str, Any]] = None

    @classmethod
    def from_beancount(cls, txn: d.Transaction) -> "Transaction":
        return cls(
            meta=txn.meta,
            date=txn.date,
            flag=txn.flag,
            payee=txn.payee,
            narration=txn.narration,
            tags=txn.tags,
            links=txn.links,
            postings=[Posting.from_beancount(p) for p in txn.postings],
        )

    def to_beancount(self) -> d.Transaction:
        return d.Transaction(
            meta=self.meta,
            date=self.date,
            flag=self.flag,
            payee=self.payee,
            narration=self.narration,
            tags=self.tags,
            links=self.links,
            postings=[p.to_beancount() for p in self.postings],
        )  # type: ignore


PydanticModels = Amount | Cost | CostSpec | Posting | Transaction


def to_beancount(any: Any) -> Any:
    if isinstance(any, PydanticModels):
        return any.to_beancount()
    return any
