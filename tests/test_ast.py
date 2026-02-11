from core.ast.node import (
    TableNode, ColumnNode, LiteralNode, VarNode, VarSetNode,
    OperatorNode, FunctionNode, SelectNode, FromNode, WhereNode, GroupByNode,
    HavingNode, OrderByNode, LimitNode, OffsetNode, QueryNode
)


def test_operand_nodes():
    """Test all operand node types"""
    print("="*50)
    print("Testing Operand Nodes")
    print("="*50)
    
    # Test TableNode
    employees = TableNode("employees", "e")
    departments = TableNode("departments")
    
    print(f"Table nodes:")
    print(f"  {employees.name} (alias: {employees.alias}) -> Type: {employees.type}")
    print(f"  {departments.name} (alias: {departments.alias}) -> Type: {departments.type}")
    
    # Test ColumnNode
    emp_id = ColumnNode("id", _parent_alias="e")
    emp_name = ColumnNode("name", "employee_name", "e")
    dept_name = ColumnNode("name", _parent_alias="d")
    
    print(f"\nColumn nodes:")
    print(f"  {emp_id.name} (parent: {emp_id.parent_alias}) -> Type: {emp_id.type}")
    print(f"  {emp_name.name} (alias: {emp_name.alias}, parent: {emp_name.parent_alias}) -> Type: {emp_name.type}")
    print(f"  {dept_name.name} (parent: {dept_name.parent_alias}) -> Type: {dept_name.type}")
    
    # Test LiteralNode
    num_literal = LiteralNode(42)
    str_literal = LiteralNode("John Doe")
    bool_literal = LiteralNode(True)
    null_literal = LiteralNode(None)
    
    print(f"\nLiteral nodes:")
    print(f"  {num_literal.value} ({type(num_literal.value).__name__}) -> Type: {num_literal.type}")
    print(f"  '{str_literal.value}' ({type(str_literal.value).__name__}) -> Type: {str_literal.type}")
    print(f"  {bool_literal.value} ({type(bool_literal.value).__name__}) -> Type: {bool_literal.type}")
    print(f"  {null_literal.value} -> Type: {null_literal.type}")
    
    # Test VarSQL nodes
    var_table = VarNode("V001")
    var_column = VarNode("V002")
    var_set = VarSetNode("VS001")
    
    print(f"\nVarSQL nodes:")
    print(f"  Variable {var_table.name} -> Type: {var_table.type}")
    print(f"  Variable {var_column.name} -> Type: {var_column.type}")
    print(f"  VarSet {var_set.name} -> Type: {var_set.type}")


def test_operator_nodes():
    """Test operator and function nodes"""
    print("="*50)
    print("Testing Operator and Function Nodes")
    print("="*50)
    
    # Create some operands for testing
    age_col = ColumnNode("age")
    salary_col = ColumnNode("salary")
    age_limit = LiteralNode(30)
    salary_limit = LiteralNode(50000)
    bonus_col = ColumnNode("bonus")
    
    # Test comparison operators
    age_gt = OperatorNode(age_col, ">", age_limit)
    salary_gte = OperatorNode(salary_col, ">=", salary_limit)
    name_like = OperatorNode(ColumnNode("name"), "LIKE", LiteralNode("%John%"))
    
    print(f"Comparison operators:")
    print(f"  {age_gt.name} operator with {len(age_gt.children)} operands -> Type: {age_gt.type}")
    print(f"  {salary_gte.name} operator with {len(salary_gte.children)} operands -> Type: {salary_gte.type}")
    print(f"  {name_like.name} operator with {len(name_like.children)} operands -> Type: {name_like.type}")
    
    # Test logical operators
    and_op = OperatorNode(age_gt, "AND", salary_gte)
    or_op = OperatorNode(and_op, "OR", name_like)
    not_op = OperatorNode(age_gt, "NOT")  # Unary operator
    
    print(f"\nLogical operators:")
    print(f"  {and_op.name} operator with {len(and_op.children)} operands -> Type: {and_op.type}")
    print(f"  {or_op.name} operator with {len(or_op.children)} operands -> Type: {or_op.type}")
    print(f"  {not_op.name} operator with {len(not_op.children)} operands -> Type: {not_op.type}")
    
    # Test arithmetic operators
    add_op = OperatorNode(salary_col, "+", bonus_col)
    mult_op = OperatorNode(add_op, "*", LiteralNode(1.1))
    neg_op = OperatorNode(salary_col, "-")  # Unary minus
    
    print(f"\nArithmetic operators:")
    print(f"  {add_op.name} operator with {len(add_op.children)} operands -> Type: {add_op.type}")
    print(f"  {mult_op.name} operator with {len(mult_op.children)} operands -> Type: {mult_op.type}")
    print(f"  {neg_op.name} operator with {len(neg_op.children)} operands -> Type: {neg_op.type}")
    
    # Test function nodes
    count_func = FunctionNode("COUNT", {ColumnNode("*")})
    max_func = FunctionNode("MAX", {salary_col})
    concat_func = FunctionNode("CONCAT", {ColumnNode("first_name"), LiteralNode(" "), ColumnNode("last_name")})
    now_func = FunctionNode("NOW")  # No arguments
    
    print(f"\nFunction nodes:")
    print(f"  {count_func.name}() with {len(count_func.children)} args -> Type: {count_func.type}")
    print(f"  {max_func.name}() with {len(max_func.children)} args -> Type: {max_func.type}")
    print(f"  {concat_func.name}() with {len(concat_func.children)} args -> Type: {concat_func.type}")
    print(f"  {now_func.name}() with {len(now_func.children)} args -> Type: {now_func.type}")


def test_query_structure_nodes():
    """Test query structure nodes"""
    print("="*50)
    print("Testing Query Structure Nodes")
    print("="*50)
    
    # Create operands
    emp_table = TableNode("employees", "e")
    dept_table = TableNode("departments", "d")
    
    emp_id = ColumnNode("id", _parent_alias="e")
    emp_name = ColumnNode("name", _parent_alias="e")
    emp_dept_id = ColumnNode("department_id", _parent_alias="e")
    dept_id = ColumnNode("id", _parent_alias="d")
    dept_name = ColumnNode("name", _parent_alias="d")
    
    # Test SELECT clause
    select_clause = SelectNode({emp_id, emp_name, dept_name})
    print(f"SELECT clause with {len(select_clause.children)} items -> Type: {select_clause.type}")
    
    # Test FROM clause with JOIN
    join_condition = OperatorNode(emp_dept_id, "=", dept_id)
    from_clause = FromNode({emp_table, dept_table})
    print(f"FROM clause with {len(from_clause.children)} sources -> Type: {from_clause.type}")
    
    # Test WHERE clause
    age_condition = OperatorNode(ColumnNode("age", _parent_alias="e"), ">", LiteralNode(25))
    salary_condition = OperatorNode(ColumnNode("salary", _parent_alias="e"), ">=", LiteralNode(40000))
    combined_condition = OperatorNode(age_condition, "AND", salary_condition)
    where_clause = WhereNode({combined_condition})
    print(f"WHERE clause with {len(where_clause.children)} predicates -> Type: {where_clause.type}")
    
    # Test GROUP BY clause
    group_by_clause = GroupByNode({dept_id, dept_name})
    print(f"GROUP BY clause with {len(group_by_clause.children)} items -> Type: {group_by_clause.type}")
    
    # Test HAVING clause
    count_condition = OperatorNode(FunctionNode("COUNT", {emp_id}), ">", LiteralNode(5))
    having_clause = HavingNode({count_condition})
    print(f"HAVING clause with {len(having_clause.children)} predicates -> Type: {having_clause.type}")
    
    # Test ORDER BY clause
    order_by_clause = OrderByNode({dept_name, emp_name})
    print(f"ORDER BY clause with {len(order_by_clause.children)} items -> Type: {order_by_clause.type}")
    
    # Test LIMIT and OFFSET
    limit_clause = LimitNode(10)
    offset_clause = OffsetNode(20)
    print(f"LIMIT clause: {limit_clause.limit} -> Type: {limit_clause.type}")
    print(f"OFFSET clause: {offset_clause.offset} -> Type: {offset_clause.type}")


def test_complete_query():
    """Test building a complete query"""
    print("="*50)
    print("Testing Complete Query Construction")
    print("="*50)
    
    # Build a complex query: 
    # SELECT e.name, d.name as dept_name, COUNT(*) as emp_count
    # FROM employees e JOIN departments d ON e.department_id = d.id
    # WHERE e.salary > 40000 AND e.age < 60
    # GROUP BY d.id, d.name
    # HAVING COUNT(*) > 2
    # ORDER BY dept_name, emp_count DESC
    # LIMIT 10 OFFSET 5
    
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
    count_star = FunctionNode("COUNT", {ColumnNode("*")})
    count_alias = ColumnNode("emp_count")  # This would be the alias for COUNT(*)
    
    # SELECT clause
    select_clause = SelectNode({emp_name, dept_name, count_star})
    
    # FROM clause (with implicit JOIN logic)
    from_clause = FromNode({emp_table, dept_table})
    
    # WHERE clause
    salary_condition = OperatorNode(emp_salary, ">", LiteralNode(40000))
    age_condition = OperatorNode(emp_age, "<", LiteralNode(60))
    where_condition = OperatorNode(salary_condition, "AND", age_condition)
    where_clause = WhereNode({where_condition})
    
    # GROUP BY clause
    group_by_clause = GroupByNode({dept_id, dept_name})
    
    # HAVING clause
    having_condition = OperatorNode(count_star, ">", LiteralNode(2))
    having_clause = HavingNode({having_condition})
    
    # ORDER BY clause
    order_by_clause = OrderByNode({dept_name, count_alias})
    
    # LIMIT and OFFSET
    limit_clause = LimitNode(10)
    offset_clause = OffsetNode(5)
    
    # Complete query
    query = QueryNode(
        _select=select_clause,
        _from=from_clause,
        _where=where_clause,
        _group_by=group_by_clause,
        _having=having_clause,
        _order_by=order_by_clause,
        _limit=limit_clause,
        _offset=offset_clause
    )
    
    print(f"Complete query built with {len(query.children)} clauses:")
    print(f"  Query type: {query.type}")
    print(f"  Total clauses: {len(query.children)}")
    
    # Analyze query structure
    clause_types = [child.type for child in query.children]
    print(f"  Clause types: {[ct.value for ct in clause_types]}")


def test_varsql_pattern_matching():
    """Test VarSQL pattern matching capabilities"""
    print("="*50)
    print("Testing VarSQL Pattern Matching")
    print("="*50)
    
    # Pattern: SELECT V1 FROM V2 WHERE V3 op V4
    var_select = VarNode("V1")  # Any select item
    var_table = VarNode("V2")   # Any table
    var_left = VarNode("V3")    # Left operand of condition
    var_op = VarNode("OP")      # Any operator
    var_right = VarNode("V4")   # Right operand of condition
    
    # Build pattern query
    pattern_select = SelectNode({var_select})
    pattern_from = FromNode({var_table})
    pattern_condition = OperatorNode(var_left, "=", var_right)  # Could use var_op.name
    pattern_where = WhereNode({pattern_condition})
    
    pattern_query = QueryNode(
        _select=pattern_select,
        _from=pattern_from,
        _where=pattern_where
    )
    
    print(f"Pattern query created:")
    print(f"  SELECT variables: {len(pattern_select.children)}")
    print(f"  FROM variables: {len(pattern_from.children)}")
    print(f"  WHERE conditions: {len(pattern_where.children)}")
    print(f"  Total pattern variables: 4 (V1, V2, V3, V4)")
    
    # Test VarSet for multiple columns
    var_columns = VarSetNode("COLS")
    multi_select = SelectNode({var_columns})
    print(f"\nVarSet pattern for multiple columns:")
    print(f"  VarSet {var_columns.name} can match multiple SELECT items")

def test_node_relationships():
    """Test node relationships and tree structure"""
    print("="*50)
    print("Testing Node Relationships")
    print("="*50)
    
    # Build a simple expression tree: (a + b) * c
    a = ColumnNode("a")
    b = ColumnNode("b")
    c = ColumnNode("c")
    
    add_op = OperatorNode(a, "+", b)
    mult_op = OperatorNode(add_op, "*", c)
    
    print(f"Expression tree: (a + b) * c")
    print(f"  Root operator: {mult_op.name} ({mult_op.type})")
    print(f"  Root has {len(mult_op.children)} children")
    
    # The children are in a set, so we need to handle that
    children = list(mult_op.children)
    for i, child in enumerate(children):
        print(f"    Child {i+1}: {child.type}")
        if hasattr(child, 'name'):
            print(f"      Name: {child.name}")
        if hasattr(child, 'children') and child.children:
            print(f"      Has {len(child.children)} sub-children")


if __name__ == '__main__':
    """Run all test functions"""
    test_functions = [
        test_operand_nodes,
        test_operator_nodes,
        test_query_structure_nodes,
        test_complete_query,
        test_varsql_pattern_matching,
        test_node_relationships
    ]
    
    for test_func in test_functions:
        try:
            test_func()
            print("\n")
        except Exception as e:
            print(f"ERROR in {test_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
            print("\n")
    
    print("="*50)
    print("All tests completed!")
    print("="*50)
