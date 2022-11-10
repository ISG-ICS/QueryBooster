import csv
import json
import mo_sql_parsing as mosql
import sys
# append the current directory
sys.path.append(".")
# append the parent directory
sys.path.append("..")
from core.rule_generator import RuleGenerator
from core.query_rewriter import QueryRewriter
from tests.string_util import StringUtil


if __name__ == '__main__':
    rewriting_examples_file = 'examples/wetune.csv'
    rewriting_examples = []
    with open(rewriting_examples_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        next(csv_reader, None)
        for row in csv_reader:
            rewriting_examples.append({
                'q0': row[0],
                'q1': row[1]
            })
    examples_count = len(rewriting_examples)

    print('=====================================================')
    print('Test Rule Generations on rewriting examples in file: [' + rewriting_examples_file + "]")
    print('=====================================================')
    
    success_count = 0
    for index, rewriting_example in enumerate(rewriting_examples):

        print('=====================================')
        print('Testing pair #' + str(index + 1) + ':')

        # example pair
        q0 = rewriting_example['q0']
        q1 = rewriting_example['q1']

        # generate rule
        rule = RuleGenerator.generate_general_rule(q0, q1)

        print('---------- Generated Rule -----------')
        print(QueryRewriter.beautify(rule['pattern']))
        print('               ||')
        print('               \/')
        print(QueryRewriter.beautify(rule['rewrite']))

        # hydrate rule for QueryRewriter
        rule['id'] = -1
        rule['pattern_json'] = json.loads(rule['pattern_json'])
        rule['constraints_json'] = json.loads(rule['constraints_json'])
        rule['rewrite_json'] = json.loads(rule['rewrite_json'])
        rule['actions_json'] = json.loads(rule['actions_json'])

        # rewrite example using generated rule
        _q1, _ = QueryRewriter.rewrite(q0, [rule])

        print('---------- Rewriten _Q1 -------------')
        print(QueryRewriter.beautify(_q1))

        print('------------ Test Result ------------')
        if mosql.format(mosql.parse(q1)) == mosql.format(mosql.parse(_q1)):
            print('   Success !!!')
            success_count += 1
        else:
            print('   Failed ???')
            print('------------ Corret Q1 --------------')
            print(QueryRewriter.beautify(q1))
    
    print('=====================================================')
    print('Tested rewriting examples:    ' + str(examples_count))
    print('Successful rewritings:    ' + str(success_count ))
    print('=====================================================')
    