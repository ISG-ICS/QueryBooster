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
    columns = ["name", "age", "salary"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_columns = RuleGenerator.columns(pattern_json, rewrite_json)
    assert set(test_columns) == set(columns)


def test_columns_5():
    pattern = '''
        select e1.*
        from employee e1,
            employee e2
        where e1.id = e2.id
        and e1.age > 17
        and e2.salary > 35000;
    '''
    rewrite = '''
        SELECT e1.*
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000;
    '''
    columns = ["id", "age", "salary"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_columns = RuleGenerator.columns(pattern_json, rewrite_json)
    assert set(test_columns) == set(columns)


def test_columns_6():
    pattern = '''
        select *
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS');
    '''
    rewrite = '''
        select distinct *
        from employee emp, department dept
        where emp.workdept = dept.deptno 
        and dept.deptname = 'OPERATIONS';
    '''
    columns = ["workdept", "deptno", "deptname"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_columns = RuleGenerator.columns(pattern_json, rewrite_json)
    assert set(test_columns) == set(columns)


def test_columns_7():
    pattern = '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1 
    '''
    rewrite = '''
        SELECT *
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
    '''
    columns = ["admin_permission_id", "admin_role_id"]

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


def test_literals_3():
    pattern = '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1 
    '''
    rewrite = '''
        SELECT *
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
    '''
    literals = [1]

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


def test_aliases_1():
    pattern = "STRPOS(LOWER(tweets.text), 'iphone') > 0"
    rewrite = "ILIKE(tweets.text, '%iphone%')"
    aliases = ["tweets"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_aliases = RuleGenerator.aliases(pattern_json, rewrite_json)
    assert set(test_aliases) == set(aliases)


def test_aliases_2():
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
    aliases = ["e1", "e2"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_aliases = RuleGenerator.aliases(pattern_json, rewrite_json)
    assert set(test_aliases) == set(aliases)


def test_aliases_3():
    pattern = '''
        select e1.name, e1.age, <x1>.salary
        from employee e1,
            employee <x1>
        where e1.id = <x1>.id
        and e1.age > 17
        and <x1>.salary > 35000;
    '''
    rewrite = '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000;
    '''
    aliases = ["e1"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_aliases = RuleGenerator.aliases(pattern_json, rewrite_json)
    assert set(test_aliases) == set(aliases)


def test_aliases_4():
    pattern = '''
        select *
        from employee e1
        where age > 17
        and salary > 35000;
    '''
    rewrite = '''
        SELECT * 
        FROM employee
        WHERE age > 17
        AND salary > 35000;
    '''
    aliases = ["e1"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_aliases = RuleGenerator.aliases(pattern_json, rewrite_json)
    assert set(test_aliases) == set(aliases)


def test_aliases_5():
    pattern = '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1 
    '''
    rewrite = '''
        SELECT *
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
    '''
    aliases = ["adminpermi0_", "allroles1_", "adminrolei2_"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_aliases = RuleGenerator.aliases(pattern_json, rewrite_json)
    assert set(test_aliases) == set(aliases)


def test_variablize_alias_1():

    rule = {
        'pattern': "STRPOS(LOWER(tweets.text), 'iphone') > 0",
        'rewrite': "ILIKE(tweets.text, '%iphone%')"
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_alias(rule, 'tweets')
    assert rule['pattern'] == "STRPOS(LOWER(<x1>.text), 'iphone') > 0"
    assert rule['rewrite'] == "ILIKE(<x1>.text, '%iphone%')"


def test_variablize_alias_2():

    rule = {
        'pattern': "STRPOS(LOWER(tweets.<x1>), 'iphone') > 0",
        'rewrite': "ILIKE(tweets.<x1>, '%iphone%')"
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_alias(rule, 'tweets')
    assert rule['pattern'] == "STRPOS(LOWER(<x2>.<x1>), 'iphone') > 0"
    assert rule['rewrite'] == "ILIKE(<x2>.<x1>, '%iphone%')"


def test_variablize_alias_3():

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
    
    rule = RuleGenerator.variablize_alias(rule, 'e1')
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT <x1>.name, <x1>.age, e2.salary
            FROM employee AS <x1>,
                employee AS e2
            WHERE <x1>.id = e2.id
            AND <x1>.age > 17
            AND e2.salary > 35000
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT <x1>.name, <x1>.age, <x1>.salary 
            FROM employee AS <x1>
            WHERE <x1>.age > 17
            AND <x1>.salary > 35000
        ''')


def test_variablize_alias_4():

    rule = {
        'pattern': '''
            select <x1>.name, <x1>.age, e2.salary
            from employee <x1>,
                employee e2
            where <x1>.id = e2.id
            and <x1>.age > 17
            and e2.salary > 35000
        ''',
        'rewrite': '''
            SELECT <x1>.name, <x1>.age, <x1>.salary 
            FROM employee <x1>
            WHERE <x1>.age > 17
            AND <x1>.salary > 35000
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_alias(rule, 'e2')
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT <x1>.name, <x1>.age, <x2>.salary
            FROM employee AS <x1>,
                employee AS <x2>
            WHERE <x1>.id = <x2>.id
            AND <x1>.age > 17
            AND <x2>.salary > 35000
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT <x1>.name, <x1>.age, <x1>.salary 
            FROM employee AS <x1>
            WHERE <x1>.age > 17
            AND <x1>.salary > 35000
        ''')


def test_tables_1():
    pattern = "STRPOS(LOWER(text), 'iphone') > 0"
    rewrite = "ILIKE(text, '%iphone%')"
    tables = []

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(test_tables) == set(tables)


def test_tables_2():
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
    tables = ["employee"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(test_tables) == set(tables)


def test_tables_3():
    pattern = '''
        select e1.name, e1.age, e2.salary
        from <tb1> e1,
             <tb1> e2
        where e1.<a1> = e2.<a1>
        and e1.age > 17
        and e2.salary > 35000;
    '''
    rewrite = '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM <tb1> e1
        WHERE e1.age > 17
        AND e1.salary > 35000;
    '''
    tables = []

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(test_tables) == set(tables)


def test_tables_4():
    pattern = '''
        select *
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS');
    '''
    rewrite = '''
        select distinct *
        from employee emp, department dept
        where emp.workdept = dept.deptno 
        and dept.deptname = 'OPERATIONS';
    '''
    tables = ["employee", "department"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(test_tables) == set(tables)


def test_tables_5():
    pattern = '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1 
    '''
    rewrite = '''
        SELECT *
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
    '''
    tables = ["blc_admin_permission", "blc_admin_role_permission_xref", "blc_admin_role"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(test_tables) == set(tables)


def test_generate_rule_graph_1():
    q0 = "SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
    q1 = "SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"

    rootRule = RuleGenerator.generate_rule_graph(q0, q1)
    assert type(rootRule) is dict

    children = rootRule['children']
    assert len(children) == 1

    childRule = children[0]
    assert childRule['pattern'] == 'CAST(<x1> AS DATE)'
    assert childRule['rewrite'] == '<x1>'


def test_generate_rule_graph_2():
    q0 = '''
        select e1.name, e1.age, e2.salary
        from employee e1,
            employee e2
        where e1.id = e2.id
        and e1.age > 17
        and e2.salary > 35000
    '''
    q1 = '''
        SELECT e1.name, e1.age, e1.salary 
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000
    '''

    rootRule = RuleGenerator.generate_rule_graph(q0, q1)
    children = rootRule['children']
    assert len(children) == 9


def test_generate_rule_graph_3():
    q0 = "SELECT * FROM t WHERE STRPOS(LOWER(text), 'iphone') > 0"
    q1 = "SELECT * FROM t WHERE ILIKE(text, '%iphone%')"

    rootRule = RuleGenerator.generate_rule_graph(q0, q1)
    assert type(rootRule) is dict

    children = rootRule['children']
    assert len(children) == 2


def test_generate_rule_graph_4():
    q0 = '''
        SELECT *
        FROM   blc_admin_permission admipermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1 
    '''
    q1 = '''
        SELECT *
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
    '''

    rootRule = RuleGenerator.generate_rule_graph(q0, q1)
    children = rootRule['children']
    assert len(children) == 10


def test_generate_rules_graph_1():
    examples = [
        {
            "q0":"SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
            "q1":"SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
        },
        {
            "q0":"SELECT * FROM t WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
            "q1":"SELECT * FROM t WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
        }
    ]

    rootRules = RuleGenerator.generate_rules_graph(examples)
    assert type(rootRules) is list
    assert len(rootRules) == 2


def test_recommend_rules_1():
    examples = [
        {
            "q0":"SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
            "q1":"SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
        },
        {
            "q0":"SELECT * FROM t WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
            "q1":"SELECT * FROM t WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
        }
    ]

    rootRules = RuleGenerator.generate_rules_graph(examples)
    assert type(rootRules) is list
    assert len(rootRules) == 2

    recommendRules = RuleGenerator.recommend_rules(rootRules, len(examples))
    assert type(recommendRules) is list
    assert len(recommendRules) == 1


def test_recommend_rules_2():
    examples = [
        {
            "q0":'''
                    SELECT  SUM(1),
                            CAST(state_name AS TEXT)
                    FROM  tweets 
                    WHERE  CAST(DATE_TRUNC('QUARTER', 
                                            CAST(created_at AS DATE)) 
                                AS DATE) IN 
                                ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                                (TIMESTAMP '2017-01-01 00:00:00.000'), 
                                (TIMESTAMP '2017-04-01 00:00:00.000'))
                    AND  (STRPOS(UPPER(text), 'iphone') > 0)
                    GROUP  BY 2;
            ''',
            "q1":'''
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
        },
        {
            "q0":'''
                    SELECT  *
                    FROM  tweets 
                    WHERE  (STRPOS(UPPER(state_name), 'iphone') > 0);
            ''',
            "q1":'''
                    SELECT  *
                    FROM  tweets 
                    WHERE  state_name ILIKE '%iphone%';
            '''
        }
    ]

    rootRules = RuleGenerator.generate_rules_graph(examples)
    assert type(rootRules) is list
    assert len(rootRules) == 2

    recommendRules = RuleGenerator.recommend_rules(rootRules, len(examples))
    assert type(recommendRules) is list
    assert len(recommendRules) == 1
