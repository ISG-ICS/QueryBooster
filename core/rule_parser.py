import re
from enum import Enum
from typing import Tuple


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

class RuleParser:

    def __init__(self) -> None:
        return
    
    def __del__(self):
       return
    
    # parse a rule (pattern, rewrite) into a SQL AST json str
    # 
    def parse(self, pattern: str, rewrite: str) -> Tuple[str, str]:
        # 1. replace user-faced variables and variable lists 
        #    with internal representations 
        # 
        pattern, rewrite = self.replaceVars(pattern, rewrite)

    # replace user-faced variables and variable lists with internal representations
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


if __name__ == '__main__':
    test_replaceVars()

    # Rule 1:
    # rule = {
    #     'pattern': 'CAST(<x> AS DATE)',
    #     'rewrite': '<x>'
    # }
    # internal_rule = {
    #     'pattern_json': '{"cast": ["v0", {"date": {}}]}',
    #     'rewrite_json': '"v0"'
    # }
    # pattern_json, rewrite_json = ruleParser.parse(rule['pattern'], rule['rewrite'])
    # assert pattern_json == internal_rule['pattern_json']
    # assert rewrite_json == internal_rule['rewrite_json']