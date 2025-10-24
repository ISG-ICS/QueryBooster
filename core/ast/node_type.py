from enum import Enum

# ============================================================================
# Node Type Enumeration
# ============================================================================

class NodeType(Enum):
    """Node type enumeration"""
    
    # Operands
    TABLE = "table"
    SUBQUERY = "subquery"
    COLUMN = "column"
    LITERAL = "literal"
    # VarSQL specific
    VAR = "var"
    VARSET = "varset"

    # Operators
    OPERATOR = "operator"
    FUNCTION = "function"
    
    # Query structure
    SELECT = "select"
    FROM = "from"
    WHERE = "where"
    GROUP_BY = "group_by"
    HAVING = "having"
    ORDER_BY = "order_by"
    ORDER_BY_ITEM = "order_by_item"
    LIMIT = "limit"
    OFFSET = "offset"
    QUERY = "query"
