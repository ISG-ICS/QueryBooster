from core.data_manager import DataManager
from data.rules import get_rules
import json


class RuleManager:

    def __init__(self, dm: DataManager) -> None:
        self.dm = dm
        self.__init_rules()
    
    def __init_rules(self) -> None:
        for rule in get_rules():
            self.dm.update_rule(rule)
    
    def __del__(self):
        del self.dm
    
    def fetch_enabled_rules(self, database: str) -> list:
        enabled_rules = self.dm.enabled_rules(database)
        res = []
        for enabled_rule in enabled_rules:
            res.append({
                'id': enabled_rule[0],
                'key': enabled_rule[1],
                'name': enabled_rule[2],
                'pattern_json': json.loads(enabled_rule[3]),
                'constraints_json': json.loads(enabled_rule[4]),
                'rewrite_json': json.loads(enabled_rule[5]),
                'actions_json': json.loads(enabled_rule[6])
            })
        return res
    
    def list_rules(self) -> list:
        rules = self.dm.list_rules()
        res = []
        for rule in rules:
            res.append({
                'id': rule[0],
                'key': rule[1],
                'name': rule[2],
                'formula': rule[3],
                'enabled': True if rule[4] == 1 else False
            })
        return res
