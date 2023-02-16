import csv
import sys
# append the current directory
sys.path.append(".")
# append the parent directory
sys.path.append("..")
from core.query_rewriter import QueryRewriter
from core.rule_generator import RuleGenerator


# Evaluate RuleGenerator.suggest_rules()
#   exp - explore_candidates approach: 'khn', 'mpn'
#   ks_or_ms - the list of varied k or m values for the corresponding explore_candidates approach
#   examples - list of input rewriting examples
#
def evaluate_suggest_rules(exp: str, ks_or_ms: list, examples: list) -> dict:
    if exp == 'khn':
        return evaluate_suggest_rules_khn(examples, ks=ks_or_ms)
    elif exp == 'mpn':
        return evaluate_suggest_rules_mpn(examples, ms=ks_or_ms)
    else:
        return None


# Evaluate RuleGenerator.sugest_rules(exp='khn')
#   Vary k value in the given ks list
#
def evaluate_suggest_rules_khn(examples: list, ks: list) -> dict:

    print('Start evaluating suggest rules using K-Hop Neighbors ...')

    profiles = {}

    for k in ks:

        print('    Evaluating K = ' + str(k) + ' ...')

        profile = {}

        # suggest rules from examples using exp='khn'
        #
        suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=k, profile=profile)

        # add description length to the profile
        dl = 0
        for index, rule in enumerate(suggestRules):
            dl += RuleGenerator.description_length(rule)
            print('    ---------- R' + str(index + 1) + ' -----------')
            print(QueryRewriter.beautify(rule['pattern']))
            print('               ||')
            print('               \/')
            print(QueryRewriter.beautify(rule['rewrite']))
        profile['description_length'] = dl

        print('    ---------- -- -----------')

        # add the entry (k -> profile) to the result
        profiles[k] = profile
    
    print('End evaluating suggest rules using K-Hop Neighbors ...')

    return profiles


# Evaluate RuleGenerator.sugest_rules(exp='mpn')
#   Vary m value in the given ms list
#
def evaluate_suggest_rules_mpn(examples: list, ms: list) -> dict:

    print('Start evaluating suggest rules using K-Promising Neighbors ...')

    profiles = {}

    for m in ms:

        print('    Evaluating M = ' + str(m) + ' ...')

        profile = {}

        # suggest rules from examples using exp='mpn'
        #
        suggestRules = RuleGenerator.suggest_rules(examples, exp='mpn', m=m, profile=profile)

        # add description length to the profile
        dl = 0
        for index, rule in enumerate(suggestRules):
            dl += RuleGenerator.description_length(rule)
            print('    ---------- R' + str(index + 1) + ' -----------')
            print(QueryRewriter.beautify(rule['pattern']))
            print('               ||')
            print('               \/')
            print(QueryRewriter.beautify(rule['rewrite']))
        profile['description_length'] = dl

        print('    ---------- -- -----------')

        # add the entry (m -> profile) to the result
        profiles[m] = profile
    
    print('End evaluating suggest rules using K-Promising Neighbors ...')

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

    ks_or_ms = [20, 40, 80, 160]
    exp = 'mpn'

    examples_file = 'join_to_filter.csv'

    # read examples file
    #
    examples = read_examples_file(examples_file)
    
    # profile suggest_rules on the examples files
    #
    profiles  = evaluate_suggest_rules(exp, ks_or_ms, examples)
    
    # outpout timings
    #
    print()
    print('=====================================================')
    print('    Evaluating Result [' + exp + ']')
    print('=====================================================')
    print('K or M, ' + ', '.join(['Time', 'Description_length', 'Cnt_iterations', 'Sum_cnt_candidates', 'Max_cnt_candidates', 'Min_cnt_candidates']))
    for k_or_m, profile in profiles.items():
        time = profile['time']
        description_length = profile['description_length']
        cnt_iterations = profile['cnt_iterations']
        cnts_candidates = profile['cnts_candidates']
        sum_cnt_candidates = sum(cnts_candidates)
        max_cnt_candidates = max(cnts_candidates)
        min_cnt_candidates = min(cnts_candidates)
        print(str(k_or_m) + ', ' + ', '.join(format(t, "10.3f") for t in [time, description_length, cnt_iterations, sum_cnt_candidates, max_cnt_candidates, min_cnt_candidates]))
    
