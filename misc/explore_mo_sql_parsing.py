from typing import Any
import mo_sql_parsing as mosql
import json
from pathlib import Path


def sql_to_ast(sqlStr: str) -> Any:
    return mosql.parse(sqlStr)

def ast_to_str(astObj: Any) -> str:
    return json.dumps(astObj)

def ast_to_sql(astObj: Any) -> str:
    return mosql.format(astObj)

def print_sql_str(title: str, sqlStr: str) -> None:
    astJson = sql_to_ast(sqlStr)
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
    print(ast_to_str(astJson))
    print("--------------------------------------------------")
    print("Formated SQL: ")
    print("--------------------------------------------------")
    print(ast_to_sql(astJson))
    print()

def explore_sql_files() -> None:
    sql_path = Path(__file__).parent / "../sql"
    sql_files = [f for f in sql_path.iterdir() if f.is_file() and f.suffix == '.sql']
    for sql_file in sql_files:
        with sql_file.open() as f:
            sql = sql_file.read_text()
            print_sql_str(sql_file.name, sql)

def explore_rules() -> None:
    # Rule #1 -> pattern
    sqlStr = '''
        SELECT * FROM t0 WHERE CAST(e AS DATE)
    '''
    print_sql_str('Rule #1 -> pattern', sqlStr)

    # Rule #1 -> rewrite
    sqlStr = '''
        SELECT * FROM t0 WHERE e
    '''
    print_sql_str('Rule #1 -> rewrite', sqlStr)

    # Rule #2 -> pattern
    sqlStr = '''
        SELECT * FROM t0 WHERE STRPOS(LOWER(e), s) > 0
    '''
    print_sql_str('Rule #2 -> pattern', sqlStr)

    # Rule #2 -> rewrite
    sqlStr = '''
        SELECT * FROM t0 WHERE e ILIKE '%s%'
    '''
    print_sql_str('Rule #2 -> rewrite', sqlStr)

    # Rule #3 -> pattern
    sqlStr = '''
        SELECT s1
          FROM tab1 t1, tab2 t2
         WHERE t1.a1 = t2.a2
           AND p1
    '''
    print_sql_str('Rule #3 -> pattern', sqlStr)

    # Rule #3 -> rewrite
    sqlStr = '''
        SELECT s1
          FROM tab1 t1
         WHERE 1=1 AND p1
    '''
    print_sql_str('Rule #3 -> rewrite', sqlStr)

    # Rule #3' -> pattern
    sqlStr = '''
        SELECT s
          FROM t1, t2
         WHERE t1.a1 = t2.a2
           AND p
    '''
    print_sql_str('Rule #3\' -> pattern', sqlStr)

    # Rule #3' -> rewrite
    sqlStr = '''
        SELECT s
          FROM t1
         WHERE p
    '''
    print_sql_str('Rule #3\' -> rewrite', sqlStr)

def explore_ast():
    sqlStr = '''
        SELECT * FROM t0 WHERE CAST(e AS DATE)
    '''
    sqlAST = sql_to_ast(sqlStr)
    print(sqlAST)

if __name__ == '__main__':
    explore_rules()
    explore_sql_files()
    explore_ast()
