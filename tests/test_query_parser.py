from core.query_parser import QueryParser
from core.ast.node import (
    QueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode, 
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, OrderByItemNode, LimitNode, OffsetNode, JoinNode, SubqueryNode
)
from core.ast.enums import JoinType, SortOrder
from data.queries import get_query

parser = QueryParser()


def test_basic_parse():
    """
    Test parsing of a complex SQL query with JOINs, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, and OFFSET clauses.
    """

    # Construct input query text
    sql = """
        SELECT e.name, d.name as dept_name, COUNT(*) as emp_count
        FROM employees e JOIN departments d ON e.department_id = d.id
        WHERE e.salary > 40000 AND e.age < 60
        GROUP BY d.id, d.name
        HAVING COUNT(*) > 2
        ORDER BY dept_name, emp_count DESC
        LIMIT 10 OFFSET 5
    """

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
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _group_by=group_by_clause,
        _having=having_clause,
        _order_by=order_by_clause,
        _limit=limit_clause,
        _offset=offset_clause
    )

    ast = parser.parse(sql)

    assert ast == expected_ast


def test_subquery_parse():
    """
    Test parsing of a SQL query with subquery in WHERE clause (IN operator).
    """
    query = get_query(9)
    sql = query['pattern']
    
    # Construct expected AST
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
    
    # WHERE clause with subquery
    # Subquery: SELECT deptno FROM department WHERE deptname = 'OPERATIONS'
    subquery_select = SelectNode([dept_deptno])
    subquery_from = FromNode([dept_table])
    subquery_where_condition = OperatorNode(dept_deptname, "=", LiteralNode("OPERATIONS"))
    subquery_where = WhereNode([subquery_where_condition])
    subquery_query = QueryNode(
        _select=subquery_select,
        _from=subquery_from,
        _where=subquery_where
    )
    subquery_node = SubqueryNode(subquery_query)
    
    # Main WHERE clause: workdept IN (subquery) AND 1=1
    in_condition = OperatorNode(emp_workdept, "IN", subquery_node)
    literal_condition = OperatorNode(LiteralNode(1), "=", LiteralNode(1))
    where_condition = OperatorNode(in_condition, "AND", literal_condition)
    where_clause = WhereNode([where_condition])
    
    # Complete query
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause
    )

    qb_ast = parser.parse(sql)
    assert qb_ast == expected_ast