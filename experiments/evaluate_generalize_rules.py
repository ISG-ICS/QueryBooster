import csv
import json
import sys
# append the current directory
sys.path.append(".")
# append the parent directory
sys.path.append("..")
from core.query_rewriter import QueryRewriter
from core.rule_generator import RuleGenerator
from core.rule_parser import RuleParser
from mo_sql_parsing import parse as mo_parse
from mo_sql_parsing import format as mo_format


# Evaluate RuleGenerator.generate_general_rule()
#
def evaluate_generalize_rules(examples: list) -> dict:

    print('Start evaluating generalize rules ...')

    rules = []
    rules_keys = set()

    print('Start generating general rules from the given examples ...')

    passed_examples = 0
    for index, example in enumerate(examples):

        print('====>  On example [' + str(index + 1) + '] ...')

        # generate a general rule from the given example
        #
        try:
            rule = RuleGenerator.generate_general_rule(q0=example['q0'], q1=example['q1'])

            finger_print = RuleGenerator.fingerPrint(rule)

            # deduplicate rules
            #
            if finger_print not in rules_keys:

                rules_keys.add(finger_print)

                # populate rule id
                rule['id'] = index + 1

                print('    ---------- R' + str(rule['id']) + ' -----------')
                print(QueryRewriter.beautify(rule['pattern']))
                print('               ||')
                print('               \/')
                print(QueryRewriter.beautify(rule['rewrite']))
                print('    ---------- -- -----------')

                # populate rule details
                rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
                rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
                rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
                rule['pattern_json'] = json.loads(rule['pattern_json'])
                rule['constraints_json'] = json.loads(rule['constraints_json'])
                rule['rewrite_json'] = json.loads(rule['rewrite_json'])
                rule['actions_json'] = json.loads(rule['actions_json'])
                rule['mapping'] = json.loads(rule['mapping'])

                rules.append(rule)
        except Exception:
            print('====>  Exception on example [' + str(index + 1) + '], pass ...')
            passed_examples += 1
            pass
    
    print('End generating general rules from the given examples.')
    print('=====================================================')
    print('    Total # of rules generated: ' + str(len(rules)))
    print('    Total # of passed examples: ' + str(passed_examples))
    print('=====================================================')

    print('Start profiling rules on the examples ...')

    # count the matched and recalled
    #
    matched = 0
    recalled = 0
    passed_examples = 0
    for index, example in enumerate(examples):

        print('====>  On example [' + str(index + 1) + '] ...')

        try:
            _q1, _ = QueryRewriter.rewrite(example['q0'], rules)
            
            if mo_format(mo_parse(example['q0'])) != mo_format(mo_parse(_q1)):
                    matched += 1
                    if mo_format(mo_parse(example['q1'])) == mo_format(mo_parse(_q1)):
                        recalled += 1
        except Exception:
            print('====>  Exception on example [' + str(index + 1) + '], pass ...')
            passed_examples += 1
            pass
    
    print('End profiling rules on the examples ...')

    return matched, recalled, len(rules), passed_examples


# Read a given examples_file
#
def read_examples_file(examples_file: str):
    examples = []
    with open('experiments/' + examples_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        # skip head
        next(csv_reader, None)
        for row in csv_reader:
            examples.append({
                'q0': row[0],
                'q1': row[1]
            })
    
    print()
    print('Reading examples file [' + examples_file + '] done!')
    print('=====================================================')
    print('    Examples')
    print('=====================================================')
    print(examples)

    return examples


if __name__ == '__main__':

    # Exp-1
    #
    examples_file = 'Test_wetune.csv'

    # read examples file
    #
    examples = read_examples_file(examples_file)
    
    # evaluate generalize_rules on the examples files
    #
    matched, recalled, cnt_rules, passed_examples  = evaluate_generalize_rules(examples)
    
    # outpout timings
    #
    print()
    print('=====================================================')
    print('    Evaluating Result [' + examples_file + ']')
    print('=====================================================')
    print('Total # of examples: ' + str(len(examples)))
    print('Total # of rules generated: ' + str(cnt_rules))
    print('Total # of matched examples: ' + str(matched))
    print('Total # of recalled examples: ' + str(recalled))
    print('Total # of passed examples: ' + str(passed_examples))
