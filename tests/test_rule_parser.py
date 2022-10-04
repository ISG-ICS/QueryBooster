from core.rule_parser import RuleParser
from core.rule_parser import Scope

def test_extendToFullSQL():
    ruleParser = RuleParser()

    # CONDITION scope
    pattern = 'CAST(V1 AS DATE)'
    rewrite = 'V1'
    pattern, scope = ruleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT * FROM t WHERE CAST(V1 AS DATE)'
    assert scope == Scope.CONDITION
    rewrite, scope = ruleParser.extendToFullSQL(rewrite)
    assert rewrite == 'SELECT * FROM t WHERE V1'
    assert scope == Scope.CONDITION

    # WHERE scope
    pattern = 'WHERE CAST(V1 AS DATE)'
    rewrite = 'WHERE V1'
    pattern, scope = ruleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT * FROM t WHERE CAST(V1 AS DATE)'
    assert scope == Scope.WHERE
    rewrite, scope = ruleParser.extendToFullSQL(rewrite)
    assert rewrite == 'SELECT * FROM t WHERE V1'
    assert scope == Scope.WHERE

    # FROM scope
    pattern = 'FROM lineitem'
    rewrite = 'FROM v_lineitem'
    pattern, scope = ruleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT * FROM lineitem'
    assert scope == Scope.FROM
    rewrite, scope = ruleParser.extendToFullSQL(rewrite)
    assert rewrite == 'SELECT * FROM v_lineitem'
    assert scope == Scope.FROM

    # SELECT scope with FROM and WHERE
    pattern = '''
        select VL1
          from V1 V2, 
               V3 V4
         where V2.V6=V4.V8
           and VL2
    '''
    rewrite = '''
        select VL1 
          from V1 V2
         where VL2
    '''
    pattern, scope = ruleParser.extendToFullSQL(pattern)
    assert pattern == '''
        select VL1
          from V1 V2, 
               V3 V4
         where V2.V6=V4.V8
           and VL2
    '''
    assert scope == Scope.SELECT
    rewrite, scope = ruleParser.extendToFullSQL(rewrite)
    assert rewrite == '''
        select VL1 
          from V1 V2
         where VL2
    '''
    assert scope == Scope.SELECT

    # SELECT scope with FROM
    pattern = 'SELECT VL1 FROM lineitem'
    rewrite = 'SELECT VL1 FROM v_lineitem'
    pattern, scope = ruleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT VL1 FROM lineitem'
    assert scope == Scope.SELECT
    rewrite, scope = ruleParser.extendToFullSQL(rewrite)
    assert rewrite == 'SELECT VL1 FROM v_lineitem'
    assert scope == Scope.SELECT

    # SELECT scope with only SELECT
    pattern = 'SELECT CAST(V1 AS DATE)'
    rewrite = 'SELECT V1'
    pattern, scope = ruleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT CAST(V1 AS DATE)'
    assert scope == Scope.SELECT
    rewrite, scope = ruleParser.extendToFullSQL(rewrite)
    assert rewrite == 'SELECT V1'
    assert scope == Scope.SELECT

def test_replaceVars():
    ruleParser = RuleParser()
    
    # single var case
    pattern = 'CAST(<x> AS DATE)'
    rewrite = '<x>'
    pattern, rewrite, mapping = ruleParser.replaceVars(pattern, rewrite)
    assert pattern == 'CAST(V1 AS DATE)'
    assert rewrite == 'V1'

    # multiple var and varList case
    pattern = '''
        select <<s1>>
          from <tb1> <t1>, 
               <tb2> <t2>
         where <t1>.<a1>=<t2>.<a2>
           and <<p1>>
    '''
    rewrite = '''
        select <<s1>> 
          from <tb1> <t1>
         where <<p1>>
    '''
    pattern, rewrite, mapping = ruleParser.replaceVars(pattern, rewrite)
    assert pattern == '''
        select VL1
          from V1 V2, 
               V3 V4
         where V2.V5=V4.V6
           and VL2
    '''
    assert rewrite == '''
        select VL1 
          from V1 V2
         where VL2
    '''

def test_parse():
    ruleParser = RuleParser()

    # Init test_rules
    test_rules = []
    # Rule 1:
    rule = {
        'pattern': 'CAST(<x> AS DATE)',
        'rewrite': '<x>'
    }
    internal_rule = {
        'pattern_json': '{"cast": ["V1", {"date": {}}]}',
        'rewrite_json': '"V1"'
    }
    test_rules.append((rule, internal_rule))
    # Rule 2:
    rule = {
        'pattern': "STRPOS(LOWER(<x>), '<s>') > 0",
        'rewrite': "<x> ILIKE '%<s>%'"
    }
    internal_rule = {
        'pattern_json': '{"gt": [{"strpos": [{"lower": "V1"}, {"literal": "V2"}]}, 0]}',
        'rewrite_json': '{"ilike": ["V1", {"literal": "%V2%"}]}'
    }
    test_rules.append((rule, internal_rule))

    # Test test_rules
    for rule, internal_rule in test_rules:
        pattern_json, rewrite_json, mapping = ruleParser.parse(rule['pattern'], rule['rewrite'])
        assert pattern_json == internal_rule['pattern_json']
        assert rewrite_json == internal_rule['rewrite_json']
