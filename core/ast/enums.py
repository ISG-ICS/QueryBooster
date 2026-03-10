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
    DATA_TYPE = "data_type"
    TIME_UNIT = "time_unit"
    LIST = "list"
    INTERVAL = "interval"

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
    JOIN = "join"
    GROUP_BY = "group_by"
    HAVING = "having"
    ORDER_BY = "order_by"
    ORDER_BY_ITEM = "order_by_item"
    LIMIT = "limit"
    OFFSET = "offset"
    QUERY = "query"
    CASE = "case"
    WHEN_THEN = "when_then"

# ============================================================================
# Join Type Enumeration
# ============================================================================

class JoinType(Enum):
    """Join type enumeration"""
    INNER = "inner"
    OUTER = "outer"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"
    CROSS = "cross"
    NATURAL = "natural"
    SEMI = "semi"
    ANTI = "anti"


# ============================================================================
# Sort Order Enumeration
# ============================================================================

class SortOrder(Enum):
    """Sort order enum"""
    ASC = "ASC"
    DESC = "DESC"