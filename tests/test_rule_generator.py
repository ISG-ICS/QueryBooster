from core.rule_generator import RuleGenerator
from core.rule_parser import RuleParser
import json
import mo_sql_parsing as mosql
from .string_util import StringUtil


def test_minDiffSubtree_1():
    q0 = "SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
    q1 = "SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"

    # Mock the logic inside generate_seed_rule()
    #
    # Extend partial SQL statement to full SQL statement
    #    for the sake of sql parser
    #
    q0, q0Scope = RuleParser.extendToFullSQL(q0)
    q1, q1Scope = RuleParser.extendToFullSQL(q1)

    # Parse full SQL statement into AST json
    #
    q0ASTJson = mosql.parse(q0)
    q1ASTJson = mosql.parse(q1)

    # Find minimum different subtrees between two AST jsons
    #
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
        q0ASTJson, q1ASTJson)

    assert patternASTJson == {'cast': ['created_at', {'date': {}}]}
    assert rewriteASTJson == 'created_at'


def test_minDiffSubtree_2():
    q0 = "CAST(created_at AS DATE)"
    q1 = "created_at"

    # Mock the logic inside generate_seed_rule()
    #
    # Extend partial SQL statement to full SQL statement
    #    for the sake of sql parser
    #
    q0, q0Scope = RuleParser.extendToFullSQL(q0)
    q1, q1Scope = RuleParser.extendToFullSQL(q1)

    # Parse full SQL statement into AST json
    #
    q0ASTJson = mosql.parse(q0)
    q1ASTJson = mosql.parse(q1)

    # Find minimum different subtrees between two AST jsons
    #
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
        q0ASTJson, q1ASTJson)

    assert patternASTJson == {'cast': ['created_at', {'date': {}}]}
    assert rewriteASTJson == 'created_at'


def test_minDiffSubtree_3():
    q0 = "SELECT CAST(state_name AS TEXT)"
    q1 = "SELECT state_name"

    # Mock the logic inside generate_seed_rule()
    #
    # Extend partial SQL statement to full SQL statement
    #    for the sake of sql parser
    #
    q0, q0Scope = RuleParser.extendToFullSQL(q0)
    q1, q1Scope = RuleParser.extendToFullSQL(q1)

    # Parse full SQL statement into AST json
    #
    q0ASTJson = mosql.parse(q0)
    q1ASTJson = mosql.parse(q1)

    # Find minimum different subtrees between two AST jsons
    #
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
        q0ASTJson, q1ASTJson)

    assert patternASTJson == {'cast': ['state_name', {'text': {}}]}
    assert rewriteASTJson == 'state_name'


def test_minDiffSubtree_4():
    q0 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(LOWER(text), 'iphone') > 0)
         GROUP  BY 2;
    '''
    q1 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  text ILIKE '%iphone%'
         GROUP  BY 2;
    '''

    # Mock the logic inside generate_seed_rule()
    #
    # Extend partial SQL statement to full SQL statement
    #    for the sake of sql parser
    #
    q0, q0Scope = RuleParser.extendToFullSQL(q0)
    q1, q1Scope = RuleParser.extendToFullSQL(q1)

    # Parse full SQL statement into AST json
    #
    q0ASTJson = mosql.parse(q0)
    q1ASTJson = mosql.parse(q1)

    # Find minimum different subtrees between two AST jsons
    #
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
        q0ASTJson, q1ASTJson)

    assert patternASTJson == {
        'gt': [{'strpos': [{'lower': 'text'}, {'literal': 'iphone'}]}, 0]}
    assert rewriteASTJson == {'ilike': ['text', {'literal': '%iphone%'}]}


def test_minDiffSubtree_5():
    q0 = "STRPOS(LOWER(text), 'iphone') > 0"
    q1 = "text ILIKE '%iphone%'"

    # Mock the logic inside generate_seed_rule()
    #
    # Extend partial SQL statement to full SQL statement
    #    for the sake of sql parser
    #
    q0, q0Scope = RuleParser.extendToFullSQL(q0)
    q1, q1Scope = RuleParser.extendToFullSQL(q1)

    # Parse full SQL statement into AST json
    #
    q0ASTJson = mosql.parse(q0)
    q1ASTJson = mosql.parse(q1)

    # Find minimum different subtrees between two AST jsons
    #
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
        q0ASTJson, q1ASTJson)

    assert patternASTJson == {
        'gt': [{'strpos': [{'lower': 'text'}, {'literal': 'iphone'}]}, 0]}
    assert rewriteASTJson == {'ilike': ['text', {'literal': '%iphone%'}]}


def test_generate_seed_rule_1():
    q0 = "SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
    q1 = "SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"

    gen_rule = RuleGenerator.generate_seed_rule(q0, q1)

    assert gen_rule['pattern'] == 'CAST(created_at AS DATE)'
    assert gen_rule['rewrite'] == 'created_at'


def test_generate_seed_rule_2():
    q0 = "CAST(created_at AS DATE)"
    q1 = "created_at"

    gen_rule = RuleGenerator.generate_seed_rule(q0, q1)

    assert gen_rule['pattern'] == 'CAST(created_at AS DATE)'
    assert gen_rule['rewrite'] == 'created_at'


def test_generate_seed_rule_3():
    q0 = "SELECT CAST(state_name AS TEXT)"
    q1 = "SELECT state_name"

    gen_rule = RuleGenerator.generate_seed_rule(q0, q1)

    assert gen_rule['pattern'] == 'CAST(state_name AS TEXT)'
    assert gen_rule['rewrite'] == 'state_name'


def test_generate_seed_rule_4():
    q0 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(LOWER(text), 'iphone') > 0)
         GROUP  BY 2;
    '''
    q1 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  text ILIKE '%iphone%'
         GROUP  BY 2;
    '''

    gen_rule = RuleGenerator.generate_seed_rule(q0, q1)

    assert gen_rule['pattern'] == "STRPOS(LOWER(text), 'iphone') > 0"
    assert gen_rule['rewrite'] == "ILIKE(text, '%iphone%')"


def test_columns_1():
    pattern = "STRPOS(LOWER(text), 'iphone') > 0"
    rewrite = "ILIKE(text, '%iphone%')"
    columns = ["text"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_columns = RuleGenerator.columns(pattern_json, rewrite_json)
    assert set(test_columns) == set(columns)


def test_columns_2():
    pattern = 'CAST(state_name AS TEXT)'
    rewrite = 'state_name'
    columns = ["state_name"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_columns = RuleGenerator.columns(pattern_json, rewrite_json)
    assert set(test_columns) == set(columns)


def test_columns_3():
    pattern = '''
        select e1.name, e1.age, e2.salary
        from employee e1,
            employee e2
        where e1.id = e2.id
        and e1.age > 17
        and e2.salary  > 35000;
    '''
    rewrite = '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000;
    '''
    columns = ["name", "age", "salary", "id"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_columns = RuleGenerator.columns(pattern_json, rewrite_json)
    assert set(test_columns) == set(columns)


def test_columns_4():
    pattern = '''
        select e1.name, e1.age, e2.salary
        from employee e1,
            employee e2
        where e1.<a1> = e2.<a1>
        and e1.age > 17
        and e2.salary  > 35000;
    '''
    rewrite = '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000;
    '''
    columns = ["name", "age", "salary"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_columns = RuleGenerator.columns(pattern_json, rewrite_json)
    assert set(test_columns) == set(columns)


def test_deparse_1():

    rule = {
        'pattern': 'CAST(V1 AS DATE)',
        'rewrite': 'V1',
        'pattern_json': '{"cast": ["V1", {"date": {}}]}',
        'rewrite_json': '"V1"'
    }
    
    pattern = RuleGenerator.deparse(json.loads(rule['pattern_json']))
    assert pattern == rule['pattern']
    rewrite = RuleGenerator.deparse(json.loads(rule['rewrite_json']))
    assert rewrite == rule['rewrite']


def test_deparse_2():

    rule = {
        'pattern': "STRPOS(LOWER(V1), 'V2') > 0",
        'rewrite': "ILIKE(V1, '%V2%')",
        'pattern_json': '{"gt": [{"strpos": [{"lower": "V1"}, {"literal": "V2"}]}, 0]}',
        'rewrite_json': '{"ilike": ["V1", {"literal": "%V2%"}]}'
    }

    pattern = RuleGenerator.deparse(json.loads(rule['pattern_json']))
    assert pattern == rule['pattern']
    rewrite = RuleGenerator.deparse(json.loads(rule['rewrite_json']))
    assert rewrite == rule['rewrite']


def test_dereplaceVars_1():

    pattern = 'CAST(V1 AS DATE)'
    rewrite = 'V1'
    mapping = {'x': 'V1'}

    pattern = RuleGenerator.dereplaceVars(pattern, mapping)
    assert pattern == 'CAST(<x> AS DATE)'
    rewrite = RuleGenerator.dereplaceVars(rewrite, mapping)
    assert rewrite == '<x>'


def test_dereplaceVars_2():

    pattern = '''
        select VL1
          from V1 V2, 
               V3 V4
         where V2.V5=V4.V6
           and VL2
    '''
    rewrite = '''
        select VL1 
          from V1 V2
         where VL2
    '''
    mapping = {'x1': 'V1', 'y1': 'VL1', 'x2': 'V2', 'y2': 'VL2', 'x3': 'V3', 'x4': 'V4', 'x5': 'V5', 'x6': 'V6'}

    pattern = RuleGenerator.dereplaceVars(pattern, mapping)
    assert pattern == '''
        select <<y1>>
          from <x1> <x2>, 
               <x3> <x4>
         where <x2>.<x5>=<x4>.<x6>
           and <<y2>>
    '''
    rewrite = RuleGenerator.dereplaceVars(rewrite, mapping)
    assert rewrite == '''
        select <<y1>> 
          from <x1> <x2>
         where <<y2>>
    '''


def test_variablize_column_1():

    rule = {
        'pattern': 'CAST(created_at AS DATE)',
        'rewrite': 'created_at'
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_column(rule, 'created_at')
    assert rule['pattern'] == 'CAST(<x1> AS DATE)'
    assert rule['rewrite'] == '<x1>'


def test_variablize_column_2():

    rule = {
        'pattern': "STRPOS(LOWER(text), 'iphone') > 0",
        'rewrite': "ILIKE(text, '%iphone%')"
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_column(rule, 'text')
    assert rule['pattern'] == "STRPOS(LOWER(<x1>), 'iphone') > 0"
    assert rule['rewrite'] == "ILIKE(<x1>, '%iphone%')"


def test_variablize_column_3():

    rule = {
        'pattern': '''
            select e1.name, e1.age, e2.salary
            from employee e1,
                employee e2
            where e1.id = e2.id
            and e1.age > 17
            and e2.salary > 35000
        ''',
        'rewrite': '''
            SELECT e1.name, e1.age, e1.salary 
            FROM employee e1
            WHERE e1.age > 17
            AND e1.salary > 35000
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_column(rule, 'id')
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT e1.name, e1.age, e2.salary
            FROM employee AS e1,
                employee AS e2
            WHERE e1.<x1> = e2.<x1>
            AND e1.age > 17
            AND e2.salary > 35000
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT e1.name, e1.age, e1.salary 
            FROM employee AS e1
            WHERE e1.age > 17
            AND e1.salary > 35000
        ''')


def test_literals_1():
    pattern = "STRPOS(LOWER(text), 'iphone') > 0"
    rewrite = "ILIKE(text, '%iphone%')"
    literals = ["iphone"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_literals = RuleGenerator.literals(pattern_json, rewrite_json)
    assert set(test_literals) == set(literals)


def test_literals_2():
    pattern = '''
        select e1.name, e1.age, e2.salary
        from employee e1,
            employee e2
        where e1.id = e2.id
        and e1.age > 17
        and e2.salary > 35000;
    '''
    rewrite = '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000;
    '''
    literals = [17, 35000]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_literals = RuleGenerator.literals(pattern_json, rewrite_json)
    assert set(test_literals) == set(literals)


def test_variablize_literal_1():

    rule = {
        'pattern': "STRPOS(LOWER(text), 'iphone') > 0",
        'rewrite': "ILIKE(text, '%iphone%')"
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_literal(rule, 'iphone')
    assert rule['pattern'] == "STRPOS(LOWER(text), '<x1>') > 0"
    assert rule['rewrite'] == "ILIKE(text, '%<x1>%')"


def test_variablize_literal_2():

    rule = {
        'pattern': '''
            select e1.name, e1.age, e2.salary
            from employee e1,
                employee e2
            where e1.id = e2.id
            and e1.age > 17
            and e2.salary > 35000
        ''',
        'rewrite': '''
            SELECT e1.name, e1.age, e1.salary 
            FROM employee e1
            WHERE e1.age > 17
            AND e1.salary > 35000
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_literal(rule, 17)
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT e1.name, e1.age, e2.salary
            FROM employee AS e1,
                employee AS e2
            WHERE e1.id = e2.id
            AND e1.age > <x1>
            AND e2.salary > 35000
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT e1.name, e1.age, e1.salary 
            FROM employee AS e1
            WHERE e1.age > <x1>
            AND e1.salary > 35000
        ''')


def test_generate_rule_graph_1():
    seedRule = {
        'pattern': 'CAST(created_at AS DATE)',
        'rewrite': 'created_at'
    }

    rootRule = RuleGenerator.generate_rule_graph(seedRule)

    assert type(rootRule) is dict
    assert rootRule['pattern'] == seedRule['pattern']
    assert rootRule['rewrite'] == seedRule['rewrite']

    children = rootRule['children']

    assert len(children) == 1

    childRule = children[0]

    assert childRule['pattern'] == 'CAST(<x1> AS DATE)'
    assert childRule['rewrite'] == '<x1>'


def test_generate_rule_graph_2():
    seedRule = {
        'pattern': '''
            select e1.name, e1.age, e2.salary
            from employee e1,
                employee e2
            where e1.id = e2.id
            and e1.age > 17
            and e2.salary > 35000
        ''',
        'rewrite': '''
            SELECT e1.name, e1.age, e1.salary 
            FROM employee e1
            WHERE e1.age > 17
            AND e1.salary > 35000
        '''
    }

    rootRule = RuleGenerator.generate_rule_graph(seedRule)

    assert type(rootRule) is dict
    assert rootRule['pattern'] == seedRule['pattern']
    assert rootRule['rewrite'] == seedRule['rewrite']

    children = rootRule['children']

    assert len(children) == 6


def test_generate_rule_graph_3():
    seedRule = {
        'pattern': "STRPOS(LOWER(text), 'iphone') > 0",
        'rewrite': "ILIKE(text, '%iphone%')"
    }

    rootRule = RuleGenerator.generate_rule_graph(seedRule)

    assert type(rootRule) is dict
    assert rootRule['pattern'] == seedRule['pattern']
    assert rootRule['rewrite'] == seedRule['rewrite']

    children = rootRule['children']

    assert len(children) == 2
