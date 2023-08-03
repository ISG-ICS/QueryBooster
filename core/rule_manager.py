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

    def add_rule(self, rule: dict, user_id: str) -> bool:
        rule['key'] = '_'.join([word.lower() for word in str(rule['name']).split(' ')])
        rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
        rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
        rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
        return self.dm.add_rule(rule, user_id)

    def edit_rule(self, rule: dict, user_id: str, rule_id: str) -> bool:
        rule['key'] = '_'.join([word.lower() for word in str(rule['name']).split(' ')])
        rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
        rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
        rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
        return self.dm.edit_rule(rule, user_id, rule_id)

    def delete_rule(self, rule: dict) -> bool:
        return self.dm.delete_rule(rule)
    
    def fetch_enabled_rules(self, appguid: str) -> list:
        enabled_rules = self.dm.enabled_rules(appguid)
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

    def fetch_all_rules(self) -> list:
        rules = self.dm.all_rules()
        res = []
        for rule in rules:
            res.append({
                'id': rule[0],
                'key': rule[1],
                'name': rule[2],
                'pattern_json': json.loads(rule[3]),
                'constraints_json': json.loads(rule[4]),
                'rewrite_json': json.loads(rule[5]),
                'actions_json': json.loads(rule[6])
            })
        return res
    
    def list_rules(self, user_id: str) -> list:
        rules = self.dm.list_rules(user_id)
        # group the rule together and 
        # list its enabled applications
        rule_applications = {}
        for rule in rules:
            rule_id = rule[0]
            application_id = rule[7]
            application_name = rule[8]
            if application_id is not None:
                if rule_id in rule_applications:
                    rule_applications[rule_id].append({"app_id": application_id, "app_name": application_name})
                else:
                    rule_applications[rule_id] = [{"app_id": application_id, "app_name": application_name}]
            else:
                rule_applications[rule_id] = []
        res = []
        visited_rule_ids = []
        for rule in rules:
            if rule[0] not in visited_rule_ids:
                res.append({
                    'id': rule[0],
                    'key': rule[1],
                    'name': rule[2],
                    'pattern': rule[3],
                    'constraints': rule[4],
                    'rewrite': rule[5],
                    'actions': rule[6],
                    'enabled_apps': rule_applications[rule[0]]
                })
                visited_rule_ids.append(rule[0])

        return res
        
    def transform_rule_graph(self, root_rule: dict) -> dict:
        rules = []
        relations = []

        # breadth-first-search
        queue = [(root_rule, None)]
        id = 1
        while len(queue) > 0:
            rule, parent = queue.pop(0)
            if 'visited' not in rule.keys():
                rule['visited'] = True
                rule['id'] = str(id)
                id += 1
                if parent is None:
                    rule['level'] = 1
                else:
                    rule['level'] = parent['level'] + 1
                # append rule
                rules.append({
                    'id': rule['id'],
                    'pattern': rule['pattern'],
                    'rewrite': rule['rewrite'],
                    'constraints': rule['constraints'],
                    'actions': rule['actions'],
                    'level': rule['level']
                })
                # enqueue children
                for child in rule['children']:
                    queue.append((child, rule))
            # append relation
            if parent is not None:
                relations.append({
                    'parentRuleId': parent['id'], 
                    'childRuleId': rule['id']
                })
        
        return {'rules': rules, 'relations': relations}
    
    def transform_rules_graph(self, root_rules: list) -> dict:
        rules = []
        relations = []

        id = 1
        # traverse root_rules
        for root_rule in root_rules:
            # breadth-first-search
            queue = [(root_rule, None)]
            while len(queue) > 0:
                rule, parent = queue.pop(0)
                if 'visited' not in rule.keys():
                    rule['visited'] = True
                    rule['id'] = str(id)
                    id += 1
                    if parent is None:
                        rule['level'] = 1
                    else:
                        rule['level'] = parent['level'] + 1
                    # append rule
                    rules.append({
                        'id': rule['id'],
                        'pattern': rule['pattern'],
                        'rewrite': rule['rewrite'],
                        'constraints': rule['constraints'],
                        'actions': rule['actions'],
                        'level': rule['level'],
                        'coveredExamples': rule['coveredExamples']
                    })
                    # enqueue children
                    for child in rule['children']:
                        queue.append((child, rule))
                # append relation
                if parent is not None:
                    relations.append({
                        'parentRuleId': parent['id'], 
                        'childRuleId': rule['id']
                    })
        
        return {'rules': rules, 'relations': relations}


if __name__ == '__main__':
    dm = DataManager()
    rm = RuleManager(dm)
    print(rm.list_rules())
    print(rm.fetch_enabled_rules('postgresql'))
    print(rm.fetch_enabled_rules('mysql'))