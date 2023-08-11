import sys
# append the path of the parent directory
sys.path.append("..")
import datetime
import json
import sqlite3
import traceback
from sqlite3 import Error
from pathlib import Path
from typing import Dict, List
from data.rules import get_rule
import os

class DataManager:

    def __init__(self, init=True) -> None:
        db_path = Path(__file__).parent / "../"
        self.db_conn = sqlite3.connect(os.path.join(db_path, 'querybooster.db'), check_same_thread=False)
        if init:
            self.__init_schema()
            self.__init_data()
    
    def __init_schema(self) -> None:
        try:
            cur = self.db_conn.cursor()
            schema_path = Path(__file__).parent / "../schema"
            with open(os.path.join(schema_path, 'schema.sql')) as schema_sql_file:
                schema_sql = schema_sql_file.read()
                cur.executescript(schema_sql)
        except Error as e:
            print(e)

    def __init_data(self) -> None:
        try:
            # create two users: Alice and Bob
            #
            self.update_user({'id': '102153741508111367852', 'email': 'alice.vldb@gmail.com'})
            self.update_user({'id': '110518596083203416821', 'email': 'bob.vldb@gmail.com'})
            # create two apps for Alice
            #
            self.update_application({'id': 1, 'name': 'TwitterPg', 'guid': 'Alice-Tableau-Twitter-Pg', 'user_id': '102153741508111367852'})
            self.update_application({'id': 2, 'name': 'TwitterMySQL', 'guid': 'Alice-Tableau-Twitter-MySQL', 'user_id': '102153741508111367852'})
            # create one app for Bob
            #
            self.update_application({'id': 3, 'name': 'TpchPg', 'guid': 'Bob-Tableau-Tpch-Pg', 'user_id': '110518596083203416821'})
            # create one rule for Alice
            #
            rule = get_rule('remove_max_distinct')
            rule['user_id'] = '102153741508111367852'
            rule['pattern_json'] = json.dumps(rule['pattern_json'])
            rule['constraints_json'] = json.dumps(rule['constraints_json'])
            rule['rewrite_json'] = json.dumps(rule['rewrite_json'])
            rule['actions_json'] = json.dumps(rule['actions_json'])
            self.update_rule(rule)
            # enable it for its app
            #
            self.enable_rule(rule_id=rule['id'], app_id=1, app_name='TwitterPg')
            
        except Error as e:
            print(e)
    
    def __del__(self):
        if self.db_conn:
            self.db_conn.close()
    
    def list_rules(self, user_id: str) -> List[Dict]:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT rules.id, 
                                  rules.key, 
                                  rules.name, 
                                  rules.pattern,
                                  rules.constraints,
                                  rules.rewrite,
                                  rules.actions,
                                  enabled.application_id,
                                  applications.name AS application_name
                           FROM rules LEFT OUTER JOIN enabled 
                                      ON rules.id = enabled.rule_id
                                LEFT OUTER JOIN applications
                                      ON enabled.application_id = applications.id
                           WHERE rules.user_id = ?''', [user_id])
            return cur.fetchall()
        except Error as e:
            print(e)
    
    def enabled_rules(self, appguid: str) -> List[Dict]:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT rules.id, 
                                  rules.key, 
                                  rules.name, 
                                  internal_rules.pattern_json,
                                  internal_rules.constraints_json,
                                  internal_rules.rewrite_json,
                                  internal_rules.actions_json
                           FROM rules JOIN enabled ON rules.id = enabled.rule_id
                                      JOIN applications ON enabled.application_id = applications.id
                                      LEFT JOIN internal_rules ON rules.id = internal_rules.rule_id 
                           WHERE applications.guid = ? 
                           ORDER BY rules.id''', [appguid])
            return cur.fetchall()
        except Error as e:
            print(e)
    
    def all_rules(self) -> List[Dict]:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT id, 
                                  key, 
                                  name, 
                                  pattern_json,
                                  constraints_json,
                                  rewrite_json,
                                  actions_json
                           FROM rules LEFT JOIN internal_rules ON rules.id = internal_rules.rule_id 
                           ORDER BY rules.id''', [])
            return cur.fetchall()
        except Error as e:
            print(e)
    
    def enable_rule(self, rule_id: int, app_id: int, app_name: str) -> bool:
        try:
            cur = self.db_conn.cursor()
            if not app_id:
                cur.execute('''SELECT id FROM applications WHERE name = ?''', [app_name])
                app_id = cur.fetchone()[0]
            cur.execute('''INSERT OR IGNORE INTO enabled (rule_id, application_id) VALUES (?, ?)''', [rule_id, app_id])
            self.db_conn.commit()
            return True
        except Error as er:
            print('[Error] in enable_rule:')
            print('rule_id: ', rule_id, 'app_id: ', app_id, 'app_name: ', app_name)
            print('SQLite error: %s' % (' '.join(er.args)))
            print("Exception class is: ", er.__class__)
            print('SQLite traceback: ')
            exc_type, exc_value, exc_tb = sys.exc_info()
            print(traceback.format_exception(exc_type, exc_value, exc_tb))
            return False
    
    def disable_rule(self, rule_id: int, app_id: int, app_name: str) -> bool:
        try:
            cur = self.db_conn.cursor()
            if not app_id:
                cur.execute('''SELECT id FROM applications WHERE name = ?''', [app_name])
                app_id = cur.fetchone()[0]
            cur.execute('''DELETE FROM enabled WHERE rule_id = ? AND application_id = ?''', [rule_id, app_id])
            self.db_conn.commit()
            return True
        except Error as er:
            print('[Error] in disable_rule:')
            print('rule_id: ', rule_id, 'app_id: ', app_id, 'app_name: ', app_name)
            print('SQLite error: %s' % (' '.join(er.args)))
            print("Exception class is: ", er.__class__)
            print('SQLite traceback: ')
            exc_type, exc_value, exc_tb = sys.exc_info()
            print(traceback.format_exception(exc_type, exc_value, exc_tb))
            return False
    
    def update_rule(self, rule: dict) -> None:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''REPLACE INTO rules (id, key, name, pattern, constraints, rewrite, actions, user_id) 
                                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                        [rule['id'], rule['key'], rule['name'], rule['pattern'], 
                         rule['constraints'], rule['rewrite'], rule['actions'], rule['user_id']
                        ])
            cur.execute('''REPLACE INTO internal_rules (rule_id, pattern_json, constraints_json, rewrite_json, actions_json) VALUES (?, ?, ?, ?, ?)''', 
                        [rule['id'], rule['pattern_json'], rule['constraints_json'], rule['rewrite_json'], rule['actions_json']])
            self.db_conn.commit()
        except Error as er:
            print('[Error] in update_rule:')
            print(rule)
            print('SQLite error: %s' % (' '.join(er.args)))
            print("Exception class is: ", er.__class__)
            print('SQLite traceback: ')
            exc_type, exc_value, exc_tb = sys.exc_info()
            print(traceback.format_exception(exc_type, exc_value, exc_tb))
    
    def add_rule(self, rule: dict, user_id: str) -> bool:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT IFNULL(MAX(id), 0) + 1 FROM rules;''')
            rule['id'] = cur.fetchone()[0]
            
            cur.execute('''INSERT INTO rules (id, key, name, pattern, constraints, rewrite, actions, user_id) 
                                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                        [rule['id'], rule['key'], rule['name'], rule['pattern'], 
                         rule['constraints'], rule['rewrite'], rule['actions'], user_id
                        ])
            cur.execute('''INSERT INTO internal_rules (rule_id, pattern_json, constraints_json, rewrite_json, actions_json) VALUES (?, ?, ?, ?, ?)''', 
                        [rule['id'], rule['pattern_json'], rule['constraints_json'], rule['rewrite_json'], rule['actions_json']])
            self.db_conn.commit()
            return True
        except Error as e:
            print(e)
            return False
    
    def delete_rule(self, rule: dict) -> bool:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''PRAGMA foreign_keys=on;''')
            cur.execute('''DELETE FROM rules WHERE id = ?''', [rule['id']])
            cur.execute('''PRAGMA foreign_keys=off;''')
            self.db_conn.commit()
            return True
        except Error as e:
            print(e)
            return False
    
    def log_query(self, appguid: str, guid: str, original_query: str, rewritten_query: str, rewriting_path: list) -> None:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT IFNULL(MAX(id), 0) + 1 FROM queries;''')
            query_id = cur.fetchone()[0]

            cur.execute('''INSERT INTO queries (id, timestamp, appguid, guid, query_time_ms, original_sql, sql) 
                                       VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                        [query_id, datetime.datetime.now(), appguid, guid, -1000, original_query, rewritten_query])
            seq = 1
            for rewriting in rewriting_path:
                cur.execute('''INSERT INTO rewriting_paths (query_id, seq, rule_id, rewritten_sql)
                                           VALUES (?, ?, ?, ?)''', 
                            [query_id, seq, rewriting[0], rewriting[1]])
                seq += 1
            self.db_conn.commit()
        except Error as e:
            print(e)
    
    def report_query(self, appguid: str, guid: str, query_time_ms: int) -> None:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''UPDATE queries
                              SET query_time_ms = ? 
                            WHERE appguid = ? 
                              AND guid = ?''', 
                        [query_time_ms, appguid, guid])
            self.db_conn.commit()
        except Error as e:
            print(e)
    
    def list_queries(self, user_id: str) -> List[Dict]:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT id, 
                                  timestamp, 
                                  rewritten,
                                  before_latency,
                                  after_latency, 
                                  sql,
                                  suggestion,
                                  suggested_latency,
                                  app_name
                           FROM query_log 
                          WHERE user_id = ?''', [user_id])
            return cur.fetchall()
        except Error as e:
            print(e)
    
    def get_original_sql(self, query_id: int) -> str:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT original_sql
                           FROM queries 
                           WHERE id = ?''', [query_id])
            return cur.fetchall()[0]
        except Error as e:
            print(e)
    
    def list_rewritings(self, query_id: int) -> List[Dict]:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT seq, 
                                  name, 
                                  rewritten_sql
                           FROM rewriting_paths LEFT JOIN rules ON rules.id = rewriting_paths.rule_id
                           WHERE query_id = ?''', [query_id])
            return cur.fetchall()
        except Error as e:
            print(e)
    
    def list_suggestion_rewritings(self, query_id: int) -> List[Dict]:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT seq, 
                                  rules.name, 
                                  rules.id,
                                  rules.user_id,
                                  users.email,
                                  rewritten_sql
                           FROM suggestion_rewriting_paths
                                LEFT JOIN rules ON rules.id = suggestion_rewriting_paths.rule_id
                                JOIN users on rules.user_id = users.id
                           WHERE query_id = ?''', [query_id])
            return cur.fetchall()
        except Error as e:
            print(e)
    
    def update_user(self, user: dict) -> None:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''REPLACE INTO users (id, email) 
                                       VALUES (?, ?)''', 
                        [user['id'], user['email']])
            self.db_conn.commit()
        except Error as e:
            print('[Error] in update_user:')
            print(e)
    
    def update_application(self, app: dict) -> None:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''REPLACE INTO applications (id, name, guid, user_id) 
                                        VALUES (?, ?, ?, ?) ''', 
                        [app['id'], app['name'], app['guid'], app['user_id']])
            self.db_conn.commit()
        except Error as e:
            print('[Error] in update_application:')
            print(e)

    def save_application(self, app: dict) -> None:
        try:
            cur = self.db_conn.cursor()
            if(app['id'] == -1):
                cur.execute('''SELECT IFNULL(MAX(id), 0) + 1 FROM applications;''')
                app['id'] = cur.fetchone()[0]
            print(app)
            cur.execute('''INSERT INTO applications (id, name, user_id) 
                                    VALUES (?, ?, ?) ON CONFLICT (id) DO UPDATE SET
                                    name=excluded.name''', 
                        [app['id'], app['name'], app['user_id']])
            self.db_conn.commit()
        except Error as e:
            print('[Error] in save_application:')
            print(e)

    def delete_application(self, app: dict) -> bool:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''DELETE FROM applications WHERE id = ? AND user_id = ?''', [app['id'], app['user_id']])
            self.db_conn.commit()
            return True
        except Error as e:
            print(e)
            return False
    
    def list_applications(self, user_id: str) -> List[Dict]:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT id,
                                  name
                           FROM applications
                           WHERE applications.user_id = ?''', [user_id])
            return cur.fetchall()
        except Error as e:
            print(e)
    
    def create_user(self, user: dict) -> bool:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''REPLACE INTO users (id, email) VALUES (?, ?)''', 
                        [user['id'], user['email']])
            self.db_conn.commit()
            return True
        except Error as e:
            print(e)
            return False
    
    def fetch_query(self, guid: str) -> dict:
        try:
            cur = self.db_conn.cursor()
            cur.execute('''SELECT query_log.id, 
                                  query_log.rewritten,
                                  query_log.sql
                           FROM query_log JOIN queries ON query_log.id = queries.id
                          WHERE queries.guid = ?''', [guid])
            return cur.fetchall()[0]
        except Error as e:
            print(e)
    
    def log_query_suggestion(self, query_id: int, rewritten_query: str, rewriting_path: list) -> None:
        try:
            cur = self.db_conn.cursor()
            # TODO - estimate the query_time_ms for suggested rewritten_sql
            cur.execute('''INSERT INTO suggestions (query_id, query_time_ms, rewritten_sql) 
                                       VALUES (?, ?, ?)''', 
                        [query_id, -1000, rewritten_query])
            seq = 1
            for rewriting in rewriting_path:
                cur.execute('''INSERT INTO suggestion_rewriting_paths (query_id, seq, rule_id, rewritten_sql)
                                           VALUES (?, ?, ?, ?)''', 
                            [query_id, seq, rewriting[0], rewriting[1]])
                seq += 1
            self.db_conn.commit()
        except Error as e:
            print(e)


if __name__ == '__main__':
    dm = DataManager()