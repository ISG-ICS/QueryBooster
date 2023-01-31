import csv
import sys
# append the current directory
sys.path.append(".")
# append the parent directory
sys.path.append("..")
from core.rule_generator import RuleGenerator
from tests.string_util import StringUtil

MAX_KHN_K = 10
MAX_KPN_K = 100


# Profile RuleGenerator.suggest_rules()
#   exp - explore_candidates approach: 'bf', 'khn', 'kpn'
#   examples - list of input rewriting examples
#   optimal_rules - list of optimal rules for the given examples
#
def profile_suggest_rules(exp: str, examples: list, optimal_rules: list) -> dict:
    if exp == 'bf':
        return profile_suggest_rules_bf(examples, optimal_rules)
    elif exp == 'khn':
        return profile_suggest_rules_khn(examples, optimal_rules)
    elif exp == 'kpn':
        return profile_suggest_rules_kpn(examples, optimal_rules)
    else:
        return {'success': False}


# Profile RuleGenerator.sugest_rules(exp='bf')
#
def profile_suggest_rules_bf(examples: list, optimalRules: list) -> dict:

    print('Start profiling suggest rules using Brute-Force ...')

    profile = {}

    # suggest rules from examples using exp='bf'
    #
    suggestRules = RuleGenerator.suggest_rules(examples, exp='bf', profile=profile)

    # verify suggestRules == optimalRules
    #
    profile['success'] = verify_rules(suggestRules, optimalRules)

    print('End profiling suggest rules using Brute-Force ...')

    return profile


# Profile RuleGenerator.sugest_rules(exp='khn')
#   Start with k=1, and increase k by 1 each time, until the suggestRules are optimal
#
def profile_suggest_rules_khn(examples: list, optimalRules: list) -> dict:

    print('Start profiling suggest rules using K-Hop Neighbors ...')

    for k in range(1, MAX_KHN_K + 1, 1):

        print('    Try K = ' + str(k) + ' ...')

        profile = {}

        # suggest rules from examples using exp='khn'
        #
        suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=k, profile=profile)

        # verify suggestRules == optimalRules
        #
        profile['success'] = verify_rules(suggestRules, optimalRules)
        if profile['success']:

            print('End profiling suggest rules using K-Hop Neighbors ... Optimal Rules Found!')

            return profile
    
    print('End profiling suggest rules using K-Hop Neighbors ... Optimal Rules Not Found! Reached Max K!')

    return profile


# Profile RuleGenerator.sugest_rules(exp='kpn')
#   Start with k=5, and increase k by 5 each time, until the suggestRules are optimal
#
def profile_suggest_rules_kpn(examples: list, optimalRules: list) -> dict:

    print('Start profiling suggest rules using K-Promising Neighbors ...')

    for k in range(5, MAX_KPN_K + 5, 5):

        print('    Try K = ' + str(k) + ' ...')

        profile = {}

        # suggest rules from examples using exp='khn'
        #
        suggestRules = RuleGenerator.suggest_rules(examples, exp='kpn', k=k, profile=profile)

        # verify suggestRules == optimalRules
        #
        profile['success'] = verify_rules(suggestRules, optimalRules)
        if profile['success']:

            print('End profiling suggest rules using K-Promising Neighbors ... Optimal Rules Found!')

            return profile
    
    print('End profiling suggest rules using K-Promising Neighbors ... Optimal Rules Not Found! Reached Max K!')

    return profile


# Verify if the given suggestRules are the same as the optimalRules
#
def verify_rules(suggestRules: list, optimalRules: list) -> bool:
    # check length
    #
    if len(suggestRules) != len(optimalRules):
        return False
    
    # check patterns
    #
    suggestRulesPatterns = [StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) for suggestRule in suggestRules]
    optimalRulesPatterns = [StringUtil.strim(RuleGenerator._fingerPrint(optimalRule['pattern'])) for optimalRule in optimalRules]
    if set(suggestRulesPatterns) != set(optimalRulesPatterns):
        return False
    
    # check rewrites
    #
    suggestRulesRewrites = [StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) for suggestRule in suggestRules]
    optimalRulesRewrites = [StringUtil.strim(RuleGenerator._fingerPrint(optimalRule['rewrite'])) for optimalRule in optimalRules]
    if set(suggestRulesRewrites) != set(optimalRulesRewrites):
        return False
    
    # success
    #
    return True


# Read a given examples_file
#
def read_examples_file(examples_file: str, num_optimal_rules: int):
    examples = []
    optimal_rules = []
    with open('experiments/' + examples_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        # skip head
        next(csv_reader, None)
        row_num = 1
        for row in csv_reader:
            if row_num <= num_optimal_rules:
                optimal_rules.append({
                    'pattern': row[0],
                    'rewrite': row[1]
                })
            else:
                examples.append({
                    'q0': row[0],
                    'q1': row[1]
                })
            row_num += 1
    
    print()
    print('Reading examples file [' + examples_file + '] done!')
    print('=====================================================')
    print('    Examples')
    print('=====================================================')
    print(examples)
    print('=====================================================')
    print('    Optimal Rules')
    print('=====================================================')
    print(optimal_rules)

    return examples, optimal_rules


if __name__ == '__main__':

    exps = ['bf', 'khn', 'kpn']

    num_optimal_rules = 1
    examples_files = ['tweets_cast_2q.csv', 'tweets_cast_3q.csv', 'tweets_cast_4q.csv', 'tweets_cast_5q.csv']
    # examples_files = ['tweets_cast_5q.csv']

    # read examples files
    #
    examples_lists, optimal_rules_lists = [], []
    for examples_file in examples_files:
        examples, optimal_rules = read_examples_file(examples_file, num_optimal_rules)
        examples_lists.append(examples)
        optimal_rules_lists.append(optimal_rules)
    
    # profile suggest_rules on the examples files
    #
    examples_file_profiles = []
    for i in range(len(examples_files)):
        examples_file = examples_files[i]
        examples = examples_lists[i]
        optimal_rules = optimal_rules_lists[i]
        print('Start on examples file [' + examples_file + '] ...')
        profiles = {}
        for exp in exps:
            profiles[exp] = profile_suggest_rules(exp, examples, optimal_rules)
        examples_file_profiles.append(profiles)
    
    # outpout timings
    #
    print()
    print('=====================================================')
    print('    Timings')
    print('=====================================================')
    print('Examples File, ' + ', '.join(exps))
    for i in range(len(examples_files)):
        examples_file = examples_files[i]
        profiles = examples_file_profiles[i]
        timings = []
        for exp in exps:
            profile = profiles[exp]
            if profile['success']:
                timings.append(profile['time'])
            else:
                timings.append(-1.0)
        print(examples_file + ', ' + ', '.join(format(t, "10.3f") for t in timings))
    
    # outpout counts of iterations
    #
    print()
    print('=====================================================')
    print('    Counts of Iterations')
    print('=====================================================')
    print('Examples File, ' + ', '.join(exps))
    for i in range(len(examples_files)):
        examples_file = examples_files[i]
        profiles = examples_file_profiles[i]
        cnts_iterations = []
        for exp in exps:
            profile = profiles[exp]
            cnts_iterations.append(profile['cnt_iterations'])
        print(examples_file + ', ' + ', '.join(format(x, "10.0f") for x in cnts_iterations))
    
    # outpout total counts of candidates
    #
    print()
    print('=====================================================')
    print('    Total Counts of Candidates')
    print('=====================================================')
    print('Examples File, ' + ', '.join(exps))
    for i in range(len(examples_files)):
        examples_file = examples_files[i]
        profiles = examples_file_profiles[i]
        total_candidates = []
        for exp in exps:
            profile = profiles[exp]
            total_candidates.append(sum(profile['cnts_candidates']))
        print(examples_file + ', ' + ', '.join(format(x, "10.0f") for x in total_candidates))
    
    # outpout max counts of candidates
    #
    print()
    print('=====================================================')
    print('    Max Counts of Candidates')
    print('=====================================================')
    print('Examples File, ' + ', '.join(exps))
    for i in range(len(examples_files)):
        examples_file = examples_files[i]
        profiles = examples_file_profiles[i]
        max_candidates = []
        for exp in exps:
            profile = profiles[exp]
            max_candidates.append(max(profile['cnts_candidates']))
        print(examples_file + ', ' + ', '.join(format(x, "10.0f") for x in max_candidates))
    
    # outpout min counts of candidates
    #
    print()
    print('=====================================================')
    print('    Min Counts of Candidates')
    print('=====================================================')
    print('Examples File, ' + ', '.join(exps))
    for i in range(len(examples_files)):
        examples_file = examples_files[i]
        profiles = examples_file_profiles[i]
        min_candidates = []
        for exp in exps:
            profile = profiles[exp]
            min_candidates.append(min(profile['cnts_candidates']))
        print(examples_file + ', ' + ', '.join(format(x, "10.0f") for x in min_candidates))
    