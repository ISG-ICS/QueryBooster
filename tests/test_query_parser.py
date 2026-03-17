import logging
from core.query_parser import QueryParser
from data.queries import get_query
from data.asts import get_ast
from .ast_util import visualize_ast

parser = QueryParser()
logger = logging.getLogger(__name__)


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
    # TODO: check if we should treat d.name as new node without alias
    logger.info("\n" + visualize_ast(sql, get_ast(44)))

    #assert parser.parse(sql) == get_ast(44)


def test_subquery_parse():
    """
    Test parsing of a SQL query with subquery in WHERE clause (IN operator).
    """
    query = get_query(9)
    sql = query['pattern']
    
    logger.info("\n" + visualize_ast(sql, get_ast(9)))

    assert parser.parse(sql) == get_ast(9)


def test_query_1():
    """Query 1: Remove Cast Date Match Twice."""
    query = get_query(1)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(1)))
    assert parser.parse(sql) == get_ast(1)


def test_query_2():
    """Query 2: Remove Cast Date Match Once."""
    query = get_query(2)
    sql = query["rewrite"]
    logger.info("\n" + visualize_ast(sql, get_ast(2)))
    assert parser.parse(sql) == get_ast(2)


# query 3 has the exact same query as query 2, so I skipped it


def test_query_4():
    """Query 4."""
    query = get_query(4)
    sql = query["rewrite"]
    logger.info("\n" + visualize_ast(sql, get_ast(4)))
    assert parser.parse(sql) == get_ast(4)


# query 5 has the exact same query as query 4, so I skipped it


def test_query_6():
    """Query 6: Remove Self Join Match."""
    query = get_query(6)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(6)))
    assert parser.parse(sql) == get_ast(6)


def test_query_7():
    """Query 7: Remove Self Join No Match."""
    query = get_query(7)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(7)))
    assert parser.parse(sql) == get_ast(7)


def test_query_8():
    """Query 8."""
    query = get_query(8)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(8)))
    assert parser.parse(sql) == get_ast(8)


# query 9 is used in test_subquery_parse


def test_query_10():
    """Query 10: Subquery to Join Match 2."""
    query = get_query(10)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(10)))
    assert parser.parse(sql) == get_ast(10)


def test_query_11():
    """Query 11: Subquery to Join Match 3."""
    query = get_query(11)
    sql = query["rewrite"]
    logger.info("\n" + visualize_ast(sql, get_ast(11)))
    assert parser.parse(sql) == get_ast(11)


def test_query_12():
    """Query 12: Join to Filter Match 1."""
    query = get_query(12)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(12)))
    assert parser.parse(sql) == get_ast(12)


def test_query_13():
    """Query 13: Join to Filter Match 2."""
    query = get_query(13)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(13)))
    assert parser.parse(sql) == get_ast(13)


def test_query_14():
    """Query 14: Test Rule Wetune 90 Match."""
    query = get_query(14)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(14)))
    assert parser.parse(sql) == get_ast(14)


# TODO: Query 15 uses UNION, which is not supported by parser yet


def test_query_16():
    """Query 16: Remove Max Distinct."""
    query = get_query(16)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(16)))
    assert parser.parse(sql) == get_ast(16)


def test_query_17():
    """Query 17."""
    query = get_query(17)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(17)))
    assert parser.parse(sql) == get_ast(17)


def test_query_18():
    """Query 18 (parser drops SELECT for SELECT DISTINCT with comma join)."""
    query = get_query(18)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(18)))
    assert parser.parse(sql) == get_ast(18)


def test_query_19():
    """Query 19: Stackoverflow 2."""
    query = get_query(19)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(19)))
    assert parser.parse(sql) == get_ast(19)


def test_query_20():
    """Query 20: Partial Matching Base Case 2."""
    query = get_query(20)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(20)))
    assert parser.parse(sql) == get_ast(20)


def test_query_21():
    """Query 21: Partial Matching 0."""
    query = get_query(21)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(21)))
    assert parser.parse(sql) == get_ast(21)


def test_query_22():
    """Query 22: Partial Matching 4."""
    query = get_query(22)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(22)))
    assert parser.parse(sql) == get_ast(22)


def test_query_23():
    """Query 23: Partial Keeps Remaining OR."""
    query = get_query(23)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(23)))
    assert parser.parse(sql) == get_ast(23)


def test_query_24():
    """Query 24: Partial Keeps Remaining AND."""
    query = get_query(24)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(24)))
    assert parser.parse(sql) == get_ast(24)


def test_query_25():
    """Query 25: And On True."""
    query = get_query(25)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(25)))
    assert parser.parse(sql) == get_ast(25)


def test_query_26():
    """Query 26: Multiple And On True."""
    query = get_query(26)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(26)))
    assert parser.parse(sql) == get_ast(26)


def test_query_27():
    """Query 27: Remove Where True."""
    query = get_query(27)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(27)))
    assert parser.parse(sql) == get_ast(27)


def test_query_28():
    """Query 28: Rewrite Skips Failed Partial."""
    query = get_query(28)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(28)))
    assert parser.parse(sql) == get_ast(28)


# TODO: Query 29: Full Matching: UNION not supported by parser


def test_query_30():
    """Query 30: Over Partial Matching."""
    query = get_query(30)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(30)))
    assert parser.parse(sql) == get_ast(30)


def test_query_31():
    """Query 31: Aggregation to Subquery."""
    query = get_query(31)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(31)))
    assert parser.parse(sql) == get_ast(31)


# TODO: Query 32: UNION not supported by parser


def test_query_33():
    """Query 33: Spreadsheet ID 3."""
    query = get_query(33)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(33)))
    assert parser.parse(sql) == get_ast(33)


def test_query_34():
    """Query 34: Spreadsheet ID 7."""
    query = get_query(34)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(34)))
    assert parser.parse(sql) == get_ast(34)


def test_query_35():
    """Query 35: Spreadsheet ID 9."""
    query = get_query(35)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(35)))
    assert parser.parse(sql) == get_ast(35)


def test_query_36():
    """Query 36: Spreadsheet ID 10."""
    query = get_query(36)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(36)))
    assert parser.parse(sql) == get_ast(36)


def test_query_37():
    """Query 37: Spreadsheet ID 11."""
    query = get_query(37)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(37)))
    assert parser.parse(sql) == get_ast(37)


def test_query_38():
    """Query 38: Spreadsheet ID 12."""
    query = get_query(38)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(38)))
    assert parser.parse(sql) == get_ast(38)


def test_query_39():
    """Query 39: Spreadsheet ID 15."""
    query = get_query(39)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(39)))
    assert parser.parse(sql) == get_ast(39)


def test_query_40():
    """Query 40."""
    query = get_query(40)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(40)))
    assert parser.parse(sql) == get_ast(40)


def test_query_41():
    """Query 41: Spreadsheet ID 20."""
    query = get_query(41)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(41)))
    assert parser.parse(sql) == get_ast(41)


def test_query_42():
    """Query 42: PostgreSQL Test."""
    query = get_query(42)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(42)))
    #assert parser.parse(sql) == get_ast(42)


def test_query_43():
    """Query 43: MySQL Test."""
    query = get_query(43)
    sql = query["pattern"]
    logger.info("\n" + visualize_ast(sql, get_ast(43)))
    assert parser.parse(sql) == get_ast(43)