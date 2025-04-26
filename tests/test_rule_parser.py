from core.rule_parser import RuleParser
from core.rule_parser import Scope

def test_extendToFullSQL():

    # CONDITION scope
    pattern = 'CAST(V1 AS DATE)'
    rewrite = 'V1'
    pattern, scope = RuleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT * FROM t WHERE CAST(V1 AS DATE)'
    assert scope == Scope.CONDITION
    rewrite, scope = RuleParser.extendToFullSQL(rewrite)
    assert rewrite == 'SELECT * FROM t WHERE V1'
    assert scope == Scope.CONDITION

    # WHERE scope
    pattern = 'WHERE CAST(V1 AS DATE)'
    rewrite = 'WHERE V1'
    pattern, scope = RuleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT * FROM t WHERE CAST(V1 AS DATE)'
    assert scope == Scope.WHERE
    rewrite, scope = RuleParser.extendToFullSQL(rewrite)
    assert rewrite == 'SELECT * FROM t WHERE V1'
    assert scope == Scope.WHERE

    # FROM scope
    pattern = 'FROM lineitem'
    rewrite = 'FROM v_lineitem'
    pattern, scope = RuleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT * FROM lineitem'
    assert scope == Scope.FROM
    rewrite, scope = RuleParser.extendToFullSQL(rewrite)
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
    pattern, scope = RuleParser.extendToFullSQL(pattern)
    assert pattern == '''
        select VL1
          from V1 V2, 
               V3 V4
         where V2.V6=V4.V8
           and VL2
    '''
    assert scope == Scope.SELECT
    rewrite, scope = RuleParser.extendToFullSQL(rewrite)
    assert rewrite == '''
        select VL1 
          from V1 V2
         where VL2
    '''
    assert scope == Scope.SELECT

    # SELECT scope with FROM
    pattern = 'SELECT VL1 FROM lineitem'
    rewrite = 'SELECT VL1 FROM v_lineitem'
    pattern, scope = RuleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT VL1 FROM lineitem'
    assert scope == Scope.SELECT
    rewrite, scope = RuleParser.extendToFullSQL(rewrite)
    assert rewrite == 'SELECT VL1 FROM v_lineitem'
    assert scope == Scope.SELECT

    # SELECT scope with only SELECT
    pattern = 'SELECT CAST(V1 AS DATE)'
    rewrite = 'SELECT V1'
    pattern, scope = RuleParser.extendToFullSQL(pattern)
    assert pattern == 'SELECT CAST(V1 AS DATE)'
    assert scope == Scope.SELECT
    rewrite, scope = RuleParser.extendToFullSQL(rewrite)
    assert rewrite == 'SELECT V1'
    assert scope == Scope.SELECT

def test_replaceVars():
    
    # single var case
    pattern = 'CAST(<x> AS DATE)'
    rewrite = '<x>'
    pattern, rewrite, mapping = RuleParser.replaceVars(pattern, rewrite)
    assert pattern == 'CAST(V001 AS DATE)'
    assert rewrite == 'V001'

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
    pattern, rewrite, mapping = RuleParser.replaceVars(pattern, rewrite)
    assert pattern == '''
        select VL001
          from V001 V002, 
               V003 V004
         where V002.V005=V004.V006
           and VL002
    '''
    assert rewrite == '''
        select VL001 
          from V001 V002
         where VL002
    '''

def test_parse():

    # Init test_rules
    test_rules = []
    # Rule 1:
    rule = {
        'pattern': 'CAST(<x> AS DATE)',
        'rewrite': '<x>'
    }
    internal_rule = {
        'pattern_json': '{"cast": ["V001", {"date": {}}]}',
        'rewrite_json': '"V001"'
    }
    test_rules.append((rule, internal_rule))
    # Rule 2:
    rule = {
        'pattern': "STRPOS(LOWER(<x>), '<s>') > 0",
        'rewrite': "<x> ILIKE '%<s>%'"
    }
    internal_rule = {
        'pattern_json': '{"gt": [{"strpos": [{"lower": "V001"}, {"literal": "V002"}]}, 0]}',
        'rewrite_json': '{"ilike": ["V001", {"literal": "%V002%"}]}'
    }
    test_rules.append((rule, internal_rule))

    # Test test_rules
    for rule, internal_rule in test_rules:
        pattern_json, rewrite_json, mapping = RuleParser.parse(rule['pattern'], rule['rewrite'])
        assert pattern_json == internal_rule['pattern_json']
        assert rewrite_json == internal_rule['rewrite_json']


#incorrect brackets
def test_brackets_1():
    
  pattern = '''WHERE <x] > 11
            AND <x> a <= 11
            '''
  
  index = RuleParser.find_malformed_brackets(pattern)
  assert index == 6

  #incorrect brackets
  def test_brackets_2():
        
    pattern = '''WHERE <x} > 11
                AND <x> a <= 11
                '''
    
    index = RuleParser.find_malformed_brackets(pattern)
    assert index == 6

#incorrect brackets
def test_parse_validator_3():
    
  pattern = '''WHERE <x) > 11
            AND <x> a <= 11
            '''

  index = RuleParser.find_malformed_brackets(pattern)
  assert index == 6

#incorrect brackets
  def test_parse_validator_4():
        
    pattern = '''WHERE [x> > 11
                AND <x> a <= 11
                '''
    
    index = RuleParser.find_malformed_brackets(pattern)
    assert index == 6


#incorrect brackets
  def test_parse_validator_5():
        
    pattern = '''WHERE (x> > 11
                AND <x> a <= 11
                '''
  
    index = RuleParser.find_malformed_brackets(pattern)
    assert index == 6
    
#incorrect brackets
  def test_parse_validator_6():
        
    pattern = '''WHERE {x> > 11
                AND <x> a <= 11
                '''
    index = RuleParser.find_malformed_brackets(pattern)
    assert index == 6
    
