"""Query syntax trees."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Term:
    text: str
    field: str = None


@dataclass(frozen=True)
class Phrase:
    text: str
    field: str = None


@dataclass(frozen=True)
class Not:
    node: object


@dataclass(frozen=True)
class And:
    nodes: tuple


@dataclass(frozen=True)
class Or:
    nodes: tuple


def canon(node):
    """A normal form of the query as text: equal queries (up to spacing) have equal canon strings."""
    if isinstance(node, Term):
        return (f"{node.field}:" if node.field else "") + node.text
    if isinstance(node, Phrase):
        return (f"{node.field}:" if node.field else "") + '"' + node.text + '"'
    if isinstance(node, Not):
        return "-" + canon(node.node)
    if isinstance(node, And):
        return "(" + " ".join(canon(n) for n in node.nodes) + ")"
    if isinstance(node, Or):
        return "(" + " OR ".join(canon(n) for n in node.nodes) + ")"
    raise TypeError(node)


def walk(node):
    """Every node of the tree, parents first."""
    yield node
    if isinstance(node, Not):
        yield from walk(node.node)
    elif isinstance(node, (And, Or)):
        for child in node.nodes:
            yield from walk(child)
