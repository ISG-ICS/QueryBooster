import sys
# append the path of the parent directory
sys.path.append("..")
from core.rule_parser import RuleParser
from data.rules import rules
import json

if __name__ == '__main__':
    ruleParser = RuleParser()

    for rule in rules:
        rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = ruleParser.parse(rule['pattern'], rule['rewrite'])
        rule['constraints_json'] = ruleParser.parse_constraints(rule['constraints'], rule['mapping'])
        rule['actions_json'] = ruleParser.parse_actions(rule['actions'], rule['mapping'])
        print(json.dumps(rule, indent=2))
