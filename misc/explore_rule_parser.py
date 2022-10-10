import sys
# append the path of the parent directory
sys.path.append("..")
from core.rule_parser import RuleParser
from data.rules import rules
import json

if __name__ == '__main__':
    for rule in rules:
        rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
        rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
        rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
        print(json.dumps(rule, indent=2))
