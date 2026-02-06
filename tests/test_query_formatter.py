from core.query_formatter import QueryFormatter
from core.ast.node import (
    OrderByItemNode, QueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode, 
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, LimitNode, OffsetNode, SubqueryNode, VarNode, VarSetNode, JoinNode
)
from core.ast.enums import JoinType, SortOrder
from re import sub
from mo_sql_parsing import parse

formatter = QueryFormatter()

def normalize_sql(s):
    """Remove extra whitespace and normalize SQL string to be used in comparisons"""
    # Remove leading/trailing whitespace and collapse multiple spaces into one
    s = s.strip()
    s = sub(r'\s+', ' ', s)
    # Remove spaces after opening parentheses and before closing parentheses
    s = sub(r'\(\s+', '(', s)
    s = sub(r'\s+\)', ')', s)
    
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
    
    assert parse(sql) == parse(expected_sql)


def test_subquery_format():
    # Tables
    emp_table = TableNode("employee")
    dept_table = TableNode("department")
    
    # Columns
    emp_empno = ColumnNode("empno")
    emp_firstnme = ColumnNode("firstnme")
    emp_lastname = ColumnNode("lastname")
    emp_phoneno = ColumnNode("phoneno")
    emp_workdept = ColumnNode("workdept")
    
    dept_deptno = ColumnNode("deptno")
    dept_deptname = ColumnNode("deptname")
    
    # SELECT clause
    select_clause = SelectNode([emp_empno, emp_firstnme, emp_lastname, emp_phoneno])
    
    # FROM clause
    from_clause = FromNode([emp_table])
    
    # Subquery: SELECT deptno FROM department WHERE deptname = 'OPERATIONS'
    subquery_select = SelectNode([dept_deptno])
    subquery_from = FromNode([dept_table])
    subquery_where_condition = OperatorNode(dept_deptname, "=", LiteralNode("OPERATIONS"))
    subquery_where = WhereNode([subquery_where_condition])
    subquery_query = QueryNode(
        _select=subquery_select,
        _from=subquery_from,
        _where=subquery_where,
    )
    subquery_node = SubqueryNode(subquery_query)
    
    # Main WHERE clause: workdept IN (subquery) AND 1=1
    in_condition = OperatorNode(emp_workdept, "IN", subquery_node)
    literal_condition = OperatorNode(LiteralNode(1), "=", LiteralNode(1))
    where_condition = OperatorNode(in_condition, "AND", literal_condition)
    where_clause = WhereNode([where_condition])
    
    # Complete query AST
    ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    
    # Expected SQL (desired canonical formatting; current formatter may not support this yet)
    expected_sql = """
        SELECT empno, firstnme, lastname, phoneno
        FROM employee
        WHERE workdept IN (
            SELECT deptno
            FROM department
            WHERE deptname = 'OPERATIONS'
        )
        AND 1 = 1
    """
    expected_sql = expected_sql.strip()
    
    sql = formatter.format(ast)
    sql = sql.strip()
    
    assert parse(sql) == parse(expected_sql)