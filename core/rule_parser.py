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
