from core.query_formatter import QueryFormatter
from core.query_parser import QueryParser
from re import sub
from mo_sql_parsing import parse, format

formatter = QueryFormatter()
parser = QueryParser()


def test_basic_format():
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

    assert parse(formatted_sql) == parse(original_sql)