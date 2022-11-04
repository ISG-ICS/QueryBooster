from typing import Any, Union
import copy
from core.profiler import Profiler
from core.query_rewriter import QueryRewriter
from core.rule_parser import RuleParser, Scope, VarType, VarTypesInfo
import json
import mo_sql_parsing as mosql
import numbers
import re


class RuleGenerator:

    # Generate the seed rule for a given rewriting pair q0 -> q1
    #
    @staticmethod
    def generate_seed_rule(q0: str, q1: str) -> dict:
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

        return {'pattern': RuleGenerator.deparse(patternASTJson), 'rewrite': RuleGenerator.deparse(rewriteASTJson)}
    
    @staticmethod
    def deparse(astJson: Any) -> str:
        # Extend given AST Json to a full AST Json
        # 
        fullASTJson, scope = RuleGenerator.extendToFullASTJson(astJson)

        # Format full AST Json into SQL statement
        # 
        fullSQL = mosql.format(fullASTJson)

        # Extract partial SQL statement based on scope
        #
        partialSQL = RuleGenerator.extractPartialSQL(fullSQL, scope)

        return partialSQL

    # Dereplace internal representations with user-faced variables and variable lists 
    #   e.g., V1 ==> <x>, VL1 ==> <<y>>
    # 
    @staticmethod
    def dereplaceVars(pattern: str, mapping: dict) -> str:
        
        for varExternal, varInternal in mapping.items():
            varType = RuleGenerator.varType(varInternal)
            var = VarTypesInfo[varType]['markerStart'] + varExternal + VarTypesInfo[varType]['markerEnd']
            # replace varInternal with var
            pattern = re.sub(varInternal, var, pattern)
        
        return pattern
    
    @staticmethod
    def varType(var: str) -> VarType:
        if var.startswith(VarTypesInfo[VarType.VarList]['internalBase']):
            return VarType.VarList
        elif var.startswith(VarTypesInfo[VarType.Var]['internalBase']):
            return VarType.Var
        else:
            return None
    
    @staticmethod
    def minDiffSubtree(leftNode: Any, rightNode: Any) -> tuple[Any, Any]:
        # Case-1: both nodes are dict
        #
        if QueryRewriter.is_dict(leftNode) and QueryRewriter.is_dict(rightNode):
            return RuleGenerator.minDiffSubtreeInDicts(leftNode, rightNode)
        
        # Case-2: both nodes are list
        #
        if QueryRewriter.is_list(leftNode) and QueryRewriter.is_list(rightNode):
            return RuleGenerator.minDiffSubtreeInLists(leftNode, rightNode)
        
        # Case-3: both nodes are constants
        # 
        if QueryRewriter.is_constant(leftNode) and QueryRewriter.is_constant(rightNode):
            return RuleGenerator.minDiffSubtreeInConstants(leftNode, rightNode)
        
        # Case-4: both nodes are dot expressions
        # 
        if QueryRewriter.is_dot_expression(leftNode) and QueryRewriter.is_dot_expression(rightNode):
            return RuleGenerator.minDiffSubtreeInDotExpressions(leftNode, rightNode)
        
        # Other cases: return themselves
        return leftNode, rightNode
    
    @staticmethod
    def minDiffSubtreeInStrings(leftNode: str, rightNode: str) -> tuple[Any, Any]:
        if leftNode.lower() == rightNode.lower():
            return None, None
        return leftNode, rightNode
    
    @staticmethod
    def minDiffSubtreeInNumbers(leftNode: numbers, rightNode: numbers) -> tuple[Any, Any]:
        if leftNode == rightNode:
            return None, None
        return leftNode, rightNode

    @staticmethod
    def minDiffSubtreeInConstants(leftNode: Any, rightNode: Any) -> tuple[Any, Any]:
        if QueryRewriter.is_string(leftNode) and QueryRewriter.is_string(rightNode):
            return RuleGenerator.minDiffSubtreeInStrings(leftNode, rightNode)
        if QueryRewriter.is_number(leftNode) and QueryRewriter.is_number(rightNode):
            return RuleGenerator.minDiffSubtreeInNumbers(leftNode, rightNode)
        return leftNode, rightNode
    
    @staticmethod
    def minDiffSubtreeInDotExpressions(leftNode: str, rightNode: str) -> tuple[Any, Any]:
        leftChildren = leftNode.split('.')
        rightChildren = rightNode.split('.')
        # if they have different length
        if len(leftChildren) != 2 or len(rightChildren) != 2:
            return leftNode, rightNode
        
        leftSubtree, rightSubtree = RuleGenerator.minDiffSubtreeInStrings(leftChildren[0], rightChildren[0])
        if leftSubtree is None and rightSubtree is None:
            return RuleGenerator.minDiffSubtreeInStrings(leftChildren[1], rightChildren[1])
        else:
            leftSubtree1, rightSubtree1 = RuleGenerator.minDiffSubtreeInStrings(leftChildren[1], rightChildren[1])
            if leftSubtree1 is None and rightSubtree1 is None:
                return leftSubtree, rightSubtree
            else:
                return leftNode, rightNode

    @staticmethod
    def minDiffSubtreeInDicts(leftNode: dict, rightNode: dict) -> tuple[Any, Any]:
        # if they have different keys, return themselves
        #
        if set(leftNode.keys()) != set(rightNode.keys()):
            return leftNode, rightNode
        
        # otherwise, traverse the keys,
        #   if zero keys have different subtrees:
        #     they are identical, return None, None
        #   if one key have different subtrees:
        #     return their recursive minDiffSubstree()
        #   if more than one keys have different subtrees:
        #     return leftNode, rightNode
        # 
        cntDiffSubtrees = 0
        leftSubtree = None
        rightSubtree = None
        for k in leftNode.keys():
            leftChild = leftNode.get(k)
            rightChild = rightNode.get(k)
            left, right = RuleGenerator.minDiffSubtree(leftChild, rightChild)
            # if two subtrees are identical
            #
            if left is None and right is None:
                continue
            # otherwise, two subtrees are different
            #
            # if this is the first key whose two children are different
            #   memorize them 
            if cntDiffSubtrees == 0:
                cntDiffSubtrees = 1
                leftSubtree = left
                rightSubtree = right
            # otherwise, more than one keys share different subtrees
            #   return leftNode, rightNode
            else:
                return leftNode, rightNode
        
        # return memorized two subtrees
        #
        return leftSubtree, rightSubtree

    @staticmethod
    def minDiffSubtreeInLists(leftNode: list, rightNode: list) -> tuple[Any, Any]:
        # if they have different length, return themselves
        #
        if len(leftNode) != len(rightNode):
            return leftNode, rightNode
        
        # otherwise, count how many elements in rightNode has no match in leftNode
        # 
        remainingInLeftNode = leftNode.copy()
        remainingInRightNode = rightNode.copy()
        for leftChild in leftNode:
            for rightChild in remainingInRightNode:
                left, right = RuleGenerator.minDiffSubtree(leftChild, rightChild)
                # if found identical subtree for leftChild
                #
                if left is None and right is None:
                    remainingInLeftNode.remove(leftChild)
                    remainingInRightNode.remove(rightChild)
                    break
        #   if no element in rightNode has no match in leftNode:
        #     they are identical, return None, None
        # 
        if len(remainingInRightNode) == 0:
            return None, None
        #   if exact one element in rightNode and exact one element in leftNode has no match:
        #     return their recursive minDiffSubstree()
        # 
        elif len(remainingInRightNode) == 1 and len(remainingInLeftNode) == 1:
            return RuleGenerator.minDiffSubtree(remainingInLeftNode[0], remainingInRightNode[0])
        #   if more than one elements in rightNode have no match:
        #     return leftNode, rightNode
        # 
        else:
            return leftNode, rightNode
    
    @staticmethod
    def extendToFullASTJson(node: Any) -> tuple[Any, Scope]:
        # case-1: no SELECT and no FROM and no WHERE
        if not RuleGenerator.existKeywordInASTJson(node, 'SELECT') and \
            not RuleGenerator.existKeywordInASTJson(node, 'FROM') and \
                not RuleGenerator.existKeywordInASTJson(node, 'WHERE'):
            scope = Scope.CONDITION
            root = {'select': '*', 'from': 't'}
            root['where'] = node
            return root, scope
        # case-2: no SELECT and no FROM but has WHERE
        elif not RuleGenerator.existKeywordInASTJson(node, 'SELECT') and \
            not RuleGenerator.existKeywordInASTJson(node, 'FROM'):
            scope = Scope.WHERE
            node['select'] = '*'
            node['from'] = 't'
            return node, scope
        # case-3: no SELECT but has FROM
        elif not RuleGenerator.existKeywordInASTJson(node, 'SELECT'):
            scope = Scope.FROM
            node['select'] = '*'
            return node, scope
        # case-4: has SELECT and has FROM
        else:
            scope = Scope.SELECT
            return node, scope
    
    @staticmethod
    def existKeywordInASTJson(node: Any, keyword: str) -> bool:
        if QueryRewriter.is_dict(node):
            if keyword.lower() in node.keys():
                return True
        return False
    
    @staticmethod
    def extractPartialSQL(fullSQL: str, scope: Scope) -> str:
        if scope == Scope.SELECT:
            return fullSQL
        elif scope == Scope.FROM:
            return fullSQL.replace('SELECT * ', '')
        elif scope == Scope.WHERE:
            return fullSQL.replace('SELECT * FROM t ', '')
        else:
            return fullSQL.replace('SELECT * FROM t WHERE ', '')
    

    # Generate the candidate rule graph for a given rewriting pair q0 -> q1
    #
    @staticmethod
    def generate_rule_graph(q0: str, q1: str) -> dict:
        
        # Generate seedRule from the given rewriting pair
        #
        seedRule = RuleGenerator.generate_seed_rule(q0, q1)

        # Parse seedRule's pattern and rewrite into SQL AST json
        #
        seedRule['pattern_json'], seedRule['rewrite_json'], seedRule['mapping'] = RuleParser.parse(seedRule['pattern'], seedRule['rewrite'])
        
        # Initially, seedRule has no constraints and actions
        #
        seedRule['constraints'], seedRule['constraints_json'], seedRule['actions'], seedRule['actions_json'] = '', '[]', '', '[]'

        # Generate the candidate rule graph starting from seedRule
        #   Breadth First Search
        #
        seedRuleFingerPrint = RuleGenerator.fingerPrint(seedRule)
        visited = {seedRuleFingerPrint: seedRule}
        queue = [seedRule]
        graphRoot = seedRule
        while len(queue) > 0:
            baseRule = queue.pop(0)
            baseRule['children'] = []
            # generate children from the baseRule
            # by applying each transformation on baseRule
            for transform in RuleGenerator.RuleTransformations.keys():
                childrenRules = getattr(RuleGenerator, transform)(baseRule)
                for childRule in childrenRules:
                    childRuleFingerPrint = RuleGenerator.fingerPrint(childRule)
                    # if childRule has not been visited
                    if childRuleFingerPrint not in visited.keys():
                        visited[childRuleFingerPrint] = childRule
                        queue.append(childRule)
                        baseRule['children'].append(childRule)
                    # else childRule has been visited (generated from an ealier baseRule)
                    else:
                        baseRule['children'].append(visited[childRuleFingerPrint])
        return graphRoot
    
    @staticmethod
    def fingerPrint(rule: dict) -> str:
        # use rule['pattern'] string as finger-print
        #   and get rid of the numbers inside each var/varList
        #   e.g., we want to treat these two generated rules as the same rule:
        #         rule 1: SELECT e1.<x1>, e1.<x2> FROM employee e1 WHERE e1.<x1> > 17 AND e1.<x2> > 35000
        #         rule 2: SELECT e1.<x2>, e1.<x1> FROM employee e1 WHERE e1.<x2> > 17 AND e1.<x1> > 35000
        fingerPrint = rule['pattern']
        fingerPrint = re.sub(r"<x(\d+)>", "<x>", fingerPrint)
        fingerPrint = re.sub(r"<<y(\d+)>>", "<<y>>", fingerPrint)
        return fingerPrint

    # transformation function - variablize columns in a rule
    #   generate a list of child rules 
    #
    @staticmethod
    def variablize_columns(rule: dict) -> list:

        Profiler.onFunctionStart('varialize_columns')

        res = []

        # 1. Get candidate columns from rule
        #
        columns = RuleGenerator.columns(rule['pattern_json'], rule['rewrite_json'])

        # 2. Traverse candidate columns, make one of them variable, and generate a new rule
        #
        for column in columns:
            res.append(RuleGenerator.variablize_column(rule, column))
        
        Profiler.onFunctionEnd('varialize_columns')

        return res

    # get list of common columns in a seed rule's pattern_json and rewrite_json
    #
    @staticmethod
    def columns(pattern_json: str, rewrite_json: str) -> list:
        
        patternASTJson = json.loads(pattern_json)
        rewriteASTJson = json.loads(rewrite_json)

        # traverse the AST jsons to get all columns
        patternColumns = RuleGenerator.columnsOfASTJson(patternASTJson, [])
        rewriteColumns = RuleGenerator.columnsOfASTJson(rewriteASTJson, [])

        # TODO - patternColumns should be superset of rewriteColumns
        #
        return list(patternColumns)
    
    # recursively get set of columns in a rule pattern/rewrite's AST Json
    #
    @staticmethod
    def columnsOfASTJson(astJson: Any, path: list) -> set:
        res = set()

        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            for key, value in astJson.items():
                # skip value of 'literal' as key
                if type(key) is str and key.lower() == 'literal':
                    continue
                # note: key can not be column, only traverse each value
                res.update(RuleGenerator.columnsOfASTJson(value, path + [key]))

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            for child in astJson:
                res.update(RuleGenerator.columnsOfASTJson(child, path))

        # Case-3: string
        if QueryRewriter.is_string(astJson):
            # skip case-1: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #            path = ['from', 'value'], patternASTJson = 'employee'
            #            path = ['from', 'name'], patternASTJson = 'e1'
            #      case-2: {'from': 'employee'}
            #            path = ['from']
            #
            if not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value') and \
               not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name') and \
               not (len(path) >=1 and path[-1] == 'from'):
                # ignore * in SELECT clause
                #
                if astJson != '*':
                    res.add(astJson)
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            # skip case-1: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #            path = ['from', 'value'], patternASTJson = 'employee'
            #            path = ['from', 'name'], patternASTJson = 'e1'
            #      case-2: {'from': 'employee'}
            #            path = ['from']
            #
            if not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value') and \
               not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name') and \
               not (len(path) >=1 and path[-1] == 'from'):
                candidate = astJson.split('.')[-1]
                # skip case: e1.<a1>
                #
                if not QueryRewriter.is_var(candidate) and not QueryRewriter.is_varList(candidate):
                    # ignore e1.* in SELECT clause
                    #
                    if candidate != '*':
                        res.add(candidate)
        
        return res
    
    
    # variablize the given column in given rule and generate a new rule
    #
    @staticmethod
    def variablize_column(rule: dict, column: str) -> dict:

        # create a new rule based on rule
        new_rule = copy.deepcopy(rule)

        # Find a variable name for the given column
        #
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_mapping, newVarInternal = RuleGenerator.findNextVarInternal(new_rule_mapping)
        new_rule['mapping'] = json.dumps(new_rule_mapping)

        # Replace given column into newVarInternal in new rule
        #
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])
        new_rule_pattern_json = RuleGenerator.replaceColumnsOfASTJson(new_rule_pattern_json, [], column, newVarInternal)
        new_rule_rewrite_json = RuleGenerator.replaceColumnsOfASTJson(new_rule_rewrite_json, [], column, newVarInternal)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)

        # TODO - add newVarInternal is a column constraint into new rule's constraints

        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # recursively replace given column into given var in a rule's pattern/rewrite AST Json
    #
    @staticmethod
    def replaceColumnsOfASTJson(astJson: Any, path: list, column: str, var: str) -> Any:
        
        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            for key, value in astJson.items():
                # skip value of 'literal' as key
                if type(key) is str and key.lower() == 'literal':
                    continue
                # note: key can not be column, only traverse each value
                astJson[key] = RuleGenerator.replaceColumnsOfASTJson(value, path + [key], column, var)
            return astJson

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            res = []
            for child in astJson:
                res.append(RuleGenerator.replaceColumnsOfASTJson(child, path, column, var))
            return res

        # Case-3: string
        if QueryRewriter.is_string(astJson):
            # skip case-1: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #            path = ['from', 'value'], patternASTJson = 'employee'
            #            path = ['from', 'name'], patternASTJson = 'e1'
            #      case-2: {'from': 'employee'}
            #            path = ['from']
            #
            if not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value') and \
               not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name') and \
               not (len(path) >=1 and path[-1] == 'from'):
                if astJson == column:
                    return var
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            # skip case-1: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #            path = ['from', 'value'], patternASTJson = 'employee'
            #            path = ['from', 'name'], patternASTJson = 'e1'
            #      case-2: {'from': 'employee'}
            #            path = ['from']
            #
            if not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value') and \
               not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name') and \
               not (len(path) >=1 and path[-1] == 'from'):
                candidate = astJson.split('.')[-1]
                # skip case: e1.<a1>
                #
                if not QueryRewriter.is_var(candidate) and not QueryRewriter.is_varList(candidate):
                    if candidate == column:
                        return '.'.join(astJson.split('.')[0:-1] + [var])
        
        return astJson
    
    # Find the next Var internal name given the current mapping
    #   Traverse all var/varList mappings in rule
    #     Count the max number of var
    # Return the new mapping with the new Var map (e.g., <x3> -> VL3) and the new VarInternal (e.g., VL3)
    #
    @staticmethod
    def findNextVarInternal(mapping: dict) -> tuple[dict, str]:
        maxVarNum = 0
        for varInternal in mapping.values():
            if VarTypesInfo[VarType.VarList]['internalBase'] not in varInternal and VarTypesInfo[VarType.Var]['internalBase'] in varInternal:
                num = int(varInternal.split(VarTypesInfo[VarType.Var]['internalBase'], 1)[1])
                if num > maxVarNum:
                    maxVarNum = num
        newVarNum = maxVarNum + 1
        newVarInternal = VarTypesInfo[VarType.Var]['internalBase'] + str(newVarNum)
        newVarExternal = VarTypesInfo[VarType.Var]['externalBase'] + str(newVarNum)
        # add new map into mapping
        mapping[newVarExternal] = newVarInternal
        return mapping, newVarInternal

    # transformation function - variablize literals in a rule
    #   generate a list of child rules 
    #
    @staticmethod
    def variablize_literals(rule: dict) -> list:

        Profiler.onFunctionStart('variablize_literals')

        res = []

        # 1. Get candidate literals from rule
        #
        literals = RuleGenerator.literals(rule['pattern_json'], rule['rewrite_json'])

        # 2. Traverse candidate literals, make one of them variable, and generate a new rule
        #
        for literal in literals:
            res.append(RuleGenerator.variablize_literal(rule, literal))
        
        Profiler.onFunctionEnd('variablize_literals')
        
        return res
    
    # get list of common literals in a seed rule's pattern_json and rewrite_json
    #
    @staticmethod
    def literals(pattern_json: str, rewrite_json: str) -> list:
        
        patternASTJson = json.loads(pattern_json)
        rewriteASTJson = json.loads(rewrite_json)

        # traverse the AST jsons to get all literals
        patternLiterals = RuleGenerator.literalsOfASTJson(patternASTJson, [])
        rewriteLiterals = RuleGenerator.literalsOfASTJson(rewriteASTJson, [])

        return list(patternLiterals.intersection(rewriteLiterals))
    
    # recursively get set of literals in a rule pattern/rewrite's AST Json
    #
    @staticmethod
    def literalsOfASTJson(astJson: Any, path: list) -> set:
        res = set()

        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            for key, value in astJson.items():
                # note: key can not be literal, only traverse each value
                res.update(RuleGenerator.literalsOfASTJson(value, path + [key]))

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            for child in astJson:
                res.update(RuleGenerator.literalsOfASTJson(child, path))

        # Case-3: string
        if QueryRewriter.is_string(astJson):
            # literal is the value of 'literal' key
            if len(path) >= 1 and type(path[-1]) is str and path[-1].lower() == 'literal':
                # special case for {'literal': '%iphone%'}
                #   get rid of wildcard chars in a literal
                #
                res.add(str(astJson).replace('%', ''))
        
        # Case-4: dot expression (false postive, if it is value of 'literal' key)
        if QueryRewriter.is_dot_expression(astJson):
            # literal is the value of 'literal' key
            if len(path) >= 1 and type(path[-1]) is str and path[-1].lower() == 'literal':
                # special case for {'literal': '%iphone.14%'}
                #   get rid of wildcard chars in a literal
                #
                res.add(str(astJson).replace('%', ''))
        
        # Case-5: number
        if QueryRewriter.is_number(astJson):
            res.add(astJson)
        
        return res
    
    # variablize the given literal in given rule and generate a new rule
    #
    @staticmethod
    def variablize_literal(rule: dict, literal: Union[str, numbers.Number]) -> dict:

        # create a new rule based on rule
        new_rule = copy.deepcopy(rule)

        # Find a variable name for the given literal
        #
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_mapping, newVarInternal = RuleGenerator.findNextVarInternal(new_rule_mapping)
        new_rule['mapping'] = json.dumps(new_rule_mapping)

        # Replace given literal into newVarInternal in new rule
        #
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])
        new_rule_pattern_json = RuleGenerator.replaceLiteralsOfASTJson(new_rule_pattern_json, [], literal, newVarInternal)
        new_rule_rewrite_json = RuleGenerator.replaceLiteralsOfASTJson(new_rule_rewrite_json, [], literal, newVarInternal)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)

        # TODO - add newVarInternal is a literal constraint into new rule's constraints

        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # recursively replace given literal into given var in a rule's pattern/rewrite AST Json
    #
    @staticmethod
    def replaceLiteralsOfASTJson(astJson: Any, path: list, literal: Union[str, numbers.Number], var: str) -> Any:
        
        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            for key, value in astJson.items():
                # note: key can not be literal, only traverse each value
                astJson[key] = RuleGenerator.replaceLiteralsOfASTJson(value, path + [key], literal, var)
            return astJson

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            res = []
            for child in astJson:
                res.append(RuleGenerator.replaceLiteralsOfASTJson(child, path, literal, var))
            return res

        # Case-3: string
        if QueryRewriter.is_string(astJson):
            # literal is the value of 'literal' key
            if len(path) >= 1 and type(path[-1]) is str and path[-1].lower() == 'literal':
                if astJson == literal:
                    return var
                # note: handle special case with wildcard chars, e.g., {'literal': '%iphone%'}
                #
                if str(astJson).replace('%', '') == literal:
                    return str(astJson).replace(literal, var)
        
        # Case-4: dot expression (false postive, if it is value of 'literal' key)
        if QueryRewriter.is_dot_expression(astJson):
            # literal is the value of 'literal' key
            if len(path) >= 1 and type(path[-1]) is str and path[-1].lower() == 'literal':
                if astJson == literal:
                    return var
                # note: handle special case with wildcard chars, e.g., {'literal': '%iphone%'}
                #
                if str(astJson).replace('%', '') == literal:
                    return str(astJson).replace(literal, var)
        
        # Case-5: number
        if QueryRewriter.is_number(astJson):
            if astJson == literal:
                return var
        
        return astJson
    
    # transformation function - variablize aliases in a rule
    #   generate a list of child rules 
    #
    @staticmethod
    def variablize_aliases(rule: dict) -> list:

        Profiler.onFunctionStart('variablize_aliases')

        res = []

        # 1. Get candidate aliases from rule
        #
        aliases = RuleGenerator.aliases(rule['pattern_json'], rule['rewrite_json'])

        # 2. Traverse candidate aliases, make one of them variable, and generate a new rule
        #
        for alias in aliases:
            res.append(RuleGenerator.variablize_alias(rule, alias))
        
        Profiler.onFunctionEnd('variablize_aliases')

        return res
    
    # get list of common aliases in a seed rule's pattern_json and rewrite_json
    #
    @staticmethod
    def aliases(pattern_json: str, rewrite_json: str) -> list:
        
        patternASTJson = json.loads(pattern_json)
        rewriteASTJson = json.loads(rewrite_json)

        # traverse the AST jsons to get all aliases
        patternAliases = RuleGenerator.aliasesOfASTJson(patternASTJson, [])
        rewriteAliases = RuleGenerator.aliasesOfASTJson(rewriteASTJson, [])

        # TODO - patternAliases should be superset of rewriteAliases
        #
        return list(patternAliases)
    
    # recursively get set of aliases in a rule pattern/rewrite's AST Json
    #   Aliases only appear in two forms (in astJson generated by mo_sql_parsing)
    #   (1) dot_expression: e.g., {"gt": ["e1.age", 17]} or "select": [{"value": "e1.name"},...
    #   (2) name of table in 'FROM' clause: e.g., "from": [{"value": "employee", "name": "e1"}, ...
    #
    @staticmethod
    def aliasesOfASTJson(astJson: Any, path: list) -> set:
        res = set()

        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            for key, value in astJson.items():
                # note: key can not be alias, only traverse each value
                res.update(RuleGenerator.aliasesOfASTJson(value, path + [key]))

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            for child in astJson:
                res.update(RuleGenerator.aliasesOfASTJson(child, path))

        # Case-3: string
        if QueryRewriter.is_string(astJson):
            # alias is the value of "name" if:
            #   path = ['from', 'name'], patternASTJson is string
            #
            if len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name':
                res.add(astJson)
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            # skip case: {'from': [{'value': 'schema.table', 'name': 't1'}]}
            #            path = ['from', 'value'], patternASTJson = 'schema.table'
            #
            if not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value'):
                # TODO - assert only one '.' exist in dot expression
                if len(astJson.split('.')) == 2:
                    candidate = astJson.split('.')[0]
                    # skip case: <x1>.id
                    #
                    if not QueryRewriter.is_var(candidate) and not QueryRewriter.is_varList(candidate):
                        res.add(candidate)
        
        return res
    
    # variablize the given alias in given rule and generate a new rule
    #
    @staticmethod
    def variablize_alias(rule: dict, alias: str) -> dict:

        # create a new rule based on rule
        new_rule = copy.deepcopy(rule)

        # Find a variable name for the given alias
        #
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_mapping, newVarInternal = RuleGenerator.findNextVarInternal(new_rule_mapping)
        new_rule['mapping'] = json.dumps(new_rule_mapping)

        # Replace given alias into newVarInternal in new rule
        #
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])
        new_rule_pattern_json = RuleGenerator.replaceAliasesOfASTJson(new_rule_pattern_json, [], alias, newVarInternal)
        new_rule_rewrite_json = RuleGenerator.replaceAliasesOfASTJson(new_rule_rewrite_json, [], alias, newVarInternal)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)

        # TODO - add newVarInternal is a alias constraint into new rule's constraints

        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # recursively replace given alias into given var in a rule's pattern/rewrite AST Json
    #
    @staticmethod
    def replaceAliasesOfASTJson(astJson: Any, path: list, alias: str, var: str) -> Any:
        
        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            for key, value in astJson.items():
                # note: key can not be alias, only traverse each value
                astJson[key] = RuleGenerator.replaceAliasesOfASTJson(value, path + [key], alias, var)
            return astJson

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            res = []
            for child in astJson:
                res.append(RuleGenerator.replaceAliasesOfASTJson(child, path, alias, var))
            return res

        # Case-3: string
        if QueryRewriter.is_string(astJson):
            # alias is the value of "name" if:
            #   path = ['from', 'name'], patternASTJson is string
            #
            if len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name':
                if astJson == alias:
                    return var
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            # skip case: {'from': [{'value': 'schema.table', 'name': 't1'}]}
            #            path = ['from', 'value'], patternASTJson = 'schema.table'
            #
            if not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value'):
                # TODO - assert only one '.' exist in dot expression
                if len(astJson.split('.')) == 2:
                    candidate = astJson.split('.')[0]
                    # skip case: <x1>.id
                    #
                    if not QueryRewriter.is_var(candidate) and not QueryRewriter.is_varList(candidate):
                        if candidate == alias:
                            return var + '.' + astJson.split('.')[1]
        
        return astJson

    RuleTransformations = {
        'variablize_columns' : variablize_columns,
        'variablize_literals' : variablize_literals,
        'variablize_aliases': variablize_aliases
    }

    # Recommend a rule given a rule graph (pointed by rootRule)
    #   TODO - currently, recommend the most general rule
    #          (the farthest child in the given rule graph)
    #
    @staticmethod
    def recommend_rule(rootRule: dict) -> dict:
        ans = rootRule
        maxLevel = 0
        # breadth-first-search, find the farthest child
        queue = [(rootRule, 0)]
        while len(queue) > 0:
            rule, level = queue.pop(0)
            if 'visited' not in rule.keys():
                rule['visited'] = True
                if level > maxLevel:
                    ans = rule
                    maxLevel = level
                # enqueue children
                for child in rule['children']:
                    queue.append((child, level + 1))
        return ans
    
    # Generate the candidate rules graph for a given set of examples
    #   e.g., a example set = [
    #                            {'q0': "SELECT * FROM tweets WHERE STRPOS(UPPER(text), 'iphone') > 0", 
    #                             'q1': "SELECT * FROM tweets WHERE text ILIKE '%iphone%'"
    #                            },
    #                            {'q0': "SELECT * FROM tweets WHERE STRPOS(UPPER(state_name), 'iphone') > 0", 
    #                             'q1': "SELECT * FROM tweets WHERE state_name ILIKE '%iphone%'"
    #                            }
    #                         ]
    #
    @staticmethod
    def generate_rules_graph(examples: list) -> list:
        graphRoots = []

        # Generate a rule graph for each example
        #
        for example in examples:
            graphRoot = RuleGenerator.generate_rule_graph(example['q0'], example['q1'])
            graphRoots.append(graphRoot)
        
        # Traverse all rules in the graph:
        #   (1) merge duplicate rules in the graph
        #   (2) compute covered examples list for each rule
        #
        visited = {}
        for graphRoot in graphRoots:
            graphRootFingerPrint = RuleGenerator.fingerPrint(graphRoot)
            visited[graphRootFingerPrint] = graphRoot
            queue = [graphRoot]
            while len(queue) > 0:
                currentRule = queue.pop(0)
                # compute covered examples for currentRule
                currentRule['coveredExamples'] = RuleGenerator.coveredExamples(currentRule, examples)
                # update pointers if any child rule is visited
                newChildren = []
                for childRule in currentRule['children']:
                    childRuleFingerPrint = RuleGenerator.fingerPrint(childRule)
                    if childRuleFingerPrint in visited.keys():
                        newChildren.append(visited[childRuleFingerPrint])
                    else:
                        newChildren.append(childRule)
                        queue.append(childRule)
                        visited[childRuleFingerPrint] = childRule
                currentRule['children'] = newChildren
        
        return graphRoots

    # Compute covered examples' indexes for a given rule
    #
    @staticmethod
    def coveredExamples(rule: dict, examples: list) -> list:
        ans = []

        # preprocess rule
        parsed_rule = {
            'id': -1,
            'pattern': rule['pattern'],
            'constraints': rule['constraints'],
            'rewrite': rule['rewrite'],
            'actions': rule['actions']
        }
        parsed_rule['pattern_json'], parsed_rule['rewrite_json'], parsed_rule['mapping'] = RuleParser.parse(parsed_rule['pattern'], parsed_rule['rewrite'])
        parsed_rule['constraints_json'] = RuleParser.parse_constraints(parsed_rule['constraints'], parsed_rule['mapping'])
        parsed_rule['actions_json'] = RuleParser.parse_actions(parsed_rule['actions'], parsed_rule['mapping'])
        parsed_rule['pattern_json'] = json.loads(parsed_rule['pattern_json'])
        parsed_rule['constraints_json'] = json.loads(parsed_rule['constraints_json'])
        parsed_rule['rewrite_json'] = json.loads(parsed_rule['rewrite_json'])
        parsed_rule['actions_json'] = json.loads(parsed_rule['actions_json'])
        parsed_rule['mapping'] = json.loads(parsed_rule['mapping'])

        for index, example in enumerate(examples):
            q0 = example['q0']
            q1 = example['q1']
            q1_test, _ = QueryRewriter.rewrite(q0, [parsed_rule])
            if mosql.format(mosql.parse(q1)) == q1_test:
                ans.append(index)
        
        return ans
    
    # Recommend rules given a rules graph (a list of roots pointed by rootRules)
    #   TODO - currently, recommend the least general rules that cover all examples
    #
    @staticmethod
    def recommend_rules(rootRules: dict, numberOfExamples: int) -> dict:
        ans = []
        
        # Traverse all rules and put them in a set with the fingerprint as the key
        #
        rulesSet = {}
        for rootRule in rootRules:
            # breadth-first-search
            queue = [rootRule]
            while len(queue) > 0:
                rule = queue.pop(0)
                fingerPrint = RuleGenerator.fingerPrint(rule)
                if fingerPrint not in rulesSet.keys():
                    priority1 = - len(rule['coveredExamples'])
                    priority2 = RuleGenerator.numberOfVariables(rule)
                    rulesSet[fingerPrint] = ((priority1, priority2), rule)
                    # enqueue children
                    for child in rule['children']:
                        queue.append(child)
        
        # Sort the rules by its priority in ascending order:
        #    The priority is defined as a tuple (- # of examples covered, # of variables)
        #
        rules = rulesSet.values()
        sortedRules = sorted(rules, key=lambda k: k[0])

        # Greedily put rules into the result set with the smallest priority first,
        #   until all examples are covered by the result set
        uncoveredExamples = set(range(0, numberOfExamples))
        for priority, rule in sortedRules:
            coveredExamples = set(rule['coveredExamples'])
            if len(uncoveredExamples.intersection(coveredExamples)) > 0:
                ans.append(rule)
                uncoveredExamples = uncoveredExamples - coveredExamples
            if len(uncoveredExamples) == 0:
                break

        return ans
    
    @staticmethod
    def numberOfVariables(rule: dict) -> int:
        return len(json.loads(rule['mapping']).keys())

