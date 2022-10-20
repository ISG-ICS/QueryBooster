from core.rule_generator import RuleGenerator
from core.rule_parser import RuleParser
import mo_sql_parsing as mosql


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
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(q0ASTJson, q1ASTJson)

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
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(q0ASTJson, q1ASTJson)

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
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(q0ASTJson, q1ASTJson)

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
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(q0ASTJson, q1ASTJson)

    assert patternASTJson == {'gt': [{'strpos': [{'lower': 'text'}, {'literal': 'iphone'}]}, 0]}
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
    patternASTJson, rewriteASTJson = RuleGenerator.minDiffSubtree(q0ASTJson, q1ASTJson)

    assert patternASTJson == {'gt': [{'strpos': [{'lower': 'text'}, {'literal': 'iphone'}]}, 0]}
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
