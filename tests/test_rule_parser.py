from core.ast.enums import NodeType
from core.ast.node import (
    DataTypeNode,
    FunctionNode,
    QueryNode,
    SelectNode,
    VarNode,
    VarSetNode,
)
from core.rule_parser import RuleParser, RuleParseResult, Scope

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


def test_parse_v2_cast_rule():
    result = RuleParser.parse_v2('CAST(<x> AS DATE)', '<x>')
    assert isinstance(result, RuleParseResult)
    assert result.pattern_scope == Scope.CONDITION
    assert result.rewrite_scope == Scope.CONDITION
    assert result.mapping == {'x': 'V001'}
    assert isinstance(result.pattern_ast, FunctionNode)
    assert result.pattern_ast.name.lower() == 'cast'
    cast_args = list(result.pattern_ast.children)
    assert isinstance(cast_args[0], VarNode) and cast_args[0].name == 'x'
    assert isinstance(cast_args[1], DataTypeNode)
    assert isinstance(result.rewrite_ast, VarNode) and result.rewrite_ast.name == 'x'


def test_parse_v2_select_list_varset():
    pattern = 'select <<s1>> from lineitem where 1 = 1'
    rewrite = 'select <<s1>> from lineitem where 1 = 1'
    result = RuleParser.parse_v2(pattern, rewrite)
    assert result.pattern_scope == Scope.SELECT
    assert isinstance(result.pattern_ast, QueryNode)
    select = next(c for c in result.pattern_ast.children if c.type == NodeType.SELECT)
    assert isinstance(select, SelectNode)
    first = list(select.children)[0]
    assert isinstance(first, VarSetNode) and first.name == 's1'


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
    
