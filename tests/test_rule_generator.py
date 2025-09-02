from core.rule_generator import RuleGenerator
from core.rule_parser import RuleParser
import json
from .string_util import StringUtil
import re


# def test_minDiffSubtree_1():
#     q0 = "SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
#     q1 = "SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"

#     # Mock the logic inside generate_seed_rule()
#     #
#     # Extend partial SQL statement to full SQL statement
#     #    for the sake of sql parser
#     #
#     q0, q0Scope = RuleParser.extendToFullSQL(q0)
#     q1, q1Scope = RuleParser.extendToFullSQL(q1)

#     # Parse full SQL statement into AST json
#     #
#     q0ASTJson = mosql.parse(q0)
#     q1ASTJson = mosql.parse(q1)

#     # Find minimum different subtrees between two AST jsons
#     #
#     patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
#         q0ASTJson, q1ASTJson)

#     assert patternASTJson == {'cast': ['created_at', {'date': {}}]}
#     assert rewriteASTJson == 'created_at'


# def test_minDiffSubtree_2():
#     q0 = "CAST(created_at AS DATE)"
#     q1 = "created_at"

#     # Mock the logic inside generate_seed_rule()
#     #
#     # Extend partial SQL statement to full SQL statement
#     #    for the sake of sql parser
#     #
#     q0, q0Scope = RuleParser.extendToFullSQL(q0)
#     q1, q1Scope = RuleParser.extendToFullSQL(q1)

#     # Parse full SQL statement into AST json
#     #
#     q0ASTJson = mosql.parse(q0)
#     q1ASTJson = mosql.parse(q1)

#     # Find minimum different subtrees between two AST jsons
#     #
#     patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
#         q0ASTJson, q1ASTJson)

#     assert patternASTJson == {'cast': ['created_at', {'date': {}}]}
#     assert rewriteASTJson == 'created_at'


# def test_minDiffSubtree_3():
#     q0 = "SELECT CAST(state_name AS TEXT)"
#     q1 = "SELECT state_name"

#     # Mock the logic inside generate_seed_rule()
#     #
#     # Extend partial SQL statement to full SQL statement
#     #    for the sake of sql parser
#     #
#     q0, q0Scope = RuleParser.extendToFullSQL(q0)
#     q1, q1Scope = RuleParser.extendToFullSQL(q1)

#     # Parse full SQL statement into AST json
#     #
#     q0ASTJson = mosql.parse(q0)
#     q1ASTJson = mosql.parse(q1)

#     # Find minimum different subtrees between two AST jsons
#     #
#     patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
#         q0ASTJson, q1ASTJson)

#     assert patternASTJson == {'cast': ['state_name', {'text': {}}]}
#     assert rewriteASTJson == 'state_name'


# def test_minDiffSubtree_4():
#     q0 = '''
#         SELECT  SUM(1),
#                 CAST(state_name AS TEXT)
#           FROM  tweets 
#          WHERE  CAST(DATE_TRUNC('QUARTER', 
#                                 CAST(created_at AS DATE)) 
#                 AS DATE) IN 
#                     ((TIMESTAMP '2016-10-01 00:00:00.000'), 
#                     (TIMESTAMP '2017-01-01 00:00:00.000'), 
#                     (TIMESTAMP '2017-04-01 00:00:00.000'))
#            AND  (STRPOS(LOWER(text), 'iphone') > 0)
#          GROUP  BY 2;
#     '''
#     q1 = '''
#         SELECT  SUM(1),
#                 CAST(state_name AS TEXT)
#           FROM  tweets 
#          WHERE  CAST(DATE_TRUNC('QUARTER', 
#                                 CAST(created_at AS DATE)) 
#                 AS DATE) IN 
#                     ((TIMESTAMP '2016-10-01 00:00:00.000'), 
#                     (TIMESTAMP '2017-01-01 00:00:00.000'), 
#                     (TIMESTAMP '2017-04-01 00:00:00.000'))
#            AND  text ILIKE '%iphone%'
#          GROUP  BY 2;
#     '''

#     # Mock the logic inside generate_seed_rule()
#     #
#     # Extend partial SQL statement to full SQL statement
#     #    for the sake of sql parser
#     #
#     q0, q0Scope = RuleParser.extendToFullSQL(q0)
#     q1, q1Scope = RuleParser.extendToFullSQL(q1)

#     # Parse full SQL statement into AST json
#     #
#     q0ASTJson = mosql.parse(q0)
#     q1ASTJson = mosql.parse(q1)

#     # Find minimum different subtrees between two AST jsons
#     #
#     patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
#         q0ASTJson, q1ASTJson)

#     assert patternASTJson == {
#         'gt': [{'strpos': [{'lower': 'text'}, {'literal': 'iphone'}]}, 0]}
#     assert rewriteASTJson == {'ilike': ['text', {'literal': '%iphone%'}]}


# def test_minDiffSubtree_5():
#     q0 = "STRPOS(LOWER(text), 'iphone') > 0"
#     q1 = "text ILIKE '%iphone%'"

#     # Mock the logic inside generate_seed_rule()
#     #
#     # Extend partial SQL statement to full SQL statement
#     #    for the sake of sql parser
#     #
#     q0, q0Scope = RuleParser.extendToFullSQL(q0)
#     q1, q1Scope = RuleParser.extendToFullSQL(q1)

#     # Parse full SQL statement into AST json
#     #
#     q0ASTJson = mosql.parse(q0)
#     q1ASTJson = mosql.parse(q1)

#     # Find minimum different subtrees between two AST jsons
#     #
#     patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(
#         q0ASTJson, q1ASTJson)

#     assert patternASTJson == {
#         'gt': [{'strpos': [{'lower': 'text'}, {'literal': 'iphone'}]}, 0]}
#     assert rewriteASTJson == {'ilike': ['text', {'literal': '%iphone%'}]}


# def test_generate_seed_rule_1():
#     q0 = "SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
#     q1 = "SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"

#     gen_rule = RuleGenerator.generate_seed_rule(q0, q1)

#     assert gen_rule['pattern'] == 'CAST(created_at AS DATE)'
#     assert gen_rule['rewrite'] == 'created_at'


# def test_generate_seed_rule_2():
#     q0 = "CAST(created_at AS DATE)"
#     q1 = "created_at"

#     gen_rule = RuleGenerator.generate_seed_rule(q0, q1)

#     assert gen_rule['pattern'] == 'CAST(created_at AS DATE)'
#     assert gen_rule['rewrite'] == 'created_at'


# def test_generate_seed_rule_3():
#     q0 = "SELECT CAST(state_name AS TEXT)"
#     q1 = "SELECT state_name"

#     gen_rule = RuleGenerator.generate_seed_rule(q0, q1)

#     assert gen_rule['pattern'] == 'CAST(state_name AS TEXT)'
#     assert gen_rule['rewrite'] == 'state_name'


# def test_generate_seed_rule_4():
#     q0 = '''
#         SELECT  SUM(1),
#                 CAST(state_name AS TEXT)
#           FROM  tweets 
#          WHERE  CAST(DATE_TRUNC('QUARTER', 
#                                 CAST(created_at AS DATE)) 
#                 AS DATE) IN 
#                     ((TIMESTAMP '2016-10-01 00:00:00.000'), 
#                     (TIMESTAMP '2017-01-01 00:00:00.000'), 
#                     (TIMESTAMP '2017-04-01 00:00:00.000'))
#            AND  (STRPOS(LOWER(text), 'iphone') > 0)
#          GROUP  BY 2;
#     '''
#     q1 = '''
#         SELECT  SUM(1),
#                 CAST(state_name AS TEXT)
#           FROM  tweets 
#          WHERE  CAST(DATE_TRUNC('QUARTER', 
#                                 CAST(created_at AS DATE)) 
#                 AS DATE) IN 
#                     ((TIMESTAMP '2016-10-01 00:00:00.000'), 
#                     (TIMESTAMP '2017-01-01 00:00:00.000'), 
#                     (TIMESTAMP '2017-04-01 00:00:00.000'))
#            AND  text ILIKE '%iphone%'
#          GROUP  BY 2;
#     '''

#     gen_rule = RuleGenerator.generate_seed_rule(q0, q1)

#     assert gen_rule['pattern'] == "STRPOS(LOWER(text), 'iphone') > 0"
#     assert gen_rule['rewrite'] == "ILIKE(text, '%iphone%')"


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
    columns = ["*", "id", "age", "salary"]

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
    columns = ["*", "workdept", "deptno", "deptname"]

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
    columns = ["*", "admin_permission_id", "admin_role_id"]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_columns = RuleGenerator.columns(pattern_json, rewrite_json)
    assert set(test_columns) == set(columns)


def test_columns_8():
    pattern = '''
        SELECT  adminpermi0_.admin_permission_id AS admin_pe1_4_,
                adminpermi0_.description         AS descript2_4_,
                adminpermi0_.is_friendly         AS is_frien3_4_,
                adminpermi0_.name                AS name4_4_,
                adminpermi0_.permission_type     AS permissi5_4_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminpermi0_.is_friendly = 1
            AND adminrolei2_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT  50 
    '''
    rewrite = '''
        SELECT  adminpermi0_.admin_permission_id AS admin_pe1_4_,
                adminpermi0_.description         AS descript2_4_,
                adminpermi0_.is_friendly         AS is_frien3_4_,
                adminpermi0_.name                AS name4_4_,
                adminpermi0_.permission_type     AS permissi5_4_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  adminpermi0_.is_friendly = 1
            AND allroles1_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT  50 
    '''
    columns = ["admin_permission_id", "description", "is_friendly", "name", "permission_type", "admin_role_id"]

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
        'rewrite': "V1 ILIKE '%V2%'",
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
        'rewrite': "text ILIKE '%iphone%'"
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_column(rule, 'text')
    assert rule['pattern'] == "STRPOS(LOWER(<x1>), 'iphone') > 0"
    assert rule['rewrite'] == "<x1> ILIKE '%iphone%'"


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


def test_variablize_column_4():

    rule = {
        'pattern': '''
            select *
            from employee
            where workdept in
                (select deptno
                    from department
                    where deptname = 'OPERATIONS');
        ''',
        'rewrite': '''
            select distinct *
            from employee emp, department dept
            where emp.workdept = dept.deptno 
            and dept.deptname = 'OPERATIONS';
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_column(rule, '*')
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT <x1>
            FROM employee
            WHERE workdept IN
                (SELECT deptno
                    FROM department
                    WHERE deptname = 'OPERATIONS')
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT DISTINCT <x1>
            FROM employee AS emp, department AS dept
            WHERE emp.workdept = dept.deptno 
            AND dept.deptname = 'OPERATIONS'
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
        'rewrite': "text ILIKE '%iphone%'"
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_literal(rule, 'iphone')
    assert rule['pattern'] == "STRPOS(LOWER(text), '<x1>') > 0"
    assert rule['rewrite'] == "text ILIKE '%<x1>%'"


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


def test_tables_1():
    pattern = "STRPOS(LOWER(text), 'iphone') > 0"
    rewrite = "ILIKE(text, '%iphone%')"
    tables = []

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(map(lambda t: t['value'] + '-' + t['name'], test_tables)) == set(map(lambda t: t['value'] + '-' + t['name'], tables))


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
    tables = [{'value': 'employee', 'name': 'e1'}, {'value': 'employee', 'name': 'e2'}]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(map(lambda t: t['value'] + '-' + t['name'], test_tables)) == set(map(lambda t: t['value'] + '-' + t['name'], tables))


def test_tables_3():
    pattern = '''
        select <tb1>.name, <tb1>.age, <tb2>.salary
        from <tb1>,
             <tb2>
        where <tb1>.<a1> = <tb2>.<a1>
        and <tb1>.age > 17
        and <tb2>.salary > 35000;
    '''
    rewrite = '''
        SELECT  <tb1>.name, 
                <tb1>.age, 
                <tb1>.salary 
        FROM <tb1>
        WHERE <tb1>.age > 17
        AND <tb1>.salary > 35000;
    '''
    tables = []

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(map(lambda t: t['value'] + '-' + t['name'], test_tables)) == set(map(lambda t: t['value'] + '-' + t['name'], tables))


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
        from employee, department
        where employee.workdept = department.deptno 
        and department.deptname = 'OPERATIONS';
    '''
    tables = [{'value': 'employee', 'name': 'employee'}, {'value': 'department', 'name': 'department'}]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(map(lambda t: t['value'] + '-' + t['name'], test_tables)) == set(map(lambda t: t['value'] + '-' + t['name'], tables))


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
    tables = [
        {'value': 'blc_admin_permission', 'name': 'adminpermi0_'}, 
        {'value': 'blc_admin_role_permission_xref', 'name': 'allroles1_'}, 
        {'value': 'blc_admin_role', 'name': 'adminrolei2_'}
    ]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(map(lambda t: t['value'] + '-' + t['name'], test_tables)) == set(map(lambda t: t['value'] + '-' + t['name'], tables))


def test_tables_6():
    pattern = '''
        SELECT Count(*)
        FROM   (SELECT 1 AS one
                FROM   group_histories
                WHERE  group_histories.group_id = 2578
                    AND group_histories.action = 2
                ORDER  BY group_histories.created_at DESC
                LIMIT  25 offset 0) subquery_for_count 
    '''
    rewrite = '''
        SELECT Count(*)
        FROM   (SELECT 1 AS one
                FROM   group_histories
                WHERE  group_histories.group_id = 2578
                    AND group_histories.action = 2
                LIMIT  25 offset 0) AS subquery_for_count 
    '''
    tables = [
        {'value': 'group_histories', 'name': 'group_histories'}
    ]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_tables = RuleGenerator.tables(pattern_json, rewrite_json)
    assert set(map(lambda t: t['value'] + '-' + t['name'], test_tables)) == set(map(lambda t: t['value'] + '-' + t['name'], tables))


def test_variablize_table_1():

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
    
    rule = RuleGenerator.variablize_table(rule, {'value': 'employee', 'name': 'e1'})
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT <x1>.name, <x1>.age, e2.salary
            FROM <x1>,
                employee AS e2
            WHERE <x1>.id = e2.id
            AND <x1>.age > 17
            AND e2.salary > 35000
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT <x1>.name, <x1>.age, <x1>.salary 
            FROM <x1>
            WHERE <x1>.age > 17
            AND <x1>.salary > 35000
        ''')


def test_variablize_table_2():

    rule = {
        'pattern': '''
            SELECT <x1>.name, <x1>.age, e2.salary
            FROM <x1>,
                employee AS e2
            WHERE <x1>.id = e2.id
            AND <x1>.age > 17
            AND e2.salary > 35000
        ''',
        'rewrite': '''
            SELECT <x1>.name, <x1>.age, <x1>.salary 
            FROM <x1>
            WHERE <x1>.age > 17
            AND <x1>.salary > 35000
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_table(rule, {'value': 'employee', 'name': 'e2'})
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT <x1>.name, <x1>.age, <x2>.salary
            FROM <x1>,
                 <x2>
            WHERE <x1>.id = <x2>.id
            AND <x1>.age > 17
            AND <x2>.salary > 35000
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT <x1>.name, <x1>.age, <x1>.salary 
            FROM <x1>
            WHERE <x1>.age > 17
            AND <x1>.salary > 35000
        ''')


def test_variablize_table_3():

    rule = {
        'pattern': '''
            SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
            FROM   blc_admin_permission adminpermi0_
                INNER JOIN blc_admin_role_permission_xref allroles1_
                        ON adminpermi0_.admin_permission_id =
                            allroles1_.admin_permission_id
                INNER JOIN blc_admin_role adminrolei2_
                        ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
            WHERE  adminpermi0_.is_friendly = 1
                AND adminrolei2_.admin_role_id = 1 
        ''',
        'rewrite': '''
            SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
            FROM   blc_admin_permission AS adminpermi0_
                INNER JOIN blc_admin_role_permission_xref AS allroles1_
                        ON adminpermi0_.admin_permission_id =
                            allroles1_.admin_permission_id
            WHERE  allroles1_.admin_role_id = 1
                AND adminpermi0_.is_friendly = 1 
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_table(rule, {'value': 'blc_admin_permission', 'name': 'adminpermi0_'})
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT COUNT(<x1>.admin_permission_id) AS col_0_0_
            FROM   <x1>
                INNER JOIN blc_admin_role_permission_xref AS allroles1_
                        ON <x1>.admin_permission_id = allroles1_.admin_permission_id
                INNER JOIN blc_admin_role AS adminrolei2_
                        ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
            WHERE  <x1>.is_friendly = 1
                AND adminrolei2_.admin_role_id = 1  
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT COUNT(<x1>.admin_permission_id) AS col_0_0_
            FROM   <x1>
                INNER JOIN blc_admin_role_permission_xref AS allroles1_
                        ON <x1>.admin_permission_id =
                            allroles1_.admin_permission_id
            WHERE  allroles1_.admin_role_id = 1
                AND <x1>.is_friendly = 1 
        ''')


def test_subtrees_1():
    pattern = "STRPOS(LOWER(text), 'iphone') > 0"
    rewrite = "text ILIKE '%iphone%'"
    subtrees = []

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_subtrees = RuleGenerator.subtrees(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_subtrees)) == set(map(lambda t: json.dumps(t), subtrees))


def test_subtrees_2():
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
    subtrees = []

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_subtrees = RuleGenerator.subtrees(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_subtrees)) == set(map(lambda t: json.dumps(t), subtrees))


def test_subtrees_3():
    pattern = '''
        select <tb1>.name, <tb1>.age, <tb2>.salary
        from <tb1>,
             <tb2>
        where <tb1>.<a1> = <tb2>.<a1>
        and <tb1>.age > 17
        and <tb2>.salary > 35000;
    '''
    rewrite = '''
        SELECT  <tb1>.name, 
                <tb1>.age, 
                <tb1>.salary 
        FROM <tb1>
        WHERE <tb1>.age > 17
        AND <tb1>.salary > 35000;
    '''
    subtrees = []

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_subtrees = RuleGenerator.subtrees(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_subtrees)) == set(map(lambda t: json.dumps(t), subtrees))


def test_subtrees_4():
    pattern = '''
        select <tb1>.<a2>, <tb1>.age, <tb2>.salary
        from <tb1>,
             <tb2>
        where <tb1>.<a1> = <tb2>.<a1>
        and <tb1>.age > 17
        and <tb2>.salary > 35000;
    '''
    rewrite = '''
        SELECT  <tb1>.<a2>, 
                <tb1>.age, 
                <tb1>.salary 
        FROM <tb1>
        WHERE <tb1>.age > 17
        AND <tb1>.salary > 35000;
    '''
    subtrees = [{'value': 'V001.V002'}]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_subtrees = RuleGenerator.subtrees(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_subtrees)) == set(map(lambda t: json.dumps(t), subtrees))


def test_subtrees_5():
    pattern = '''
        SELECT <x1>.<x7> AS admin_pe1_4_, <x1>.<x6> AS descript2_4_, <x1>.<x8> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x4> AS permissi5_4_
        FROM <x1>
        INNER JOIN <x2> ON <x1>.<x7> = <x2>.<x7>
        INNER JOIN <x3> ON <x2>.<x5> = <x3>.<x5>
        WHERE <x1>.<x8> = <x10>
        AND <x3>.<x5> = <x10>
        ORDER BY <x1>.<x6> ASC
        LIMIT <x11>
    '''
    rewrite = '''
        SELECT <x1>.<x7> AS admin_pe1_4_, <x1>.<x6> AS descript2_4_, <x1>.<x8> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x4> AS permissi5_4_
        FROM <x1>
        INNER JOIN <x2> ON <x1>.<x7> = <x2>.<x7>
        WHERE <x1>.<x8> = <x10>
        AND <x2>.<x5> = <x10>
        ORDER BY <x1>.<x6> ASC
        LIMIT <x11>
    '''
    subtrees = [
        {'eq': ['V001.V004', 'V010']}, 
        {'eq': ['V001.V002', 'V007.V002']}, 
        {'name': 'permissi5_4_', 'value': 'V001.V006'}, 
        {'name': 'name4_4_', 'value': 'V001.V005'}, 
        {'name': 'is_frien3_4_', 'value': 'V001.V004'}, 
        {'name': 'descript2_4_', 'value': 'V001.V003'}, 
        {'name': 'admin_pe1_4_', 'value': 'V001.V002'}
    ]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_subtrees = RuleGenerator.subtrees(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_subtrees)) == set(map(lambda t: json.dumps(t), subtrees))


def test_variablize_subtree_1():

    rule = {
        'pattern': '''
            select <tb1>.<a2>, <tb1>.age, <tb2>.salary
            from <tb1>,
                <tb2>
            where <tb1>.<a1> = <tb2>.<a1>
            and <tb1>.age > 17
            and <tb2>.salary > 35000
        ''',
        'rewrite': '''
            SELECT  <tb1>.<a2>, 
                    <tb1>.age, 
                    <tb1>.salary 
            FROM <tb1>
            WHERE <tb1>.age > 17
            AND <tb1>.salary > 35000
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.variablize_subtree(rule, {'value': 'V001.V002'})
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT <x5>, <tb1>.age, <tb2>.salary
            FROM <tb1>,
                <tb2>
            WHERE <tb1>.<a1> = <tb2>.<a1>
            AND <tb1>.age > 17
            AND <tb2>.salary > 35000
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT  <x5>, 
                    <tb1>.age, 
                    <tb1>.salary 
            FROM <tb1>
            WHERE <tb1>.age > 17
            AND <tb1>.salary > 35000
        ''')


def test_variablize_subtrees_1():

    rule = {
        'pattern': '''
            SELECT <x1>.<x7> AS admin_pe1_4_, <x1>.<x6> AS descript2_4_, <x1>.<x8> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x4> AS permissi5_4_
            FROM <x1>
            INNER JOIN <x2> ON <x1>.<x7> = <x2>.<x7>
            INNER JOIN <x3> ON <x2>.<x5> = <x3>.<x5>
            WHERE <x1>.<x8> = <x10>
            AND <x3>.<x5> = <x10>
            ORDER BY <x1>.<x6> ASC
            LIMIT <x11>
        ''',
        'rewrite': '''
            SELECT <x1>.<x7> AS admin_pe1_4_, <x1>.<x6> AS descript2_4_, <x1>.<x8> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x4> AS permissi5_4_
            FROM <x1>
            INNER JOIN <x2> ON <x1>.<x7> = <x2>.<x7>
            WHERE <x1>.<x8> = <x10>
            AND <x2>.<x5> = <x10>
            ORDER BY <x1>.<x6> ASC
            LIMIT <x11>
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    children = RuleGenerator.variablize_subtrees(rule)
    assert len(children) == 7


def test_variable_lists_1():
    pattern = '''
        SELECT <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        INNER JOIN <x2> ON <x13>
        INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
        WHERE <x12>
        AND <x3>.<x4> = <x10>
        ORDER BY <x1>.<x9> ASC
        LIMIT <x11>
    '''
    rewrite = '''
        SELECT <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        INNER JOIN <x2> ON <x13>
        WHERE <x12>
        AND <x2>.<x4> = <x10>
        ORDER BY <x1>.<x9> ASC
        LIMIT <x11>
    '''
    variable_lists = [['V011'], ['V001', 'V005', 'V003', 'V004', 'V002'], ['V008']]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_variable_lists = RuleGenerator.variable_lists(pattern_json, rewrite_json)
    assert set(map(lambda t: ','.join(sorted(t)), test_variable_lists)) == set(map(lambda t: ','.join(sorted(t)), variable_lists))


def test_variable_lists_2():
    pattern = '''
        SELECT <x11>
        FROM <x1>
        INNER JOIN <x2> ON <x9>
        INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
        WHERE <x8>
        AND <x3>.<x4> = <x7>
    '''
    rewrite = '''
        SELECT <x11>
        FROM <x1>
        INNER JOIN <x2> ON <x9>
        WHERE <x2>.<x4> = <x7>
        AND <x8>
    '''
    variable_lists = [['V007'], ['V001'], ['V004']]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_variable_lists = RuleGenerator.variable_lists(pattern_json, rewrite_json)
    assert set(map(lambda t: ','.join(sorted(t)), test_variable_lists)) == set(map(lambda t: ','.join(sorted(t)), variable_lists))


def test_variable_lists_3():
    pattern = '''
        SELECT <x19>, <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        LEFT OUTER JOIN <x2> ON <x13>
        LEFT OUTER JOIN <x3> ON <x2>.<x11> = <x3>.<x4>
        WHERE <x3>.<x4> = <x12>
    '''
    rewrite = '''
        SELECT <x19>, <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        LEFT OUTER JOIN <x2> ON <x13>
        WHERE <x2>.<x11> = <x12>
    '''
    variable_lists = [['V001', 'V002', 'V003', 'V004', 'V005', 'V006'], ['V009']]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_variable_lists = RuleGenerator.variable_lists(pattern_json, rewrite_json)
    assert set(map(lambda t: ','.join(sorted(t)), test_variable_lists)) == set(map(lambda t: ','.join(sorted(t)), variable_lists))


def test_merge_variable_list_1():

    rule = {
        'pattern': '''
            SELECT <x18>, <x17>, <x16>, <x15>, <x14>
            FROM <x1>
            INNER JOIN <x2> ON <x13>
            INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
            WHERE <x12>
            AND <x3>.<x4> = <x10>
            ORDER BY <x1>.<x9> ASC
            LIMIT <x11>
        ''',
        'rewrite': '''
            SELECT <x18>, <x17>, <x16>, <x15>, <x14>
            FROM <x1>
            INNER JOIN <x2> ON <x13>
            WHERE <x12>
            AND <x2>.<x4> = <x10>
            ORDER BY <x1>.<x9> ASC
            LIMIT <x11>
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.merge_variable_list(rule, ['V001', 'V005', 'V003', 'V004', 'V002'])
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT <<y1>>
            FROM <x1>
            INNER JOIN <x2> ON <x13>
            INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
            WHERE <x12>
            AND <x3>.<x4> = <x10>
            ORDER BY <x1>.<x9> ASC
            LIMIT <x11>
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT <<y1>>
            FROM <x1>
            INNER JOIN <x2> ON <x13>
            WHERE <x12>
            AND <x2>.<x4> = <x10>
            ORDER BY <x1>.<x9> ASC
            LIMIT <x11>
        ''')


def test_merge_variable_list_2():

    rule = {
        'pattern': '''
            SELECT <x18>, <x17>, <x16>, <x15>, <x14>
            FROM <x1>
            INNER JOIN <x2> ON <x13>
            INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
            WHERE <x12>
            AND <x3>.<x4> = <x10>
            ORDER BY <x1>.<x9> ASC
            LIMIT <x11>
        ''',
        'rewrite': '''
            SELECT <x18>, <x17>, <x16>, <x15>, <x14>
            FROM <x1>
            INNER JOIN <x2> ON <x13>
            WHERE <x12>
            AND <x2>.<x4> = <x10>
            ORDER BY <x1>.<x9> ASC
            LIMIT <x11>
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.merge_variable_list(rule, ['V011'])
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            SELECT <x18>, <x17>, <x16>, <x15>, <x14>
            FROM <x1>
            INNER JOIN <x2> ON <x13>
            INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
            WHERE <<y1>>
            AND <x3>.<x4> = <x10>
            ORDER BY <x1>.<x9> ASC
            LIMIT <x11>
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            SELECT <x18>, <x17>, <x16>, <x15>, <x14>
            FROM <x1>
            INNER JOIN <x2> ON <x13>
            WHERE <<y1>>
            AND <x2>.<x4> = <x10>
            ORDER BY <x1>.<x9> ASC
            LIMIT <x11>
        ''')


def test_branches_1():
    pattern = "SELECT <<x>> FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
    rewrite = "SELECT <<x>> FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
    branches = [{'key': 'select', 'value': {'value': 'VL001'}}]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_branches = RuleGenerator.branches(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_branches)) == set(map(lambda t: json.dumps(t), branches))


def test_branches_2():
    pattern = "FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
    rewrite = "FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
    branches = [{'key': 'from', 'value': 'V001'}]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_branches = RuleGenerator.branches(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_branches)) == set(map(lambda t: json.dumps(t), branches))


def test_branches_3():
    pattern = "WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
    rewrite = "WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
    branches = [{'key': 'where', 'value': None}]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_branches = RuleGenerator.branches(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_branches)) == set(map(lambda t: json.dumps(t), branches))


def test_branches_4():
    pattern = "CAST(created_at AS DATE) = TIMESTAMP '<x>'"
    rewrite = "created_at = TIMESTAMP '<x>'"
    branches = [{'key': 'eq', 'value': {'timestamp': {'literal': 'V001'}}}]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_branches = RuleGenerator.branches(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_branches)) == set(map(lambda t: json.dumps(t), branches))


def test_branches_5():
    pattern = "SELECT * FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
    rewrite = "SELECT * FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
    branches = [{'key': 'select', 'value': {"all_columns": {}}}]

    pattern_json, rewrite_json, mapping = RuleParser.parse(pattern, rewrite)

    test_branches = RuleGenerator.branches(pattern_json, rewrite_json)
    assert set(map(lambda t: json.dumps(t), test_branches)) == set(map(lambda t: json.dumps(t), branches))


def test_drop_branch_1():

    rule = {
        'pattern': '''
            SELECT <<x>> FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'
        ''',
        'rewrite': '''
            SELECT <<x>> FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.drop_branch(rule, {'key': 'select', 'value': {'value': 'VL001'}})
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            FROM <t> WHERE created_at = TIMESTAMP('2016-10-01 00:00:00.000')
        ''')


def test_drop_branch_2():

    rule = {
        'pattern': '''
            FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'
        ''',
        'rewrite': '''
            FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.drop_branch(rule, {'key': 'from', 'value': 'V001'})
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            WHERE CAST(created_at AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            WHERE created_at = TIMESTAMP('2016-10-01 00:00:00.000')
        ''')


def test_drop_branch_3():

    rule = {
        'pattern': '''
            WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'
        ''',
        'rewrite': '''
            WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.drop_branch(rule, {'key': 'where', 'value': None})
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            CAST(created_at AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            created_at = TIMESTAMP('2016-10-01 00:00:00.000')
        ''')


def test_drop_branch_4():

    rule = {
        'pattern': '''
            CAST(created_at AS DATE) = TIMESTAMP '<x>'
        ''',
        'rewrite': '''
            created_at = TIMESTAMP '<x>'
        '''
    }
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints'], rule['constraints_json'], rule['actions'], rule['actions_json'] = '', '[]', '', '[]'
    
    rule = RuleGenerator.drop_branch(rule, {'key': 'eq', 'value': {'timestamp': {'literal': 'V001'}}})
    assert StringUtil.strim(rule['pattern']) == StringUtil.strim('''
            CAST(created_at AS DATE)
        ''')
    assert StringUtil.strim(rule['rewrite']) == StringUtil.strim('''
            created_at
        ''')


def test_generate_rule_graph_0():
    q0 = "CAST(created_at AS DATE)"
    q1 = "created_at"

    rootRule = RuleGenerator.generate_rule_graph(q0, q1)
    assert type(rootRule) is dict

    children = rootRule['children']
    assert len(children) == 1

    childRule = children[0]
    assert childRule['pattern'] == "CAST(<x1> AS DATE)"
    assert childRule['rewrite'] == "<x1>"


# TODO - generate_rule_graph runs for ever
#
# def test_generate_rule_graph_1():
#     q0 = "SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
#     q1 = "SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"

#     rootRule = RuleGenerator.generate_rule_graph(q0, q1)
#     assert type(rootRule) is dict

#     children = rootRule['children']
#     assert len(children) == 5

#     targetChildRule = {
#         'pattern': "SELECT * FROM t WHERE CAST(<x1> AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')",
#         'rewrite': "SELECT * FROM t WHERE <x1> = TIMESTAMP('2016-10-01 00:00:00.000')"
#     }
#     targetExists = False
#     for childRule in children:
#         if StringUtil.strim(RuleGenerator._fingerPrint(childRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint(targetChildRule['pattern'])) \
#             and StringUtil.strim(RuleGenerator._fingerPrint(childRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint(targetChildRule['rewrite'])):
#             targetExists = True
#     assert targetExists


# def test_generate_rule_graph_2():
#     q0 = '''
#         select e1.name, e1.age, e2.salary
#         from employee e1,
#             employee e2
#         where e1.id = e2.id
#         and e1.age > 17
#         and e2.salary > 35000
#     '''
#     q1 = '''
#         SELECT e1.name, e1.age, e1.salary 
#         FROM employee e1
#         WHERE e1.age > 17
#         AND e1.salary > 35000
#     '''

#     rootRule = RuleGenerator.generate_rule_graph(q0, q1)
#     children = rootRule['children']
#     assert len(children) == 8


# def test_generate_rule_graph_3():
#     q0 = "STRPOS(LOWER(text), 'iphone') > 0"
#     q1 = "ILIKE(text, '%iphone%')"

#     rootRule = RuleGenerator.generate_rule_graph(q0, q1)
#     assert type(rootRule) is dict

#     children = rootRule['children']
#     assert len(children) == 2


# def test_generate_rule_graph_4():
#     q0 = '''
#         SELECT *
#         FROM   blc_admin_permission adminpermi0_
#             INNER JOIN blc_admin_role_permission_xref allroles1_
#                     ON adminpermi0_.admin_permission_id =
#                         allroles1_.admin_permission_id
#             INNER JOIN blc_admin_role adminrolei2_
#                     ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
#         WHERE  adminrolei2_.admin_role_id = 1 
#     '''
#     q1 = '''
#         SELECT *
#         FROM   blc_admin_permission AS adminpermi0_
#             INNER JOIN blc_admin_role_permission_xref AS allroles1_
#                     ON adminpermi0_.admin_permission_id =
#                         allroles1_.admin_permission_id
#         WHERE  allroles1_.admin_role_id = 1
#     '''

#     rootRule = RuleGenerator.generate_rule_graph(q0, q1)
#     children = rootRule['children']
#     assert len(children) == 7


# def test_generate_rules_graph_1():
#     examples = [
#         {
#             "q0":"SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM t WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM t WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     rootRules = RuleGenerator.generate_rules_graph(examples)
#     assert type(rootRules) is list
#     assert len(rootRules) == 2


# def test_recommend_rules_1():
#     examples = [
#         {
#             "q0":"SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM t WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM t WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     rootRules = RuleGenerator.generate_rules_graph(examples)
#     assert type(rootRules) is list
#     assert len(rootRules) == 2

#     recommendRules = RuleGenerator.recommend_rules(rootRules, len(examples))
#     assert type(recommendRules) is list
#     assert len(recommendRules) == 1


# def test_recommend_rules_2():
#     examples = [
#         {
#             "q0":'''
#                     SELECT STRPOS(UPPER(text), 'iphone') > 0
#             ''',
#             "q1":'''
#                     SELECT text ILIKE '%iphone%'
#             '''
#         },
#         {
#             "q0":'''
#                     SELECT STRPOS(UPPER(state_name), 'iphone') > 0
#             ''',
#             "q1":'''
#                     SELECT state_name ILIKE '%iphone%'
#             '''
#         }
#     ]

#     rootRules = RuleGenerator.generate_rules_graph(examples)
#     assert type(rootRules) is list
#     assert len(rootRules) == 2

#     recommendRules = RuleGenerator.recommend_rules(rootRules, len(examples))
#     assert type(recommendRules) is list
#     assert len(recommendRules) == 1


def unify_variable_names(q0, q1):
    # Variable pattern
    pattern = r'<<[^>]*>>|<[^>]*>'

    # Find all variables in q0 and q1, and unify their names into xi in ascending order
    substrings = re.findall(pattern, q0 + q1)
    unique_substrings = []
    for substr in substrings:
        if substr not in unique_substrings:
            unique_substrings.append(substr)

    # Mapping from original variable names to new variable names
    mapping = {substr: f'{"<" * substr.count("<") }x{i+1}{">" * substr.count(">") }'
               for i, substr in enumerate(unique_substrings)}

    # Function for replacement using the mapping
    def replacer(match):
        return mapping[match.group(0)]

    # Replace all occurrences in one go using re.sub
    q0_unified = re.sub(pattern, replacer, q0)
    q1_unified = re.sub(pattern, replacer, q1)

    return q0_unified, q1_unified

def test_unify_variable_names_1():
    q0 = "FROM <<x9>> INNER JOIN <x10> ON <<x9>>.<x5> = <x10>.<x6>"
    q1 = "FROM <x10>"
    a, b = unify_variable_names(q0, q1)
    assert a == "FROM <<x1>> INNER JOIN <x2> ON <<x1>>.<x3> = <x2>.<x4>"
    assert b == "FROM <x2>"

def test_unify_variable_names_2():
    q0 = "<x2> <<x1>>"
    q1 = "<x2>"
    a, b = unify_variable_names(q0, q1)
    assert a == "<x1> <<x2>>"
    assert b == "<x1>"

def test_unify_variable_names_3():
    q0 = "<x> <<x1>> <x> <x> <y>"
    q1 = "<x> <<x1>> <y>"
    a, b = unify_variable_names(q0, q1)
    assert a == "<x1> <<x2>> <x1> <x1> <x3>"
    assert b == "<x1> <<x2>> <x3>"


def test_generate_general_rule_1():
    q0 = "SELECT CAST(created_at AS DATE)"
    q1 = "SELECT created_at"

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    assert rule['pattern'] == "CAST(<x1> AS DATE)"
    assert rule['rewrite'] == "<x1>"


def test_generate_general_rule_2():
    q0 = "SELECT STRPOS(LOWER(text), 'iphone') > 0"
    q1 = "SELECT ILIKE(text, '%iphone%')"

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    assert rule['pattern'] == "STRPOS(LOWER(<x1>), '<x2>') > 0"
    assert rule['rewrite'] == "<x1> ILIKE '%<x2>%'"


def test_generate_general_rule_3():
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

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        SELECT <<y1>>, <x2>.<x3>
        FROM   <x1>, <x2>
        WHERE  <x1>.<x4> = <x2>.<x4>
        AND    <<y2>>
        AND    <x2>.<x3> > <x5>
    '''))
    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        SELECT <<y1>>, <x1>.<x3>
        FROM   <x1>
        WHERE  <<y2>>
        AND    <x1>.<x3> > <x5>
    '''))


def test_generate_general_rule_4():
    q0 = '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
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

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    pattern, rewrite = unify_variable_names('''
        FROM       <x1>
        INNER JOIN <x2>
        ON         <<x9>>
        INNER JOIN <x3>
        ON         <x2>.<x5> = <x3>.<x5>
        WHERE      <x3>.<x5> = <x7>
    ''', '''
        FROM       <x1>
        INNER JOIN <x2>
        ON         <<x9>>
        WHERE      <x2>.<x5> = <x7>
    ''')

    assert StringUtil.strim(q0_rule) == StringUtil.strim(pattern)
    assert StringUtil.strim(q1_rule) == StringUtil.strim(rewrite)


def test_generate_general_rule_5():
    q0 = '''
        SELECT  adminpermi0_.admin_permission_id AS admin_pe1_4_,
                adminpermi0_.description         AS descript2_4_,
                adminpermi0_.is_friendly         AS is_frien3_4_,
                adminpermi0_.name                AS name4_4_,
                adminpermi0_.permission_type     AS permissi5_4_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminpermi0_.is_friendly = 1
            AND adminrolei2_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT  50 
    '''
    q1 = '''
        SELECT  adminpermi0_.admin_permission_id AS admin_pe1_4_,
                adminpermi0_.description         AS descript2_4_,
                adminpermi0_.is_friendly         AS is_frien3_4_,
                adminpermi0_.name                AS name4_4_,
                adminpermi0_.permission_type     AS permissi5_4_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  adminpermi0_.is_friendly = 1
            AND allroles1_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT  50 
    '''

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    pattern, rewrite = unify_variable_names('''
        FROM       <x1>
        INNER JOIN <x2>
        ON         <<x9>>
        INNER JOIN <x3>
        ON         <x2>.<x5> = <x3>.<x5>
        WHERE      <<y1>>
        AND        <x3>.<x5> = <x7>
    ''', '''
        FROM       <x1>
        INNER JOIN <x2>
        ON         <<x9>>
        WHERE      <<y1>>
        AND        <x2>.<x5> = <x7>
    ''')

    assert StringUtil.strim(q0_rule) == StringUtil.strim(pattern)
    assert StringUtil.strim(q1_rule) == StringUtil.strim(rewrite)


def test_generate_general_rule_6():
    q0 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminpermi0_.is_friendly = 1
            AND adminrolei2_.admin_role_id = 1 
    '''
    q1 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
            AND adminpermi0_.is_friendly = 1 
    '''

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    pattern, rewrite = unify_variable_names('''
        FROM       <x1>
        INNER JOIN <x2>
        ON         <<x9>>
        INNER JOIN <x3>
        ON         <x2>.<x5> = <x3>.<x5>
        WHERE      <<y1>>
        AND        <x3>.<x5> = <x7>
    ''', '''
        FROM       <x1>
        INNER JOIN <x2>
        ON         <<x9>>
        WHERE      <x2>.<x5> = <x7>
        AND        <<y1>>
    ''')

    assert StringUtil.strim(q0_rule) == StringUtil.strim(pattern)
    assert StringUtil.strim(q1_rule) == StringUtil.strim(rewrite)


def test_generate_general_rule_7():

    q0 = '''
        SELECT o_auth_applications.id
        FROM   o_auth_applications
            INNER JOIN authorizations
                    ON o_auth_applications.id = authorizations.o_auth_application_id
        WHERE  authorizations.user_id = 1465 
    '''
    q1 = '''
        SELECT authorizations.o_auth_application_id 
        FROM   authorizations AS authorizations
        WHERE  authorizations.user_id = 1465 
    '''

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        SELECT     <x1>.<x4>
        FROM       <x1>
        INNER JOIN <x2>
        ON         <x1>.<x4> = <x2>.<x3>
    '''))
    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        SELECT <x2>.<x3>
        FROM   <x2>
    '''))


def test_generate_general_rule_8():

    q0 = '''
        SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'
    '''
    q1 = '''
        SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'
    '''

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        CAST(<x1> AS DATE)
    ''')) or StringUtil.strim(RuleGenerator._fingerPrint(rule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        CAST(<<y>> AS DATE)
    '''))

    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        <x1>
    ''')) or StringUtil.strim(RuleGenerator._fingerPrint(rule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        <<y>>
    '''))


def test_generate_general_rule_9():

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
           GROUP  BY 2
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
         GROUP  BY 2
    '''

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        STRPOS(LOWER(<x1>), '<x2>') > 0
    '''))
    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        <x> ILIKE '%<x>%'
    '''))


def test_generate_general_rule_10():

    q0 = '''
        select *
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
    '''
    q1 = '''
        select distinct *
        from employee, department
        where employee.workdept = department.deptno 
        and department.deptname = 'OPERATIONS'
    '''

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        SELECT <x3> 
        FROM   <x1> 
        WHERE  <x6> IN (SELECT <x5> 
                        FROM   <x2> 
                        WHERE  <x4> = <x8>)
    '''))
    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        SELECT DISTINCT <x3> 
        FROM   <x1>, <x2> 
        WHERE  <x1>.<x6> = <x2>.<x5> 
        AND    <x2>.<x4> = <x8>
    '''))


def test_generate_general_rule_11():

    q0 = '''
        SELECT Count(*)
        FROM   (SELECT 1 AS one
                FROM   group_histories
                WHERE  group_histories.group_id = 2578
                    AND group_histories.action = 2
                ORDER  BY group_histories.created_at DESC
                LIMIT  25 offset 0) subquery_for_count 
    '''
    q1 = '''
        SELECT Count(*)
        FROM   (SELECT 1 AS one
                FROM   group_histories
                WHERE  group_histories.group_id = 2578
                    AND group_histories.action = 2
                LIMIT  25 offset 0) AS subquery_for_count 
    '''

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        FROM <x1> ORDER BY <x1>.<x2> DESC
    '''))
    assert StringUtil.strim(RuleGenerator._fingerPrint(rule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
        FROM <x1>
    '''))


def test_generate_general_rule_12():
    q0 = "SELECT student.ids from student WHERE student.id = 100 AND student.abc = 100"
    q1 = "SELECT student.id from student WHERE student.id = 100"

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    assert q0_rule== "SELECT <x1>.<x2> FROM <x1> WHERE <<x3>> AND <x1>.<x4> = <x5>"
    assert q1_rule == "SELECT <x1>.<x6> FROM <x1> WHERE <<x3>>"


def test_generate_general_rule_13():
    q0 = '''
        SELECT COUNT(adminpermi0_.admin_permission_id) AS col_0_0_ 
        FROM blc_admin_permission adminpermi0_ 
        INNER JOIN blc_admin_role_permission_xref allroles1_ 
        ON adminpermi0_.admin_permission_id=allroles1_.admin_permission_id 
        INNER JOIN blc_admin_role adminrolei2_ 
        ON allroles1_.admin_role_id=adminrolei2_.admin_role_id 
        WHERE adminpermi0_.is_friendly=1 AND adminrolei2_.admin_role_id=1
    '''
    q1 = '''
        SELECT COUNT(adminpermi0_.admin_permission_id) AS col_0_0_ 
        FROM blc_admin_permission AS adminpermi0_ 
        INNER JOIN blc_admin_role_permission_xref AS allroles1_ 
        ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id 
        WHERE allroles1_.admin_role_id = 1 
        AND adminpermi0_.is_friendly = 1
    '''

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    pattern, rewrite = unify_variable_names('''
        FROM <x1> INNER JOIN <x2> ON <<x3>> INNER JOIN <x4> ON <x2>.<x5> = <x4>.<x5> 
        WHERE <<x6>> AND <x4>.<x5> = <x7>
    ''','''
        FROM <x1> INNER JOIN <x2> ON <<x3>> WHERE <x2>.<x5> = <x7> AND <<x6>>
    ''')

    assert StringUtil.strim(q0_rule) == StringUtil.strim(pattern)
    assert StringUtil.strim(q1_rule) == StringUtil.strim(rewrite)


def test_generate_general_rule_14():
    q0 = """select
            distinct c.customer_id
            from table1 c
            join table2 l
            on c.customer_id = l.customer_id
            join table3 cal
            on c.customer_id = cal.customer_id
            WHERE
            (l.customer_group_id = 'loyalty' and c.loyalty_number = '123456789')
            or
            (cal.account_id = '123456789' and cal.account_type  = 'loyalty')"""
    q1 = """SELECT customer_id
            FROM   table1 c
            JOIN   table2 l   USING (customer_id)
            JOIN   table3 cal USING (customer_id)
            WHERE  l.customer_group_id = 'loyalty'
            AND    c.loyalty_number = '123456789'
            UNION
            SELECT customer_id
            FROM   table1 c
            JOIN   table2 l   USING (customer_id)
            JOIN   table3 cal USING (customer_id)
            WHERE  cal.account_id = '123456789'
            AND    cal.account_type  = 'loyalty'"""

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    assert StringUtil.strim(q0_rule) == StringUtil.strim("SELECT DISTINCT <x1>.<x2> FROM <x1> JOIN <x3> ON <x1>.<x2> = <x3>.<x2> JOIN <x4> ON <x1>.<x2> = <x4>.<x2> WHERE <x5> OR <x6>")
    assert StringUtil.strim(q1_rule)  == StringUtil.strim("SELECT <x2> FROM <x1> JOIN <x3> USING <x2> JOIN <x4> USING <x2> WHERE <x5> UNION SELECT <x2> FROM <x1> JOIN <x3> USING <x2> JOIN <x4> USING <x2> WHERE <x6>")


def test_generate_general_rule_15():
    q0 = "select * from A a left join B b on a.id = b.cid where b.cl1 = 's1' or b.cl1 ='s2' or b.cl1 ='s3'"
    q1 = "select * from A a left join B b  on a.id = b.cid where b.cl1 in ('s1','s2','s3')"

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    assert q0_rule== "<x1>.<x2> = '<x3>' OR <x1>.<x2> = '<x4>' OR <x1>.<x2> = '<x5>'"
    assert q1_rule == "<x1>.<x2> IN ('<x3>', '<x4>', '<x5>')"


def test_generate_general_rule_16():
    q0 = """SELECT historicoestatusrequisicion_id, requisicion_id, estatusrequisicion_id, 
            comentario, fecha_estatus, usuario_id
            FROM historicoestatusrequisicion hist1
            WHERE requisicion_id IN
            (
            SELECT requisicion_id FROM historicoestatusrequisicion hist2
            WHERE usuario_id = 27 AND estatusrequisicion_id = 1
            )
            ORDER BY requisicion_id, estatusrequisicion_id"""
    q1 = """SELECT hist1.historicoestatusrequisicion_id, hist1.requisicion_id, hist1.estatusrequisicion_id, hist1.comentario, hist1.fecha_estatus, hist1.usuario_id
            FROM historicoestatusrequisicion hist1
            JOIN historicoestatusrequisicion hist2 ON hist2.requisicion_id = hist1.requisicion_id
            WHERE hist2.usuario_id = 27 AND hist2.estatusrequisicion_id = 1
            ORDER BY hist1.requisicion_id, hist1.estatusrequisicion_id"""

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    assert q0_rule== "SELECT <x1>, <x2>, <x3>, <x4>, <x5>, <x6> FROM <x7> WHERE <x2> IN (SELECT <x2> FROM <x8> WHERE <x6> = <x9> AND <x3> = <x10>) ORDER BY <x2>, <x3>"
    assert q1_rule == "SELECT <x7>.<x1>, <x7>.<x2>, <x7>.<x3>, <x7>.<x4>, <x7>.<x5>, <x7>.<x6> FROM <x7> JOIN <x8> ON <x8>.<x2> = <x7>.<x2> WHERE <x8>.<x6> = <x9> AND <x8>.<x3> = <x10> ORDER BY <x7>.<x2>, <x7>.<x3>"


def test_generate_general_rule_17():
    q0 = """select wpis_id from spoleczniak_oznaczone
            where etykieta_id in(
            select tag_id
            from spoleczniak_subskrypcje
            where postac_id = 376476
            )"""
    q1 = """select spoleczniak_oznaczone.wpis_id 
            from spoleczniak_oznaczone
            inner join spoleczniak_subskrypcje on spoleczniak_subskrypcje.tag_id = spoleczniak_oznaczone.etykieta_id
            where spoleczniak_subskrypcje.postac_id = 376476"""

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    assert q0_rule== "SELECT <x1> FROM <x2> WHERE <x3> IN (SELECT <x4> FROM <x5> WHERE <x6> = <x7>)"
    assert q1_rule == "SELECT <x2>.<x1> FROM <x2> INNER JOIN <x5> ON <x5>.<x4> = <x2>.<x3> WHERE <x5>.<x6> = <x7>"

def test_generate_general_rule_18():
    q0 = "SELECT EMP.EMPNO FROM EMP WHERE EMP.EMPNO > 10 AND EMP.EMPNO <= 10"
    q1 = "SELECT EMPNO FROM EMP WHERE FALSE"

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    # TODO: there's a bug when calling unify_variable_names on this test case
    # q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    q0_rule, q1_rule = rule['pattern'], rule['rewrite']
    assert q0_rule== "SELECT <x1>.<x2> FROM <x1> WHERE <x1>.<x2> > <x3> AND <x1>.<x2> <= <x3>"
    assert q1_rule == "SELECT <x2> FROM <x1> WHERE False"

def test_generate_general_rule_19():
    q0 = "SELECT max(id) FROM Emp"
    q1 = "SELECT max(DISTINCT id) FROM Emp"

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    assert q0_rule == "MAX(<x1>)"
    assert q1_rule == "MAX(DISTINCT <x1>)"

def test_generate_general_rule_20():
    q0 = """SELECT * 
            FROM   accounts 
            WHERE  LOWER(accounts.firstname) = LOWER('Sam') 
                AND accounts.id IN (SELECT addresses.account_id 
                                                FROM addresses 
                                        WHERE LOWER(addresses.name) = LOWER('Street1'))         
                AND accounts.id IN (SELECT alternate_ids.account_id 
                                        FROM alternate_ids 
                                        WHERE alternate_ids.alternate_id_glbl = '5'); """
    q1 = """SELECT * 
            FROM accounts 
            JOIN addresses ON accounts.id = addresses.account_id
            JOIN alternate_ids ON accounts.id = alternate_ids.account_id
            WHERE LOWER(accounts.firstname) = LOWER('Sam') 
            AND LOWER(addresses.name) = LOWER('Street1') 
            AND alternate_ids.alternate_id_glbl = '5';"""

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    assert q0_rule == "FROM <x1> WHERE <<x2>> AND <x1>.<x3> IN (SELECT <x4>.<x5> FROM <x4> WHERE <<x6>>) AND <x1>.<x3> IN (SELECT <x7>.<x5> FROM <x7> WHERE <<x8>>)"
    assert q1_rule == "FROM <x1> JOIN <x4> ON <x1>.<x3> = <x4>.<x5> JOIN <x7> ON <x1>.<x3> = <x7>.<x5> WHERE <<x2>> AND <<x6>> AND <<x8>>"

def test_generate_general_rule_21():
    q0 = """SELECT product.name, category.description, category.category_id, 
FROM product NATURAL JOIN category
WHERE product.price > 100
AND product.category_id = 4"""
    
    q1 = """SELECT product.name, category.description, category.category_id 
FROM product INNER JOIN category ON product.category_id = category.category_id
WHERE product.price > 100"""

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    assert q0_rule == "FROM <x1> NATURAL JOIN (<x2>) WHERE <<x3>> AND <x1>.<x4> = 4"
    assert q1_rule == "FROM <x1> INNER JOIN <x2> ON <x1>.<x4> = <x2>.<x4> WHERE <<x3>>"

def test_generate_general_rule_22():
    q0 = """SELECT 
    t1.CPF,
    DATE(t1.data),
    CASE WHEN SUM(CASE WHEN t1.login_ok = true
                       THEN 1
                       ELSE 0
                  END) >= 1
         THEN true
         ELSE false
    END
FROM db_risco.site_rn_login AS t1
GROUP BY t1.CPF, DATE(t1.data)"""
    
    q1 = """SELECT
    t1.CPF,
    t1.data    
FROM (
    SELECT 
        CPF, 
        DATE(data)
    FROM db_risco.site_rn_login
    WHERE login_ok = true
) t1
GROUP BY t1.CPF, t1.data"""

    rule = RuleGenerator.generate_general_rule(q0, q1)
    assert type(rule) is dict

    q0_rule, q1_rule = unify_variable_names(rule['pattern'], rule['rewrite'])
    assert q0_rule == "SELECT <<x1>>, DATE(<x2>.<x3>), CASE WHEN SUM(CASE WHEN <x2>.<x4> = <x5> THEN <x5> ELSE <x6> END) >= <x5> THEN <x5> ELSE <x6> END FROM <x2> GROUP BY <<x7>>, DATE(<x2>.<x3>)"
    assert q1_rule == "SELECT <<x1>>, <x2>.<x3> FROM (SELECT <x8>, DATE(<x3>) FROM <x2> WHERE <x4> = <x5>) AS t1 GROUP BY <<x7>>, <x2>.<x3>"


# def test_suggest_rules_bf_1():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='bf')
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE CAST(<x1> AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE <x1> = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))


# def test_suggest_rules_bf_2():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='bf')
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_bf_3():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='bf')
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x3> WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x3> WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_bf_4():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT id FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT id FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='bf')
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT <<y1>> FROM <x3> WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT <<y1>> FROM <x3> WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_bf_5():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT CAST(deleted_at AS DATE) FROM users",
#             "q1":"SELECT deleted_at FROM users"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='bf')
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         CAST(<x1> AS DATE)
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         <x1>
#     '''))


# def test_suggest_rules_khn_k1_1():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=1)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE CAST(<x1> AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE <x1> = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))


# def test_suggest_rules_khn_k1_2():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=1)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_khn_k1_3():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=1)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 2

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRules[0]['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP('2018-10-01 00:00:00.000')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRules[0]['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE created_at = TIMESTAMP('2018-10-01 00:00:00.000')
#     '''))

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRules[1]['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x2> WHERE CAST(<x1> AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRules[1]['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x2> WHERE <x1> = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))


# def test_suggest_rules_khn_k2_3():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=2)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x3> WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x3> WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_khn_k2_4():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT id FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT id FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=2)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 2

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRules[0]['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT id FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRules[0]['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT id FROM users WHERE deleted_at = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRules[1]['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x3> WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRules[1]['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x3> WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_khn_k4_4():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT id FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT id FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='khn', k=4)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT <<y1>> FROM <x3> WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT <<y1>> FROM <x3> WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_mpn_m5_1():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='mpn', m=5)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE CAST(<x1> AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE <x1> = TIMESTAMP('2016-10-01 00:00:00.000')
#     '''))


# def test_suggest_rules_mpn_m10_2():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='mpn', m=10)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM tweets WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_mpn_m15_3():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='mpn', m=15)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x3> WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT * FROM <x3> WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_mpn_m20_4():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2018-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2018-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT * FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT id FROM users WHERE CAST(deleted_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT id FROM users WHERE deleted_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='mpn', m=20)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT <<y1>> FROM <x3> WHERE CAST(<x1> AS DATE) = TIMESTAMP('<x2>')
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         SELECT <<y1>> FROM <x3> WHERE <x1> = TIMESTAMP('<x2>')
#     '''))


# def test_suggest_rules_mpn_m10_5():
#     examples = [
#         {
#             "q0":"SELECT * FROM tweets WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
#             "q1":"SELECT * FROM tweets WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
#         },
#         {
#             "q0":"SELECT CAST(deleted_at AS DATE) FROM users",
#             "q1":"SELECT deleted_at FROM users"
#         }
#     ]

#     suggestRules = RuleGenerator.suggest_rules(examples, exp='mpn', m=10)
#     assert type(suggestRules) is list
#     assert len(suggestRules) == 1

#     suggestRule = suggestRules[0]

#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['pattern'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         CAST(<x1> AS DATE)
#     '''))
#     assert StringUtil.strim(RuleGenerator._fingerPrint(suggestRule['rewrite'])) == StringUtil.strim(RuleGenerator._fingerPrint('''
#         <x1>
#     '''))

def test_recommend_simple_rules_1():
    examples = [
        {'q0': "SELECT * FROM employee WHERE workdept IN (SELECT deptno FROM department WHERE deptname = 'OPERATIONS')",
        'q1': "SELECT DISTINCT * FROM employee, department where employee.workdept = department.deptno AND department.deptname = 'OPERATIONS'"
        }
    ]
    recommend_rules_json = RuleGenerator.recommend_simple_rules(examples)

    assert StringUtil.strim(recommend_rules_json[0]["pattern"]) == StringUtil.strim("SELECT * FROM <x1> WHERE workdept IN (SELECT deptno FROM department WHERE deptname = 'OPERATIONS')")
    assert StringUtil.strim(recommend_rules_json[0]["rewrite"]) == StringUtil.strim("SELECT DISTINCT * FROM <x1>, department WHERE <x1>.workdept = department.deptno AND department.deptname = 'OPERATIONS'")

def test_recommend_simple_rules_2():
    examples = [
        {'q0': "SELECT Count(*) FROM   (SELECT 1 AS one FROM   group_histories WHERE  group_histories.group_id = 2578 AND group_histories.action = 2 ORDER  BY group_histories.created_at DESC LIMIT  25 offset 0) subquery_for_count",
        'q1': "SELECT Count(*) FROM   (SELECT 1 AS one FROM   group_histories WHERE  group_histories.group_id = 2578 AND group_histories.action = 2 LIMIT  25 offset 0) AS subquery_for_count"
        },
        {'q0': "SELECT Count(*) FROM   (SELECT 1 AS one FROM   gh WHERE  gh.group_id = 2578 AND gh.action = 2 ORDER  BY gh.created_at DESC LIMIT  25 offset 0) subquery_for_count",
        'q1': "SELECT Count(*) FROM   (SELECT 1 AS one FROM   gh WHERE  gh.group_id = 2578 AND gh.action = 2 LIMIT  25 offset 0) AS subquery_for_count"
        }
    ]
    recommend_rules_json = RuleGenerator.recommend_simple_rules(examples)

    assert StringUtil.strim(recommend_rules_json[0]["pattern"]) == StringUtil.strim(
        "SELECT COUNT(*) FROM (SELECT 1 AS one FROM <x1> WHERE <x1>.group_id = 2578 AND <x1>.action = 2 ORDER BY <x1>.created_at DESC LIMIT 25 OFFSET 0) AS subquery_for_count")
    assert StringUtil.strim(recommend_rules_json[0]["rewrite"]) == StringUtil.strim(
        "SELECT COUNT(*) FROM (SELECT 1 AS one FROM <x1> WHERE <x1>.group_id = 2578 AND <x1>.action = 2 LIMIT 25 OFFSET 0) AS subquery_for_count")

def test_recommend_simple_rules_3():
    examples = [
        {'q0': "SELECT CAST(create_at as DATE)",
        'q1': "SELECT create_at"
        },
        {'q0': "SELECT CAST(create_at1 as DATE)", 
        'q1': "SELECT create_at1"
        },
        {'q0': "SELECT STRPOS(LOWER(text), 'iphone') > 0", 
        'q1': "SELECT ILIKE(text, '%iphone%')"
        },
        {'q0': "SELECT STRPOS(LOWER(text1), 'iphone') > 0", 
        'q1': "SELECT ILIKE(text1, '%iphone%')"
        },
        {'q0': "SELECT STRPOS(LOWER(text), 'iphone1') > 0", 
        'q1': "SELECT ILIKE(text, '%iphone1%')"
        }
    ]
    recommend_rules_json = RuleGenerator.recommend_simple_rules(examples)

    assert StringUtil.strim(recommend_rules_json[0]["pattern"]) == StringUtil.strim("SELECT CAST(<x1> AS DATE)")
    assert StringUtil.strim(recommend_rules_json[0]["rewrite"]) == StringUtil.strim("SELECT <x1>")
    assert StringUtil.strim(recommend_rules_json[1]["pattern"]) == StringUtil.strim("SELECT STRPOS(LOWER(text), '<x1>') > 0")
    assert StringUtil.strim(recommend_rules_json[1]["rewrite"]) == StringUtil.strim("SELECT text ILIKE '%<x1>%'")

def test_recommend_simple_rules_4():
    examples = [
        {'q0': "SELECT e1.name, e1.age, e2.salary FROM employee e1, employee e2 WHERE e1.id = e2.id AND e1.age > 17 AND e2.salary > 35000",
        'q1': "SELECT e1.name, e1.age, e1.salary FROM employee e1 WHERE e1.age > 17 AND e1.salary > 35000"
        },
        {'q0': "SELECT e1.name, e1.ages, e2.salary FROM employee e1, employee e2 WHERE e1.id = e2.id AND e1.ages > 17 AND e2.salary > 35000",
        'q1': "SELECT e1.name, e1.ages, e1.salary FROM employee e1 WHERE e1.ages > 17 AND e1.salary > 35000"
        },
        {'q0': "SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        'q1': "SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
        },
        {'q0': "SELECT s.ids from s WHERE s.x = 100 AND s.abc = 100",
        'q1': "SELECT s.x from s WHERE s.x = 100"
        },
        {'q0': "SELECT student.ids from student WHERE student.id = 100 AND student.abc = 100",
        'q1': "SELECT student.id from student WHERE student.id = 100"
        }
    ]
    recommend_rules_json = RuleGenerator.recommend_simple_rules(examples)

    assert StringUtil.strim(recommend_rules_json[0]["pattern"]) == StringUtil.strim("SELECT e1.name, e1.<x1>, e2.salary FROM employee AS e1, employee AS e2 WHERE e1.id = e2.id AND e1.<x1> > 17 AND e2.salary > 35000")
    assert StringUtil.strim(recommend_rules_json[0]["rewrite"]) == StringUtil.strim("SELECT e1.name, e1.<x1>, e1.salary FROM employee AS e1 WHERE e1.<x1> > 17 AND e1.salary > 35000")
    assert StringUtil.strim(recommend_rules_json[1]["pattern"]) == StringUtil.strim("SELECT * FROM <x1> WHERE CAST(created_at AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')")
    assert StringUtil.strim(recommend_rules_json[1]["rewrite"]) == StringUtil.strim("SELECT * FROM <x1> WHERE created_at = TIMESTAMP('2016-10-01 00:00:00.000')")
    assert StringUtil.strim(recommend_rules_json[2]["pattern"]) == StringUtil.strim("SELECT <x1>.ids FROM <x1> WHERE <x1>.<x2> = 100 AND <x1>.abc = 100")
    assert StringUtil.strim(recommend_rules_json[2]["rewrite"]) == StringUtil.strim("SELECT <x1>.<x2> FROM <x1> WHERE <x1>.<x2> = 100")




#success
def test_parse_validator_1():
    
  pattern = 'CAST(<x> AS DATE)'
  rewrite = '<x>'

  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert True == success1

  success2, errormessage2, index2 = RuleGenerator.parse_validate_single(rewrite)
  assert True == success2

  success3, errormessage3, index3 = RuleGenerator.parse_validate(pattern, rewrite)
  assert True == success3

#fails becasue <y> is not mapped to anythig in pattern so you cant rewrite it
def test_parse_validator_2():
    
  pattern = 'CAST(<x> AS DATE)'
  rewrite = '<y>'
  success, errormessage, index = RuleGenerator.parse_validate(pattern, rewrite)
  assert False == success
  assert index == 0
  assert "not in first rule" in errormessage

#spelling error in DATEE
def test_parse_validator_3():
    
  pattern = 'CAST(<x> AS DATEE)'
  rewrite = '<x>'

  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert False == success1
  assert index1 == 13
  assert "DATEE" in errormessage1

  success2, errormessage2, index2 = RuleGenerator.parse_validate(pattern, rewrite)
  assert False == success2
  assert index2 == 13
  assert "DATEE" in errormessage2

#spelling error in CAST
def test_parse_validator_4():
    
  pattern = 'CA NT(<x> AS DATE)'
  rewrite = '<x>' 

  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert False == success1
  assert index1 == 3
  assert "NT" in errormessage1

  success2, errormessage2, index2 = RuleGenerator.parse_validate(pattern, rewrite)
  assert False == success2
  assert index2 == 3
  assert "NT" in errormessage2

#success
def test_parse_validator_5():
    
  pattern = '''SELECT <x>
            FROM <y>
            WHERE <x> > 10 
            AND <x> <= 10
            '''
  
  rewrite = '''SELECT <x> 
            FROM <x> 
            WHERE FALSE
            '''
  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert True == success1
  assert index1 == 0

  success2, errormessage2, index2 = RuleGenerator.parse_validate_single(rewrite)
  assert True == success2
  assert index2 == 0

  success3, errormessage3, index3 = RuleGenerator.parse_validate(pattern, rewrite)
  assert True == success3
  assert index3 == 0

#cant check spelling error for from (frum)
def test_parse_validator_6():
    
  pattern = '''FRUM <y> 
            WHERE <x> > 10 
            AND <x> <= 10
            '''
  
  rewrite = ''' 
            FROM <y> 
            WHERE FALSE
            '''

  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert False == success1
  assert index1 == 0
  assert "spelling" in errormessage1

  success2, errormessage2, index2 = RuleGenerator.parse_validate(pattern, rewrite)
  assert False == success2
  assert index2 == 0
  assert "spelling" in errormessage2


#cant check spelling error for where (whure)
def test_parse_validator_7():
    
  pattern = '''WHURE <x> > 10 
            AND <x> <= 10
            '''
  
  rewrite = '''
            WHERE FALSE
            '''
  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert False == success1
  assert index1 == 0
  assert "spelling" in errormessage1

  success2, errormessage2, index2 = RuleGenerator.parse_validate(pattern, rewrite)
  assert False == success2
  assert index2 == 0
  assert "spelling" in errormessage2

def test_parse_validator_8():
    
  pattern = '''SELUCT <x>
            FROM <y>
            WHERE <x> >> 10 
            AND <x> <= 10
            '''
  
  rewrite = '''SELECT <x> 
            FROM <y>
            WHERE FALSE
            '''
  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert False == success1
  assert index1 == 0
  assert "spelling" in errormessage1

  success2, errormessage2, index2 = RuleGenerator.parse_validate(pattern, rewrite)
  assert False == success2
  assert index2 == 0
  assert "spelling" in errormessage2

def test_parse_validator_9():
    
  pattern = '''FRUM <x>, EN END 
            '''
  
  rewrite = ''' 
            FROM <x>
            '''
  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert False == success1
  assert index1 == 0
  assert "spelling" in errormessage1

  success2, errormessage2, index2 = RuleGenerator.parse_validate(pattern, rewrite)
  assert False == success2
  assert index2 == 0
  assert "spelling" in errormessage2

#extra numbers
def test_parse_validator_10():
    
  pattern = '''WHERE <x> > 11 5 10
            AND <x> <= 11
            '''
  
  rewrite = '''
            WHERE FALSE
            '''
  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert False == success1
  assert index1 == 16
  assert "5 10" in errormessage1

  success2, errormessage2, index2 = RuleGenerator.parse_validate(pattern, rewrite)
  assert False == success2
  assert index2 == 16
  assert "5 10" in errormessage2

#extra a 
def test_parse_validator_13():
    
  pattern = '''WHERE a <4x> > 11
            AND <x> a <= 11
            '''
  
  rewrite = '''
            WHERE FALSE
            '''

  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  assert False == success1
  assert index1 == 8
  assert "<4x>" in errormessage1

  success2, errormessage2, index2 = RuleGenerator.parse_validate(pattern, rewrite)
  assert False == success2
  assert index2 == 8
  assert "<4x>" in errormessage2

def test_parse_validator_14():

  pattern = 'CAST(<x3> AS TEXT)'
  
  rewrite = '<x3>'
  
  success1, errormessage1, index1 = RuleGenerator.parse_validate_single(pattern)
  success2, errormessage2, index2 = RuleGenerator.parse_validate_single(rewrite)
  assert True == success1
  assert True == success2

  success3, errormessage3, index3 = RuleGenerator.parse_validate(pattern, rewrite)
  assert True == success3