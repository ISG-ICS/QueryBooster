from core.query_formatter import QueryFormatter
from data.queries import get_query
from data.asts import get_ast
from mo_sql_parsing import parse

formatter = QueryFormatter()


def test_basic_format():
    expected_sql = """
        SELECT e.name, d.name AS dept_name, COUNT(*) AS emp_count
        FROM employees AS e JOIN departments AS d ON e.department_id = d.id
        WHERE e.salary > 40000 AND e.age < 60
        GROUP BY d.id, d.name
        HAVING COUNT(*) > 2
        ORDER BY dept_name, emp_count DESC
        LIMIT 10 OFFSET 5
    """
    sql = formatter.format(get_ast(44))
    assert parse(sql) == parse(expected_sql)


def test_subquery_format():
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
    sql = formatter.format(get_ast(9))
    assert parse(sql) == parse(expected_sql)


def test_query_1():
    """Query 1: Remove Cast Date Match Twice."""
    query = get_query(1)
    sql = formatter.format(get_ast(1))
    assert parse(sql) == parse(query["pattern"])


def test_query_2():
    """Query 2: Remove Cast Date Match Once."""
    query = get_query(2)
    sql = formatter.format(get_ast(2))
    assert parse(sql) == parse(query["rewrite"])


# query 3 has the exact same query as query 2, so I skipped it


def test_query_4():
    """Query 4."""
    query = get_query(4)
    sql = formatter.format(get_ast(4))
    assert parse(sql) == parse(query["rewrite"])


# query 5 has the exact same query as query 4, so I skipped it


def test_query_6():
    """Query 6: Remove Self Join Match."""
    query = get_query(6)
    sql = formatter.format(get_ast(6))
    assert parse(sql) == parse(query["pattern"])


def test_query_7():
    """Query 7: Remove Self Join No Match."""
    query = get_query(7)
    sql = formatter.format(get_ast(7))
    assert parse(sql) == parse(query["pattern"])


def test_query_8():
    """Query 8."""
    query = get_query(8)
    sql = formatter.format(get_ast(8))
    assert parse(sql) == parse(query["pattern"])


# query 9 is used in test_subquery_format


def test_query_10():
    """Query 10: Subquery to Join Match 2."""
    query = get_query(10)
    sql = formatter.format(get_ast(10))
    assert parse(sql) == parse(query["pattern"])


def test_query_11():
    """Query 11: Subquery to Join Match 3."""
    query = get_query(11)
    sql = formatter.format(get_ast(11))
    assert parse(sql) == parse(query["rewrite"])


def test_query_12():
    """Query 12: Join to Filter Match 1."""
    query = get_query(12)
    sql = formatter.format(get_ast(12))
    assert parse(sql) == parse(query["pattern"])


def test_query_13():
    """Query 13: Join to Filter Match 2."""
    query = get_query(13)
    sql = formatter.format(get_ast(13))
    assert parse(sql) == parse(query["pattern"])


def test_query_14():
    """Query 14: Test Rule Wetune 90 Match."""
    query = get_query(14)
    sql = formatter.format(get_ast(14))
    assert parse(sql) == parse(query["pattern"])


# TODO: Query 15 uses UNION, which is not supported by parser yet


def test_query_16():
    """Query 16: Remove Max Distinct."""
    query = get_query(16)
    sql = formatter.format(get_ast(16))
    assert parse(sql) == parse(query["pattern"])


def test_query_17():
    """Query 17."""
    query = get_query(17)
    sql = formatter.format(get_ast(17))
    assert parse(sql) == parse(query["pattern"])


def test_query_18():
    """Query 18 (parser drops SELECT for SELECT DISTINCT with comma join)."""
    query = get_query(18)
    sql = formatter.format(get_ast(18))
    assert parse(sql) == parse(query["pattern"])


def test_query_19():
    """Query 19: Stackoverflow 2."""
    query = get_query(19)
    sql = formatter.format(get_ast(19))
    assert parse(sql) == parse(query["pattern"])


def test_query_20():
    """Query 20: Partial Matching Base Case 2."""
    query = get_query(20)
    sql = formatter.format(get_ast(20))
    assert parse(sql) == parse(query["pattern"])


def test_query_21():
    """Query 21: Partial Matching 0."""
    query = get_query(21)
    sql = formatter.format(get_ast(21))
    assert parse(sql) == parse(query["pattern"])


def test_query_22():
    """Query 22: Partial Matching 4."""
    query = get_query(22)
    sql = formatter.format(get_ast(22))
    assert parse(sql) == parse(query["pattern"])


def test_query_23():
    """Query 23: Partial Keeps Remaining OR."""
    query = get_query(23)
    sql = formatter.format(get_ast(23))
    assert parse(sql) == parse(query["pattern"])


def test_query_24():
    """Query 24: Partial Keeps Remaining AND."""
    query = get_query(24)
    sql = formatter.format(get_ast(24))
    assert parse(sql) == parse(query["pattern"])


def test_query_25():
    """Query 25: And On True."""
    query = get_query(25)
    sql = formatter.format(get_ast(25))
    assert parse(sql) == parse(query["pattern"])


def test_query_26():
    """Query 26: Multiple And On True."""
    query = get_query(26)
    sql = formatter.format(get_ast(26))
    assert parse(sql) == parse(query["pattern"])


def test_query_27():
    """Query 27: Remove Where True."""
    query = get_query(27)
    sql = formatter.format(get_ast(27))
    assert parse(sql) == parse(query["pattern"])


def test_query_28():
    """Query 28: Rewrite Skips Failed Partial."""
    query = get_query(28)
    sql = formatter.format(get_ast(28))
    assert parse(sql) == parse(query["pattern"])


# TODO: Query 29: Full Matching: UNION not supported by parser


def test_query_30():
    """Query 30: Over Partial Matching."""
    query = get_query(30)
    sql = formatter.format(get_ast(30))
    assert parse(sql) == parse(query["pattern"])


def test_query_31():
    """Query 31: Aggregation to Subquery."""
    query = get_query(31)
    sql = formatter.format(get_ast(31))
    assert parse(sql) == parse(query["pattern"])


# TODO: Query 32: UNION not supported by parser


def test_query_33():
    """Query 33: Spreadsheet ID 3."""
    query = get_query(33)
    sql = formatter.format(get_ast(33))
    assert parse(sql) == parse(query["pattern"])


def test_query_34():
    """Query 34: Spreadsheet ID 7."""
    query = get_query(34)
    sql = formatter.format(get_ast(34))
    assert parse(sql) == parse(query["pattern"])


def test_query_35():
    """Query 35: Spreadsheet ID 9."""
    query = get_query(35)
    sql = formatter.format(get_ast(35))
    assert parse(sql) == parse(query["pattern"])


def test_query_36():
    """Query 36: Spreadsheet ID 10."""
    query = get_query(36)
    sql = formatter.format(get_ast(36))
    assert parse(sql) == parse(query["pattern"])


def test_query_37():
    """Query 37: Spreadsheet ID 11."""
    query = get_query(37)
    sql = formatter.format(get_ast(37))
    assert parse(sql) == parse(query["pattern"])


def test_query_38():
    """Query 38: Spreadsheet ID 12."""
    query = get_query(38)
    sql = formatter.format(get_ast(38))
    assert parse(sql) == parse(query["pattern"])


def test_query_39():
    """Query 39: Spreadsheet ID 15."""
    query = get_query(39)
    sql = formatter.format(get_ast(39))
    assert parse(sql) == parse(query["pattern"])


def test_query_40():
    """Query 40."""
    query = get_query(40)
    sql = formatter.format(get_ast(40))
    assert parse(sql) == parse(query["pattern"])


def test_query_41():
    """Query 41: Spreadsheet ID 20."""
    query = get_query(41)
    sql = formatter.format(get_ast(41))
    assert parse(sql) == parse(query["pattern"])


def test_query_42():
    """Query 42: PostgreSQL Test."""
    query = get_query(42)
    sql = formatter.format(get_ast(42))
    assert parse(sql) == parse(query["pattern"])


def test_query_43():
    """Query 43: MySQL Test."""
    query = get_query(43)
    sql = formatter.format(get_ast(43))
    assert parse(sql) == parse(query["pattern"])