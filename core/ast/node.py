from datetime import datetime
from typing import List, Set, Optional, Union
from abc import ABC

from .enums import NodeType, JoinType, SortOrder

# ============================================================================
# Base Node Structure
# ============================================================================

class Node(ABC):
    """Base class for all nodes"""
    def __init__(self, type: NodeType, children: Optional[Set['Node']|List['Node']] = None):
        self.type = type
        self.children = children if children is not None else set()
    
    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        if self.type != other.type:
            return False
        if len(self.children) != len(other.children):
            return False
        # Compare children
        if isinstance(self.children, set) and isinstance(other.children, set):
            return self.children == other.children
        elif isinstance(self.children, list) and isinstance(other.children, list):
            return self.children == other.children
        else:
            return False
    
    def __hash__(self):
        # Make nodes hashable by using their type and a hash of their children
        if isinstance(self.children, set):
            # For sets, create a deterministic hash by sorting children by their string representation
            children_hash = hash(tuple(sorted(self.children, key=lambda x: str(x))))
        else:
            # For lists, just hash the tuple directly
            children_hash = hash(tuple(self.children))
        return hash((self.type, children_hash))


# ============================================================================
# Operand Nodes
# ============================================================================

class TableNode(Node):
    """Table reference node"""
    def __init__(self, _name: str, _alias: Optional[str] = None, **kwargs):
        super().__init__(NodeType.TABLE, **kwargs)
        self.name = _name
        self.alias = _alias
    
    def __eq__(self, other):
        if not isinstance(other, TableNode):
            return False
        return (super().__eq__(other) and 
                self.name == other.name and 
                self.alias == other.alias)
    
    def __hash__(self):
        return hash((super().__hash__(), self.name, self.alias))


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
    
    def __eq__(self, other):
        if not isinstance(other, ColumnNode):
            return False
        return (super().__eq__(other) and 
                self.name == other.name and 
                self.alias == other.alias and 
                self.parent_alias == other.parent_alias)
    
    def __hash__(self):
        return hash((super().__hash__(), self.name, self.alias, self.parent_alias))


class LiteralNode(Node):
    """Literal value node"""
    def __init__(self, _value: str|int|float|bool|datetime|None, **kwargs):
        super().__init__(NodeType.LITERAL, **kwargs)
        self.value = _value

    def __eq__(self, other):
        if not isinstance(other, LiteralNode):
            return False
        return (super().__eq__(other) and 
                self.value == other.value)
    
    def __hash__(self):
        return hash((super().__hash__(), self.value))


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
    
    def __eq__(self, other):
        if not isinstance(other, OperatorNode):
            return False
        return (super().__eq__(other) and 
                self.name == other.name)
    
    def __hash__(self):
        return hash((super().__hash__(), self.name))


class FunctionNode(Node):
    """Function call node"""
    def __init__(self, _name: str, _args: Optional[List[Node]] = None, _alias: Optional[str] = None, **kwargs):
        if _args is None:
            _args = []
        super().__init__(NodeType.FUNCTION, children=_args, **kwargs)
        self.name = _name
        self.alias = _alias
    
    def __eq__(self, other):
        if not isinstance(other, FunctionNode):
            return False
        return (super().__eq__(other) and 
                self.name == other.name and 
                self.alias == other.alias)
    
    def __hash__(self):
        return hash((super().__hash__(), self.name, self.alias))


class JoinNode(Node):
    """JOIN clause node"""
    def __init__(self, _left_table: Union['TableNode', 'JoinNode'], _right_table: 'TableNode', _join_type: JoinType = JoinType.INNER, _on_condition: Optional['Node'] = None, **kwargs):
        children = [_left_table, _right_table]
        if _on_condition:
            children.append(_on_condition)
        super().__init__(NodeType.JOIN, children=children, **kwargs)
        self.left_table = _left_table
        self.right_table = _right_table
        self.join_type = _join_type
        self.on_condition = _on_condition
    
    def __eq__(self, other):
        if not isinstance(other, JoinNode):
            return False
        return (super().__eq__(other) and 
                self.join_type == other.join_type)
    
    def __hash__(self):
        return hash((super().__hash__(), self.join_type))

# ============================================================================
# Query Structure Nodes
# ============================================================================

class SelectNode(Node):
    """SELECT clause node"""
    def __init__(self, _items: List['Node'], **kwargs):
        super().__init__(NodeType.SELECT, children=_items, **kwargs)


# TODO - confine the valid NodeTypes as children of FromNode
class FromNode(Node):
    """FROM clause node"""
    def __init__(self, _sources: List['Node'], **kwargs):
        super().__init__(NodeType.FROM, children=_sources, **kwargs)


class WhereNode(Node):
    """WHERE clause node"""
    def __init__(self, _predicates: List['Node'], **kwargs):
        super().__init__(NodeType.WHERE, children=_predicates, **kwargs)


class GroupByNode(Node):
    """GROUP BY clause node"""
    def __init__(self, _items: List['Node'], **kwargs):
        super().__init__(NodeType.GROUP_BY, children=_items, **kwargs)


class HavingNode(Node):
    """HAVING clause node"""
    def __init__(self, _predicates: List['Node'], **kwargs):
        super().__init__(NodeType.HAVING, children=_predicates, **kwargs)


class OrderByItemNode(Node):
    """Single ORDER BY item"""
    def __init__(self, _column: Node, _sort: SortOrder = SortOrder.ASC, **kwargs):
        super().__init__(NodeType.ORDER_BY_ITEM, children=[_column], **kwargs)
        self.sort = _sort

    def __eq__(self, other):
        if not isinstance(other, OrderByItemNode):
            return False
        return (super().__eq__(other) and 
                self.sort == other.sort)
    
    def __hash__(self):
        return hash((super().__hash__(), self.sort))

class OrderByNode(Node):
    """ORDER BY clause node"""
    def __init__(self, _items: List[OrderByItemNode], **kwargs):
        super().__init__(NodeType.ORDER_BY, children=_items, **kwargs)


class LimitNode(Node):
    """LIMIT clause node"""
    def __init__(self, _limit: int, **kwargs):
        super().__init__(NodeType.LIMIT, **kwargs)
        self.limit = _limit
    
    def __eq__(self, other):
        if not isinstance(other, LimitNode):
            return False
        return (super().__eq__(other) and 
                self.limit == other.limit)
    
    def __hash__(self):
        return hash((super().__hash__(), self.limit))


class OffsetNode(Node):
    """OFFSET clause node"""
    def __init__(self, _offset: int, **kwargs):
        super().__init__(NodeType.OFFSET, **kwargs)
        self.offset = _offset
    
    def __eq__(self, other):
        if not isinstance(other, OffsetNode):
            return False
        return (super().__eq__(other) and 
                self.offset == other.offset)
    
    def __hash__(self):
        return hash((super().__hash__(), self.offset))


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
