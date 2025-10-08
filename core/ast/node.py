from datetime import datetime
from typing import List, Set, Optional
from abc import ABC

from .node_type import NodeType

# ============================================================================
# Base Node Structure
# ============================================================================

class Node(ABC):
    """Base class for all nodes"""
    def __init__(self, type: NodeType, children: Optional[Set['Node']|List['Node']] = None):
        self.type = type
        self.children = children if children is not None else set()


# ============================================================================
# Operand Nodes
# ============================================================================

class TableNode(Node):
    """Table reference node"""
    def __init__(self, _name: str, _alias: Optional[str] = None, **kwargs):
        super().__init__(NodeType.TABLE, **kwargs)
        self.name = _name
        self.alias = _alias


# TODO - including query structure arguments (similar to QueryNode) in constructor.
class SubqueryNode(Node):
    """Subquery node"""
    def __init__(self, query: 'Node', _alias: Optional[str] = None, **kwargs):
        super().__init__(NodeType.SUBQUERY, children={query}, **kwargs)
        self.alias = _alias


class ColumnNode(Node):
    """Column reference node"""
    def __init__(self, _name: str, _alias: Optional[str] = None, _parent_alias: Optional[str] = None, _parent: Optional[TableNode|SubqueryNode] = None, **kwargs):
        super().__init__(NodeType.COLUMN, **kwargs)
        self.name = _name
        self.alias = _alias
        self.parent_alias = _parent_alias
        self.parent = _parent


class LiteralNode(Node):
    """Literal value node"""
    def __init__(self, _value: str|int|float|bool|datetime|None, **kwargs):
        super().__init__(NodeType.LITERAL, **kwargs)
        self.value = _value


class VarNode(Node):
    """VarSQL variable node"""
    def __init__(self, _name: str, **kwargs):
        super().__init__(NodeType.VAR, **kwargs)
        self.name = _name


class VarSetNode(Node):
    """VarSQL variable set node"""
    def __init__(self, _name: str, **kwargs):
        super().__init__(NodeType.VARSET, **kwargs)
        self.name = _name


class OperatorNode(Node):
    """Operator node"""
    def __init__(self, _left: Node, _name: str, _right: Optional[Node] = None, **kwargs):
        children = [_left, _right] if _right else [_left]
        super().__init__(NodeType.OPERATOR, children=children, **kwargs)
        self.name = _name


class FunctionNode(Node):
    """Function call node"""
    def __init__(self, _name: str, _args: Optional[List[Node]] = None, **kwargs):
        if _args is None:
            _args = []
        super().__init__(NodeType.FUNCTION, children=_args, **kwargs)
        self.name = _name


# ============================================================================
# Query Structure Nodes
# ============================================================================

class SelectNode(Node):
    """SELECT clause node"""
    def __init__(self, _items: Set['Node'], **kwargs):
        super().__init__(NodeType.SELECT, children=_items, **kwargs)


# TODO - confine the valid NodeTypes as children of FromNode
class FromNode(Node):
    """FROM clause node"""
    def __init__(self, _sources: Set['Node'], **kwargs):
        super().__init__(NodeType.FROM, children=_sources, **kwargs)


class WhereNode(Node):
    """WHERE clause node"""
    def __init__(self, _predicates: Set['Node'], **kwargs):
        super().__init__(NodeType.WHERE, children=_predicates, **kwargs)


class GroupByNode(Node):
    """GROUP BY clause node"""
    def __init__(self, _items: List['Node'], **kwargs):
        super().__init__(NodeType.GROUP_BY, children=_items, **kwargs)


class HavingNode(Node):
    """HAVING clause node"""
    def __init__(self, _predicates: Set['Node'], **kwargs):
        super().__init__(NodeType.HAVING, children=_predicates, **kwargs)


class OrderByNode(Node):
    """ORDER BY clause node"""
    def __init__(self, _items: List['Node'], **kwargs):
        super().__init__(NodeType.ORDER_BY, children=_items, **kwargs)


class LimitNode(Node):
    """LIMIT clause node"""
    def __init__(self, _limit: int, **kwargs):
        super().__init__(NodeType.LIMIT, **kwargs)
        self.limit = _limit


class OffsetNode(Node):
    """OFFSET clause node"""
    def __init__(self, _offset: int, **kwargs):
        super().__init__(NodeType.OFFSET, **kwargs)
        self.offset = _offset


class QueryNode(Node):
    """Query root node"""
    def __init__(self, 
                 _select: Optional['Node'] = None, 
                 _from: Optional['Node'] = None,
                 _where: Optional['Node'] = None,
                 _group_by: Optional['Node'] = None,
                 _having: Optional['Node'] = None,
                 _order_by: Optional['Node'] = None,
                 _limit: Optional['Node'] = None,
                 _offset: Optional['Node'] = None,
                 **kwargs):
        children = []
        if _select:
            children.append(_select)
        if _from:
            children.append(_from)
        if _where:
            children.append(_where)
        if _group_by:
            children.append(_group_by)
        if _having:
            children.append(_having)
        if _order_by:
            children.append(_order_by)
        if _limit:
            children.append(_limit)
        if _offset:
            children.append(_offset)
        super().__init__(NodeType.QUERY, children=children, **kwargs)
