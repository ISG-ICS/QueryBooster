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


# Evaluate RuleGenerator.suggest_rules()
#   exp - explore_candidates approach: 'khn', 'mpn'
#   ks_or_ms - the list of varied k or m values for the corresponding explore_candidates approach
#   examples - list of input rewriting examples
#   tests -  list of testing rewriting pairs
#
def evaluate_suggest_rules(exp: str, ks_or_ms: list, examples: list, tests: list) -> dict:
    if exp == 'khn':
        return evaluate_suggest_rules_khn(examples, ks=ks_or_ms, tests=tests)
    elif exp == 'mpn':
        return evaluate_suggest_rules_mpn(examples, ms=ks_or_ms, tests=tests)
    else:
        return None


# Evaluate RuleGenerator.sugest_rules(exp='khn')
#   Vary k value in the given ks list
#
def evaluate_suggest_rules_khn(examples: list, ks: list, tests: list) -> dict:

    print('Start evaluating suggest rules using K-Hop Neighbors ...')

    profiles = {}

    for k in ks:

        print('    Evaluating K = ' + str(k) + ' ...')

        profile = {}

        # suggest rules from examples using exp='khn'
        #
        suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=k, profile=profile)

        # add description length to the profile
        #
        dl = 0
        for index, rule in enumerate(suggestRules):
            dl += RuleGenerator.description_length(rule)
            # populate rule id
            rule['id'] = index + 1
            print('    ---------- R' + str(rule['id']) + ' -----------')
            print(QueryRewriter.beautify(rule['pattern']))
            print('               ||')
            print('               \/')
            print(QueryRewriter.beautify(rule['rewrite']))
        profile['description_length'] = dl

        print('    ---------- -- -----------')

        # add counts of matched and recalled to the profile
        #
        if len(tests) > 0:
            matched = 0
            recalled = 0
            for test in tests:
                _q1, _ = QueryRewriter.rewrite(test['q0'], suggestRules)
                if mo_format(mo_parse(test['q0'])) != mo_format(mo_parse(_q1)):
                    matched += 1
                    if mo_format(mo_parse(test['q1'])) == mo_format(mo_parse(_q1)):
                        recalled += 1
            profile['matched'] = matched
            profile['recalled'] = recalled

        # add the entry (k -> profile) to the result
        #
        profiles[k] = profile
    
    print('End evaluating suggest rules using K-Hop Neighbors ...')

    return profiles


# Evaluate RuleGenerator.sugest_rules(exp='mpn')
#   Vary m value in the given ms list
#
def evaluate_suggest_rules_mpn(examples: list, ms: list, tests: list) -> dict:

    print('Start evaluating suggest rules using M-Promising Neighbors ...')

    profiles = {}

    for m in ms:

        print('    Evaluating M = ' + str(m) + ' ...')

        profile = {}

        # suggest rules from examples using exp='mpn'
        #
        suggestRules = RuleGenerator.suggest_rules(examples, exp='mpn', m=m, profile=profile)

        # add description length to the profile
        #
        dl = 0
        for index, rule in enumerate(suggestRules):
            dl += RuleGenerator.description_length(rule)
            # populate rule id
            rule['id'] = index + 1
            # populate rule details
            rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
            rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
            rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
            rule['pattern_json'] = json.loads(rule['pattern_json'])
            rule['constraints_json'] = json.loads(rule['constraints_json'])
            rule['rewrite_json'] = json.loads(rule['rewrite_json'])
            rule['actions_json'] = json.loads(rule['actions_json'])
            rule['mapping'] = json.loads(rule['mapping'])
            print('    ---------- R' + str(rule['id']) + ' -----------')
            print(QueryRewriter.beautify(rule['pattern']))
            print('               ||')
            print('               \/')
            print(QueryRewriter.beautify(rule['rewrite']))
        profile['description_length'] = dl

        print('    ---------- -- -----------')

        # add counts of matched and recalled to the profile
        #
        if len(tests) > 0:
            matched = 0
            recalled = 0
            for test in tests:
                _q1, _ = QueryRewriter.rewrite(test['q0'], suggestRules)
                if mo_format(mo_parse(test['q0'])) != mo_format(mo_parse(_q1)):
                    matched += 1
                    if mo_format(mo_parse(test['q1'])) == mo_format(mo_parse(_q1)):
                        recalled += 1
            profile['matched'] = matched
            profile['recalled'] = recalled

        # add the entry (k -> profile) to the result
        #
        profiles[m] = profile
    
    print('End evaluating suggest rules using M-Promising Neighbors ...')

    return profiles


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
    # ks_or_ms = [10, 20, 30, 40, 50, 60]
    # exp = 'mpn'
    # examples_file = 'Train_Remove_1Useless_InnerJoin.csv'
    # test_file = 'Test_Remove_1Useless_InnerJoin.csv'

    # Exp-2
    #
    ks_or_ms = [10, 20, 30, 40, 50, 60]
    exp = 'mpn'
    examples_file = 'Train_Remove_1Useless_InnerJoin_Agg.csv'
    test_file = 'Test_Remove_1Useless_InnerJoin_Agg.csv'

    # read examples file
    #
    examples = read_examples_file(examples_file)

    # read test file
    #
    tests = read_examples_file(test_file)
    
    # profile suggest_rules on the examples files
    #
    profiles  = evaluate_suggest_rules(exp, ks_or_ms, examples, tests)
    
    # outpout timings
    #
    print()
    print('=====================================================')
    print('    Evaluating Result [' + exp + ']')
    print('=====================================================')
    print('K or M, ' + ', '.join(['Time', 'Description_length', 'Cnt_iterations', 'Sum_cnt_candidates', 'Max_cnt_candidates', 'Min_cnt_candidates', 'Matched', 'Recalled']))
    for k_or_m, profile in profiles.items():
        time = profile['time']
        description_length = profile['description_length']
        cnt_iterations = profile['cnt_iterations']
        cnts_candidates = profile['cnts_candidates']
        sum_cnt_candidates = sum(cnts_candidates)
        max_cnt_candidates = max(cnts_candidates)
        min_cnt_candidates = min(cnts_candidates)
        matched = profile['matched']
        recalled = profile['recalled']
        print(str(k_or_m) + ', ' + ', '.join(format(t, "10.3f") for t in [time, description_length, cnt_iterations, sum_cnt_candidates, max_cnt_candidates, min_cnt_candidates, matched, recalled]))
    
