import datetime
from decimal import Decimal
from typing import Any, Optional, Union
from pydantic import BaseModel, Field
import beancount.core.data as d
from beancount.core.number import MISSING


class Amount(BaseModel):
    number: Optional[Decimal] = None
    currency: Optional[str] = None
    is_missing: Optional[bool] = None

    @classmethod
    def from_beancount(cls, amount: d.Amount | MISSING) -> "Amount":
        if type(amount) == type(MISSING) and amount == MISSING:
            return cls(is_missing=True)
        return cls(number=amount.number, currency=amount.currency)

    def to_beancount(self) -> d.Amount | MISSING:
        if self.is_missing:
            return MISSING
        return d.Amount(number=self.number, currency=self.currency)


class Cost(BaseModel):
    """Represents a cost basis."""

    number: Optional[Decimal] = None
    currency: str
    date: Optional[datetime.date] = None
    label: Optional[str] = None

    @classmethod
    def from_beancount(cls, cost: d.Cost) -> "Cost":
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

    number_per: Optional[Decimal] = None
    number_total: Optional[Decimal] = None
    currency: Optional[str] = None
    date: Optional[datetime.date] = None
    label: Optional[str] = None
    merge: Optional[bool] = None

    @classmethod
    def from_beancount(cls, cost: d.CostSpec) -> "CostSpec":
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
            number_per=self.number_per,
            number_total=self.number_total,
            currency=self.currency,
            date=self.date,
            label=self.label,
            merge=self.merge,
        )


class Posting(BaseModel):
    account: str
    units: Amount
    cost: Optional[Union[Cost, CostSpec]] = None
    price: Optional[Amount] = None
    flag: Optional[str] = None
    meta: Optional[dict[str, Any]] = None

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
            units=self.units.to_beancount(),
            cost=self.cost.to_beancount() if self.cost is not None else None,
            price=self.price.to_beancount() if self.price is not None else None,
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
