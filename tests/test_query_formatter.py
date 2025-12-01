import mo_sql_parsing as mosql
from core.query_formatter import QueryFormatter
from core.ast.node import (
    OrderByItemNode, QueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode, 
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, LimitNode, OffsetNode, SubqueryNode, VarNode, VarSetNode
)
from core.ast.enums import NodeType, JoinType, SortOrder
from data.queries import get_query
from re import sub

formatter = QueryFormatter()

def normalize_sql(s):
    """Remove extra whitespace and normalize SQL string to be used in comparisons"""
    s = s.strip()
    s = sub(r'\s+', ' ', s)
    
    return s

def test_basic_format():
    # Construct input AST
    # Tables
    emp_table = TableNode("employees", "e")
    dept_table = TableNode("departments", "d")
    # Columns
    emp_name = ColumnNode("name", _parent_alias="e")
    dept_name = ColumnNode("name", "dept_name", "d")
    emp_salary = ColumnNode("salary", _parent_alias="e")
    emp_age = ColumnNode("age", _parent_alias="e")
    emp_dept_id = ColumnNode("department_id", _parent_alias="e")
    dept_id = ColumnNode("id", _parent_alias="d")
    count_star = FunctionNode("COUNT", {ColumnNode("*")}, 'emp_count')
    count_alias = ColumnNode("emp_count")
    dept_alias = ColumnNode("dept_name")

    # SELECT clause
    select_clause = SelectNode([emp_name, dept_name, count_star])
    # FROM clause (with implicit JOIN logic)
    from_clause = FromNode([emp_table, dept_table])
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
    order_by_clause = OrderByNode([
        OrderByItemNode(dept_alias, SortOrder.DESC),
        OrderByItemNode(count_alias, SortOrder.DESC)  
    ])  
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
    print(mosql.parse(expected_sql))
    print(ast)

    sql = formatter.format(ast)
    sql = sql.strip()
    
    assert normalize_sql(sql) == normalize_sql(expected_sql)