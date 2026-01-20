from core.query_formatter import QueryFormatter
from core.ast.node import (
    OrderByItemNode, QueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode, 
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, LimitNode, OffsetNode, SubqueryNode, VarNode, VarSetNode, JoinNode
)
from core.ast.enums import JoinType, SortOrder
from re import sub

formatter = QueryFormatter()

def normalize_sql(s):
    """Remove extra whitespace and normalize SQL string to be used in comparisons"""
    s = s.strip()
    s = sub(r'\s+', ' ', s)
    
    return s

def test_basic_format():
    # Construct expected AST
    # Tables
    emp_table = TableNode("employees", "e")
    dept_table = TableNode("departments", "d")
    # Columns
    emp_name = ColumnNode("name", _parent_alias="e")
    emp_salary = ColumnNode("salary", _parent_alias="e")
    emp_age = ColumnNode("age", _parent_alias="e")
    emp_dept_id = ColumnNode("department_id", _parent_alias="e")

    dept_name = ColumnNode("name", _alias="dept_name", _parent_alias="d")
    dept_id = ColumnNode("id", _parent_alias="d")

    count_star = FunctionNode("COUNT", _alias="emp_count", _args=[ColumnNode("*")])

    # SELECT clause
    select_clause = SelectNode([emp_name, dept_name, count_star])
    # FROM clause with JOIN
    join_condition = OperatorNode(emp_dept_id, "=", dept_id)
    join_node = JoinNode(emp_table, dept_table, JoinType.INNER, join_condition)
    from_clause = FromNode([join_node])
    # WHERE clause
    salary_condition = OperatorNode(emp_salary, ">", LiteralNode(40000))
    age_condition = OperatorNode(emp_age, "<", LiteralNode(60))
    where_condition = OperatorNode(salary_condition, "AND", age_condition)
    where_clause = WhereNode([where_condition])
    # GROUP BY clause
    group_by_clause = GroupByNode([dept_id, dept_name])
    # HAVING clause
    having_condition = OperatorNode(count_star, ">", LiteralNode(2))
    having_clause = HavingNode([having_condition])
    # ORDER BY clause
    order_by_item1 = OrderByItemNode(dept_name, SortOrder.ASC)
    order_by_item2 = OrderByItemNode(count_star, SortOrder.DESC)
    order_by_clause = OrderByNode([order_by_item1, order_by_item2])
    # LIMIT and OFFSET
    limit_clause = LimitNode(10)
    offset_clause = OffsetNode(5)
    # Complete query
    ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _group_by=group_by_clause,
        _having=having_clause,
        _order_by=order_by_clause,
        _limit=limit_clause,
        _offset=offset_clause
    )

    # Construct expected query text
    expected_sql = """
        SELECT e.name, d.name AS dept_name, COUNT(*) AS emp_count
        FROM employees AS e JOIN departments AS d ON e.department_id = d.id
        WHERE e.salary > 40000 AND e.age < 60
        GROUP BY d.id, d.name
        HAVING COUNT(*) > 2
        ORDER BY dept_name, emp_count DESC
        LIMIT 10 OFFSET 5
    """
    expected_sql = expected_sql.strip()

    sql = formatter.format(ast)
    sql = sql.strip()
    
    assert normalize_sql(sql) == normalize_sql(expected_sql)