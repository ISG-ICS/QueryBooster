"""
Utility functions for visualizing and working with AST structures.
"""
import textwrap
import sqlparse
from core.ast.node import (
    Node, QueryNode, CompoundQueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode,
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, OrderByItemNode, LimitNode, OffsetNode, JoinNode, SubqueryNode,
    VarNode, VarSetNode
)


def _beautify_sql(sql: str) -> str:
    """
    Beautify SQL query string with proper indentation and formatting.
    
    Uses sqlparse library.
    
    Args:
        sql: Raw SQL query string
        
    Returns:
        Formatted SQL string with proper indentation
    """

    formatted = sqlparse.format(
        sql,
        reindent=True,
        keyword_case="upper"
    )

    return formatted


def _node_to_string(node: Node, indent: int = 0) -> str:
    """
    Convert an AST node to a tree-formatted string representation.
    
    This function recursively converts AST nodes into a human-readable tree format
    for visualization. The translation rules for each node type are:
    
    - TableNode: "table: name [alias]"
      - name: table name
      - [alias]: optional table alias (e.g., "employees [e]")
    
    - ColumnNode: "column: name (parent_alias) as alias"
      - name: column name
      - (parent_alias): optional table alias this column references (e.g., "salary (e)")
      - as alias: optional column-level alias (e.g., "as emp_count")
    
    - LiteralNode: "literal: value"
      - value: the literal value (e.g., 40000, 'text')
    
    - FunctionNode: "function: name as alias"
      - name: function name (e.g., COUNT, SUM)
      - as alias: optional function alias (e.g., "as emp_count")
      - children: function arguments displayed as child nodes
    
    - OperatorNode: "operator: op_name"
      - op_name: the operator (e.g., =, AND, OR, IN, >)
      - children: operands as child nodes
      - Special case for IN: displays a "values:" node containing the list items
    
    - JoinNode: "join: join_type"
      - join_type: INNER, LEFT, RIGHT, FULL, CROSS, etc.
      - children: left table, right table, and join condition
    
    - OrderByItemNode: "order_by_item: sort_order"
      - sort_order: ASC or DESC
      - children: the column being sorted
    
    - SelectNode, FromNode, WhereNode, GroupByNode, HavingNode, OrderByNode: 
      "select", "from", "where", "group_by", "having", "order_by"
      - These clause nodes have children representing their contents
    
    - LimitNode, OffsetNode: "limit: value" / "offset: value"
      - value: the numeric limit or offset
    
    - QueryNode: "query"
      - Represents the root query or a subquery's internal structure
      - children: SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, OFFSET clauses
    
    - SubqueryNode: "subquery [alias]"
      - [alias]: optional subquery alias (e.g., "[grouped_items]")
      - children: the internal QueryNode
    
    Args:
        node: AST node to convert
        indent: Current indentation level
        
    Returns:
        String representation of the node in tree format
    """
    result = []
    prefix = "| " * indent + "+- "
    
    # Get node type name
    node_type = node.type.value if hasattr(node.type, 'value') else str(node.type)
    
    # Build node representation based on node type
    if isinstance(node, TableNode):
        # TableNode: display as "table: table_name [alias]"
        # Example: "table: employees [e]" - "e" is the table alias for reference in WHERE/SELECT
        alias_str = f" [{node.alias}]" if node.alias else ""
        result.append(f"{prefix}{node_type}: {node.name}{alias_str}")
    
    elif isinstance(node, ColumnNode):
        # ColumnNode: display as "column: column_name (parent_alias) as alias"
        # Example: "column: salary (e) as avg_salary"
        # - (e) indicates this column belongs to table with alias "e"
        # - "as avg_salary" is the column's output alias in the result set
        parent_alias = f" ({node.parent_alias})" if node.parent_alias else ""
        alias_str = f" as {node.alias}" if node.alias else ""
        result.append(f"{prefix}{node_type}: {node.name}{parent_alias}{alias_str}")
    
    elif isinstance(node, LiteralNode):
        # LiteralNode: display the literal value
        # Examples: "literal: 40000", "literal: 'hello'", "literal: true"
        result.append(f"{prefix}{node_type}: {node.value}")
    
    elif isinstance(node, FunctionNode):
        # FunctionNode: display as "function: function_name as alias"
        # Example: "function: COUNT as emp_count", "function: SUM"
        # The function arguments are shown as child nodes
        alias_str = f" as {node.alias}" if node.alias else ""
        result.append(f"{prefix}{node_type}: {node.name}{alias_str}")
        if node.children:
            for i, child in enumerate(node.children):
                child_lines = _node_to_string(child, indent + 1).split('\n')
                for line in child_lines:
                    result.append(line)
    
    elif isinstance(node, OperatorNode):
        # OperatorNode: display as "operator: operator_symbol"
        # Examples: "operator: =", "operator: AND", "operator: >", "operator: IN"
        # Binary operators like "=" have two operands (left, right) as children
        # Logical operators like "AND" combine conditions
        result.append(f"{prefix}{node_type}: {node.name}")
        if node.children:
            for i, child in enumerate(node.children):
                if isinstance(child, list):
                    # Special handling for IN operator with list of values
                    # IN can have: (column, IN, [value1, value2, ...])
                    list_prefix = "| " * (indent + 1) + "+- "
                    result.append(f"{list_prefix}values:")
                    for item in child:
                        item_lines = _node_to_string(item, indent + 2).split('\n')
                        for line in item_lines:
                            result.append(line)
                else:
                    child_lines = _node_to_string(child, indent + 1).split('\n')
                    for line in child_lines:
                        result.append(line)
    
    elif isinstance(node, JoinNode):
        # JoinNode: display as "join: join_type"
        # Example: "join: inner" for INNER JOIN
        # Children include: left table, right table, and join condition (ON clause)
        join_type = node.join_type.value if hasattr(node.join_type, 'value') else str(node.join_type)
        result.append(f"{prefix}{node_type}: {join_type}")
        left_lines = _node_to_string(node.left_table, indent + 1).split('\n')
        for line in left_lines:
            result.append(line)
        right_lines = _node_to_string(node.right_table, indent + 1).split('\n')
        for line in right_lines:
            result.append(line)
        if node.on_condition:
            cond_lines = _node_to_string(node.on_condition, indent + 1).split('\n')
            for line in cond_lines:
                result.append(line)
    
    elif isinstance(node, OrderByItemNode):
        # OrderByItemNode: display as "order_by_item: sort_order"
        # Example: "order_by_item: ASC" or "order_by_item: DESC"
        # The column being sorted is shown as a child
        sort_order = node.sort.value if hasattr(node.sort, 'value') else str(node.sort)
        result.append(f"{prefix}{node_type}: {sort_order}")
        if node.children:
            for child in node.children:
                child_lines = _node_to_string(child, indent + 1).split('\n')
                for line in child_lines:
                    result.append(line)
    
    elif isinstance(node, (SelectNode, FromNode, WhereNode, GroupByNode, HavingNode, OrderByNode)):
        # Clause nodes: display as the clause name only
        # Examples: "select", "from", "where", "group_by", "having", "order_by"
        # Children represent the contents of each clause
        result.append(f"{prefix}{node_type}")
        if node.children:
            for child in node.children:
                child_lines = _node_to_string(child, indent + 1).split('\n')
                for line in child_lines:
                    result.append(line)
    
    elif isinstance(node, (LimitNode, OffsetNode)):
        # LimitNode/OffsetNode: display as "limit: value" or "offset: value"
        # Example: "limit: 10", "offset: 5"
        value = node.limit if isinstance(node, LimitNode) else node.offset
        result.append(f"{prefix}{node_type}: {value}")
    
    elif isinstance(node, CompoundQueryNode):
        op = "UNION ALL" if node.is_all else "UNION"
        result.append(f"{prefix}compound_query: {op}")
        for child in node.children:
            child_lines = _node_to_string(child, indent + 1).split('\n')
            for line in child_lines:
                result.append(line)

    elif isinstance(node, QueryNode):
        # QueryNode: root query or subquery structure, display as "query"
        # Maintains tree structure consistency by using proper prefix and indentation
        # Children are the clauses: SELECT, FROM, WHERE, GROUP BY, etc.
        result.append(f"{prefix}query")
        if node.children:
            for child in node.children:
                child_lines = _node_to_string(child, indent + 1).split('\n')
                for line in child_lines:
                    result.append(line)
    
    elif isinstance(node, SubqueryNode):
        # SubqueryNode: display as "subquery [alias]"
        # Example: "subquery [t1]" where "t1" is the alias used to reference this subquery
        # Children: the internal QueryNode representing the subquery's structure
        alias_str = f" [{node.alias}]" if node.alias else ""
        result.append(f"{prefix}{node_type}{alias_str}")
        if node.children:
            for child in node.children:
                child_lines = _node_to_string(child, indent + 1).split('\n')
                for line in child_lines:
                    result.append(line)
    
    elif isinstance(node, (VarNode, VarSetNode)):
        # VarNode/VarSetNode: VarSQL variable, display as "var: name" or "varset: name"
        result.append(f"{prefix}{node_type}: {node.name}")
    
    else:
        # Default case for any other node types
        result.append(f"{prefix}{node_type}")
        if node.children:
            for child in node.children:
                child_lines = _node_to_string(child, indent + 1).split('\n')
                for line in child_lines:
                    result.append(line)
    
    return '\n'.join(result)


def visualize_ast(sql: str, ast: Node, max_sql_width: int = 50) -> str:
    """
    Generate a side-by-side visualization of SQL query and AST structure.
    
    This function beautifies the SQL query on the left and displays the AST
    tree structure on the right, allowing for easy comparison and review.
    Individual SQL lines that exceed max_sql_width are automatically wrapped.
    
    Args:
        sql: SQL query string to visualize
        ast: Root AST node (QueryNode or CompoundQueryNode, etc.)
        max_sql_width: Maximum width for SQL column before wrapping (default: 50)
        
    Returns:
        Formatted string with SQL on the left and AST tree on the right
    """
    # Beautify SQL
    beautified_sql = _beautify_sql(sql)
    sql_lines = beautified_sql.split('\n')
    
    # Wrap long SQL lines to fit within max_sql_width
    wrapped_sql_lines = []
    for line in sql_lines:
        if len(line) > max_sql_width:
            # Wrap long lines, preserving indentation
            wrapped = textwrap.fill(
                line,
                width=max_sql_width,
                subsequent_indent='  ',  # Indent continuation lines
                break_long_words=False,
                break_on_hyphens=False
            )
            wrapped_sql_lines.extend(wrapped.split('\n'))
        else:
            wrapped_sql_lines.append(line)
    
    # Convert AST to tree format
    ast_tree = _node_to_string(ast)
    ast_lines = ast_tree.split('\n')
    
    # Calculate column widths based on wrapped SQL
    actual_sql_width = max(len(line) for line in wrapped_sql_lines) if wrapped_sql_lines else 0
    max_ast_width = max(len(line) for line in ast_lines) if ast_lines else 0
    padding = 3  # Space between columns
    
    total_width = actual_sql_width + padding + max_ast_width
    
    result = []
    result.append("=" * total_width)
    result.append(f"{'SQL QUERY':<{actual_sql_width}}{' ' * padding}{'AST STRUCTURE'}")
    result.append("=" * total_width)
    
    # Merge lines side-by-side
    max_lines = max(len(wrapped_sql_lines), len(ast_lines))
    for i in range(max_lines):
        sql_line = wrapped_sql_lines[i] if i < len(wrapped_sql_lines) else ""
        ast_line = ast_lines[i] if i < len(ast_lines) else ""
        
        # Pad SQL line to match column width
        result.append(f"{sql_line:<{actual_sql_width}}{' ' * padding}{ast_line}")
    
    result.append("=" * total_width)
    
    return '\n'.join(result)
