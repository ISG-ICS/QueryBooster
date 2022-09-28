import sys
# append the path of the parent directory
sys.path.append("..")
from core.rule_parser import RuleParser
from data.rules import rules

if __name__ == '__main__':
    ruleParser = RuleParser()

    for rule in rules:
        if rule['pattern_json'] is None or rule['rewrite_json'] is None:
            rule['pattern_json'], rule['rewrite_json'] = ruleParser.parse(rule['pattern'], rule['rewrite'])
            print(rule)
