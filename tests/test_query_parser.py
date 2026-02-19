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


def test_query_1():
    """Query 1: Remove Cast Date Match Twice."""
    query = get_query(1)
    sql = query["pattern"]

    # Construct expected AST
    # Tables
    tweets_table = TableNode("tweets")
    # SELECT: SUM(1), CAST(state_name AS TEXT)
    sum_one = FunctionNode("SUM", _args=[LiteralNode(1)])
    cast_state = FunctionNode(
        "CAST",
        # TODO: keywords like TEXT, INTEGER should not be function node
        _args=[ColumnNode("state_name"), FunctionNode("TEXT", _args=[LiteralNode("{}")])],
    )
    select_clause = SelectNode([sum_one, cast_state])
    # FROM
    from_clause = FromNode([tweets_table])
    # WHERE: CAST(DATE_TRUNC(...)) IN (timestamps) AND STRPOS(text, 'iphone') > 0
    ts_list = [
        FunctionNode("TIMESTAMP", _args=[LiteralNode("2016-10-01 00:00:00.000")]),
        FunctionNode("TIMESTAMP", _args=[LiteralNode("2017-01-01 00:00:00.000")]),
        FunctionNode("TIMESTAMP", _args=[LiteralNode("2017-04-01 00:00:00.000")]),
    ]
    date_trunc_inner = FunctionNode(
        "CAST",
        _args=[
            ColumnNode("created_at"),
            # TODO: keywords like DATE should not be function node
            FunctionNode("DATE", _args=[LiteralNode("{}")]),
        ],
    )
    date_trunc_outer = FunctionNode(
        "CAST",
        _args=[
            FunctionNode("DATE_TRUNC", _args=[LiteralNode("QUARTER"), date_trunc_inner]),
            # TODO: same as above
            FunctionNode("DATE", _args=[LiteralNode("{}")]),
        ],
    )
    in_timestamps = OperatorNode(date_trunc_outer, "IN", ts_list)
    strpos_cond = OperatorNode(
        FunctionNode("STRPOS", _args=[ColumnNode("text"), LiteralNode("iphone")]),
        ">",
        LiteralNode(0),
    )
    where_condition = OperatorNode(in_timestamps, "AND", strpos_cond)
    where_clause = WhereNode([where_condition])
    # GROUP BY 2
    group_by_clause = GroupByNode([LiteralNode(2)])
    # Complete query
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _group_by=group_by_clause,
    )
    #assert parser.parse(sql) == expected_ast


def test_query_2():
    """Query 2: Remove Cast Date Match Once."""
    query = get_query(2)
    sql = query["rewrite"]

    # Construct expected AST
    # Tables
    tweets_table = TableNode("tweets")
    # SELECT
    sum_one = FunctionNode("SUM", _args=[LiteralNode(1)])
    cast_state = FunctionNode(
        "CAST",
        # TODO: keywords like TEXT, INTEGER should not be function node
        _args=[ColumnNode("state_name"), FunctionNode("TEXT", _args=[LiteralNode("{}")])],
    )
    select_clause = SelectNode([sum_one, cast_state])
    from_clause = FromNode([tweets_table])
    # WHERE: DATE_TRUNC(QUARTER, created_at) IN (...) AND STRPOS(...) > 0
    ts_list = [
        FunctionNode("TIMESTAMP", _args=[LiteralNode("2016-10-01 00:00:00.000")]),
        FunctionNode("TIMESTAMP", _args=[LiteralNode("2017-01-01 00:00:00.000")]),
        FunctionNode("TIMESTAMP", _args=[LiteralNode("2017-04-01 00:00:00.000")]),
    ]
    in_timestamps = OperatorNode(
        FunctionNode("DATE_TRUNC", _args=[LiteralNode("QUARTER"), ColumnNode("created_at")]),
        "IN",
        ts_list,
    )
    strpos_cond = OperatorNode(
        FunctionNode("STRPOS", _args=[ColumnNode("text"), LiteralNode("iphone")]),
        ">",
        LiteralNode(0),
    )
    where_clause = WhereNode([OperatorNode(in_timestamps, "AND", strpos_cond)])
    group_by_clause = GroupByNode([LiteralNode(2)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _group_by=group_by_clause,
    )
    #assert parser.parse(sql) == expected_ast

# query 3 has the exact same query as query 2, so I skipped it

def test_query_4():
    """Query 4."""
    query = get_query(4)
    sql = query["rewrite"]

    # Construct expected AST
    tweets_table = TableNode("tweets")
    sum_one = FunctionNode("SUM", _args=[LiteralNode(1)])
    cast_state = FunctionNode(
        "CAST",
        _args=[ColumnNode("state_name"), FunctionNode("TEXT", _args=[LiteralNode("{}")])],
    )
    select_clause = SelectNode([sum_one, cast_state])
    from_clause = FromNode([tweets_table])
    ts_list = [
        FunctionNode("TIMESTAMP", _args=[LiteralNode("2016-10-01 00:00:00.000")]),
        FunctionNode("TIMESTAMP", _args=[LiteralNode("2017-01-01 00:00:00.000")]),
        FunctionNode("TIMESTAMP", _args=[LiteralNode("2017-04-01 00:00:00.000")]),
    ]
    date_trunc_inner = FunctionNode(
        "CAST",
        # TODO: keywords like DATE should not be function node
        _args=[ColumnNode("created_at"), FunctionNode("DATE", _args=[LiteralNode("{}")])],
    )
    date_trunc_outer = FunctionNode(
        "CAST",
        _args=[
            FunctionNode("DATE_TRUNC", _args=[LiteralNode("QUARTER"), date_trunc_inner]),
            # TODO: same as above
            FunctionNode("DATE", _args=[LiteralNode("{}")]),
        ],
    )
    in_timestamps = OperatorNode(date_trunc_outer, "IN", ts_list)
    ilike_cond = FunctionNode(
        "ILIKE",
        _args=[ColumnNode("text"), LiteralNode("%iphone%")],
    )
    where_clause = WhereNode([OperatorNode(in_timestamps, "AND", ilike_cond)])
    group_by_clause = GroupByNode([LiteralNode(2)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _group_by=group_by_clause,
    )
    #assert parser.parse(sql) == expected_ast

# query 5 has the exact same query as query 4, so I skipped it

def test_query_6():
    """Query 6: Remove Self Join Match."""
    query = get_query(6)
    sql = query["pattern"]

    # Construct expected AST
    # Tables (self-join: employee e1, employee e2)
    e1_table = TableNode("employee", _alias="e1")
    e2_table = TableNode("employee", _alias="e2")
    # Columns
    e1_name = ColumnNode("name", _parent_alias="e1")
    e1_age = ColumnNode("age", _parent_alias="e1")
    e1_id = ColumnNode("id", _parent_alias="e1")
    e2_id = ColumnNode("id", _parent_alias="e2")
    e2_salary = ColumnNode("salary", _parent_alias="e2")
    # SELECT
    select_clause = SelectNode([e1_name, e1_age, e2_salary])
    from_clause = FromNode([e1_table, e2_table])
    # WHERE: e1.id = e2.id AND e1.age > 17 AND e2.salary > 35000
    id_eq = OperatorNode(e1_id, "=", e2_id)
    age_cond = OperatorNode(e1_age, ">", LiteralNode(17))
    salary_cond = OperatorNode(e2_salary, ">", LiteralNode(35000))
    where_condition = OperatorNode(
        OperatorNode(id_eq, "AND", age_cond),
        "AND",
        salary_cond,
    )
    where_clause = WhereNode([where_condition])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_7():
    """Query 7: Remove Self Join No Match."""
    query = get_query(7)
    sql = query["pattern"]

    # Construct expected AST
    e1_table = TableNode("employee", _alias="e1")
    e1_name = ColumnNode("name", _parent_alias="e1")
    e1_age = ColumnNode("age", _parent_alias="e1")
    e1_salary = ColumnNode("salary", _parent_alias="e1")
    select_clause = SelectNode([e1_name, e1_age, e1_salary])
    from_clause = FromNode([e1_table])
    age_cond = OperatorNode(e1_age, ">", LiteralNode(17))
    salary_cond = OperatorNode(e1_salary, ">", LiteralNode(35000))
    where_clause = WhereNode([OperatorNode(age_cond, "AND", salary_cond)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_8():
    """Query 8."""
    query = get_query(8)
    sql = query["pattern"]

    # Construct expected AST
    e1_table = TableNode("employee", _alias="e1")
    e2_table = TableNode("employee", _alias="e2")
    e1_age = ColumnNode("age", _parent_alias="e1")
    e1_id = ColumnNode("id", _parent_alias="e1")
    e2_id = ColumnNode("id", _parent_alias="e2")
    select_clause = SelectNode([e1_age])
    from_clause = FromNode([e1_table, e2_table])
    id_eq = OperatorNode(e1_id, "=", e2_id)
    age_cond = OperatorNode(e1_age, ">", LiteralNode(17))
    where_clause = WhereNode([OperatorNode(id_eq, "AND", age_cond)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast

# query 9 is used in test_subquery_parse

def test_query_10():
    """Query 10: Subquery to Join Match 2."""
    query = get_query(10)
    sql = query["pattern"]

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
    emp_age = ColumnNode("age")
    dept_deptno = ColumnNode("deptno")
    dept_deptname = ColumnNode("deptname")
    # Subquery: SELECT deptno FROM department WHERE deptname = 'OPERATIONS'
    subquery_select = SelectNode([dept_deptno])
    subquery_from = FromNode([dept_table])
    subquery_where = WhereNode([OperatorNode(dept_deptname, "=", LiteralNode("OPERATIONS"))])
    subquery_node = SubqueryNode(
        QueryNode(_select=subquery_select, _from=subquery_from, _where=subquery_where)
    )
    # Main query
    select_clause = SelectNode([emp_empno, emp_firstnme, emp_lastname, emp_phoneno])
    from_clause = FromNode([emp_table])
    in_cond = OperatorNode(emp_workdept, "IN", subquery_node)
    age_cond = OperatorNode(emp_age, ">", LiteralNode(17))
    where_clause = WhereNode([OperatorNode(in_cond, "AND", age_cond)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_11():
    """Query 11: Subquery to Join Match 3."""
    query = get_query(11)
    sql = query["rewrite"]

    # Construct expected AST for rewrite: SELECT DISTINCT e.* FROM employee e, department d WHERE e.workdept = d.deptno AND d.deptname = 'OPERATIONS' AND e.age > 17
    # TODO: Rewrite has SELECT DISTINCT (not supported by parser yet)
    emp_table = TableNode("employee", _alias="e")
    dept_table = TableNode("department", _alias="d")
    e_empno = ColumnNode("empno", _parent_alias="e")
    e_firstnme = ColumnNode("firstnme", _parent_alias="e")
    e_lastname = ColumnNode("lastname", _parent_alias="e")
    e_phoneno = ColumnNode("phoneno", _parent_alias="e")
    e_workdept = ColumnNode("workdept", _parent_alias="e")
    e_age = ColumnNode("age", _parent_alias="e")
    d_deptno = ColumnNode("deptno", _parent_alias="d")
    d_deptname = ColumnNode("deptname", _parent_alias="d")
    select_clause = SelectNode([e_empno, e_firstnme, e_lastname, e_phoneno])
    from_clause = FromNode([emp_table, dept_table])
    workdept_eq = OperatorNode(e_workdept, "=", d_deptno)
    deptname_eq = OperatorNode(d_deptname, "=", LiteralNode("OPERATIONS"))
    age_cond = OperatorNode(e_age, ">", LiteralNode(17))
    where_condition = OperatorNode(
        OperatorNode(workdept_eq, "AND", deptname_eq),
        "AND",
        age_cond,
    )
    where_clause = WhereNode([where_condition])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    #assert parser.parse(sql) == expected_ast


def test_query_12():
    """Query 12: Join to Filter Match 1."""
    query = get_query(12)
    sql = query["pattern"]

    # Construct expected AST
    # Tables and JOINs (two INNER JOINs)
    t0 = TableNode("blc_admin_permission", _alias="adminpermi0_")
    t1 = TableNode("blc_admin_role_permission_xref", _alias="allroles1_")
    t2 = TableNode("blc_admin_role", _alias="adminrolei2_")
    join_on_1 = OperatorNode(
        ColumnNode("admin_permission_id", _parent_alias="adminpermi0_"),
        "=",
        ColumnNode("admin_permission_id", _parent_alias="allroles1_"),
    )
    join_on_2 = OperatorNode(
        ColumnNode("admin_role_id", _parent_alias="allroles1_"),
        "=",
        ColumnNode("admin_role_id", _parent_alias="adminrolei2_"),
    )
    join_1 = JoinNode(t0, t1, JoinType.INNER, join_on_1)
    join_2 = JoinNode(join_1, t2, JoinType.INNER, join_on_2)
    select_clause = SelectNode([ColumnNode("*")])
    from_clause = FromNode([join_2])
    role_eq_1 = OperatorNode(
        ColumnNode("admin_role_id", _parent_alias="adminrolei2_"),
        "=",
        LiteralNode(1),
    )
    one_eq_one = OperatorNode(LiteralNode(1), "=", LiteralNode(1))
    where_clause = WhereNode([OperatorNode(role_eq_1, "AND", one_eq_one)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_13():
    """Query 13: Join to Filter Match 2."""
    query = get_query(13)
    sql = query["pattern"]

    # Construct expected AST
    t0 = TableNode("blc_admin_permission", _alias="adminpermi0_")
    t1 = TableNode("blc_admin_role_permission_xref", _alias="allroles1_")
    t2 = TableNode("blc_admin_role", _alias="adminrolei2_")
    join_on_1 = OperatorNode(
        ColumnNode("admin_permission_id", _parent_alias="adminpermi0_"),
        "=",
        ColumnNode("admin_permission_id", _parent_alias="allroles1_"),
    )
    join_on_2 = OperatorNode(
        ColumnNode("admin_role_id", _parent_alias="allroles1_"),
        "=",
        ColumnNode("admin_role_id", _parent_alias="adminrolei2_"),
    )
    join_1 = JoinNode(t0, t1, JoinType.INNER, join_on_1)
    join_2 = JoinNode(join_1, t2, JoinType.INNER, join_on_2)
    count_col = FunctionNode(
        "COUNT",
        _args=[ColumnNode("admin_permission_id", _parent_alias="adminpermi0_")],
        _alias="col_0_0_",
    )
    select_clause = SelectNode([count_col])
    from_clause = FromNode([join_2])
    is_friendly_cond = OperatorNode(
        ColumnNode("is_friendy", _parent_alias="adminpermi0_"),
        "=",
        LiteralNode(1),
    )
    role_eq_cond = OperatorNode(
        ColumnNode("admin_role_id", _parent_alias="adminrolei2_"),
        "=",
        LiteralNode(1),
    )
    where_clause = WhereNode([OperatorNode(is_friendly_cond, "AND", role_eq_cond)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_14():
    """Query 14: Test Rule Wetune 90 Match."""
    query = get_query(14)
    sql = query["pattern"]

    # Construct expected AST
    t0 = TableNode("blc_admin_permission", _alias="adminpermi0_")
    t1 = TableNode("blc_admin_role_permission_xref", _alias="allroles1_")
    t2 = TableNode("blc_admin_role", _alias="adminrolei2_")
    join_on_1 = OperatorNode(
        ColumnNode("admin_permission_id", _parent_alias="adminpermi0_"),
        "=",
        ColumnNode("admin_permission_id", _parent_alias="allroles1_"),
    )
    join_on_2 = OperatorNode(
        ColumnNode("admin_role_id", _parent_alias="allroles1_"),
        "=",
        ColumnNode("admin_role_id", _parent_alias="adminrolei2_"),
    )
    join_1 = JoinNode(t0, t1, JoinType.INNER, join_on_1)
    join_2 = JoinNode(join_1, t2, JoinType.INNER, join_on_2)
    # SELECT (aliased columns)
    col_id = ColumnNode("admin_permission_id", _alias="admin_pe1_4_", _parent_alias="adminpermi0_")
    col_desc = ColumnNode("description", _alias="descript2_4_", _parent_alias="adminpermi0_")
    col_friendly = ColumnNode("is_friendly", _alias="is_frien3_4_", _parent_alias="adminpermi0_")
    col_name = ColumnNode("name", _alias="name4_4_", _parent_alias="adminpermi0_")
    col_type = ColumnNode("permission_type", _alias="permissi5_4_", _parent_alias="adminpermi0_")
    select_clause = SelectNode([col_id, col_desc, col_friendly, col_name, col_type])
    from_clause = FromNode([join_2])
    is_friendly_cond = OperatorNode(
        ColumnNode("is_friendly", _parent_alias="adminpermi0_"), "=", LiteralNode(1)
    )
    role_eq_cond = OperatorNode(
        ColumnNode("admin_role_id", _parent_alias="adminrolei2_"), "=", LiteralNode(1)
    )
    where_clause = WhereNode([OperatorNode(is_friendly_cond, "AND", role_eq_cond)])
    order_by_clause = OrderByNode(
        [OrderByItemNode(ColumnNode("description", _parent_alias="adminpermi0_"), SortOrder.ASC)]
    )
    limit_clause = LimitNode(50)
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _order_by=order_by_clause,
        _limit=limit_clause,
    )
    assert parser.parse(sql) == expected_ast


#TODO: Query 15 uses UNION, which is not supported by parser yet


def test_query_16():
    """Query 16: Remove Max Distinct."""
    query = get_query(16)
    sql = query["pattern"]

    # Construct expected AST
    # TODO: DISTINCT is not supported by parser yet
    table_s = TableNode("S")
    table_r = TableNode("R")
    col_a = ColumnNode("A")
    col_d = ColumnNode("D")
    # Subquery: SELECT B FROM R WHERE C = 0
    subquery_select = SelectNode([ColumnNode("B")])
    subquery_from = FromNode([table_r])
    subquery_where = WhereNode([OperatorNode(ColumnNode("C"), "=", LiteralNode(0))])
    subquery_node = SubqueryNode(QueryNode(_select=subquery_select, _from=subquery_from, _where=subquery_where))
    # MAX(DISTINCT(subquery))
    distinct_subquery = FunctionNode("DISTINCT", _args=[subquery_node])
    max_distinct = FunctionNode("MAX", _args=[distinct_subquery])
    select_clause = SelectNode([col_a, max_distinct, col_d])
    from_clause = FromNode([table_s])
    expected_ast = QueryNode(_select=select_clause, _from=from_clause)
    
    #assert parser.parse(sql) == expected_ast


def test_query_17():
    """Query 17."""
    query = get_query(17)
    sql = query["pattern"]

    # Construct expected AST
    t0 = TableNode("o_auth_applications")
    t1 = TableNode("authorizations")
    join_on = OperatorNode(
        ColumnNode("id", _parent_alias="o_auth_applications"),
        "=",
        ColumnNode("o_auth_application_id", _parent_alias="authorizations"),
    )
    join_node = JoinNode(t0, t1, JoinType.INNER, join_on)
    id_col = ColumnNode("id", _parent_alias="o_auth_applications")
    select_clause = SelectNode([id_col])
    from_clause = FromNode([join_node])
    user_id_cond = OperatorNode(
        ColumnNode("user_id", _parent_alias="authorizations"), "=", LiteralNode(1465)
    )
    where_clause = WhereNode([user_id_cond])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_18():
    """Query 18 (parser drops SELECT for SELECT DISTINCT with comma join)."""
    query = get_query(18)
    sql = query["pattern"]

    # Construct expected AST
    # TODO: DISTINCT is not supported by parser yet
    my_table = TableNode("my_table")
    your_table = TableNode("your_table")
    my_foo = ColumnNode("foo", _parent_alias="my_table")
    your_boo = ColumnNode("boo", _parent_alias="your_table")
    select_clause = SelectNode([my_foo, your_boo])  # DISTINCT keyword not represented
    from_clause = FromNode([my_table, your_table])
    num_my = OperatorNode(ColumnNode("num", _parent_alias="my_table"), "=", LiteralNode(1))
    num_your = OperatorNode(ColumnNode("num", _parent_alias="your_table"), "=", LiteralNode(2))
    where_clause = WhereNode([OperatorNode(num_my, "OR", num_your)])
    expected_ast = QueryNode(_select=select_clause, _from=from_clause, _where=where_clause)
    #assert parser.parse(sql) == expected_ast


def test_query_19():
    """Query 19: Stackoverflow 2."""
    query = get_query(19)
    sql = query["pattern"]

    # Construct expected AST
    table_a = TableNode("A", _alias="a")
    table_b = TableNode("B", _alias="b")
    join_on = OperatorNode(
        ColumnNode("id", _parent_alias="a"),
        "=",
        ColumnNode("cid", _parent_alias="b"),
    )
    join_node = JoinNode(table_a, table_b, JoinType.LEFT, join_on)
    select_clause = SelectNode([ColumnNode("*")])
    from_clause = FromNode([join_node])
    b_cl1 = ColumnNode("cl1", _parent_alias="b")
    b_cl1_s1 = OperatorNode(b_cl1, "=", LiteralNode("s1"))
    b_cl1_s2 = OperatorNode(b_cl1, "=", LiteralNode("s2"))
    where_clause = WhereNode([OperatorNode(b_cl1_s1, "OR", b_cl1_s2)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_20():
    """Query 20: Partial Matching Base Case 2."""
    query = get_query(20)
    sql = query["pattern"]

    # Construct expected AST
    table_b = TableNode("b")
    b_cl1 = ColumnNode("cl1", _parent_alias="b")
    in_s1_s2 = OperatorNode(b_cl1, "IN", LiteralNode(["s1", "s2"]))
    eq_s3 = OperatorNode(b_cl1, "=", LiteralNode("s3"))
    select_clause = SelectNode([ColumnNode("*")])
    from_clause = FromNode([table_b])
    where_clause = WhereNode([OperatorNode(in_s1_s2, "OR", eq_s3)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_21():
    """Query 21: Partial Matching 0."""
    query = get_query(21)
    sql = query["pattern"]

    # Construct expected AST
    table_a = TableNode("A", _alias="a")
    table_b = TableNode("B", _alias="b")
    join_on = OperatorNode(
        ColumnNode("id", _parent_alias="a"),
        "=",
        ColumnNode("cid", _parent_alias="b"),
    )
    join_node = JoinNode(table_a, table_b, JoinType.LEFT, join_on)
    b_cl1 = ColumnNode("cl1", _parent_alias="b")
    or_s1_s2 = OperatorNode(
        OperatorNode(b_cl1, "=", LiteralNode("s1")),
        "OR",
        OperatorNode(b_cl1, "=", LiteralNode("s2")),
    )
    or_s3 = OperatorNode(b_cl1, "=", LiteralNode("s3"))
    select_clause = SelectNode([ColumnNode("*")])
    from_clause = FromNode([join_node])
    where_clause = WhereNode([OperatorNode(or_s1_s2, "OR", or_s3)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_22():
    """Query 22: Partial Matching 4."""
    query = get_query(22)
    sql = query["pattern"]

    # Construct expected AST
    emp_table = TableNode("employee")
    dept_table = TableNode("department")
    emp_empno = ColumnNode("empno")
    emp_firstname = ColumnNode("firstname")
    emp_lastname = ColumnNode("lastname")
    emp_phoneno = ColumnNode("phoneno")
    emp_workdept = ColumnNode("workdept")
    dept_deptno = ColumnNode("deptno")
    dept_deptname = ColumnNode("deptname")
    subquery_select = SelectNode([dept_deptno])
    subquery_from = FromNode([dept_table])
    subquery_where = WhereNode([OperatorNode(dept_deptname, "=", LiteralNode("OPERATIONS"))])
    subquery_node = SubqueryNode(
        QueryNode(_select=subquery_select, _from=subquery_from, _where=subquery_where)
    )
    select_clause = SelectNode([emp_empno, emp_firstname, emp_lastname, emp_phoneno])
    from_clause = FromNode([emp_table])
    in_cond = OperatorNode(emp_workdept, "IN", subquery_node)
    like_cond = FunctionNode("LIKE", _args=[emp_firstname, LiteralNode("B%")])
    where_clause = WhereNode([OperatorNode(in_cond, "AND", like_cond)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_23():
    """Query 23: Partial Keeps Remaining OR."""
    query = get_query(23)
    sql = query["pattern"]

    # Construct expected AST
    entities_table = TableNode("entities")
    entities_data = ColumnNode("data", _parent_alias="entities")
    entities_id = ColumnNode("_id", _parent_alias="entities")
    # Subquery 1: index_users_email
    sub1_select = SelectNode([ColumnNode("_id", _parent_alias="index_users_email")])
    sub1_from = FromNode([TableNode("index_users_email")])
    sub1_where = WhereNode([
        OperatorNode(ColumnNode("key", _parent_alias="index_users_email"), "=", LiteralNode("test"))
    ])
    sub1 = SubqueryNode(QueryNode(_select=sub1_select, _from=sub1_from, _where=sub1_where))
    # Subquery 2: index_users_profile_name
    sub2_select = SelectNode([ColumnNode("_id", _parent_alias="index_users_profile_name")])
    sub2_from = FromNode([TableNode("index_users_profile_name")])
    sub2_where = WhereNode([
        OperatorNode(
            ColumnNode("key", _parent_alias="index_users_profile_name"),
            "=",
            LiteralNode("test"),
        )
    ])
    sub2 = SubqueryNode(QueryNode(_select=sub2_select, _from=sub2_from, _where=sub2_where))
    select_clause = SelectNode([entities_data])
    from_clause = FromNode([entities_table])
    in1 = OperatorNode(entities_id, "IN", sub1)
    in2 = OperatorNode(entities_id, "IN", sub2)
    where_clause = WhereNode([OperatorNode(in1, "OR", in2)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_24():
    """Query 24: Partial Keeps Remaining AND."""
    query = get_query(24)
    sql = query["pattern"]

    # Construct expected AST
    emp_table = TableNode("EMP")
    empno_gt = OperatorNode(ColumnNode("EMPNO"), ">", LiteralNode(10))
    empno_lte = OperatorNode(ColumnNode("EMPNO"), "<=", LiteralNode(10))
    like_cond = FunctionNode("LIKE", _args=[ColumnNode("EMPNAME"), LiteralNode("%Jason%")])
    select_clause = SelectNode([ColumnNode("Empno")])
    from_clause = FromNode([emp_table])
    and_contradiction = OperatorNode(empno_gt, "AND", empno_lte)
    where_clause = WhereNode([OperatorNode(and_contradiction, "AND", like_cond)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_25():
    """Query 25: And On True."""
    query = get_query(25)
    sql = query["pattern"]

    # Construct expected AST
    people_table = TableNode("people")
    name_col = ColumnNode("name", _parent_alias="people")
    select_clause = SelectNode([name_col])
    from_clause = FromNode([people_table])
    one_and_one = OperatorNode(LiteralNode(1), "AND", LiteralNode(1))
    where_clause = WhereNode([one_and_one])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_26():
    """Query 26: Multiple And On True."""
    query = get_query(26)
    sql = query["pattern"]

    # Construct expected AST
    people_table = TableNode("people")
    name_col = ColumnNode("name")
    select_clause = SelectNode([name_col])
    from_clause = FromNode([people_table])
    one_eq_one = OperatorNode(LiteralNode(1), "=", LiteralNode(1))
    two_eq_two = OperatorNode(LiteralNode(2), "=", LiteralNode(2))
    where_clause = WhereNode([OperatorNode(one_eq_one, "AND", two_eq_two)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_27():
    """Query 27: Remove Where True."""
    query = get_query(27)
    sql = query["pattern"]

    # Construct expected AST
    emp_table = TableNode("Emp")
    age_col = ColumnNode("age")
    #TODO: parser does not support arithmetic expressions yet
    age_minus_two = OperatorNode(age_col, "-", LiteralNode(2))
    select_clause = SelectNode([ColumnNode("*")])
    from_clause = FromNode([emp_table])
    where_condition = OperatorNode(age_col, ">", age_minus_two)
    where_clause = WhereNode([where_condition])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    #assert parser.parse(sql) == expected_ast


def test_query_28():
    """Query 28: Rewrite Skips Failed Partial."""
    query = get_query(28)
    sql = query["pattern"]

    # Construct expected AST
    accounts_table = TableNode("accounts")
    acc_firstname = ColumnNode("firstname", _parent_alias="accounts")
    acc_id = ColumnNode("id", _parent_alias="accounts")
    # Subquery 1: addresses (LOWER(name) = LOWER('Street1'))
    sub1_select = SelectNode([ColumnNode("account_id", _parent_alias="addresses")])
    sub1_from = FromNode([TableNode("addresses")])
    sub1_where = WhereNode([
        OperatorNode(
            FunctionNode("LOWER", _args=[ColumnNode("name", _parent_alias="addresses")]),
            "=",
            FunctionNode("LOWER", _args=[LiteralNode("Street1")]),
        )
    ])
    sub1 = SubqueryNode(QueryNode(_select=sub1_select, _from=sub1_from, _where=sub1_where))
    # Subquery 2: alternate_ids
    sub2_select = SelectNode([ColumnNode("account_id", _parent_alias="alternate_ids")])
    sub2_from = FromNode([TableNode("alternate_ids")])
    sub2_where = WhereNode([
        OperatorNode(
            ColumnNode("alternate_id_glbl", _parent_alias="alternate_ids"),
            "=",
            LiteralNode("5"),
        )
    ])
    sub2 = SubqueryNode(QueryNode(_select=sub2_select, _from=sub2_from, _where=sub2_where))
    # Main WHERE: LOWER(firstname)=LOWER('Sam') AND id IN (sub1) AND id IN (sub2)
    lower_sam = OperatorNode(
        FunctionNode("LOWER", _args=[acc_firstname]),
        "=",
        FunctionNode("LOWER", _args=[LiteralNode("Sam")]),
    )
    id_in_sub1 = OperatorNode(acc_id, "IN", sub1)
    id_in_sub2 = OperatorNode(acc_id, "IN", sub2)
    select_clause = SelectNode([ColumnNode("*")])
    from_clause = FromNode([accounts_table])
    where_condition = OperatorNode(
        OperatorNode(lower_sam, "AND", id_in_sub1),
        "AND",
        id_in_sub2,
    )
    where_clause = WhereNode([where_condition])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


#TODO: Query 29: Full Matching: UNION not supported by parser 

def test_query_30():
    """Query 30: Over Partial Matching."""
    query = get_query(30)
    sql = query["pattern"]

    # Construct expected AST
    # Query pattern: SELECT * FROM table_name WHERE (title=1 AND grade=2) OR (title=2 AND debt=2 AND grade=3) OR (prog=1 AND title=1 AND debt=3)
    # Tables
    table_name = TableNode("table_name")
    # Columns
    title = ColumnNode("title", _parent_alias="table_name")
    grade = ColumnNode("grade", _parent_alias="table_name")
    debt = ColumnNode("debt", _parent_alias="table_name")
    prog = ColumnNode("prog", _parent_alias="table_name")
    # SELECT clause
    select_clause = SelectNode([ColumnNode("*")])
    # FROM clause
    from_clause = FromNode([table_name])
    # WHERE: (title=1 AND grade=2) OR (title=2 AND debt=2 AND grade=3) OR (prog=1 AND title=1 AND debt=3)
    cond1 = OperatorNode(
        OperatorNode(title, "=", LiteralNode(1)),
        "AND",
        OperatorNode(grade, "=", LiteralNode(2)),
    )
    cond2 = OperatorNode(
        OperatorNode(
            OperatorNode(title, "=", LiteralNode(2)),
            "AND",
            OperatorNode(debt, "=", LiteralNode(2)),
        ),
        "AND",
        OperatorNode(grade, "=", LiteralNode(3)),
    )
    cond3 = OperatorNode(
        OperatorNode(
            OperatorNode(prog, "=", LiteralNode(1)),
            "AND",
            OperatorNode(title, "=", LiteralNode(1)),
        ),
        "AND",
        OperatorNode(debt, "=", LiteralNode(3)),
    )
    where_condition = OperatorNode(
        OperatorNode(cond1, "OR", cond2),
        "OR",
        cond3,
    )
    where_clause = WhereNode([where_condition])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_31():
    """Query 31: Aggregation to Subquery."""
    query = get_query(31)
    sql = query["pattern"]

    # Construct expected AST
    # Query pattern: SELECT t1.CPF, DATE(t1.data) AS data, CASE WHEN SUM(CASE WHEN t1.login_ok=true THEN 1 ELSE 0 END)>=1 THEN true ELSE false END
    #             FROM db_risco.site_rn_login AS t1 GROUP BY t1.CPF, DATE(t1.data)
   
    # Tables
    t1_table = TableNode("db_risco.site_rn_login", _alias="t1")
    # Columns
    t1_cpf = ColumnNode("CPF", _parent_alias="t1")
    t1_data = ColumnNode("data", _parent_alias="t1")
    t1_login_ok = ColumnNode("login_ok", _parent_alias="t1")
    # SELECT: t1.CPF, DATE(t1.data) AS data, CASE WHEN ... END
    date_data = FunctionNode(
        "DATE",
        _args=[t1_data],
        _alias="data",
    )
    #TODO: make CASE as a specific node instead of FunctionNode?
    inner_case = FunctionNode(
        "CASE",
        _args=[
            FunctionNode("WHEN", _args=[OperatorNode(t1_login_ok, "=", LiteralNode(True))]),
            FunctionNode("THEN", _args=[LiteralNode(1)]),
            FunctionNode("ELSE", _args=[LiteralNode(0)]),
        ],
    )
    sum_inner = FunctionNode("SUM", _args=[inner_case])
    outer_case = FunctionNode(
        "CASE",
        _args=[
            FunctionNode("WHEN", _args=[OperatorNode(sum_inner, ">=", LiteralNode(1))]),
            FunctionNode("THEN", _args=[LiteralNode(True)]),
            FunctionNode("ELSE", _args=[LiteralNode(False)]),
        ],
    )
    select_clause = SelectNode([t1_cpf, date_data, outer_case])
    # FROM
    from_clause = FromNode([t1_table])
    # GROUP BY t1.CPF, DATE(t1.data)
    group_by_clause = GroupByNode([t1_cpf, date_data])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _group_by=group_by_clause,
    )
    #assert parser.parse(sql) == expected_ast


#TODO: Query 32: UNION not supported by parser

def test_query_33():
    """Query 33: Spreadsheet ID 3."""
    query = get_query(33)
    sql = query["pattern"]

    # Construct expected AST
    emp_table = TableNode("EMP")
    empno_col = ColumnNode("EMPNO")
    select_clause = SelectNode([empno_col])
    from_clause = FromNode([emp_table])
    gt_10 = OperatorNode(empno_col, ">", LiteralNode(10))
    lte_10 = OperatorNode(empno_col, "<=", LiteralNode(10))
    where_clause = WhereNode([OperatorNode(gt_10, "AND", lte_10)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_34():
    """Query 34: Spreadsheet ID 7."""
    query = get_query(34)
    sql = query["pattern"]

    # Construct expected AST
    table_a = TableNode("a")
    table_b = TableNode("b")
    join_on = OperatorNode(
        ColumnNode("id", _parent_alias="a"),
        "=",
        ColumnNode("cid", _parent_alias="b"),
    )
    join_node = JoinNode(table_a, table_b, JoinType.LEFT, join_on)
    b_cl1 = ColumnNode("cl1", _parent_alias="b")
    or_s1_s2 = OperatorNode(
        OperatorNode(b_cl1, "=", LiteralNode("s1")),
        "OR",
        OperatorNode(b_cl1, "=", LiteralNode("s2")),
    )
    or_s3 = OperatorNode(b_cl1, "=", LiteralNode("s3"))
    select_clause = SelectNode([ColumnNode("*")])
    from_clause = FromNode([join_node])
    where_clause = WhereNode([OperatorNode(or_s1_s2, "OR", or_s3)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_35():
    """Query 35: Spreadsheet ID 9."""
    query = get_query(35)
    sql = query["pattern"]

    # Construct expected AST
    # TODO: DISTINCT is not supported by parser yet
    my_table = TableNode("my_table")
    my_foo = ColumnNode("foo", _parent_alias="my_table")
    select_clause = SelectNode([my_foo])  # DISTINCT keyword not represented
    from_clause = FromNode([my_table])
    num_cond = OperatorNode(
        ColumnNode("num", _parent_alias="my_table"),
        "=",
        LiteralNode(1),
    )
    where_clause = WhereNode([num_cond])
    expected_ast = QueryNode(_select=select_clause, _from=from_clause, _where=where_clause)
    
    #assert parser.parse(sql) == expected_ast


def test_query_36():
    """Query 36: Spreadsheet ID 10."""
    query = get_query(36)
    sql = query["pattern"]

    # Construct expected AST
    table1 = TableNode("table1")
    table2 = TableNode("table2")
    # Subquery: SELECT tag_id FROM table2 WHERE postac_id = 376476
    sub_select = SelectNode([ColumnNode("tag_id", _parent_alias="table2")])
    sub_from = FromNode([table2])
    sub_where = WhereNode([
        OperatorNode(ColumnNode("postac_id", _parent_alias="table2"), "=", LiteralNode(376476))
    ])
    subquery_node = SubqueryNode(QueryNode(_select=sub_select, _from=sub_from, _where=sub_where))
    select_clause = SelectNode([ColumnNode("wpis_id", _parent_alias="table1")])
    from_clause = FromNode([table1])
    in_cond = OperatorNode(
        ColumnNode("etykieta_id", _parent_alias="table1"),
        "IN",
        subquery_node,
    )
    where_clause = WhereNode([in_cond])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_37():
    """Query 37: Spreadsheet ID 11."""
    query = get_query(37)
    sql = query["pattern"]

    # Construct expected AST
    hist1_table = TableNode("historicoestatusrequisicion", _alias="hist1")
    hist2_table = TableNode("historicoestatusrequisicion", _alias="hist2")
    # Subquery: SELECT requisicion_id FROM hist2 WHERE usuario_id=27 AND estatusrequisicion_id=1
    sub_select = SelectNode([ColumnNode("requisicion_id")])
    sub_from = FromNode([hist2_table])
    sub_where = WhereNode([
        OperatorNode(
            OperatorNode(ColumnNode("usuario_id"), "=", LiteralNode(27)),
            "AND",
            OperatorNode(ColumnNode("estatusrequisicion_id"), "=", LiteralNode(1)),
        )
    ])
    subquery_node = SubqueryNode(QueryNode(_select=sub_select, _from=sub_from, _where=sub_where))
    # Main query SELECT list
    select_cols = [
        ColumnNode("historicoestatusrequisicion_id"),
        ColumnNode("requisicion_id"),
        ColumnNode("estatusrequisicion_id"),
        ColumnNode("comentario"),
        ColumnNode("fecha_estatus"),
        ColumnNode("usuario_id"),
    ]
    select_clause = SelectNode(select_cols)
    from_clause = FromNode([hist1_table])
    in_cond = OperatorNode(ColumnNode("requisicion_id"), "IN", subquery_node)
    where_clause = WhereNode([in_cond])
    order_by_clause = OrderByNode([
        OrderByItemNode(ColumnNode("requisicion_id"), SortOrder.ASC),
        OrderByItemNode(ColumnNode("estatusrequisicion_id"), SortOrder.ASC),
    ])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _order_by=order_by_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_38():
    """Query 38: Spreadsheet ID 12."""
    query = get_query(38)
    sql = query["pattern"]

    # Construct expected AST
    # Tables
    po_table = TableNode("purchase_orders", _alias="po")
    items_table = TableNode("items")
    # Columns
    po_id = ColumnNode("id", _parent_alias="po")
    po_shop_id = ColumnNode("shop_id", _parent_alias="po")
    items_purchase_order_id = ColumnNode("purchase_order_id", _parent_alias="items")
    items_quantity = ColumnNode("quantity", _parent_alias="items")
    grouped_items_total_quantity = ColumnNode("total_quantity", _parent_alias="grouped_items")
    grouped_items_purchase_order_id = ColumnNode("purchase_order_id", _parent_alias="grouped_items")
    # Subquery: SELECT items.purchase_order_id, SUM(items.quantity) AS item_total FROM items GROUP BY items.purchase_order_id
    subquery_sum = FunctionNode(
        "SUM",
        _args=[items_quantity],
        _alias="item_total",
    )
    subquery_select = SelectNode([items_purchase_order_id, subquery_sum])
    subquery_from = FromNode([items_table])
    subquery_group_by = GroupByNode([items_purchase_order_id])
    subquery_node = SubqueryNode(
        QueryNode(
            _select=subquery_select,
            _from=subquery_from,
            _group_by=subquery_group_by,
        ),
        _alias="grouped_items",
    )
    # Main query SELECT: po.id, SUM(grouped_items.total_quantity) AS order_total_quantity
    main_sum = FunctionNode(
        "SUM",
        _args=[grouped_items_total_quantity],
        _alias="order_total_quantity",
    )
    select_clause = SelectNode([po_id, main_sum])
    # FROM: purchase_orders po LEFT JOIN (subquery) grouped_items ON po.id = grouped_items.purchase_order_id
    join_on = OperatorNode(
        po_id,
        "=",
        grouped_items_purchase_order_id,
    )
    join_node = JoinNode(po_table, subquery_node, JoinType.LEFT, join_on)
    from_clause = FromNode([join_node])
    # WHERE: po.shop_id = 195
    where_condition = OperatorNode(po_shop_id, "=", LiteralNode(195))
    where_clause = WhereNode([where_condition])
    # GROUP BY po.id
    group_by_clause = GroupByNode([po_id])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _group_by=group_by_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_39():
    """Query 39: Spreadsheet ID 15."""
    query = get_query(39)
    sql = query["pattern"]

    # Construct expected AST
    # Query pattern: SELECT * FROM users u WHERE u.id IN (SELECT s1.user_id FROM sessions s1
    #   WHERE s1.user_id <> 1234 AND (s1.ip IN (sub_s2) OR s1.cookie_identifier IN (sub_s3)) GROUP BY s1.user_id)
    # sub_s2: SELECT s2.ip FROM sessions s2 WHERE s2.user_id = 1234 GROUP BY s2.ip
    # sub_s3: SELECT s3.cookie_identifier FROM sessions s3 WHERE s3.user_id = 1234 GROUP BY s3.cookie_identifier
   
    # Tables
    users_table = TableNode("users", _alias="u")
    sessions_s2 = TableNode("sessions", _alias="s2")
    sessions_s3 = TableNode("sessions", _alias="s3")
    sessions_s1 = TableNode("sessions", _alias="s1")
    # Columns (s2)
    s2_ip = ColumnNode("ip", _parent_alias="s2")
    s2_user_id = ColumnNode("user_id", _parent_alias="s2")
    # Subquery s2: SELECT s2.ip FROM sessions s2 WHERE s2.user_id = 1234 GROUP BY s2.ip
    sub_s2_select = SelectNode([s2_ip])
    sub_s2_from = FromNode([sessions_s2])
    sub_s2_where = WhereNode([
        OperatorNode(s2_user_id, "=", LiteralNode(1234)),
    ])
    sub_s2_group_by = GroupByNode([s2_ip])
    sub_s2_node = SubqueryNode(
        QueryNode(
            _select=sub_s2_select,
            _from=sub_s2_from,
            _where=sub_s2_where,
            _group_by=sub_s2_group_by,
        )
    )
    # Columns (s3)
    s3_cookie_identifier = ColumnNode("cookie_identifier", _parent_alias="s3")
    s3_user_id = ColumnNode("user_id", _parent_alias="s3")
    # Subquery s3: SELECT s3.cookie_identifier FROM sessions s3 WHERE s3.user_id = 1234 GROUP BY s3.cookie_identifier
    sub_s3_select = SelectNode([s3_cookie_identifier])
    sub_s3_from = FromNode([sessions_s3])
    sub_s3_where = WhereNode([
        OperatorNode(s3_user_id, "=", LiteralNode(1234)),
    ])
    sub_s3_group_by = GroupByNode([s3_cookie_identifier])
    sub_s3_node = SubqueryNode(
        QueryNode(
            _select=sub_s3_select,
            _from=sub_s3_from,
            _where=sub_s3_where,
            _group_by=sub_s3_group_by,
        )
    )
    # Columns (s1)
    s1_user_id = ColumnNode("user_id", _parent_alias="s1")
    s1_ip = ColumnNode("ip", _parent_alias="s1")
    s1_cookie_identifier = ColumnNode("cookie_identifier", _parent_alias="s1")
    # Subquery s1: SELECT s1.user_id FROM sessions s1 WHERE s1.user_id <> 1234 AND (s1.ip IN sub_s2 OR s1.cookie_identifier IN sub_s3) GROUP BY s1.user_id
    s1_user_ne = OperatorNode(s1_user_id, "!=", LiteralNode(1234))
    s1_ip_in_s2 = OperatorNode(s1_ip, "IN", sub_s2_node)
    s1_cookie_in_s3 = OperatorNode(s1_cookie_identifier, "IN", sub_s3_node)
    s1_or = OperatorNode(s1_ip_in_s2, "OR", s1_cookie_in_s3)
    s1_and = OperatorNode(s1_user_ne, "AND", s1_or)
    sub_s1_select = SelectNode([s1_user_id])
    sub_s1_from = FromNode([sessions_s1])
    sub_s1_where = WhereNode([s1_and])
    sub_s1_group_by = GroupByNode([s1_user_id])
    sub_s1_node = SubqueryNode(
        QueryNode(
            _select=sub_s1_select,
            _from=sub_s1_from,
            _where=sub_s1_where,
            _group_by=sub_s1_group_by,
        )
    )
    # Main query: SELECT * FROM users u WHERE u.id IN sub_s1
    select_clause = SelectNode([ColumnNode("*")])
    from_clause = FromNode([users_table])
    u_id = ColumnNode("id", _parent_alias="u")
    where_condition = OperatorNode(u_id, "IN", sub_s1_node)
    where_clause = WhereNode([where_condition])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    assert parser.parse(sql) == expected_ast


def test_query_40():
    """Query 40."""
    query = get_query(40)
    sql = query["pattern"]

    # Construct expected AST
    # Tables
    t_table = TableNode("userPlayerIdMap", _alias="t")
    p_table = TableNode("userPreferences", _alias="p")
    s_table = TableNode("segment", _alias="s")
    # Columns
    t_gzpId = ColumnNode("gzpId", _parent_alias="t")
    t_pubCode = ColumnNode("pubCode", _parent_alias="t")
    t_playerId = ColumnNode("playerId", _parent_alias="t")
    t_provider = ColumnNode("provider", _parent_alias="t")
    p_gzpId = ColumnNode("gzpId", _parent_alias="p")
    p_preferenceValue = ColumnNode("preferenceValue", _parent_alias="p")
    s_gzpId = ColumnNode("gzpId", _parent_alias="s")
    s_segmentId = ColumnNode("segmentId", _parent_alias="s")
    # SELECT: DISTINCT ON (t.playerId) t.gzpId, t.pubCode, t.playerId, COALESCE(p.preferenceValue,'en'), s.segmentId
    # TODO: DISTINCT ON is not supported by parser yet
    coalesce_expr = FunctionNode(
        "COALESCE",
        _args=[p_preferenceValue, LiteralNode("en")],
    )
    select_clause = SelectNode([t_gzpId, t_pubCode, t_playerId, coalesce_expr, s_segmentId])
    # FROM: t LEFT JOIN p ON t.gzpId = p.gzpId LEFT JOIN s ON t.gzpId = s.gzpId
    join_on_1 = OperatorNode(t_gzpId, "=", p_gzpId)
    join_1 = JoinNode(t_table, p_table, JoinType.LEFT, join_on_1)
    join_on_2 = OperatorNode(t_gzpId, "=", s_gzpId)
    join_2 = JoinNode(join_1, s_table, JoinType.LEFT, join_on_2)
    from_clause = FromNode([join_2])
    # WHERE: t.pubCode IN (...) AND t.provider IN (...) AND s.segmentId IN (...) AND p.preferenceValue IN (...)
    pubcode_in = OperatorNode(
        t_pubCode,
        "IN",
        LiteralNode(["hyrmas", "ayqioa", "rj49as99"]),
    )
    provider_in = OperatorNode(
        t_provider,
        "IN",
        LiteralNode(["FCM", "ONE_SIGNAL"]),
    )
    segmentid_in = OperatorNode(
        s_segmentId,
        "IN",
        [
            LiteralNode(0),
            LiteralNode(1),
            LiteralNode(2),
            LiteralNode(3),
            LiteralNode(4),
            LiteralNode(5),
            LiteralNode(6),
        ],
    )
    prefvalue_in = OperatorNode(
        p_preferenceValue,
        "IN",
        LiteralNode(["en", "hi"]),
    )
    where_condition = OperatorNode(
        OperatorNode(
            OperatorNode(pubcode_in, "AND", provider_in),
            "AND",
            segmentid_in,
        ),
        "AND",
        prefvalue_in,
    )
    where_clause = WhereNode([where_condition])
    # ORDER BY t.playerId DESC
    order_by_clause = OrderByNode(
        [OrderByItemNode(t_playerId, SortOrder.DESC)]
    )
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _order_by=order_by_clause,
    )
    #assert parser.parse(sql) == expected_ast


def test_query_41():
    """Query 41: Spreadsheet ID 20."""
    query = get_query(41)
    sql = query["pattern"]

    # Construct expected AST
    # Query pattern: SELECT * FROM (SELECT * FROM (SELECT NULL FROM EMP) WHERE N IS NULL) WHERE N IS NULL
    # TODO: NULL should be a keyword node (like TEXT, INTEGER), not supported yet.
    # Parser currently converts IS NULL to FunctionNode("MISSING", ...); when fixed, use OperatorNode(col, "IS", null_keyword).
    # Tables
    emp_table = TableNode("EMP")
    # Inner subquery: SELECT NULL FROM EMP
    inner_select = SelectNode([LiteralNode(None)])
    inner_from = FromNode([emp_table])
    inner_subquery = SubqueryNode(
        QueryNode(_select=inner_select, _from=inner_from)
    )
    # Middle subquery: SELECT * FROM (inner) WHERE N IS NULL
    n_col = ColumnNode("N")
    null_rhs = LiteralNode(None)  # should be keyword NULL, not literal
    is_null_cond = OperatorNode(n_col, "IS", null_rhs)
    middle_select = SelectNode([ColumnNode("*")])
    middle_from = FromNode([inner_subquery])
    middle_where = WhereNode([is_null_cond])
    middle_subquery = SubqueryNode(
        QueryNode(_select=middle_select, _from=middle_from, _where=middle_where)
    )
    # Main query: SELECT * FROM (middle) WHERE N IS NULL
    select_clause = SelectNode([ColumnNode("*")])
    from_clause = FromNode([middle_subquery])
    outer_is_null = OperatorNode(n_col, "IS", null_rhs)
    where_clause = WhereNode([outer_is_null])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
    )
    # assert parser.parse(sql) == expected_ast


def test_query_42():
    """Query 42: PostgreSQL Test."""
    query = get_query(42)
    sql = query["pattern"]

    # TODO: Special query, please double check the AST
    # Construct expected AST
    # Query pattern: SELECT "tweets"."latitude" AS "latitude", "tweets"."longitude" AS "longitude"
    #   FROM "public"."tweets" "tweets"
    #   WHERE (("tweets"."latitude" >= -90) AND ("tweets"."latitude" <= 80) 
    #     AND ((("tweets"."longitude" >= -173.80000000000001) AND ("tweets"."longitude" <= 180)) OR ("tweets"."longitude" IS NULL))
    #     AND (CAST(DATE_TRUNC('day', CAST(created_at AS DATE)) + (-EXTRACT(DOW FROM created_at) * INTERVAL '1 DAY') AS DATE) = TIMESTAMP '...')
    #     AND (STRPOS(CAST(LOWER(CAST(CAST("tweets"."text" AS TEXT) AS TEXT)) AS TEXT), CAST('microsoft' AS TEXT)) > 0)
    #   GROUP BY 1, 2
    # Tables
    tweets_table = TableNode("tweets", _alias="tweets")
    # Columns
    t_latitude = ColumnNode("latitude", _alias="latitude", _parent_alias="tweets")
    t_longitude = ColumnNode("longitude", _alias="longitude", _parent_alias="tweets")
    created_at = ColumnNode("created_at", _parent_alias="tweets")
    text_col = ColumnNode("text", _parent_alias="tweets")
    # SELECT clause
    select_clause = SelectNode([t_latitude, t_longitude])
    # FROM clause
    from_clause = FromNode([tweets_table])
    # WHERE: five parts ANDed
    # 1. latitude >= -90 AND latitude <= 80
    lat_ge = OperatorNode(t_latitude, ">=", LiteralNode(-90))
    lat_le = OperatorNode(t_latitude, "<=", LiteralNode(80))
    lat_range = OperatorNode(lat_ge, "AND", lat_le)
    # 2. (longitude >= -173.8 AND longitude <= 180) OR longitude IS NULL
    lon_ge = OperatorNode(t_longitude, ">=", LiteralNode(-173.80000000000001))
    lon_le = OperatorNode(t_longitude, "<=", LiteralNode(180))
    lon_range = OperatorNode(lon_ge, "AND", lon_le)
    lon_is_null = OperatorNode(t_longitude, "IS", LiteralNode(None))  # NULL as keyword not supported yet
    lon_part = OperatorNode(lon_range, "OR", lon_is_null)
    # 3. CAST(DATE_TRUNC('day', CAST(created_at AS DATE)) + (-EXTRACT(DOW FROM created_at) * INTERVAL '1 DAY') AS DATE) = TIMESTAMP '...'
    cast_created = FunctionNode(
        "CAST",
        # TODO: keywords like DATE should not be function node
        _args=[created_at, FunctionNode("DATE", _args=[LiteralNode("{}")])],
    )
    date_trunc_day = FunctionNode("DATE_TRUNC", _args=[LiteralNode("day"), cast_created])
    extract_dow = FunctionNode("EXTRACT", _args=[LiteralNode("DOW"), created_at])
    # TODO: double check on how we should handle INTERVAL, it's not supported by parser yet
    interval_1day = FunctionNode("INTERVAL", _args=[LiteralNode("1 DAY")])
    # -EXTRACT(DOW FROM created_at) * INTERVAL '1 DAY'  =>  0 - (extract_dow * interval_1day)
    neg_expr = OperatorNode(
        LiteralNode(0),
        "-",
        OperatorNode(extract_dow, "*", interval_1day),
    )
    date_plus = OperatorNode(date_trunc_day, "+", neg_expr)
    cast_date = FunctionNode(
        "CAST",
        # TODO: same as above
        _args=[date_plus, FunctionNode("DATE", _args=[LiteralNode("{}")])],
    )
    ts_lit = FunctionNode("TIMESTAMP", _args=[LiteralNode("2018-04-22 00:00:00.000")])
    date_eq = OperatorNode(cast_date, "=", ts_lit)
    # 4. STRPOS(CAST(LOWER(CAST(CAST(text AS TEXT) AS TEXT)) AS TEXT), CAST('microsoft' AS TEXT)) > 0
    cast_text_inner = FunctionNode(
        "CAST",
        _args=[text_col, FunctionNode("TEXT", _args=[LiteralNode("{}")])],
    )
    cast_text_outer = FunctionNode(
        "CAST",
        _args=[cast_text_inner, FunctionNode("TEXT", _args=[LiteralNode("{}")])],
    )
    lower_text = FunctionNode("LOWER", _args=[cast_text_outer])
    cast_lower = FunctionNode(
        "CAST",
        _args=[lower_text, FunctionNode("TEXT", _args=[LiteralNode("{}")])],
    )
    cast_microsoft = FunctionNode(
        "CAST",
        _args=[LiteralNode("microsoft"), FunctionNode("TEXT", _args=[LiteralNode("{}")])],
    )
    strpos_cond = OperatorNode(
        FunctionNode("STRPOS", _args=[cast_lower, cast_microsoft]),
        ">",
        LiteralNode(0),
    )
    # Combine all WHERE conditions with AND
    where_12 = OperatorNode(lat_range, "AND", lon_part)
    where_123 = OperatorNode(where_12, "AND", date_eq)
    where_condition = OperatorNode(where_123, "AND", strpos_cond)
    where_clause = WhereNode([where_condition])
    # GROUP BY 1, 2
    group_by_clause = GroupByNode([LiteralNode(1), LiteralNode(2)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _group_by=group_by_clause,
    )
    #assert parser.parse(sql) == expected_ast


def test_query_43():
    """Query 43: MySQL Test."""
    query = get_query(43)
    sql = query["pattern"]

    # Construct expected AST
    # Query pattern: SELECT tweets.latitude AS latitude, tweets.longitude AS longitude
    #   FROM tweets WHERE (ADDDATE(DATE_FORMAT(created_at,...), INTERVAL 0 SECOND) = TIMESTAMP(...)) AND (LOCATE('iphone', LOWER(text)) > 0) GROUP BY 1, 2
    # Tables
    tweets_table = TableNode("tweets")
    # Columns
    lat_col = ColumnNode("latitude", _alias="latitude", _parent_alias="tweets")
    lon_col = ColumnNode("longitude", _alias="longitude", _parent_alias="tweets")
    created_at = ColumnNode("created_at", _parent_alias="tweets")
    text_col = ColumnNode("text", _parent_alias="tweets")
    # SELECT clause
    select_clause = SelectNode([lat_col, lon_col])
    # FROM clause
    from_clause = FromNode([tweets_table])
    # WHERE: (ADDDATE(DATE_FORMAT(created_at, '%Y-%m-01 00:00:00'), INTERVAL 0 SECOND) = TIMESTAMP(...)) AND (LOCATE('iphone', LOWER(text)) > 0)
    date_format_expr = FunctionNode(
        "DATE_FORMAT",
        _args=[created_at, LiteralNode("%Y-%m-01 00:00:00")],
    )
    interval_0_second = FunctionNode("INTERVAL", _args=[LiteralNode(0), ColumnNode("second")])
    adddate_expr = FunctionNode(
        "ADDDATE",
        _args=[date_format_expr, interval_0_second],
    )
    timestamp_lit = FunctionNode("TIMESTAMP", _args=[LiteralNode("2017-03-01 00:00:00")])
    date_eq = OperatorNode(adddate_expr, "=", timestamp_lit)
    locate_expr = FunctionNode(
        "LOCATE",
        _args=[LiteralNode("iphone"), FunctionNode("LOWER", _args=[text_col])],
    )
    locate_cond = OperatorNode(locate_expr, ">", LiteralNode(0))
    where_condition = OperatorNode(date_eq, "AND", locate_cond)
    where_clause = WhereNode([where_condition])
    # GROUP BY 1, 2 -> actually refer to the 1st and 2nd columns in the SELECT clause
    # TODO: group by should be a list of columns, not literals, but how to do the translation?
    group_by_clause = GroupByNode([LiteralNode(1), LiteralNode(2)])
    expected_ast = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _group_by=group_by_clause,
    )
    #assert parser.parse(sql) == expected_ast

