from moz_sql_parser import parse
from moz_sql_parser import format
import json
from pathlib import Path

if __name__ == '__main__':
    sql_path = Path(__file__).parent / "../sql"
    sql_files = [f for f in sql_path.iterdir() if f.is_file() and f.suffix == '.sql']
    for sql_file in sql_files:
        with sql_file.open() as f:
            sql = sql_file.read_text()
            print()
            print("==================================================")
            print("    " + sql_file.name)
            print("==================================================")
            print(sql)
            print("--------------------------------------------------")
            print(json.dumps(parse(sql)))
            print("--------------------------------------------------")
            print(format(parse(sql)))
            print()
