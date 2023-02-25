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

    print('(1) Start generating general rules from the given examples ...')
    generated_rules = []
    # rules that cover more than one examples
    #
    common_rules = []
    # those example ids covered by common rules
    #
    common_rules_example_ids = set()
    # hashmap storing keys of unique generated rules and their source example ids
    #
    uniqueue_rules_keys = {}
    # hashset storing keys of unique common rules
    #
    common_rules_keys = set()
    failed_generating_rule_example_ids = set()
    cnt_failed_generating_rule = 0
    cnt_duplicated_rule = 0
    for example in examples:

        print('====>  Generating rule on example [' + str(example['id']) + '] ...')

        # generate a general rule from the given example
        #
        try:
            rule = RuleGenerator.generate_general_rule(q0=example['q0'], q1=example['q1'])

            # populate rule id as the example id
            #
            rule['id'] = int(example['id'])

            print('    ---------- R' + str(rule['id']) + ' -----------')
            print(QueryRewriter.beautify(rule['pattern']))
            print('               ||')
            print('               \/')
            print(QueryRewriter.beautify(rule['rewrite']))
            print('    ---------- -- -----------')


            finger_print = RuleGenerator.fingerPrint(rule)

            # duplicated rule
            #
            if finger_print in uniqueue_rules_keys:
                cnt_duplicated_rule += 1
                # make sure common_rules list has only one copy of the rule
                #
                if finger_print not in common_rules_keys:
                    common_rules_keys.add(finger_print)
                    common_rules.append(rule)
                # take down the examples that generated the common rules
                #
                # the example initially generated the common rule
                common_rules_example_ids.add(uniqueue_rules_keys[finger_print])
                # the current example that generated the same common rule
                common_rules_example_ids.add(example['id'])
            else:
                uniqueue_rules_keys[finger_print] = example['id']
                generated_rules.append(rule)

        except Exception as e:
            print('====>  Generating rule on example [' + str(example['id']) + '] failed!')
            print(e)
            cnt_failed_generating_rule += 1
            failed_generating_rule_example_ids.add(example['id'])
            pass
    
    print('(1) End generating general rules from the given examples.')
    print('=====================================================')
    print('    # of examples processed: ' + str(len(examples)))
    print('    # of failed generating rules: ' + str(cnt_failed_generating_rule))
    print('    # of successfully generated rules : ' + str(len(generated_rules) + cnt_duplicated_rule))
    print('    # of duplicated rules: ' + str(cnt_duplicated_rule))
    print('    # of unique generated rules: ' + str(len(generated_rules)))
    print('    # of common rules: ' + str(len(common_rules)))
    print('    # of examples that share the common rules: ' + str(len(common_rules_example_ids)))
    print('    -------------------------------------------')
    print('    common_rule_example_ids:')
    print(common_rules_example_ids)
    print('=====================================================')

    print('(1.1) Filter examples by removing source examples that failed to generate rules')
    print('Before filter: # of examples: ' + str(len(examples)))
    examples = [example for example in examples if example['id'] not in failed_generating_rule_example_ids]
    print('After filter: # of examples: ' + str(len(examples)))

    print('(2) Start populating rules from generated_rules ...')
    populated_rules = []
    cnt_failed_populating_rule = 0
    failed_populating_rule_example_ids = set()
    for rule in generated_rules:
        try:
            # populate rule details
            rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
            rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
            rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
            rule['pattern_json'] = json.loads(rule['pattern_json'])
            rule['constraints_json'] = json.loads(rule['constraints_json'])
            rule['rewrite_json'] = json.loads(rule['rewrite_json'])
            rule['actions_json'] = json.loads(rule['actions_json'])
            rule['mapping'] = json.loads(rule['mapping'])
            populated_rules.append(rule)
        except Exception as e:
            print('====>  Parsing rule [' + str(rule['id']) + '] failed!')
            print(e)
            cnt_failed_populating_rule += 1
            failed_populating_rule_example_ids.add(rule['id'])
            pass
    print('(2) End populating rules from generated_rules.')
    print('=====================================================')
    print('    # of rules populated: ' + str(len(populated_rules)))
    print('    # of failed populating rules: ' + str(cnt_failed_populating_rule))
    print('=====================================================')

    print('(2.1) Filter examples by removing source examples that failed to populate rules')
    print('Before filter: # of examples: ' + str(len(examples)))
    examples = [example for example in examples if example['id'] not in failed_populating_rule_example_ids]
    print('After filter: # of examples: ' + str(len(examples)))

    print('(3) Start profiling rules on the examples ...')
    # count the succesfully matched and succesfully rewritten
    #
    matched = 0
    rewritten = 0
    for example in examples:

        print('====>  Evaluating rules on example [' + str(example['id']) + '] ...')

        try:
            _q1, _path = QueryRewriter.rewrite(example['q0'], populated_rules, iterate=False)
            
            if len(_path) > 0:
                    matched += 1
                    example['matched'] = 1
                    example['path'] = '-'.join([str(x[0]) for x in _path])
                    if mo_format(mo_parse(example['q1'])) == mo_format(mo_parse(_q1)):
                        rewritten += 1
                        example['rewritten'] = 1
                    else:
                        example['rewritten'] = 0
                        print('  [^] no rewritten')
                        print('  ---- target rewritten ----')
                        print(QueryRewriter.beautify(example['q1']))
                        print('  ---- actual rewritten ----')
                        print(QueryRewriter.beautify(_q1))
                        print('  --------------------------')
            else:
                example['matched'] = 0
                example['path'] = ''
                example['rewritten'] = 0
                print('  [x] no match')
                print('  ------- original --------')
                print(QueryRewriter.beautify(example['q0']))
                print('  ---- R' + str(example['id']) + ' ----')
                corresponding_rule = next(x for x in populated_rules if x['id'] == example['id'])
                print(QueryRewriter.beautify(corresponding_rule['pattern']))
                print('  --------------------------')
        except Exception as e:
            print('====>  Evaluating rules on example [' + str(example['id']) + '] failed!')
            print(e)
            example['matched'] = 0
            example['path'] = ''
            example['rewritten'] = 0
            pass
    
    print('(3) End profiling rules on the examples.')
    print('=====================================================')
    print('    # of examples: ' + str(len(examples)))
    print('    # of rules populated: ' + str(len(populated_rules)))
    print('    # of matched examples: ' + str(matched))
    print('    # of rewritten examples: ' + str(rewritten))
    print('=====================================================')
    print('id, name, matched, path, rewritten')
    for example in examples:
        print(', '.join([str(example['id']), example['name'], str(example['matched']), example['path'], str(example['rewritten'])]))


    return len(examples), len(populated_rules), matched, rewritten

    # Zoom into common rule examples
    # 
    # print('(1.2) Filter examples by only keeping common rule examples')
    # print('Before filter: # of examples: ' + str(len(examples)))
    # examples = [example for example in examples if example['id'] in common_rules_example_ids]
    # print('After filter: # of examples: ' + str(len(examples)))

    # print('(4) Start populating common rules ...')
    # populated_common_rules = []
    # cnt_failed_populating_common_rule = 0
    # failed_populating_common_rule_example_ids = set()
    # for rule in common_rules:
    #     try:
    #         # populate rule details
    #         rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    #         rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
    #         rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
    #         rule['pattern_json'] = json.loads(rule['pattern_json'])
    #         rule['constraints_json'] = json.loads(rule['constraints_json'])
    #         rule['rewrite_json'] = json.loads(rule['rewrite_json'])
    #         rule['actions_json'] = json.loads(rule['actions_json'])
    #         rule['mapping'] = json.loads(rule['mapping'])
    #         populated_common_rules.append(rule)
    #     except Exception as e:
    #         print('====>  Parsing rule [' + str(rule['id']) + '] failed!')
    #         print(e)
    #         cnt_failed_populating_common_rule += 1
    #         failed_populating_common_rule_example_ids.add(rule['id'])
    #         pass
    # print('(4) End populating common rules.')
    # print('=====================================================')
    # print('    # of common rules populated: ' + str(len(populated_common_rules)))
    # print('    # of failed populating common rules: ' + str(cnt_failed_populating_common_rule))
    # print('=====================================================')

    # print('(4.1) Filter examples by removing source examples that failed to populate common rules')
    # print('Before filter: # of examples: ' + str(len(examples)))
    # examples = [example for example in examples if example['id'] not in failed_populating_common_rule_example_ids]
    # print('After filter: # of examples: ' + str(len(examples)))

    # print('(5) Start profiling common rules on the common rule examples ...')
    # # count the succesfully matched and succesfully rewritten
    # #
    # matched = 0
    # rewritten = 0
    # for example in examples:

    #     print('====>  Evaluating rules on example [' + str(example['id']) + '] ...')

    #     try:
    #         _q1, _path = QueryRewriter.rewrite(example['q0'], populated_common_rules)
            
    #         if len(_path) > 0:
    #                 matched += 1
    #                 if mo_format(mo_parse(example['q1'])) == mo_format(mo_parse(_q1)):
    #                     rewritten += 1
    #     except Exception as e:
    #         print('====>  Evaluating rules on example [' + str(example['id']) + '] failed!')
    #         print(e)
    #         pass
    
    # print('(5) End profiling common rules on the common rule examples.')

    # return len(examples), len(populated_common_rules), matched, rewritten


# filter examples
#   remove examples that cannot be parsed using mo_sql_parsing
#
def filter_examples(examples: list) -> dict:

    filtered_examples = []

    print('Start filtering the given examples that can be parsed using mo_sql_parsing ...')

    cnt_parsing_failed = 0
    for example in examples:
        parsing_failed = False
        # try parsing the original query
        #
        try:
            query_ast = mo_parse(example['q0'])
        except Exception as e:
            print('====>  Parsing example [' + str(example['id']) + ']->Q0 failed!')
            print(example['q0'])
            print('---- Exception ----')
            print(e)
            parsing_failed = True
        # try parsing the rewritten query
        #
        try:
            query_ast = mo_parse(example['q1'])
        except Exception as e:
            print('====>  Parsing example [' + str(example['id']) + ']->Q1 failed!')
            print(example['q1'])
            print('---- Exception ----')
            print(e)
            parsing_failed = True
        if not parsing_failed:
            filtered_examples.append(example)
        else:
            cnt_parsing_failed += 1
    print('End filtering the given examples that can be parsed using mo_sql_parsing.')
    print('=====================================================')
    print('    # of examples failed parsing: ' + str(cnt_parsing_failed))
    print('    # of examples fitered: ' + str(len(filtered_examples)))
    print('=====================================================')
    
    return filtered_examples


# Read a given examples_file
#   assume the csv file has four columns (with header): id, name, q1, q2
#
def read_examples_file(examples_file: str):
    examples = []
    with open('experiments/' + examples_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        # skip head
        next(csv_reader, None)
        for row in csv_reader:
            examples.append({
                'id': int(row[0]),
                'name': row[1],
                'q0': row[2],
                'q1': row[3]
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
    examples_file = 'calcite_tests.csv'

    # read examples file
    #   assume the csv file has four columns (with header): id, name, q1, q2
    #
    examples = read_examples_file(examples_file)

    # filter examples that can be parsed using mo_sql_parsing
    #
    examples = filter_examples(examples)
    
    # evaluate generalize_rules on the examples files
    #
    cnt_examples, cnt_rules, cnt_matched, cnt_rewritten  = evaluate_generalize_rules(examples)
    
    # outpout timings
    #
    print()
    print('=====================================================')
    print('    Evaluating Result [' + examples_file + ']')
    print('=====================================================')
    print('Total # of examples: ' + str(cnt_examples))
    print('Total # of rules populated: ' + str(cnt_rules))
    print('Total # of matched examples: ' + str(cnt_matched))
    print('Total # of rewritten examples: ' + str(cnt_rewritten))
