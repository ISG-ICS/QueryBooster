from core.data_manager import DataManager
import json


class RuleManager:

    def __init__(self, dm: DataManager) -> None:
        self.dm = dm
    
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
                'pattern': json.loads(enabled_rule[3]),
                'constraints': enabled_rule[4],
                'rewrite': json.loads(enabled_rule[5]),
                'actions': enabled_rule[6]
            })
        return res
