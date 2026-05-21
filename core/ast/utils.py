"""Shared AST helpers (small utilities used across files)."""

from __future__ import annotations

from typing import List

from core.ast.node import Node, OperatorNode, UnaryOperatorNode


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
