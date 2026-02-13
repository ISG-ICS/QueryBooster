from core.query_formatter import QueryFormatter
from core.query_parser import QueryParser
from mo_sql_parsing import parse

formatter = QueryFormatter()
parser = QueryParser()

def test_basic_e2e():
    original_sql = """
        SELECT e.name, d.name as dept_name, COUNT(*) as emp_count
        FROM employees e JOIN departments d ON e.department_id = d.id
        WHERE e.salary > 40000 AND e.age < 60
        GROUP BY d.id, d.name
        HAVING COUNT(*) > 2
        ORDER BY dept_name, emp_count DESC
        LIMIT 10 OFFSET 5
    """
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)

    # test our output is semantically equivalent to input using mo_sql_parsing
    assert parse(formatted_sql) == parse(original_sql)


def test_subquery_e2e():
    original_sql = """
        SELECT empno, firstnme, lastname, phoneno
        FROM employee
        WHERE workdept IN
            (SELECT deptno
                FROM department
                WHERE deptname = 'OPERATIONS')
        AND 1=1
    """
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)