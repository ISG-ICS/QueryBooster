from core.query_formatter import QueryFormatter
from core.query_parser import QueryParser
from data.queries import get_query
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
    assert parse(formatted_sql) == parse(original_sql)


def test_subquery_e2e():
    query = get_query(9)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_1():
    query = get_query(1)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_2():
    query = get_query(2)
    original_sql = query["rewrite"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


# query 3 has the exact same query as query 2, so the query was skipped


def test_query_4():
    query = get_query(4)
    original_sql = query["rewrite"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


# query 5 has the exact same query as query 4, so the query was skipped


def test_query_6():
    query = get_query(6)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_7():
    query = get_query(7)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_8():
    query = get_query(8)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


# query 9 is used in test_subquery_e2e


def test_query_10():
    query = get_query(10)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_11():
    query = get_query(11)
    original_sql = query["rewrite"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_12():
    query = get_query(12)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_13():
    query = get_query(13)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_14():
    query = get_query(14)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_15():
    query = get_query(15)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_16():
    query = get_query(16)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_17():
    query = get_query(17)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_18():
    query = get_query(18)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_19():
    query = get_query(19)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_20():
    query = get_query(20)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_21():
    query = get_query(21)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_22():
    query = get_query(22)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_23():
    query = get_query(23)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_24():
    query = get_query(24)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_25():
    query = get_query(25)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_26():
    query = get_query(26)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_27():
    query = get_query(27)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_28():
    query = get_query(28)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_29():
    query = get_query(29)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_30():
    query = get_query(30)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_31():
    query = get_query(31)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_32():
    query = get_query(32)
    original_sql = query["rewrite"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_33():
    query = get_query(33)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_34():
    query = get_query(34)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_35():
    query = get_query(35)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_36():
    query = get_query(36)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_37():
    query = get_query(37)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_38():
    query = get_query(38)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_39():
    query = get_query(39)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_40():
    query = get_query(40)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_41():
    query = get_query(41)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_42():
    query = get_query(42)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)


def test_query_43():
    query = get_query(43)
    original_sql = query["pattern"]
    parsed_ast = parser.parse(original_sql)
    formatted_sql = formatter.format(parsed_ast)
    assert parse(formatted_sql) == parse(original_sql)