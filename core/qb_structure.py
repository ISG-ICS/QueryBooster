from dataclasses import dataclass, field
from typing import Any, List, Optional
from enum import Enum
from abc import ABC

# ============================================================================
# Base Node Structure
# ============================================================================

class NodeKind(Enum):
    """Node type enumeration"""
    # Query structure
    QUERY = "query"
    SELECT = "select"
    FROM = "from"
    WHERE = "where"
    GROUP_BY = "group_by"
    HAVING = "having"
    ORDER_BY = "order_by"
    LIMIT = "limit"
    OFFSET = "offset"
    
    # Tables and columns
    TABLE = "table"
    COLUMN = "column"
    SUBQUERY = "subquery"
    
    # Expressions
    LITERAL = "literal"
    COMPARISON = "comparison"
    LOGICAL = "logical"
    ARITHMETIC = "arithmetic"
    CASE = "case"
    CAST = "cast"
    
    # Pattern matching
    VAR = "var"
    VARLIST = "varlist"
    
    # Other
    LIST = "list"
    TUPLE = "tuple"


@dataclass
class Node(ABC):
    """Base class for all nodes"""
    type: NodeKind
    name: str = "" 
    alias: Optional[str] = None
    value: Any = None
    children: List['Node'] = field(default_factory=list)


# ============================================================================
# Specific Node Types
# ============================================================================

@dataclass
class TableNode(Node):
    """Table reference node"""
    type: NodeKind = NodeKind.TABLE
    
    def __init__(self, name: str, alias: Optional[str] = None, **kwargs):
        super().__init__(
            type=NodeKind.TABLE,
            name=name,
            alias=alias,
            **kwargs
        )
    
    def get_identity(self) -> str:
        """Get table identity (alias-insensitive)"""
        return self.name.lower()


@dataclass
class ColumnNode(Node):
    """Column reference node"""
    type: NodeKind = NodeKind.COLUMN
    
    def __init__(self, name: str, table_alias: Optional[str] = None, **kwargs):
        super().__init__(
            type=NodeKind.COLUMN,
            name=name,
            alias=table_alias,
            **kwargs
        )
    
    def get_identity(self) -> str:
        """Get column identity (qualifier-insensitive)"""
        return self.name.lower()


@dataclass
class ComparisonNode(Node):
    """Comparison operation node"""
    type: NodeKind = NodeKind.COMPARISON
    
    def __init__(self, left: 'Node', op: str, right: 'Node', **kwargs):
        super().__init__(
            type=NodeKind.COMPARISON,
            name=op,
            children=[left, right],
            **kwargs
        )


@dataclass
class LogicalNode(Node):
    """Logical operation node (AND/OR)"""
    type: NodeKind = NodeKind.LOGICAL
    
    def __init__(self, op: str, terms: List['Node'], **kwargs):
        super().__init__(
            type=NodeKind.LOGICAL,
            name=op,
            children=terms,
            **kwargs
        )


@dataclass
class ArithmeticNode(Node):
    """Arithmetic operation node"""
    type: NodeKind = NodeKind.ARITHMETIC
    
    def __init__(self, left: 'Node', op: str, right: 'Node', **kwargs):
        super().__init__(
            type=NodeKind.ARITHMETIC,
            name=op,
            children=[left, right],
            **kwargs
        )


@dataclass
class LiteralNode(Node):
    """Literal value node"""
    type: NodeKind = NodeKind.LITERAL
    
    def __init__(self, value: Any, **kwargs):
        super().__init__(
            type=NodeKind.LITERAL,
            value=value,
            **kwargs
        )


@dataclass
class ListNode(Node):
    """List node"""
    type: NodeKind = NodeKind.LIST
    
    def __init__(self, items: List['Node'] = None, **kwargs):
        if items is None:
            items = []
        super().__init__(
            type=NodeKind.LIST,
            children=items,
            **kwargs
        )
    

@dataclass
class VarNode(Node):
    """Pattern variable node"""
    type: NodeKind = NodeKind.VAR
    
    def __init__(self, name: str, var_type: str = 'expr', **kwargs):
        super().__init__(
            type=NodeKind.VAR,
            name=name,
            alias=var_type,
            **kwargs
        )


@dataclass
class VarListNode(Node):
    """Pattern variable list node"""
    type: NodeKind = NodeKind.VARLIST
    
    def __init__(self, name: str, items: List['Node'] = None, **kwargs):
        if items is None:
            items = []
        super().__init__(
            type=NodeKind.VARLIST,
            name=name,
            children=items,
            **kwargs
        )

# ============================================================================
# Query Structure Nodes
# ============================================================================

@dataclass
class SelectNode(Node):
    """SELECT clause node"""
    type: NodeKind = NodeKind.SELECT
    
    def __init__(self, items: List['Node'], **kwargs):
        super().__init__(
            type=NodeKind.SELECT,
            children=items,
            **kwargs
        )


@dataclass
class FromNode(Node):
    """FROM clause node"""
    type: NodeKind = NodeKind.FROM
    
    def __init__(self, tables: List['Node'], **kwargs):
        super().__init__(
            type=NodeKind.FROM,
            children=tables,
            **kwargs
        )


@dataclass
class WhereNode(Node):
    """WHERE clause node"""
    type: NodeKind = NodeKind.WHERE
    
    def __init__(self, condition: 'Node', **kwargs):
        super().__init__(
            type=NodeKind.WHERE,
            children=[condition],
            **kwargs
        )


@dataclass
class QueryNode(Node):
    """Query root node"""
    type: NodeKind = NodeKind.QUERY
    
    def __init__(self, select: Optional['Node'] = None, from_: Optional['Node'] = None, 
                 where: Optional['Node'] = None, **kwargs):
        children = []
        if select:
            children.append(select)
        if from_:
            children.append(from_)
        if where:
            children.append(where)
        super().__init__(
            type=NodeKind.QUERY,
            children=children,
            **kwargs
        )



if __name__ == '__main__':    

    def basic_nodes():
        # Table nodes
        employee_table = TableNode('employee', 'e1')
        department_table = TableNode('department', 'd1')
        
        print(f"Table nodes:")
        print(f"  {employee_table.name} (alias: {employee_table.alias}) -> identity: {employee_table.get_identity()}")
        print(f"  {department_table.name} (alias: {department_table.alias}) -> identity: {department_table.get_identity()}")
        
        # Column nodes
        id_column = ColumnNode('id', 'e1')
        name_column = ColumnNode('name', 'e1')
        salary_column = ColumnNode('salary', 'e1')
        
        print(f"\nColumn nodes:")
        print(f"  {id_column.name} (qualifier: {id_column.alias}) -> identity: {id_column.get_identity()}")
        print(f"  {name_column.name} (qualifier: {name_column.alias}) -> identity: {name_column.get_identity()}")
        print(f"  {salary_column.name} (qualifier: {salary_column.alias}) -> identity: {salary_column.get_identity()}")
        
        # Literal nodes
        age_literal = LiteralNode(25)
        salary_literal = LiteralNode(50000)
        
        print(f"\nLiteral nodes:")
        print(f"  Age: {age_literal.value}")
        print(f"  Salary: {salary_literal.value}")
        
        # Variable nodes for pattern matching
        table_var = VarNode('V001', 'table')
        column_var = VarNode('V002', 'column')
        
        print(f"\nVariable nodes:")
        print(f"  Table var: {table_var.name} (type: {table_var.alias})")
        print(f"  Column var: {column_var.name} (type: {column_var.alias})")
    

    def simple_query():
       # SELECT clause
        select_items = [
            ColumnNode('name', 'e1'),
            ColumnNode('salary', 'e1')
        ]
        select_clause = SelectNode(select_items)
        
        # FROM clause
        from_tables = [TableNode('employee', 'e1')]
        from_clause = FromNode(from_tables)
        
        # WHERE clause
        where_condition = ComparisonNode(
            ColumnNode('age', 'e1'),
            '>',
            LiteralNode(25)
        )
        where_clause = WhereNode(where_condition)
        
        # Complete query
        query = QueryNode(select=select_clause, from_=from_clause, where=where_clause)
        
        print(f"\nQuery structure:")
        print(f"  Type: {query.type}")
        print(f"  Children: {len(query.children)} clauses")
        print(f"  SELECT items: {len(query.children[0].children)}")
        print(f"  FROM tables: {len(query.children[1].children)}")
        print(f"  WHERE conditions: {len(query.children[2].children)}")


    def arithmetic_expressions():
       # Simple arithmetic
        addition = ArithmeticNode(ColumnNode('salary', 'e1'), '+', LiteralNode(1000))
        multiplication = ArithmeticNode(addition, '*', LiteralNode(1.1))
        
        # Complex arithmetic
        complex_arithmetic = ArithmeticNode(
            ArithmeticNode(ColumnNode('base_salary', 'e1'), '+', ColumnNode('bonus', 'e1')),
            '*',
            ArithmeticNode(LiteralNode(1), '+', ColumnNode('raise_percent', 'e1'))
        )
        
        print(f"\nArithmetic expressions:")
        print(f"  Simple: {addition.children[0].name} {addition.name} {addition.children[1].value}")
        print(f"  Nested: {multiplication.children[0].children[0].name} {multiplication.children[0].name} {multiplication.children[0].children[1].value} {multiplication.name} {multiplication.children[1].value}")
        print(f"  Complex: {len(complex_arithmetic.children)} terms")
        
        # Use in WHERE clause
        where_with_arithmetic = WhereNode(
            ComparisonNode(
                complex_arithmetic,
                '>',
                LiteralNode(100000)
            )
        )
        print(f"  Used in WHERE: {where_with_arithmetic.children[0].name}")
    

    def list_operations():
       # Create a list of columns
        columns = [
            ColumnNode('id', 'e1'),
            ColumnNode('name', 'e1'),
            ColumnNode('salary', 'e1')
        ]
        column_list = ListNode(columns)
        
        print(f"\nColumn list:")
        print(f"  Items: {len(column_list.children)}")
        for i, col in enumerate(column_list.children):
            print(f"    {i+1}. {col.name} (qualifier: {col.alias})")
        
        # Add more columns
        column_list.children.append(ColumnNode('hire_date', 'e1'))
        column_list.children.append(ColumnNode('department', 'e1'))
        print(f"  After adding: {len(column_list.children)} items")
        
        # Remove a column
        column_list.children.pop(1)  # Remove 'name'
        print(f"  After removing 'name': {len(column_list.children)} items")
        
        # Modify existing column
        column_list.children[0].name = 'employee_id'
        print(f"  Modified first column: {column_list.children[0].name}")
        
        # Create variable list
        var_list = VarListNode('VL001', [
            VarNode('V001', 'column'),
            VarNode('V002', 'column')
        ])
        print(f"\nVariable list:")
        print(f"  Name: {var_list.name}")
        print(f"  Items: {len(var_list.children)}")
        for i, var in enumerate(var_list.children):
            print(f"    {i+1}. {var.name} (type: {var.alias})")
    

    examples = [basic_nodes, simple_query, arithmetic_expressions, list_operations]

    for example in examples:
        print("="*40)
        example()
