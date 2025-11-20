import mo_sql_parsing as mosql
from core.query_parser import QueryParser
from core.ast.node import (
    OrderByItemNode, QueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode, 
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, LimitNode, OffsetNode, SubqueryNode, VarNode, VarSetNode
)
from core.ast.enums import NodeType, JoinType, SortOrder
from data.queries import get_query
from re import sub

parser = QueryParser()

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
    count_alias = ColumnNode("emp_count")  # This would be the alias for COUNT(*)
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
        OrderByItemNode(ColumnNode("dept_name"), _sort=SortOrder.DESC),
        OrderByItemNode(ColumnNode("emp_count"), _sort=SortOrder.DESC)  
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

    sql = parser.format(ast)
    sql = sql.strip()
    
    assert normalize_sql(sql) == normalize_sql(expected_sql)    

def test_parse_1():
    query = get_query(1)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause

    # select_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.SELECT:
    #         select_clause = child
    #         break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 2
    
    # Check FROM clause
    # from_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.FROM:
    #         from_clause = child
    #         break
    
    # assert from_clause is not None
    # table_node = next(iter(from_clause.children))
    # assert isinstance(table_node, TableNode)
    # assert table_node.name == "tweets"
    
    # Check WHERE clause
    # where_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.WHERE:
    #         where_clause = child
    #         break
    
    # assert where_clause is not None
    # assert len(where_clause.children) == 1
    
    # Check GROUP BY clause
    # group_by_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.GROUP_BY:
    #         group_by_clause = child
    #         break
    
    # assert group_by_clause is not None
    # assert len(group_by_clause.children) == 1


def test_parse_2():
    query = get_query(6)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check FROM clause has multiple tables
    # from_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.FROM:
    #         from_clause = child
    #         break
    
    # assert from_clause is not None
    # assert len(from_clause.children) == 2
    
    # Check WHERE clause has multiple conditions
    # where_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.WHERE:
    #         where_clause = child
    #         break
    
    # assert where_clause is not None
    # condition = next(iter(where_clause.children))
    # assert isinstance(condition, OperatorNode)


def test_parse_3():
    query = get_query(9)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check WHERE clause has IN with subquery
    # where_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.WHERE:
    #         where_clause = child
    #         break
    
    # assert where_clause is not None
    # condition = next(iter(where_clause.children))
    # assert isinstance(condition, OperatorNode)
    # assert condition.name == "AND"


def test_parse_4():
    query = get_query(12)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check FROM clause has multiple JOINs
    # from_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.FROM:
    #         from_clause = child
    #         break
    
    # assert from_clause is not None
    # Check for JOIN nodes in the FROM clause
    # join_count = 0
    # for child in from_clause.children:
    #     if hasattr(child, 'type') and 'JOIN' in str(child.type):
    #         join_count += 1
    # assert join_count >= 2


def test_parse_5():
    query = get_query(16)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause has aggregation with subquery
    # select_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.SELECT:
    #         select_clause = child
    #         break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 3
    
    # Check for MAX function
    # for child in select_clause.children:
    #     if isinstance(child, FunctionNode) and child.name == "MAX":
    #         assert True
    #         break


def test_parse_6():
    query = get_query(18)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause has DISTINCT
    # select_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.SELECT:
    #         select_clause = child
    #         break
    
    # assert select_clause is not None
    # Check for DISTINCT keyword
    # assert hasattr(select_clause, 'distinct') and select_clause.distinct
    
    # Check FROM clause has multiple tables
    # from_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.FROM:
    #         from_clause = child
    #         break
    
    # assert from_clause is not None
    # assert len(from_clause.children) == 2


def test_parse_7():
    query = get_query(25)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check WHERE clause has boolean logic
    # where_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.WHERE:
    #         where_clause = child
    #         break
    
    # assert where_clause is not None
    # condition = next(iter(where_clause.children))
    # assert isinstance(condition, OperatorNode)
    # assert condition.name == "AND"


def test_parse_8():
    query = get_query(29)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check for UNION operation (this query has UNION)
    # Check if the query contains UNION
    # assert 'UNION' in sql.upper()
    
    # Check for subqueries in WHERE clause
    # where_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.WHERE:
    #         where_clause = child
    #         break
    
    # assert where_clause is not None


def test_parse_9():
    query = get_query(31)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause has complex aggregation
    # select_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.SELECT:
    #         select_clause = child
    #         break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 3
    
    # Check for CASE statement
    # for child in select_clause.children:
    #     if isinstance(child, FunctionNode) and child.name == "CASE":
    #         assert True
    #         break
    
    # Check GROUP BY clause
    # group_by_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.GROUP_BY:
    #         group_by_clause = child
    #         break
    
    # assert group_by_clause is not None


def test_parse_10():
    query = get_query(42)
    sql = query['pattern']
    
    qb_ast = parser.parse(sql)
    # assert isinstance(qb_ast, QueryNode)
    
    # Check SELECT clause
    # select_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.SELECT:
    #         select_clause = child
    #         break
    
    # assert select_clause is not None
    # assert len(select_clause.children) == 2
    
    # Check WHERE clause has complex conditions
    # where_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.WHERE:
    #         where_clause = child
    #         break
    
    # assert where_clause is not None
    
    # Check GROUP BY clause
    # group_by_clause = None
    # for child in qb_ast.children:
    #     if child.type == NodeType.GROUP_BY:
    #         group_by_clause = child
    #         break
    
    # assert group_by_clause is not None
    # assert len(group_by_clause.children) == 2