"""Syntax tree. Every node is a frozen dataclass, so trees compare with ==. Identifiers (table names, aliases,
column names) are stored in lower case; function names in upper case. See docs/SPEC.md for how the parser
builds them."""
from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass(frozen=True)
class Literal:
    value: Any  # int, float, str or None (NULL). TRUE and FALSE are the ints 1 and 0.


@dataclass(frozen=True)
class Column:
    table: Optional[str]
    name: str


@dataclass(frozen=True)
class Unary:
    op: str  # "-" or "NOT"
    operand: Any


@dataclass(frozen=True)
class Binary:
    op: str  # + - * / = != < <= > >= AND OR
    left: Any
    right: Any


@dataclass(frozen=True)
class IsNull:
    expr: Any
    negated: bool


@dataclass(frozen=True)
class InList:
    expr: Any
    items: Tuple[Any, ...]
    negated: bool


@dataclass(frozen=True)
class Like:
    expr: Any
    pattern: Any
    negated: bool


@dataclass(frozen=True)
class Between:
    expr: Any
    low: Any
    high: Any
    negated: bool


@dataclass(frozen=True)
class Func:
    name: str
    args: Tuple[Any, ...]
    distinct: bool = False
    star: bool = False  # COUNT(*)


@dataclass(frozen=True)
class SelectItem:
    expr: Any  # None for `*` and `t.*`
    alias: Optional[str]  # as written after AS
    text: str  # the SQL source text of the item
    star: bool = False
    star_table: Optional[str] = None


@dataclass(frozen=True)
class TableRef:
    name: str
    alias: Optional[str]


@dataclass(frozen=True)
class Join:
    kind: str  # "INNER" or "LEFT"
    table: TableRef
    on: Any


@dataclass(frozen=True)
class OrderItem:
    expr: Any
    desc: bool


@dataclass(frozen=True)
class Query:
    distinct: bool
    items: Tuple[SelectItem, ...]
    table: TableRef
    joins: Tuple[Join, ...]
    where: Any
    group_by: Tuple[Any, ...]
    having: Any
    order_by: Tuple[OrderItem, ...]
    limit: Optional[int]
    offset: Optional[int]
