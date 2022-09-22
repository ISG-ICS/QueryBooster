from typing import Any
import mo_sql_parsing as mosql
import json
from pathlib import Path


def sql_to_json(sqlStr: str) -> Any:
    return mosql.parse(sqlStr)

def json_to_str(jsonStr: Any) -> str:
    return json.dumps(jsonStr)

def json_to_sql(jsonObj: Any) -> str:
    return mosql.format(jsonObj)

def test_sql_str(title: str, sqlStr: str) -> None:
    sqlJson = sql_to_json(sqlStr)
    print()
    print("==================================================")
    print("    " + title)
    print("==================================================")
    print("Original SQL: ")
    print("--------------------------------------------------")
    print(sqlStr)
    print("--------------------------------------------------")
    print("Parsed JSON: ")
    print("--------------------------------------------------")
    print(json_to_str(sqlJson))
    print("--------------------------------------------------")
    print("Formated SQL: ")
    print("--------------------------------------------------")
    print(json_to_sql(sqlJson))
    print()

def test_sql_files() -> None:
    sql_path = Path(__file__).parent / "../sql"
    sql_files = [f for f in sql_path.iterdir() if f.is_file() and f.suffix == '.sql']
    for sql_file in sql_files:
        with sql_file.open() as f:
            sql = sql_file.read_text()
            test_sql_str(sql_file.name, sql)

def test_rules() -> None:
    # Rule #1 -> pattern
    sqlStr = '''
        SELECT * FROM t0 WHERE CAST(e AS DATE)
    '''
    test_sql_str('Rule #1 -> pattern', sqlStr)

    # Rule #1 -> rewrite
    sqlStr = '''
        SELECT * FROM t0 WHERE e
    '''
    test_sql_str('Rule #1 -> rewrite', sqlStr)

    # Rule #2 -> pattern
    sqlStr = '''
        SELECT * FROM t0 WHERE STRPOS(LOWER(e), s) > 0
    '''
    test_sql_str('Rule #2 -> pattern', sqlStr)

    # Rule #2 -> rewrite
    sqlStr = '''
        SELECT * FROM t0 WHERE e ILIKE '%s%'
    '''
    test_sql_str('Rule #2 -> rewrite', sqlStr)

    # Rule #3 -> pattern
    sqlStr = '''
        SELECT s1
          FROM tab1 t1, tab2 t2
         WHERE t1.a1 = t2.a2
           AND p1
    '''
    test_sql_str('Rule #3 -> pattern', sqlStr)

    # Rule #3 -> rewrite
    sqlStr = '''
        SELECT s1
          FROM tab1 t1
         WHERE 1=1 AND p1
    '''
    test_sql_str('Rule #3 -> rewrite', sqlStr)


if __name__ == '__main__':
    test_rules()
    test_sql_files()
