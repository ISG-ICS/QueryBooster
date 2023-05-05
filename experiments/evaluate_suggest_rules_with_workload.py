import csv
import sys
# append the current directory
sys.path.append(".")
# append the parent directory
sys.path.append("..")
from core.query_rewriter import QueryRewriter
from core.rule_generator import RuleGenerator


K = 3
M = 30


# Evaluate RuleGenerator.suggest_rules()
#   exp - explore_candidates approach: 'khn', 'mpn'
#   betas - the list of varied beta values
#   examples - list of input rewriting examples
#   workload -  list of queries
#
def evaluate_suggest_rules(exp: str, betas: list, examples: list, workload: list) -> dict:
    if exp == 'khn':
        return evaluate_suggest_rules_khn(examples, betas=betas, workload=workload)
    elif exp == 'mpn':
        return evaluate_suggest_rules_mpn(examples, betas=betas, workload=workload)
    else:
        return None


# Evaluate RuleGenerator.sugest_rules(exp='khn')
#   Vary beta value in the given betas list
#
def evaluate_suggest_rules_khn(examples: list, betas: list, workload: list) -> dict:

    print('Start evaluating suggest rules using K-Hop Neighbors ...')

    profiles = {}

    for beta in betas:

        print('    Evaluating Beta = ' + str(beta) + ' ...')

        profile = {}

        # suggest rules from examples using exp='khn'
        #
        suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=K, profile=profile, workload=workload, beta=beta)

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

        # add total query cost in workload to the profile
        #
        profile['total_cost'] = 0.0
        if workload and len(workload) > 0:
            total_cost = sum(RuleGenerator.query_cost(q, suggestRules) for q in workload)
            profile['total_cost'] = total_cost

        # add the entry (beta -> profile) to the result
        #
        profiles[beta] = profile
    
    print('End evaluating suggest rules using K-Hop Neighbors ...')

    return profiles


# Evaluate RuleGenerator.sugest_rules(exp='mpn')
#   Vary beta value in the given betas list
#
def evaluate_suggest_rules_mpn(examples: list, betas: list, workload: list) -> dict:

    print('Start evaluating suggest rules using M-Promising Neighbors ...')

    profiles = {}

    for beta in betas:

        print('    Evaluating Beta = ' + str(beta) + ' ...')

        profile = {}

        # suggest rules from examples using exp='mpn'
        #
        suggestRules = RuleGenerator.suggest_rules(examples, exp='mpn', m=M, profile=profile, workload=workload, beta=beta)

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

        # add total query cost in workload to the profile
        #
        profile['total_cost'] = 0.0
        if workload and len(workload) > 0:
            total_cost = sum(RuleGenerator.query_cost(q, suggestRules) for q in workload)
            profile['total_cost'] = total_cost

        # add the entry (beta -> profile) to the result
        #
        profiles[beta] = profile
    
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


# Read a given workload_file
#
def read_workload_file(workload_file: str):
    queries = []
    with open('experiments/' + workload_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        # skip head
        next(csv_reader, None)
        for row in csv_reader:
            queries.append(row[0])
    
    print()
    print('Reading workload file [' + workload_file + '] done!')
    print('=====================================================')
    print('    Queries')
    print('=====================================================')
    print(queries)

    return queries


if __name__ == '__main__':

    # Exp-1: Vary beta
    #  
    # betas = [1.0, 0.75, 0.5, 0.25, 0.0]
    # M = 30
    # exp = 'mpn'
    # examples_files = ['tweets2_cast_4q.csv']
    # workload_files = ['tweets2_workload_5q.csv']

    # Exp-2: Vary # of queries in workload
    #  
    # betas = [0.75]
    # M = 30
    # exp = 'mpn'
    # examples_files = ['tweets2_cast_4q.csv']
    # workload_files = ['tweets2_workload_4q.csv', 'tweets2_workload_3q.csv', 'tweets2_workload_2q.csv']

    # Exp-3: Vary # of examples
    #  
    betas = [0.75]
    M = 30
    exp = 'mpn'
    examples_files = ['tweets2_cast_1q.csv', 'tweets2_cast_2q.csv', 'tweets2_cast_3q.csv']
    workload_files = ['tweets2_workload_5q.csv']

    for examples_file in examples_files:
        # read examples file
        #
        examples = read_examples_file(examples_file)

        for workload_file in workload_files:
            # read workload file
            #
            workload = read_workload_file(workload_file)
            
            # profile suggest_rules on the examples files with given workload
            #
            profiles = evaluate_suggest_rules(exp, betas, examples, workload)
            
            # outpout timings
            #
            print()
            print('=====================================================')
            print('    Evaluating Result [' + examples_file + '][' + workload_file + ']')
            print('=====================================================')
            print('Beta, ' + ', '.join(['Time', 'Description_length', 'Cnt_iterations', 'Sum_cnt_candidates', 'Max_cnt_candidates', 'Min_cnt_candidates', 'Total_Cost']))
            for beta, profile in profiles.items():
                time = profile['time']
                description_length = profile['description_length']
                cnt_iterations = profile['cnt_iterations']
                cnts_candidates = profile['cnts_candidates']
                sum_cnt_candidates = sum(cnts_candidates)
                max_cnt_candidates = max(cnts_candidates)
                min_cnt_candidates = min(cnts_candidates)
                total_cost = profile['total_cost']
                print(format(beta, "1.2f") + ', ' + ', '.join(format(t, "10.3f") for t in [time, description_length, cnt_iterations, sum_cnt_candidates, max_cnt_candidates, min_cnt_candidates, total_cost]))
    
