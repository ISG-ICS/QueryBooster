"""Shared AST helpers (small utilities used across files)."""

from __future__ import annotations

import re
from typing import List

from core.ast.node import Node, OperatorNode, UnaryOperatorNode

_PLACEHOLDER_PREFIXES = ("x", "y")


def is_placeholder_name(name: str) -> bool:
    """Return True when name is a generator-internal placeholder identifier.

    Matches the parser-friendly tokens (__rv_x?__, __rvs_y?__) and bare x?/y?
    external names.
    """
    lower = name.lower()
    if re.fullmatch(r"__rv_[xy]\d+__", lower):
        return True
    if re.fullmatch(r"__rvs_[xy]\d+__", lower):
        return True
    for prefix in _PLACEHOLDER_PREFIXES:
        if lower.startswith(prefix):
            suffix = lower[len(prefix):]
            if suffix.isdigit():
                return True
    return False


def flatten_logical_operands(node: Node, op_name: str) -> List[Node]:
    """Flatten a left-associative tree of binary ``op_name`` (e.g. AND/OR).

    Unary operators are excluded even if they subtype :class:`OperatorNode`.
    """
    op_upper = op_name.upper()
    if (
        isinstance(node, OperatorNode)
        and not isinstance(node, UnaryOperatorNode)
        and node.name.upper() == op_upper
    ):
        out: List[Node] = []
        for child in list(node.children):
            out.extend(flatten_logical_operands(child, op_name))
        return out
    return [node]
