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
        'internalBase': 'V',
        'externalBase': 'x',
    },
    VarType.VarList: {
        'markerStart': '<<',
        'markerEnd': '>>',
        'internalBase': 'VL',
        'exteranlBase': 'y'
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
    
    # parse a rule (pattern, rewrite) into a SQL AST json str
    # 
    @staticmethod
    def parse(pattern: str, rewrite: str) -> Tuple[str, str, str]:
        # 1. Replace user-faced variables and variable lists 
        #    with internal representations 
        # 
        pattern, rewrite, mapping = RuleParser.replaceVars(pattern, rewrite)

        # 2. Extend partial SQL statement to full SQL statement
        #    for the sake of sql parser
        # 
        pattern, patternScope = RuleParser.extendToFullSQL(pattern)
        rewrite, rewriteScope = RuleParser.extendToFullSQL(rewrite)

        # 3. Parse extended full SQL statement into AST json
        patternASTJson = mosql.parse(pattern)
        rewriteASTJson = mosql.parse(rewrite)

        # 4. Extract subtree from AST json based on scope
        patternASTJson = RuleParser.extractASTSubtree(patternASTJson, patternScope)
        rewriteASTJson = RuleParser.extractASTSubtree(rewriteASTJson, rewriteScope)

        # 5. Return the AST subtree as json string
        return json.dumps(patternASTJson), json.dumps(rewriteASTJson), json.dumps(mapping)

    #  Extend pattern/rewrite to full SQL statement
    # 
    @staticmethod
    def extendToFullSQL(partialSQL: str) -> Tuple[str, Scope]:
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
    @staticmethod
    def extractASTSubtree(aSTJson: Any, scope: Scope) -> Any:
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
    @staticmethod
    def replaceVars(pattern: str, rewrite: str) -> Tuple[str, str, dict]:
        
        # common function to replace one VarType
        # 
        def replaceVars(pattern: str, rewrite: str, varType: VarType, mapping: dict) -> Tuple[str, str]:
            regexPattern = VarTypesInfo[varType]['markerStart'] + '(\w+)' + VarTypesInfo[varType]['markerEnd']
            vars = re.findall(regexPattern, pattern)
            varInternalBase = VarTypesInfo[varType]['internalBase']
            varInternalCount = 1
            for var in vars:
                if var not in mapping:
                    # var -> varInternal map
                    #   e.g., <x> ==> V1, <<y>> ==> VL1
                    specificRegexPattern = VarTypesInfo[varType]['markerStart'] + var + VarTypesInfo[varType]['markerEnd']
                    varInternal = varInternalBase + str(varInternalCount).zfill(3)
                    varInternalCount += 1
                    # replace var with varInternal in both pattern and rewrite
                    pattern = re.sub(specificRegexPattern, varInternal, pattern)
                    rewrite = re.sub(specificRegexPattern, varInternal, rewrite)
                    # take down the mapping x -> V1
                    mapping[var] = varInternal
            return pattern, rewrite
        
        # replace VarList first, then Var
        mapping = {}
        pattern, rewrite = replaceVars(pattern, rewrite, VarType.VarList, mapping)
        pattern, rewrite = replaceVars(pattern, rewrite, VarType.Var, mapping)
        return pattern, rewrite, mapping
        
    # parse a rule constraints into a list of conditions
    #
    @staticmethod
    def parse_constraints(constraints: str, mapping: str) -> str:
        mapping = json.loads(mapping)
        _conditions = constraints.lower().split('and')
        conditions = []
        for _condition in _conditions:
            condition = {}
            # TODO - we only support = conditions now
            # 
            if '=' in _condition:
                condition['operator'] = '='
                condition['operands'] = []
                _operands = _condition.split('=')
                for _operand in _operands:
                    if '(' in _operand and ')' in _operand:
                        operand = {}
                        func = RuleParser.extractFunc(_operand)
                        vars = RuleParser.extractVars(_operand)
                        operand['function'] = func
                        operand['variables'] = [mapping[var] if var in mapping else var for var in vars]
                    else:
                        operand = mapping[_operand] if _operand in mapping else _operand
                    condition['operands'].append(operand)
                conditions.append(condition)
            # or a boolean function, e.g., UNIQUE(t1, a1)
            #    we treat it as UNIQUE(t1, a1) = TRUE automatically
            # 
            else:
                condition['operator'] = '='
                condition['operands'] = []
                _operand = _condition
                if '(' in _operand and ')' in _operand:
                    operand = {}
                    func = RuleParser.extractFunc(_operand)
                    vars = RuleParser.extractVars(_operand)
                    operand['function'] = func
                    operand['variables'] = [mapping[var] if var in mapping else var for var in vars]
                else:
                    operand = mapping[_operand] if _operand in mapping else _operand
                condition['operands'].append(operand)
                condition['operands'].append('true')
                conditions.append(condition)

        return json.dumps(conditions)
    
    # extract function name from an operand in a condition in constraints
    # 
    @staticmethod
    def extractFunc(operand: str) -> str:
        parts = operand.split('(')
        return parts[0].strip()
    
    # extract variables inside a function of an operand in a condition in constraints
    # 
    @staticmethod
    def extractVars(operand: str) -> list:
        parts = operand.split(')')
        parts = parts[0].split('(')
        vars = parts[1].split(',')
        return [var.strip() for var in vars]
    
    # parse a rule actions into a list of actions
    # 
    @staticmethod
    def parse_actions(actions: str, mapping: str) -> list:
        mapping = json.loads(mapping)
        _actions = actions.lower().split('and')
        actions = []
        for _action in _actions:
            # TODO - we only support function in actions now
            # 
            if '(' in _action and ')' in _action:
                action = {}
                func = RuleParser.extractFunc(_action)
                vars = RuleParser.extractVars(_action)
                action['function'] = func
                action['variables'] = [mapping[var] if var in mapping else var for var in vars]
                actions.append(action)
        return json.dumps(actions)


if __name__ == '__main__':

    def print_rule(_title, _pattern, _rewrite, _constraints="", _actions=""):
        _patternASTJson, _rewriteASTJson, _mapping = RuleParser.parse(_pattern, _rewrite)
        _constraintsJson = RuleParser.parse_constraints(_constraints, _mapping)
        _actionsJson = RuleParser.parse_actions(_actions, _mapping)
        print()
        print("==================================================")
        print("    " + _title)
        print("--------------------------------------------------")
        print("pattern     |  " + _pattern)
        print("constraints |  " + _constraints)
        print("rewrite     |  " + _rewrite)
        print("actions     |  " + _actions)
        print("--------------------------------------------------")
        print("pattern AST Json |  " + _patternASTJson)
        print("constraints Json |  " + _constraintsJson)
        print("rewrite AST Json |  " + _rewriteASTJson)
        print("actions Json     |  " + _actionsJson)
        print("vars mapping     |  " + _mapping)

    # rule 1
    pattern = 'CAST(<x> AS DATE)'
    rewrite = '<x>'
    constraints = "TYPE(x) = DATE"
    print_rule('Rule 1', pattern, rewrite, constraints)
    
    # rule 2
    pattern = 'STRPOS(LOWER(<x>), <y>) > 0'
    rewrite = "<x> ILIKE '%<y>%'"
    print_rule('Rule 2', pattern, rewrite)

    # rule 3
    pattern = '''
            select <<s1>>
            from <tb1> <t1>, 
                 <tb1> <t2>
            where <t1>.<a1>=<t2>.<a1>
            and <<p1>>
        '''
    rewrite = '''
            select <<s1>> 
            from <tb1> <t1>
            where 1=1 
            and <<p1>>
        '''
    print_rule('Rule 3', pattern, rewrite)

    # rule 101
    pattern = 'ADDDATE(<x>, INTERVAL 0 SECOND)'
    rewrite = '<x>'
    print_rule('Rule 101', pattern, rewrite)

    # rule 102
    pattern = '<x> = TIMESTAMP(<y>)'
    rewrite = '<x> = <y>'
    print_rule('Rule 102', pattern, rewrite)