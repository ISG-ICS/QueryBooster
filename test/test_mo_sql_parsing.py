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

def test_sql_files() -> None:
    sql_path = Path(__file__).parent / "../sql"
    sql_files = [f for f in sql_path.iterdir() if f.is_file() and f.suffix == '.sql']
    for sql_file in sql_files:
        with sql_file.open() as f:
            sql = sql_file.read_text()
            sqlJson = sql_to_json(sql)
            print()
            print("==================================================")
            print("    " + sql_file.name)
            print("==================================================")
            print("Original SQL: ")
            print("--------------------------------------------------")
            print(sql)
            print("--------------------------------------------------")
            print("Parsed JSON: ")
            print("--------------------------------------------------")
            print(json_to_str(sqlJson))
            print("--------------------------------------------------")
            print("Formated SQL: ")
            print("--------------------------------------------------")
            print(json_to_sql(sqlJson))
            print()


def test_sql_str(sqlStr: str) -> None:
    sqlJson = sql_to_json(sqlStr)
    print()
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


if __name__ == '__main__':
    # test_sql_files()
    
    # Rule #1 -> pattern
    sqlStr = '''
        SELECT * FROM t0 WHERE CAST(e AS DATE)
    '''
    test_sql_str(sqlStr)

    # Rule #1 -> rewrite
    sqlStr = '''
        SELECT * FROM t0 WHERE e
    '''
    test_sql_str(sqlStr)

    # Rule #3 -> pattern
    sqlStr = '''
        SELECT s1
          FROM tab1 t1, tab2 t2
         WHERE t1.a1 = t2.a2
           AND p1
    '''
    test_sql_str(sqlStr)

    # Rule #3 -> rewrite
    sqlStr = '''
        SELECT s1
          FROM tab1 t1
         WHERE 1=1 AND p1
    '''
    test_sql_str(sqlStr)

    # Rule #3 -> left
    sqlStr = '''
        SELECT e1.name, 
               e1.age, 
               e2.salary 
          FROM employee e1, employee e2
         WHERE e1.id = e2.id
           AND e1.age > 17
           AND e2.salary > 35000
    '''
    test_sql_str(sqlStr)

    # Rule #3 -> right
    sqlStr = '''
        SELECT e1.name, 
               e1.age, 
               e1.salary 
          FROM employee e1
         WHERE e1.age > 17
           AND e1.salary > 35000
    '''
    test_sql_str(sqlStr)