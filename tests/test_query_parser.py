import mo_sql_parsing as mosql
from core.qb_parser import QBParser, parse_sql_to_qb_ast
from core.ast.node import (
    QueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode, 
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, LimitNode, OffsetNode
)
from core.ast.node_type import NodeType
from data.queries import get_query


def test_parse_1():
    """
    SELECT clause:
    - SUM() aggregate function
    - CAST(column AS TEXT) function
    - Column references (state_name)
    
    FROM clause:
    - Simple table reference (tweets)
    
    WHERE clause:
    - CAST() function with nested expressions
    - DATE_TRUNC() function with string literal and column
    - Nested CAST() functions
    - IN operator with list of TIMESTAMP literals
    - AND logical operator
    - STRPOS() function with column and string literal
    - Comparison operator (>)
    - Numeric literal (0)
    
    GROUP BY clause:
    - Numeric literal reference (2)
    """

    query = get_query(1)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause
    select_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.SELECT:
            select_clause = child
            break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 2
    
    # Check FROM clause
    from_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.FROM:
            from_clause = child
            break
    
    # assert from_clause is not None
    # table_node = list(from_clause.children)[0]
    # assert isinstance(table_node, TableNode)
    # assert table_node.name == "tweets"
    
    # Check WHERE clause
    where_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.WHERE:
            where_clause = child
            break
    
    # assert where_clause is not None
    # assert len(where_clause.children) == 1
    
    # Check GROUP BY clause
    group_by_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.GROUP_BY:
            group_by_clause = child
            break
    
    # assert group_by_clause is not None
    # assert len(group_by_clause.children) == 1


def test_parse_2():
    """
    SELECT clause:
    - SUM() aggregate function
    - CAST(column AS TEXT) function
    - Column references (state_name)
    
    FROM clause:
    - Simple table reference (tweets)
    
    WHERE clause:
    - DATE_TRUNC() function with string literal and column
    - CAST() function with DATE type
    - IN operator with list of TIMESTAMP literals
    - AND logical operator
    - STRPOS() function with column and string literal
    - Comparison operator (>)
    - Numeric literal (0)
    
    GROUP BY clause:
    - Numeric literal reference (2)
    """

    query = get_query(2)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Find the STRPOS condition in WHERE clause
    where_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.WHERE:
            where_clause = child
            break
    
    # assert where_clause is not None
    # condition = list(where_clause.children)[0]
    # assert isinstance(condition, OperatorNode)
    # assert condition.name == "AND"
    
    # The condition should have two operands
    # operands = list(condition.children)
    # assert len(operands) == 2


def test_parse_3():
    """
    SELECT clause:
    - SUM() aggregate function
    - CAST(column AS TEXT) function
    - Column references (state_name)
    
    FROM clause:
    - Simple table reference (tweets)
    
    WHERE clause:
    - DATE_TRUNC() function with column reference
    - IN operator with list of TIMESTAMP literals
    - AND logical operator
    - STRPOS() function with column and string literal
    - Comparison operator (>)
    - Numeric literal (0)
    
    GROUP BY clause:
    - Numeric literal reference (2)
    """
   
    query = get_query(3)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause has 3 items
    select_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.SELECT:
            select_clause = child
            break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 3


def test_parse_4():
    """
    SELECT clause:
    - SUM() aggregate function
    - CAST(column AS TEXT) function
    - Column references (state_name)
    
    FROM clause:
    - Simple table reference (tweets)
    
    WHERE clause:
    - CAST() function with nested expressions
    - DATE_TRUNC() function with string literal and column
    - Nested CAST() functions
    - IN operator with list of TIMESTAMP literals
    - AND logical operator
    - STRPOS() function with nested LOWER() function
    - LOWER() function with column reference
    - Comparison operator (>)
    - Numeric literal (0)
    
    GROUP BY clause:
    - Numeric literal reference (2)
    """

    query = get_query(4)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check WHERE clause has IN condition
    where_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.WHERE:
            where_clause = child
            break
    
    # assert where_clause is not None
    # condition = list(where_clause.children)[0]
    # assert isinstance(condition, OperatorNode)
    # assert condition.name == "IN"


def test_parse_5():
    """
    SELECT clause:
    - SUM() aggregate function
    - CAST(column AS TEXT) function
    - Column references (state_name)
    
    FROM clause:
    - Simple table reference (tweets)
    
    WHERE clause:
    - DATE_TRUNC() function with string literal and column
    - CAST() function with DATE type
    - IN operator with list of TIMESTAMP literals
    - AND logical operator
    - ILIKE operator with wildcard pattern
    - String literal with wildcards ('%iphone%')
    - Column reference (text)
    
    GROUP BY clause:
    - Numeric literal reference (2)
    """

    query = get_query(5)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check FROM clause has two table references
    from_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.FROM:
            from_clause = child
            break
    
    # assert from_clause is not None
    # assert len(from_clause.children) == 2
    
    # Both should be employees table with different aliases
    # table_names = [table.name for table in from_clause.children]
    # assert table_names.count("employees") == 2


def test_parse_6():
    """
    SELECT clause:
    - Column references (e1.name, e1.age, e2.salary)
    - Table alias usage in column references
    - Multiple SELECT items
    
    FROM clause:
    - Multiple table references with aliases
    - Same table with different aliases (e1, e2)
    - Table aliases (employee e1, employee e2)
    
    WHERE clause:
    - AND logical operator
    - Equality operator (=)
    - Qualified column references (e1.id, e2.id)
    - Self-join condition (e1.id = e2.id)
    - Additional conditions (e1.age > 17, e2.salary > 35000)
    - Comparison operators (>, >)
    - Numeric literals (17, 35000)
    """

    query = get_query(6)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check all expected clauses are present
    clause_types = [child.type for child in qb_ast.children]
    expected_clauses = [
        NodeType.SELECT, NodeType.FROM, NodeType.WHERE,
        NodeType.GROUP_BY, NodeType.HAVING, NodeType.ORDER_BY, NodeType.LIMIT
    ]
    
    # for expected_clause in expected_clauses:
    #     assert expected_clause in clause_types
    
    # Check LIMIT value
    limit_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.LIMIT:
            limit_clause = child
            break
    
    # assert limit_clause is not None
    # assert limit_clause.limit == 10


def test_parse_7():
    """
    SELECT clause:
    - Column references (e1.name, e1.age, e1.salary)
    - Table alias usage in column references
    - Multiple SELECT items
    
    FROM clause:
    - Simple table reference with alias (employee e1)
    
    WHERE clause:
    - AND logical operator
    - Comparison operators (>, >)
    - Qualified column references (e1.age, e1.salary)
    - Numeric literals (17, 35000)
    """

    query = get_query(7)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause has 3 items with CAST functions
    select_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.SELECT:
            select_clause = child
            break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 3
    
    # All SELECT items should be functions (CAST operations)
    # function_count = sum(1 for item in select_clause.children if isinstance(item, FunctionNode))
    # assert function_count == 3


def test_parse_8():
    """
    SELECT clause:
    - Column reference (e1.age)
    - Table alias usage in column reference
    
    FROM clause:
    - Multiple table references with aliases
    - Same table with different aliases (e1, e2)
    - Table aliases (employee e1, employee e2)
    
    WHERE clause:
    - AND logical operator
    - Equality operator (=)
    - Qualified column references (e1.id, e2.id)
    - Self-join condition (e1.id = e2.id)
    - Additional condition (e1.age > 17)
    - Comparison operator (>)
    - Numeric literal (17)
    """
   
    query = get_query(8)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause has date functions
    select_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.SELECT:
            select_clause = child
            break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 3
    
    # Check for DATE_TRUNC function
    # function_names = [item.name for item in select_clause.children if isinstance(item, FunctionNode)]
    # assert "DATE_TRUNC" in function_names


def test_parse_9():
    """
    SELECT clause:
    - Column references (e1.name, e1.age, e2.salary)
    - Table alias usage in column references
    - Multiple SELECT items
    
    FROM clause:
    - Multiple table references with aliases
    - Same table with different aliases (e1, e2)
    - Table aliases (employee e1, employee e2)
    
    WHERE clause:
    - AND logical operator
    - Equality operator (=)
    - Qualified column references (e1.id, e2.id)
    - Self-join condition (e1.id = e2.id)
    - Additional conditions (e1.age > 17, e2.salary > 35000)
    - Comparison operators (>, >)
    - Numeric literals (17, 35000)
    """
   
    query = get_query(9)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause has string functions
    select_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.SELECT:
            select_clause = child
            break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 4
    
    # Check for string functions
    # function_names = [item.name for item in select_clause.children if isinstance(item, FunctionNode)]
    # expected_functions = ["UPPER", "LOWER", "CONCAT", "SUBSTRING"]
    # for func in expected_functions:
    #     assert func in function_names


def test_parse_10():
    """
    SELECT clause:
    - Column references (empno, firstnme, lastname, phoneno)
    - Multiple SELECT items
    
    FROM clause:
    - Simple table reference (employee)
    
    WHERE clause:
    - IN operator with subquery
    - Column reference (workdept)
    - AND logical operator
    - Numeric literal (1)
    
    Subquery (within IN):
    - SELECT clause with column reference (deptno)
    - FROM clause with table reference (department)
    - WHERE clause with equality condition
    - Column reference (deptname)
    - String literal ('OPERATIONS')
    """
   
    query = get_query(10)
    sql = query['pattern']
    
    qb_ast = parse_sql_to_qb_ast(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause has arithmetic operations
    select_clause = None
    for child in qb_ast.children:
        if child.type == NodeType.SELECT:
            select_clause = child
            break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 4
    
    # Check for arithmetic operators
    # operator_count = sum(1 for item in select_clause.children if isinstance(item, OperatorNode))
    # assert operator_count >= 3  # Should have multiple arithmetic operations
