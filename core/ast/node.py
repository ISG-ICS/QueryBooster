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


class SubqueryNode(Node):
    """Subquery node"""
    def __init__(self, query: 'Node', _alias: Optional[str] = None, **kwargs):
        super().__init__(NodeType.SUBQUERY, children={query}, **kwargs)
        self.alias = _alias
    
    def __eq__(self, other):
        if not isinstance(other, SubqueryNode):
            return False
        return (super().__eq__(other) and 
                self.alias == other.alias)
    
    def __hash__(self):
        return hash((super().__hash__(), self.alias))


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

class DataTypeNode(Node):
    """SQL data type node used in CAST expressions (e.g. TEXT, DATE, INTEGER)"""
    SQL_DATA_TYPES = {"TEXT", "DATE", "INTEGER", "TIMESTAMP", "VARCHAR", "BOOLEAN", "FLOAT"}

    def __init__(self, _name: str, **kwargs):
        if _name not in DataTypeNode.SQL_DATA_TYPES:
            raise ValueError(f"Invalid SQL data type: {_name}")
        super().__init__(NodeType.DATA_TYPE, **kwargs)
        self.name = _name
    
    def __eq__(self, other):
        if not isinstance(other, DataTypeNode):
            return False
        return super().__eq__(other) and self.name == other.name
    
    def __hash__(self):
        return hash((super().__hash__(), self.name))


class TimeUnitNode(Node):
    """SQL time unit node used in INTERVAL and temporal functions (e.g. DAY, MONTH, SECOND)"""
    TIME_UNITS = {"SECOND", "MINUTE", "HOUR", "DAY", "WEEK", "MONTH", "YEAR"}

    def __init__(self, _name: str, **kwargs):
        if _name not in TimeUnitNode.TIME_UNITS:
            raise ValueError(f"Invalid SQL time unit: {_name}")
        super().__init__(NodeType.TIME_UNIT, **kwargs)
        self.name = _name
    
    def __eq__(self, other):
        if not isinstance(other, TimeUnitNode):
            return False
        return super().__eq__(other) and self.name == other.name
    
    def __hash__(self):
        return hash((super().__hash__(), self.name))

class ListNode(Node):
    """A list of nodes, e.g. the right-hand side of an IN expression"""
    def __init__(self, _items: List[Node], **kwargs):
        super().__init__(NodeType.LIST, children=_items, **kwargs)
    
class IntervalNode(Node):
    def __init__(self, _value, _unit: TimeUnitNode, **kwargs):
        # Include the value in children when it is itself a Node, so that
        # generic traversals/formatters that walk via `children` see it.
        if isinstance(_value, Node):
            children = [_value, _unit]
        else:
            children = [_unit]
        super().__init__(NodeType.INTERVAL, children=children, **kwargs)
        self.value = _value
        self.unit = _unit
    
    def __eq__(self, other):
        if not isinstance(other, IntervalNode):
            return False
        return super().__eq__(other) and self.value == other.value and self.unit == other.unit
    
    def __hash__(self):
        return hash((super().__hash__(), self.value, self.unit))

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
    def __init__(self, _left_table: Union['TableNode', 'JoinNode', 'SubqueryNode'], _right_table: Union['TableNode', 'SubqueryNode'], _join_type: JoinType = JoinType.INNER, _on_condition: Optional['Node'] = None, **kwargs):
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
    """SELECT clause node. _distinct_on is the list of expressions for DISTINCT ON (e.g. ListNode of columns)."""
    def __init__(self, _items: List['Node'], _distinct: bool = False, _distinct_on: Optional['Node'] = None, **kwargs):
        children = list(_items)
        if _distinct_on is not None:
            children.append(_distinct_on)
        super().__init__(NodeType.SELECT, children=children, **kwargs)
        self.distinct = _distinct
        self.distinct_on = _distinct_on

    def __eq__(self, other):
        if not isinstance(other, SelectNode):
            return False
        return super().__eq__(other) and self.distinct == other.distinct and self.distinct_on == other.distinct_on  

    def __hash__(self):
        return hash((super().__hash__(), self.distinct, self.distinct_on))


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
    
class WhenThenNode(Node):
    """Single WHEN ... THEN ... branch of a CASE expression"""
    def __init__(self, _when: Node, _then: Node, **kwargs):
        super().__init__(NodeType.WHEN_THEN, children=[_when, _then], **kwargs)
        self.when = _when
        self.then = _then

    def __eq__(self, other):
        if not isinstance(other, WhenThenNode):
            return False
        return super().__eq__(other) and self.when == other.when and self.then == other.then

    def __hash__(self):
        return hash((super().__hash__(), self.when, self.then))


class CaseNode(Node):
    """SQL CASE WHEN ... THEN ... ELSE ... END expression"""
    def __init__(self, _whens: List[WhenThenNode], _else: Optional[Node] = None, **kwargs):
        children: List[Node] = list(_whens)
        if _else is not None:
            children.append(_else)
        super().__init__(NodeType.CASE, children=children, **kwargs)
        self.whens = _whens
        self.else_val = _else

    def __eq__(self, other):
        if not isinstance(other, CaseNode):
            return False
        return super().__eq__(other) and self.whens == other.whens and self.else_val == other.else_val

    def __hash__(self):
        return hash((super().__hash__(), tuple(self.whens), self.else_val))