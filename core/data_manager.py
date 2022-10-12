import sqlite3
from sqlite3 import Error
from pathlib import Path
from typing import Dict, List

class DataManager:

    def __init__(self) -> None:
        db_path = Path(__file__).parent / "../"
        self.db_conn = sqlite3.connect(db_path / 'querybooster.db')
        self.__init_schema()
    
    def __init_schema(self) -> None:
        try:
            cur = self.db_conn.cursor()
            schema_path = Path(__file__).parent / "../schema"
            with open(schema_path / 'rules.sql') as rules_sql_file:
                rules_sql = rules_sql_file.read()
                cur.executescript(rules_sql)
        except Error as e:
            print(e)
    
    def __del__(self):
        if self.db_conn:
            self.db_conn.close()
    
    def list_rules(self) -> List[Dict]:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT id, 
                                  key, 
                                  name, 
                                  pattern,
                                  constraints,
                                  rewrite,
                                  actions, 
                                  CASE WHEN disabled is NULL THEN 1 ELSE 0 END AS enabled,
                                  database
                           FROM rules LEFT OUTER JOIN disable_rules 
                                      ON rules.id = disable_rules.rule_id''')
            return cur.fetchall()
        except Error as e:
            print(e)
    
    def enabled_rules(self, database: str) -> List[Dict]:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT id, 
                                  key, 
                                  name, 
                                  pattern_json,
                                  constraints_json,
                                  rewrite_json,
                                  actions_json
                           FROM rules LEFT JOIN disable_rules ON rules.id = disable_rules.rule_id
                                      LEFT JOIN internal_rules ON rules.id = internal_rules.rule_id 
                           WHERE disable_rules.disabled IS NULL AND rules.database = ? 
                           ORDER BY rules.id''', [database])
            return cur.fetchall()
        except Error as e:
            print(e)
    
    def switch_rule(self, rule_id: int, enabled: bool) -> bool:
        try:
            cur = self.db_conn.cursor()
            if enabled:
                cur.execute('''DELETE FROM disable_rules WHERE rule_id = ?''', [rule_id])
            else:
                cur.execute('''INSERT OR IGNORE INTO disable_rules (rule_id, disabled) VALUES (?, 1)''', [rule_id])
            self.db_conn.commit()
            return True
        except Error as e:
            print(e)
            return False
    
    def update_rule(self, rule: dict) -> None:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''REPLACE INTO rules (id, key, name, pattern, constraints, rewrite, actions, database) 
                                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                        [rule['id'], rule['key'], rule['name'], rule['pattern'], 
                         rule['constraints'], rule['rewrite'], rule['actions'], rule['database']
                        ])
            cur.execute('''REPLACE INTO internal_rules (rule_id, pattern_json, constraints_json, rewrite_json, actions_json) VALUES (?, ?, ?, ?, ?)''', 
                        [rule['id'], rule['pattern_json'], rule['constraints_json'], rule['rewrite_json'], rule['actions_json']])
            self.db_conn.commit()
        except Error as e:
            print(e)


if __name__ == '__main__':
    dm = DataManager()
    print(dm.list_rules())
    print(dm.enabled_rules('postgresql'))
    print(dm.enabled_rules('mysql'))