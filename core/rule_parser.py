from enum import Enum
import json
import mo_sql_parsing as mosql
import re
from typing import Any, Tuple


# Variable Type
# 
class VarType(Enum):
    Var = 1
    VarList = 2

# Variable Types' infro
VarTypesInfo = {
    VarType.Var: {
        'markerStart': '<',
        'markerEnd': '>',
        'internalBase': 'V'
    },
    VarType.VarList: {
        'markerStart': '<<',
        'markerEnd': '>>',
        'internalBase': 'VL'
    }
}

# Scope of pattern/rewrite describes
class Scope(Enum):
    SELECT = 1
    FROM = 2
    WHERE = 3
    CONDITION = 4

# Partial SQL statement for extension
ScopeExtension = {
    Scope.CONDITION: 'SELECT * FROM t WHERE ',
    Scope.WHERE: 'SELECT * FROM t ',
    Scope.FROM: 'SELECT * ',
    Scope.SELECT: ''
}

class RuleParser:

    def __init__(self) -> None:
        return
    
    def __del__(self):
       return
    
    # parse a rule (pattern, rewrite) into a SQL AST json str
    # 
    def parse(self, pattern: str, rewrite: str) -> Tuple[str, str]:
        # 1. Replace user-faced variables and variable lists 
        #    with internal representations 
        # 
        pattern, rewrite = self.replaceVars(pattern, rewrite)

        # 2. Extend partial SQL statement to full SQL statement
        #    for the sake of sql parser
        # 
        pattern, patternScope = self.extendToFullSQL(pattern)
        rewrite, rewriteScope = self.extendToFullSQL(rewrite)

        # 3. Parse extended full SQL statement into AST json
        patternASTJson = mosql.parse(pattern)
        rewriteASTJson = mosql.parse(rewrite)

        # 4. Extract subtree from AST json based on scope
        patternASTJson = self.extractASTSubtree(patternASTJson, patternScope)
        rewriteASTJson = self.extractASTSubtree(rewriteASTJson, rewriteScope)

        # 5. Return the AST subtree as json string
        return json.dumps(patternASTJson), json.dumps(rewriteASTJson)

    #  Extend pattern/rewrite to full SQL statement
    # 
    def extendToFullSQL(self, partialSQL: str) -> Tuple[str, Scope]:
        # case-1: no SELECT and no FROM and no WHERE
        if not 'SELECT' in partialSQL.upper() and \
            not 'FROM' in partialSQL.upper() and \
                not 'WHERE' in partialSQL.upper():
            scope = Scope.CONDITION
        # case-2: no SELECT and no FROM but has WHERE
        elif not 'SELECT' in partialSQL.upper() and \
            not 'FROM' in partialSQL.upper():
            scope = Scope.WHERE
        # case-3: no SELECT but has FROM
        elif not 'SELECT' in partialSQL.upper():
            scope = Scope.FROM
        # case-4: has SELECT and has FROM
        else:
            scope = Scope.SELECT
        
        partialSQL = ScopeExtension[scope] + partialSQL
        return partialSQL, scope
    
    # Extract the AST subtree of pattern/rewrite based on scope
    # 
    def extractASTSubtree(self, aSTJson: Any, scope: Scope) -> Any:
        if scope == Scope.CONDITION:
            aSTJson = aSTJson['where']
        elif scope == Scope.WHERE:
            aSTJson.pop('select', None)
            aSTJson.pop('from', None)
        elif scope == Scope.FROM:
            aSTJson.pop('select', None)
        return aSTJson

    # Replace user-faced variables and variable lists with internal representations
    #   e.g., <x> ==> V1, <<y>> ==> VL1
    # 
    def replaceVars(self, pattern: str, rewrite: str) -> Tuple[str, str]:
        
        # common function to replace one VarType
        # 
        def replaceVars(pattern: str, rewrite: str, varType: VarType) -> Tuple[str, str]:
            regexPattern = VarTypesInfo[varType]['markerStart'] + '(\w+)' + VarTypesInfo[varType]['markerEnd']
            vars = re.findall(regexPattern, pattern)
            varInternalBase = VarTypesInfo[varType]['internalBase']
            varInternalCount = 1
            for var in vars:
                # var -> varInternal map
                #   e.g., <x> ==> V1, <<y>> ==> VL1
                specificRegexPattern = VarTypesInfo[varType]['markerStart'] + var + VarTypesInfo[varType]['markerEnd']
                varInternal = varInternalBase + str(varInternalCount)
                varInternalCount += 1
                # replace var with varInternal in both pattern and rewrite
                pattern = re.sub(specificRegexPattern, varInternal, pattern)
                rewrite = re.sub(specificRegexPattern, varInternal, rewrite)
            return pattern, rewrite
        
        # replace VarList first, then Var
        pattern, rewrite = replaceVars(pattern, rewrite, VarType.VarList)
        pattern, rewrite = replaceVars(pattern, rewrite, VarType.Var)
        return pattern, rewrite


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
    pattern, rewrite = ruleParser.replaceVars(pattern, rewrite)
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
    pattern, rewrite = ruleParser.replaceVars(pattern, rewrite)
    assert pattern == '''
        select VL1
          from V1 V2, 
               V3 V4
         where V2.V6=V4.V8
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
        'pattern': 'STRPOS(LOWER(<x>), <s>) > 0',
        'rewrite': '<x> ILIKE "%<s>%"'
    }
    internal_rule = {
        'pattern_json': '{"gt": [{"strpos": [{"lower": "V1"}, "V2"]}, 0]}',
        'rewrite_json': '{"ilike": ["V1", "%V2%"]}'
    }
    test_rules.append((rule, internal_rule))

    # Test test_rules
    for rule, internal_rule in test_rules:
        pattern_json, rewrite_json = ruleParser.parse(rule['pattern'], rule['rewrite'])
        print(pattern_json)
        print(rewrite_json)
        assert pattern_json == internal_rule['pattern_json']
        assert rewrite_json == internal_rule['rewrite_json']


if __name__ == '__main__':
    test_replaceVars()
    test_extendToFullSQL()
    test_parse()
    