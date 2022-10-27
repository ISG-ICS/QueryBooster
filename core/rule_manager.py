import sys
# append the path of the parent directory
sys.path.append("..")
from core.data_manager import DataManager
from core.rule_parser import RuleParser
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

    def add_rule(self, rule: dict) -> bool:
        rule['key'] = '_'.join([word.lower() for word in str(rule['name']).split(' ')])
        rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
        rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
        rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
        return self.dm.add_rule(rule)
    
    def delete_rule(self, rule: dict) -> bool:
        return self.dm.delete_rule(rule)
    
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
                'pattern': rule[3],
                'constraints': rule[4],
                'rewrite': rule[5],
                'actions': rule[6],
                'enabled': True if rule[7] == 1 else False
            })
        return res


if __name__ == '__main__':
    dm = DataManager()
    rm = RuleManager(dm)
    print(rm.list_rules())
    print(rm.fetch_enabled_rules('postgresql'))
    print(rm.fetch_enabled_rules('mysql'))