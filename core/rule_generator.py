from collections import defaultdict
from typing import Any, Union, Tuple
import copy
from core.profiler import Profiler
from core.query_rewriter import QueryRewriter
from core.rule_parser import RuleParser, Scope, VarType, VarTypesInfo
import json
import mo_sql_parsing as mosql
import numbers
import re
import time



MAX_INT = 2147483647

class RuleGenerator:

    # Copy the given rule to a new rule
    #
    @staticmethod
    def copy_a_rule(rule: dict) -> dict:
        
        # create a new rule based on rule
        new_rule = copy.deepcopy(rule)

        # cleanup attributes
        if 'fingerPrint' in new_rule:
            del new_rule['fingerPrint']
        if 'children' in new_rule:
            del new_rule['children']
        if 'promisingScore' in new_rule:
            del new_rule['promisingScore']

        return new_rule

    # Initialize the seed rule for a given rewriting pair q0 -> q1
    #
    @staticmethod
    def initialize_seed_rule(q0: str, q1: str) -> dict:
        # Extend partial SQL statement to full SQL statement
        #    for the sake of sql parser
        # 
        q0, q0Scope = RuleParser.extendToFullSQL(q0)
        q1, q1Scope = RuleParser.extendToFullSQL(q1)

        # Parse full SQL statement into AST json
        # 
        q0ASTJson = mosql.parse(q0)
        q1ASTJson = mosql.parse(q1)

        # Extract subtree from AST json based on scope
        patternASTJson = RuleParser.extractASTSubtree(q0ASTJson, q0Scope)
        rewriteASTJson = RuleParser.extractASTSubtree(q1ASTJson, q1Scope)

        seedRule = {'pattern': RuleGenerator.deparse(patternASTJson), 'rewrite': RuleGenerator.deparse(rewriteASTJson)}

        # Parse seedRule's pattern and rewrite into SQL AST json
        #
        seedRule['pattern_json'], seedRule['rewrite_json'], seedRule['mapping'] = RuleParser.parse(seedRule['pattern'], seedRule['rewrite'])
        
        # Initially, seedRule has no constraints and actions
        #
        seedRule['constraints'], seedRule['constraints_json'], seedRule['actions'], seedRule['actions_json'] = '', '[]', '', '[]'

        return seedRule
    
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
    def minDiffSubtreeInStrings(leftNode: str, rightNode: str) -> Tuple[Any, Any]:
        if leftNode.lower() == rightNode.lower():
            return None, None
        return leftNode, rightNode
    
    @staticmethod
    def minDiffSubtreeInNumbers(leftNode: numbers, rightNode: numbers) -> Tuple[Any, Any]:
        if leftNode == rightNode:
            return None, None
        return leftNode, rightNode

    @staticmethod
    def minDiffSubtreeInConstants(leftNode: Any, rightNode: Any) -> Tuple[Any, Any]:
        if QueryRewriter.is_string(leftNode) and QueryRewriter.is_string(rightNode):
            return RuleGenerator.minDiffSubtreeInStrings(leftNode, rightNode)
        if QueryRewriter.is_number(leftNode) and QueryRewriter.is_number(rightNode):
            return RuleGenerator.minDiffSubtreeInNumbers(leftNode, rightNode)
        return leftNode, rightNode
    
    @staticmethod
    def minDiffSubtreeInDotExpressions(leftNode: str, rightNode: str) -> Tuple[Any, Any]:
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
    def minDiffSubtreeInDicts(leftNode: dict, rightNode: dict) -> Tuple[Any, Any]:
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
    def minDiffSubtreeInLists(leftNode: list, rightNode: list) -> Tuple[Any, Any]:
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
    
    # TODO - Handle cases where the generalized rule has only 
    #          "INNER JOIN <x1> ON <x1>.<x2> = <x3>.<x4> AND <x1>.<x5> = <x6>"
    #
    @staticmethod
    def extendToFullASTJson(node: Any) -> Tuple[Any, Scope]:
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
    
    @staticmethod
    def fingerPrint(rule: dict) -> str:
        # use rule['pattern'] string as finger-print
        #   and get rid of the numbers inside each var/varList
        #   e.g., we want to treat these two generated rules as the same rule:
        #         rule 1: SELECT e1.<x1>, e1.<x2> FROM employee e1 WHERE e1.<x1> > 17 AND e1.<x2> > 35000
        #         rule 2: SELECT e1.<x2>, e1.<x1> FROM employee e1 WHERE e1.<x2> > 17 AND e1.<x1> > 35000
        # return RuleGenerator._fingerPrint(rule['pattern'])
        return RuleGenerator._fingerPrint2(rule['pattern_json'])
    
    @staticmethod
    def _fingerPrint(fingerPrint: str) -> str:
        #   get rid of the numbers inside each var/varList
        fingerPrint = re.sub(r"<x(\d+)>", "<x>", fingerPrint)
        fingerPrint = re.sub(r"<<y(\d+)>>", "<<y>>", fingerPrint)
        return fingerPrint
    
    @staticmethod
    def _fingerPrint2(fingerPrint: str) -> str:
        #   get rid of the numbers inside each var/varList
        fingerPrint = re.sub(r"V(\d+)>", "V", fingerPrint)
        fingerPrint = re.sub(r"VL(\d+)", "VL", fingerPrint)
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
                # special case: {'all_columns': 'e1'}
                #  this is a new change in the mo_sql_parser library,
                #  to make it compatible with our code, 
                #  make it as before the '*' column name.
                if type(key) is str and key.lower() == 'all_columns':
                    res.add('*')
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
            # case-1: {'from': 'employee'}
            #   path = ['from']
            if len(path) >=1 and path[-1] == 'from':
                pass
            # case-2: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #   path = ['from', 'value']
            #   path = ['from', 'name']
            elif len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value':
                pass
            elif len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name':
                pass
            # case-3: {'from': [..., {'inner join': {'value': 'employee', 'name': 'e1'}}]}
            #   path = ['inner join', 'value']
            #   path = ['inner join', 'name']
            elif len(path) >= 2 and path[-2] == 'inner join' and path[-1] == 'value':
                pass
            elif len(path) >= 2 and path[-2] == 'inner join' and path[-1] == 'name':
                pass
            # case-4: {'select': [{'value': 'e1.salary', 'name': 'sal'}]}
            #   path = ['select', 'name']
            elif len(path) >= 2 and path[-2] == 'select' and path[-1] == 'name':
                pass
            # case-5: {'orderby': {..., 'sort': 'asc'}}
            #   path = ['sort']
            elif len(path) >= 1 and path[-1] == 'sort':
                pass
            # treat '*' as a column for now
            # # ignore '*'
            # elif astJson != '*':
            #     res.add(astJson)
            else:
                res.add(astJson)
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            # case-1: {'from': 'employee'}
            #   path = ['from']
            if len(path) >=1 and path[-1] == 'from':
                pass
            # case-2: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #   path = ['from', 'value']
            #   path = ['from', 'name']
            elif len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value':
                pass
            elif len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name':
                pass
            # case-3: {'from': [..., {'inner join': {'value': 'employee', 'name': 'e1'}}]}
            #   path = ['inner join', 'value']
            #   path = ['inner join', 'name']
            elif len(path) >= 2 and path[-2] == 'inner join' and path[-1] == 'value':
                pass
            elif len(path) >= 2 and path[-2] == 'inner join' and path[-1] == 'name':
                pass
            # case-4: {'select': [{'value': 'e1.salary', 'name': 'sal'}]}
            #   path = ['select', 'name']
            elif len(path) >= 2 and path[-2] == 'select' and path[-1] == 'name':
                pass
            # case-5: {'orderby': {..., 'sort': 'asc'}}
            #   path = ['sort']
            elif len(path) >= 1 and path[-1] == 'sort':
                pass
            else:
                candidate = astJson.split('.')[-1]
                # skip case: e1.<a1>
                #
                if not QueryRewriter.is_var(candidate) and not QueryRewriter.is_varList(candidate):
                    # treat '*' as a column for now
                    # # ignore e1.* in SELECT clause
                    # #
                    # if candidate != '*':
                    #     res.add(candidate)
                    res.add(candidate)
        
        return res
    
    
    # variablize the given column in given rule and generate a new rule
    #
    @staticmethod
    def variablize_column(rule: dict, column: str) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)

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
            # special case for {'all_columns': {}} under 'select' key
            #   it can match '*', return {'value': var}
            #
            if 'all_columns' in astJson.keys() and astJson['all_columns'] == {}:
                return {'value': var}
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
            # case-1: {'from': 'employee'}
            #   path = ['from']
            if len(path) >=1 and path[-1] == 'from':
                pass
            # case-2: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #   path = ['from', 'value']
            #   path = ['from', 'name']
            elif len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value':
                pass
            elif len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name':
                pass
            # case-3: {'from': [..., {'inner join': {'value': 'employee', 'name': 'e1'}}]}
            #   path = ['inner join', 'value']
            #   path = ['inner join', 'name']
            elif len(path) >= 2 and path[-2] == 'inner join' and path[-1] == 'value':
                pass
            elif len(path) >= 2 and path[-2] == 'inner join' and path[-1] == 'name':
                pass
            # case-4: {'select': [{'value': 'e1.salary', 'name': 'sal'}]}
            #   path = ['select', 'name']
            elif len(path) >= 2 and path[-2] == 'select' and path[-1] == 'name':
                pass
            # case-5: {'orderby': {..., 'sort': 'asc'}}
            #   path = ['sort']
            elif len(path) >= 1 and path[-1] == 'sort':
                pass
            elif astJson == column:
                return var
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            # case-1: {'from': 'employee'}
            #   path = ['from']
            if len(path) >=1 and path[-1] == 'from':
                pass
            # case-2: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #   path = ['from', 'value']
            #   path = ['from', 'name']
            elif len(path) >= 2 and path[-2] == 'from' and path[-1] == 'value':
                pass
            elif len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name':
                pass
            # case-3: {'from': [..., {'inner join': {'value': 'employee', 'name': 'e1'}}]}
            #   path = ['inner join', 'value']
            #   path = ['inner join', 'name']
            elif len(path) >= 2 and path[-2] == 'inner join' and path[-1] == 'value':
                pass
            elif len(path) >= 2 and path[-2] == 'inner join' and path[-1] == 'name':
                pass
            # case-4: {'select': [{'value': 'e1.salary', 'name': 'sal'}]}
            #   path = ['select', 'name']
            elif len(path) >= 2 and path[-2] == 'select' and path[-1] == 'name':
                pass
            # case-5: {'orderby': {..., 'sort': 'asc'}}
            #   path = ['sort']
            elif len(path) >= 1 and path[-1] == 'sort':
                pass
            else:
                candidate = astJson.split('.')[-1]
                # skip case: e1.<a1>
                #
                if not QueryRewriter.is_var(candidate) and not QueryRewriter.is_varList(candidate):
                    if candidate == column:
                        return '.'.join(astJson.split('.')[0:-1] + [var])
        
        return astJson
    
    # Find the next Var internal name given the current mapping
    #   Traverse all Var/VarList mappings in rule
    #     Count the max number of Var
    # Return the new mapping with the new Var map (e.g., <x3> -> V3) and the new VarInternal (e.g., V3)
    #
    @staticmethod
    def findNextVarInternal(mapping: dict) -> Tuple[dict, str]:
        maxVarNum = 0
        for varInternal in mapping.values():
            if VarTypesInfo[VarType.VarList]['internalBase'] not in varInternal and VarTypesInfo[VarType.Var]['internalBase'] in varInternal:
                num = int(varInternal.split(VarTypesInfo[VarType.Var]['internalBase'], 1)[1])
                if num > maxVarNum:
                    maxVarNum = num
        newVarNum = maxVarNum + 1
        newVarInternal = VarTypesInfo[VarType.Var]['internalBase'] + str(newVarNum).zfill(3)
        newVarExternal = VarTypesInfo[VarType.Var]['externalBase'] + str(newVarNum)
        # add new map into mapping
        mapping[newVarExternal] = newVarInternal
        return mapping, newVarInternal
    
    # Find the next VarList internal name given the current mapping
    #   Traverse all Var/VarList mappings in rule
    #     Count the max number of varList
    # Return the new mapping with the new VarList map (e.g., <<y3>> -> VL3) and the new VarListInternal (e.g., VL3)
    #
    @staticmethod
    def findNextVarListInternal(mapping: dict) -> Tuple[dict, str]:
        maxVarListNum = 0
        for varInternal in mapping.values():
            if VarTypesInfo[VarType.VarList]['internalBase'] in varInternal:
                num = int(varInternal.split(VarTypesInfo[VarType.VarList]['internalBase'], 1)[1])
                if num > maxVarListNum:
                    maxVarListNum = num
        newVarListNum = maxVarListNum + 1
        newVarListInternal = VarTypesInfo[VarType.VarList]['internalBase'] + str(newVarListNum).zfill(3)
        newVarListExternal = VarTypesInfo[VarType.VarList]['externalBase'] + str(newVarListNum)
        # add new map into mapping
        mapping[newVarListExternal] = newVarListInternal
        return mapping, newVarListInternal

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
        new_rule = RuleGenerator.copy_a_rule(rule)

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
    
    # transformation function - variablize tables in a rule
    #   generate a list of child rules 
    #
    @staticmethod
    def variablize_tables(rule: dict) -> list:

        Profiler.onFunctionStart('varialize_tables')

        res = []

        # 1. Get candidate tables from rule
        #
        tables = RuleGenerator.tables(rule['pattern_json'], rule['rewrite_json'])

        # 2. Traverse candidate tables, make one of them variable, and generate a new rule
        #
        for table in tables:
            res.append(RuleGenerator.variablize_table(rule, table))
        
        Profiler.onFunctionEnd('varialize_tables')

        return res

    # get list of common tables in a seed rule's pattern_json and rewrite_json
    #   a table is a dict with name and alias, e.g., {'value': 'employee', 'name': 'e1'}
    #
    @staticmethod
    def tables(pattern_json: str, rewrite_json: str) -> list:
        
        patternASTJson = json.loads(pattern_json)
        rewriteASTJson = json.loads(rewrite_json)

        # traverse the AST jsons to get all tables
        patternTables = RuleGenerator.tablesOfASTJson(patternASTJson, [])
        rewriteTables = RuleGenerator.tablesOfASTJson(rewriteASTJson, [])

        # patternTables should be superset of rewriteTables
        #
        # the patternSet and the rewriteSet are re-structured from patternTables and rewriteTables.
        # they are dictioanries with key as table value and value as a list of alias names for that table value
        #   e.g. patternTables: [{'value': 'employee', 'name': 'e1'}, {'value': 'employee', 'name': 'e2'}]
        #        patternSet: {'employee': ['e1', 'e2']}
        #
        patternSet = defaultdict(list)
        rewriteSet = defaultdict(list)

        for table in patternTables:
            if type(table['value']) is str and type(table['name']) is str:
                patternSet[table['value']].append(table['name'])

        for table in rewriteTables:
            if type(table['value']) is str and type(table['name']) is str:
                rewriteSet[table['value']].append(table['name'])

        superSet = []
        for patternValue, patternNames in patternSet.items():
            rewriteNames = rewriteSet.get(patternValue, [])
            # special case: 
            #   if the patternTable ONLY has {'value': 'employee', 'name': 'employee'}
            #   and the rewriteTable ONLY has {'value': 'employee', 'name': 'e1'},
            #   we replace 'employee' with 'e1' as table alias  
            #   the purpose is for the next step when we replace tables with variables, 
            #   we should be able to know the patternTable and rewriteTable should be replaced with the same variable.  
            #   This logic will much simpler once we complete refactoring the code to introduce an internal tree structure  
            #   to represent the AST instead of the current JSON structure, where can easily determine if two tables  
            #   are the same table with different alias names.
            #
            if len(patternNames) == 1 and len(rewriteNames) == 1 and patternNames[0] == patternValue:
                patternNames = rewriteNames
            else:
                patternNames += [name for name in rewriteNames if name not in patternNames]
            superSet += [{'value': patternValue, 'name': name} for name in patternNames]

        patternTables = superSet

        # deduplicate the list
        #
        fingerprints = set()
        ans = []
        for table in patternTables:
            fingerprint = table['value'] + '-' + table['name']
            if fingerprint not in fingerprints:
                ans.append(table)
                fingerprints.add(fingerprint)
        patternTables = ans

        return patternTables
    
    # recursively get set of tables in a rule pattern/rewrite's AST Json
    #   a table is a dict with name and alias, e.g., {'value': 'employee', 'name': 'e1'}
    #
    @staticmethod
    def tablesOfASTJson(astJson: Any, path: list) -> list:
        res = []

        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            # format is {'value': ..., 'name': ...}
            #
            if 'value' in astJson and 'name' in astJson:
                # case-1: {'from': {'value': 'employee', 'name': 'e1'}} 
                #         or {'from': [{'value': 'employee', 'name': 'e1'}]}
                #         path = ['from']
                #
                if len(path) >= 1 and path[-1] == 'from':
                    res.append(astJson)
                # case-2: {'inner join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['inner join']
                #
                elif len(path) >= 1 and path[-1] == 'inner join':
                    res.append(astJson)
                # case-3: {'left outer join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['left outer join']
                #
                elif len(path) >= 1 and path[-1] == 'left outer join':
                    res.append(astJson)
                # case-4: {'left join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['left join']
                #
                elif len(path) >= 1 and path[-1] == 'left join':
                    res.append(astJson)
                # case-5: {'join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['join']
                #
                elif len(path) >= 1 and path[-1] == 'join':
                    res.append(astJson)
            # recursively traverse the dict
            #
            for key, value in astJson.items():
                # note: key can not be table, only traverse each value
                res.extend(RuleGenerator.tablesOfASTJson(value, path + [key]))

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            for child in astJson:
                res.extend(RuleGenerator.tablesOfASTJson(child, path))

        # Case-3: string
        if QueryRewriter.is_string(astJson):
            # case-1: {'from': 'employee'}
            #         path = ['from']
            #
            if len(path) >=1 and path[-1] == 'from':
                # treat the table name itself as the alias
                #
                res.append({'value': astJson, 'name': astJson})
            # case-2: {'inner join': 'employee'}
            #         path = ['inner join']
            #
            elif len(path) >=1 and path[-1] == 'inner join':
                # treat the table name itself as the alias
                #
                res.append({'value': astJson, 'name': astJson})
            # case-3: {'left outer join': 'employee'}
            #         path = ['left outer join']
            #
            elif len(path) >=1 and path[-1] == 'left outer join':
                # treat the table name itself as the alias
                #
                res.append({'value': astJson, 'name': astJson})
            # case-4: {'left join': 'employee'}
            #         path = ['left join']
            #
            elif len(path) >= 1 and path[-1] == 'left join':
                res.append({'value': astJson, 'name': astJson})
            # case-5: {'join': 'employee'}
            #         path = ['join']
            #
            elif len(path) >= 1 and path[-1] == 'join':
                res.append({'value': astJson, 'name': astJson})
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            # case-1: {'from': 'tablespace.employee'}
            #         path = ['from']
            #
            if len(path) >=1 and path[-1] == 'from':
                # treat the table name itself as the alias
                #
                res.append({'value': astJson, 'name': astJson})
            # case-2: {'inner join': 'tablespace.employee'}
            #         path = ['inner join']
            #
            elif len(path) >=1 and path[-1] == 'inner join':
                # treat the table name itself as the alias
                #
                res.append({'value': astJson, 'name': astJson})
            # case-3: {'left outer join': 'tablespace.employee'}
            #         path = ['left outer join']
            #
            elif len(path) >=1 and path[-1] == 'left outer join':
                # treat the table name itself as the alias
                #
                res.append({'value': astJson, 'name': astJson})
            # case-4: {'left join': 'tablespace.employee'}
            #         path = ['left join']
            #
            elif len(path) >=1 and path[-1] == 'left join':
                # treat the table name itself as the alias
                #
                res.append({'value': astJson, 'name': astJson})
            # case-5: {'join': 'tablespace.employee'}
            #         path = ['join']
            #
            elif len(path) >=1 and path[-1] == 'join':
                # treat the table name itself as the alias
                #
                res.append({'value': astJson, 'name': astJson})
        
        return res
    
    # variablize the given table in given rule and generate a new rule
    #
    @staticmethod
    def variablize_table(rule: dict, table: dict) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)

        # Find a variable name for the given table
        #
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_mapping, newVarInternal = RuleGenerator.findNextVarInternal(new_rule_mapping)
        new_rule['mapping'] = json.dumps(new_rule_mapping)

        # Replace given table into newVarInternal in new rule
        #
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])
        new_rule_pattern_json = RuleGenerator.replaceTablesOfASTJson(new_rule_pattern_json, [], table, newVarInternal)
        new_rule_rewrite_json = RuleGenerator.replaceTablesOfASTJson(new_rule_rewrite_json, [], table, newVarInternal)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)

        # TODO - add newVarInternal is a table constraint into new rule's constraints

        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # recursively replace given table into given var in a rule's pattern/rewrite AST Json
    #
    @staticmethod
    def replaceTablesOfASTJson(astJson: Any, path: list, table: dict, var: str) -> Any:
        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            # format is {'value': ..., 'name': ...}
            #
            if 'value' in astJson and 'name' in astJson:
                # case-1: {'from': {'value': 'employee', 'name': 'e1'}} 
                #         or {'from': [{'value': 'employee', 'name': 'e1'}]}
                #         path = ['from']
                #
                if len(path) >= 1 and path[-1] == 'from':
                    if astJson['value'] == table['value'] and astJson['name'] == table['name']:
                        return var 
                    # special case: if it's a general table with no alias, e.g., {'value': 'employee', 'name': 'employee'}
                    elif astJson['value'] == table['value'] and astJson['value'] == astJson['name']:
                        return var
                # case-2: {'inner join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['inner join']
                #
                elif len(path) >= 1 and path[-1] == 'inner join':
                    if astJson['value'] == table['value'] and astJson['name'] == table['name']:
                        return var 
                    # special case: if it's a general table with no alias, e.g., {'value': 'employee', 'name': 'employee'}
                    elif astJson['value'] == table['value'] and astJson['value'] == astJson['name']:
                        return var
                # case-3: {'left outer join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['left outer join']
                #
                elif len(path) >= 1 and path[-1] == 'left outer join':
                    if astJson['value'] == table['value'] and astJson['name'] == table['name']:
                        return var 
                    # special case: if it's a general table with no alias, e.g., {'value': 'employee', 'name': 'employee'}
                    elif astJson['value'] == table['value'] and astJson['value'] == astJson['name']:
                        return var
                # case-4: {'left join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['left join']
                #
                elif len(path) >= 1 and path[-1] == 'left join':
                    if astJson['value'] == table['value'] and astJson['name'] == table['name']:
                        return var 
                    # special case: if it's a general table with no alias, e.g., {'value': 'employee', 'name': 'employee'}
                    elif astJson['value'] == table['value'] and astJson['value'] == astJson['name']:
                        return var
                # case-5: {'join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['join']
                #
                elif len(path) >= 1 and path[-1] == 'join':
                    if astJson['value'] == table['value'] and astJson['name'] == table['name']:
                        return var 
                    # special case: if it's a general table with no alias, e.g., {'value': 'employee', 'name': 'employee'}
                    elif astJson['value'] == table['value'] and astJson['value'] == astJson['name']:
                        return var
            # recursively traverse the dict
            #
            for key, value in astJson.items():
                # note: key can not be table, only traverse each value
                astJson[key] = RuleGenerator.replaceTablesOfASTJson(value, path + [key], table, var)
            return astJson

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            res = []
            for child in astJson:
                res.append(RuleGenerator.replaceTablesOfASTJson(child, path, table, var))
            return res

        # Case-3: string
        if QueryRewriter.is_string(astJson):
            # case-1: {'from': 'employee'}
            #         path = ['from']
            #
            if len(path) >=1 and path[-1] == 'from':
                if astJson == table['value']:
                    return var
            # case-2: {'inner join': 'employee'}
            #         path = ['inner join']
            #
            elif len(path) >=1 and path[-1] == 'inner join':
                if astJson == table['value']:
                    return var
            # case-3: {'left outer join': 'employee'}
            #         path = ['left outer join']
            #
            elif len(path) >=1 and path[-1] == 'left outer join':
                if astJson == table['value']:
                    return var
            # case-4: {'left join': 'employee'}
            #         path = ['left join']
            #
            elif len(path) >=1 and path[-1] == 'left join':
                if astJson == table['value']:
                    return var
            # case-5: {'join': 'employee'}
            #         path = ['join']
            #
            elif len(path) >=1 and path[-1] == 'join':
                if astJson == table['value']:
                    return var
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            # case-1: {'from': 'tablespace.employee'}
            #         path = ['from']
            #
            if len(path) >=1 and path[-1] == 'from':
                if astJson == table['value']:
                    return var
            # case-2: {'inner join': 'tablespace.employee'}
            #         path = ['inner join']
            #
            elif len(path) >=1 and path[-1] == 'inner join':
                if astJson == table['value']:
                    return var
            # case-3: {'left outer join': 'tablespace.employee'}
            #         path = ['left outer join']
            #
            elif len(path) >=1 and path[-1] == 'left outer join':
                if astJson == table['value']:
                    return var
            # case-4: {'left join': 'tablespace.employee'}
            #         path = ['left join']
            #
            elif len(path) >=1 and path[-1] == 'left join':
                if astJson == table['value']:
                    return var
            # case-5: {'join': 'tablespace.employee'}
            #         path = ['join']
            #
            elif len(path) >=1 and path[-1] == 'join':
                if astJson == table['value']:
                    return var
            # case-6: table's alias occurs in select or where clause
            #
            else:
                # split the dot expression into two parts
                #   e.g., ['tablespace.employee'],['age']
                #
                _table = '.'.join(astJson.split('.')[0:-1])
                _column = astJson.split('.')[-1]
                # skip case: <x1>.id
                #
                if not QueryRewriter.is_var(_table) and not QueryRewriter.is_varList(_table):
                    if _table == table['name'] or _table == table['value']:
                        return var + '.' + _column
        
        return astJson
    
    # transformation function - variablize subtrees in a rule
    #   generate a list of child rules 
    # 
    # note: subtrees are defined as follows:
    #       (1) it has one or two variables in leaves
    #       (2) it has exact the same occurrences in both the pattern and rewrite of the rule
    #       
    #       to variablize a subtree is to replace the subtree as a new variable in both pattern and rewrite
    #
    @staticmethod
    def variablize_subtrees(rule: dict) -> list:

        Profiler.onFunctionStart('varialize_subtrees')

        res = []

        # 1. Get candidate subtrees from rule
        #
        subtrees = RuleGenerator.subtrees(rule['pattern_json'], rule['rewrite_json'])

        # 2. Traverse candidate subtrees, make one of them variable, and generate a new rule
        #
        for subtree in subtrees:
            res.append(RuleGenerator.variablize_subtree(rule, subtree))
        
        Profiler.onFunctionEnd('varialize_subtrees')

        return res
    
    # get list of common subtrees in a seed rule's pattern_json and rewrite_json
    #
    @staticmethod
    def subtrees(pattern_json: str, rewrite_json: str) -> list:
        
        patternASTJson = json.loads(pattern_json)
        rewriteASTJson = json.loads(rewrite_json)

        # traverse the AST jsons to get all subtrees
        patternSubtrees = RuleGenerator.subtreesOfASTJson(patternASTJson, [])
        rewriteSubtrees = RuleGenerator.subtreesOfASTJson(rewriteASTJson, [])

        # find the common subtrees in pattern and rewrite
        #
        ans = []
        while len(patternSubtrees) > 0:
            patternSubtree = patternSubtrees.pop()
            for rewriteSubtree in rewriteSubtrees:
                if RuleGenerator.sameSubtree(patternSubtree, rewriteSubtree):
                    rewriteSubtrees.remove(rewriteSubtree)
                    ans.append(patternSubtree)
                    break

        return ans
    
    # check if the given two subtrees are the same
    #
    @staticmethod
    def sameSubtree(left: dict, right: dict) -> bool:
        for key, leftValue in left.items():
            if key not in right:
                return False
            rightValue = right[key]
            # a child cannot be a dict
            #
            # when a child is a list
            if QueryRewriter.is_list(leftValue):
                if not QueryRewriter.is_list(rightValue):
                    return False
                # each element is guaranteed to be one of 
                #   constant, dot_expression, Var, or VarList
                if set(leftValue) != set(rightValue):
                    return False
            # when a child is a constant
            elif QueryRewriter.is_constant(leftValue):
                if not QueryRewriter.is_constant(rightValue):
                    return False
                if leftValue != rightValue:
                    return False
            # when a child is a dot_expression
            elif QueryRewriter.is_dot_expression(leftValue):
                if not QueryRewriter.is_dot_expression(rightValue):
                    return False
                if leftValue != rightValue:
                    return False
            # when a child is Var
            elif QueryRewriter.is_var(leftValue):
                if not QueryRewriter.is_var(rightValue):
                    return False
                if leftValue != rightValue:
                    return False
            # when a child is VarList
            elif QueryRewriter.is_varList(leftValue):
                if not QueryRewriter.is_varList(rightValue):
                    return False
                if leftValue != rightValue:
                    return False
        return True
    
    # recursively get set of subtrees in a rule pattern/rewrite's AST Json
    #
    @staticmethod
    def subtreesOfASTJson(astJson: Any, path: list) -> list:
        res = []

        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            # if current node is the root of a subtree
            #
            if RuleGenerator.isSubtree(astJson):
                # put in result
                #
                res.append(astJson)
            # otherwise
            #
            else:
                # recursively traverse the dict
                #
                for key, value in astJson.items():
                    # note: key can not be subtree, only traverse each value
                    res.extend(RuleGenerator.subtreesOfASTJson(value, path + [key]))

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            for child in astJson:
                res.extend(RuleGenerator.subtreesOfASTJson(child, path))
        
        return res
    
    # check if a node in rule pattern/rewrite's AST Json is a subtree
    #   see comments in variablize_subtrees() for the definition of a subtree
    #
    @staticmethod
    def isSubtree(astJson: dict) -> bool:
        var_count = 0
        for key, value in astJson.items():
            # key can not be keywords of [SELECT, FROM, WHERE, LIMIT, ORDERBY, SORT, INNER JOIN, LEFT OUTER JOIN, JOIN, LEFT JOIN]
            if key in ['select', 'from', 'where', 'limit', 'orderby', 'sort', 'inner join', 'left outer join', 'join', 'left join']:
                return False
            # a child cannot be a dict
            if QueryRewriter.is_dict(value):
                return False
            # when a child is a list
            elif QueryRewriter.is_list(value):
                # each element in the list has to be constant, dot_expression, Var or VarList
                for element in value:
                    if QueryRewriter.is_constant(element):
                        pass
                    elif QueryRewriter.is_dot_expression(element):
                        # count Var
                        #
                        # split the dot expression into two parts
                        # 
                        _table = '.'.join(element.split('.')[0:-1])
                        _column = element.split('.')[-1]
                        # we count a dot_expression as a Var only if both parts are Vars
                        #
                        if QueryRewriter.is_var(_table) and QueryRewriter.is_var(_column): 
                            var_count += 1
                    elif QueryRewriter.is_var(element):
                        var_count += 1
                    elif QueryRewriter.is_varList(element):
                        var_count += 1
                    else:
                        return False
            # when a child is a constant
            elif QueryRewriter.is_constant(value):
                pass
            # when a child is a dot_expression
            elif QueryRewriter.is_dot_expression(value):
                # count Var
                #
                # split the dot expression into two parts
                # 
                _table = '.'.join(value.split('.')[0:-1])
                _column = value.split('.')[-1]
                # we count a dot_expression as a Var only if both parts are Vars
                #
                if QueryRewriter.is_var(_table) and QueryRewriter.is_var(_column): 
                    var_count += 1
            # when a child is Var
            elif QueryRewriter.is_var(value):
                # count Var
                #
                var_count += 1
            # when a child is VarList
            elif QueryRewriter.is_varList(value):
                # count Var
                #
                var_count += 1

        if var_count >= 1:
            return True
        else:
            return False
    
    # variablize the given subtree in given rule and generate a new rule
    #
    @staticmethod
    def variablize_subtree(rule: dict, subtree: dict) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)

        # Find a variable name for the given subtree
        #
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_mapping, newVarInternal = RuleGenerator.findNextVarInternal(new_rule_mapping)
        new_rule['mapping'] = json.dumps(new_rule_mapping)

        # Replace given subtree into newVarInternal in new rule
        #
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])
        new_rule_pattern_json = RuleGenerator.replaceSubtreesOfASTJson(new_rule_pattern_json, [], subtree, newVarInternal)
        new_rule_rewrite_json = RuleGenerator.replaceSubtreesOfASTJson(new_rule_rewrite_json, [], subtree, newVarInternal)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)

        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # recursively replace given subtree into given var in a rule's pattern/rewrite AST Json
    #
    @staticmethod
    def replaceSubtreesOfASTJson(astJson: Any, path: list, subtree: dict, var: str) -> Any:
        
        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            # if current node is the root of the subtree
            #
            if RuleGenerator.isSubtree(astJson):
                # if the subtree is the same as the given subtree
                #
                if RuleGenerator.sameSubtree(astJson, subtree):
                    # special case for 'select' list
                    #  e.g., for {'select': [{'value': 'V001.V002'}, {'value': 'V001.age'}, ...]}
                    #        astJson = {'value': 'V001.V002'}
                    #        subtree = {'value': 'V001.V002'}
                    #        var = 'V005'
                    #        we should return {'value': 'V005'}
                    if len(path) > 0 and path[-1] == 'select' and 'value'in astJson.keys():
                        return {'value': var}
                    # otherwise
                    return var
            # otherwise
            #
            else:
                # recursively traverse the dict
                #
                for key, value in astJson.items():
                    # note: key can not be subtree, only traverse each value
                    astJson[key] = RuleGenerator.replaceSubtreesOfASTJson(value, path + [key], subtree, var)
                return astJson

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            res = []
            for child in astJson:
                res.append(RuleGenerator.replaceSubtreesOfASTJson(child, path, subtree, var))
            return res
        
        return astJson
    
    # transformation function - merge variables in a rule
    #   generate a list of child rules 
    # 
    # note: we find common lists of variables in pattern and rewrite
    #       and merge each list of variables into a VarList
    #
    @staticmethod
    def merge_variables(rule: dict) -> list:

        Profiler.onFunctionStart('merge_variables')

        res = []

        # 1. Get candidate variable lists from rule
        #
        variableLists = RuleGenerator.variable_lists(rule['pattern_json'], rule['rewrite_json'])

        # 2. Traverse candidate variable lists, make one of them VarList, and generate a new rule
        #
        for variableList in variableLists:
            res.append(RuleGenerator.merge_variable_list(rule, variableList))
        
        Profiler.onFunctionEnd('merge_variables')

        return res
    
    # get list of variable lists in a seed rule's pattern_json and rewrite_json
    #
    @staticmethod
    def variable_lists(pattern_json: str, rewrite_json: str) -> list:
        
        patternASTJson = json.loads(pattern_json)
        rewriteASTJson = json.loads(rewrite_json)

        # traverse the AST jsons to get all variable lists
        patternVariableLists = RuleGenerator.variableListsOfASTJson(patternASTJson, [])
        rewriteVariableLists = RuleGenerator.variableListsOfASTJson(rewriteASTJson, [])

        # find the common variable lists in pattern and rewrite
        #   and for each common variable list, find the common variables
        #
        ans = []
        patternVariableLists = list(map(lambda x: set(x), patternVariableLists))
        rewriteVariableLists = list(map(lambda x: set(x), rewriteVariableLists))
        while len(patternVariableLists) > 0:
            patternVariableList = patternVariableLists.pop()
            for rewriteVariableList in rewriteVariableLists:
                intersection = patternVariableList.intersection(rewriteVariableList)
                if len(intersection) > 0:
                    ans.append(list(intersection))
                    rewriteVariableLists.remove(rewriteVariableList)
                    break

        return ans
    
    # recursively get set of variable lists in a rule pattern/rewrite's AST Json
    #
    @staticmethod
    def variableListsOfASTJson(astJson: Any, path: list) -> list:
        res = []

        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            # special case for single node under SELECT clause
            #   e.g., 'select': {'value': 'V001'}
            #     extract the variable from child['value']
            #
            if len(path) >= 1 and path[-1] in ['select'] and 'value' in astJson and 'name' not in astJson and QueryRewriter.is_var(astJson['value']):
                res.append([astJson['value']])
            # recursively traverse the dict
            #
            for key, value in astJson.items():
                # note: key can not be variable list, only traverse each value
                res.extend(RuleGenerator.variableListsOfASTJson(value, path + [key]))

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            # traverse the chidlren
            #
            variableList = []
            for child in astJson:
                # put Var into the candidate variable list
                #
                if QueryRewriter.is_var(child):
                    variableList.append(child)
                # special case for list under SELECT clause
                #   e.g., 'select': [{'value': 'V001'}, {'value': 'V002'}, ...]
                #     extract the variable from child['value']
                #
                elif QueryRewriter.is_dict(child) and 'value' in child and 'name' not in child and QueryRewriter.is_var(child['value']):
                    variableList.append(child['value'])
                # otherwise, recursively traverse the child
                #
                else:
                    res.extend(RuleGenerator.variableListsOfASTJson(child, path))
            # TODO - currently only consider the variable list under SELECT, AND keys
            #
            if len(path) >= 1 and path[-1] in ['select', 'and'] and len(variableList) > 0:
                res.append(variableList)
        
        # Case-3: var
        #
        if QueryRewriter.is_var(astJson):
            # special case for single Var under SELECT, WHERE, ON
            #
            if len(path) >= 1 and path[-1] in ['select', 'where', 'on']:
            #if len(path) >= 1 and path[-1] in ['select', 'where']:
                res.append([astJson])
        
        return res
    
    # merge the given variable list in given rule and generate a new rule
    #
    @staticmethod
    def merge_variable_list(rule: dict, variableList: list) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)

        # Find a VarList name for the given variable list
        #
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_mapping, newVarListInternal = RuleGenerator.findNextVarListInternal(new_rule_mapping)
        new_rule['mapping'] = json.dumps(new_rule_mapping)

        # Replace given variable list into newVarListInternal in new rule
        #
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])
        new_rule_pattern_json = RuleGenerator.replaceVariableListsOfASTJson(new_rule_pattern_json, [], variableList, newVarListInternal)
        new_rule_rewrite_json = RuleGenerator.replaceVariableListsOfASTJson(new_rule_rewrite_json, [], variableList, newVarListInternal)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)

        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # recursively replace given variable list into given VarList in a rule's pattern/rewrite AST Json
    #
    @staticmethod
    def replaceVariableListsOfASTJson(astJson: Any, path: list, variableList: list, varList: str) -> Any:
        
        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            # special case for single node under SELECT clause
            #   e.g., 'select': {'value': 'V001'}
            #     extract the variable from child['value']
            #
            if len(path) >= 1 and path[-1] in ['select'] and 'value' in astJson and 'name' not in astJson and QueryRewriter.is_var(astJson['value']):
                if len(variableList) == 1 and astJson['value'] == variableList[0]:
                    #   in new mo_sql_parser, the child of 'select' can not be the column var directly,
                    #   but has to be like {'value': 'VL001'}
                    #
                    return {'value': varList}
            # recursively traverse the dict
            #
            for key, value in astJson.items():
                # note: key can not be variable list, only traverse each value
                astJson[key] = RuleGenerator.replaceVariableListsOfASTJson(value, path + [key], variableList, varList)
            return astJson

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            res = []
            # traverse the chidlren 1st time
            #   find candidate variable list
            #
            candidateVariableList = []
            for child in astJson:
                # put Var into the candidate variable list
                #
                if QueryRewriter.is_var(child):
                    candidateVariableList.append(child)
                # special case for list under SELECT clause
                #   e.g., 'select': [{'value': 'V001'}, {'value': 'V002'}, ...]
                #     extract the variable from child['value']
                #
                elif QueryRewriter.is_dict(child) and 'value' in child and 'name' not in child and QueryRewriter.is_var(child['value']):
                    candidateVariableList.append(child['value'])
            # if candidate variable list contains all variables in the list we want to replace
            #
            if set(variableList).issubset(set(candidateVariableList)):
                # make the candidate variable list the ones we will replace
                #
                candidateVariableList = variableList
            # otherwise, we do nothing on this astJson
            #
            else:
                candidateVariableList = []

            # traverse the chidlren 2nd time
            #   skip those variables in the candidate variable list
            #   NOTE: we intentionally do the traversal twice to 
            #         keep the original order of the list
            #
            for child in astJson:
                if QueryRewriter.is_var(child) and child in candidateVariableList:
                    # append the varList into the result children only once
                    # 
                    if varList not in res:
                        res.append(varList) 
                # special case for list under SELECT clause
                #   e.g., 'select': [{'value': 'V001'}, {'value': 'V002'}, ...]
                #     extract the variable from child['value']
                #
                elif QueryRewriter.is_dict(child) and 'value' in child and 'name' not in child and QueryRewriter.is_var(child['value']) and child['value'] in candidateVariableList:
                    # append the varList into the result children only once
                    #   in new mo_sql_parser, the child of 'select' can not be the column var directly,
                    #   but has to be like {'value': 'VL001'}
                    #
                    if {'value': varList} not in res:
                        res.append({'value': varList})
                else:
                    res.append(RuleGenerator.replaceVariableListsOfASTJson(child, path, variableList, varList))

            return res

        # Case-3: var
        #
        if QueryRewriter.is_var(astJson):
            # special case for single Var under SELECT, WHERE, ON
            #
            if len(path) >= 1 and path[-1] in ['select', 'where', 'on']:
                if len(variableList) == 1 and astJson == variableList[0]:
                    return varList
        
        return astJson
    
    # transformation function - drop branches in a rule
    #   generate a list of child rules 
    # 
    # note: we find common branches (starting from root) with variables 
    #       in pattern and rewrite and drop each branch
    # 
    # note: branches are defined as follows:
    #       (1) it must start from pattern's or rewrite's root
    #       (2) it does not have any un-variablized leaves, un-variablized subtrees, or un-merged variable sets
    #       (2) it has exact the same occurrences in both the pattern and rewrite of the rule
    #
    @staticmethod
    def drop_branches(rule: dict) -> list:

        Profiler.onFunctionStart('drop_branches')

        res = []

        # 1. Get candidate branches from rule
        #
        branches = RuleGenerator.branches(rule['pattern_json'], rule['rewrite_json'])

        # 2. Traverse candidate branches, drop one of them, and generate a new rule
        #
        for branch in branches:
            res.append(RuleGenerator.drop_branch(rule, branch))
        
        Profiler.onFunctionEnd('drop_branches')

        return res
    
    # get list of common branches (starting from root) in a seed rule's pattern_json and rewrite_json
    #
    @staticmethod
    def branches(pattern_json: str, rewrite_json: str) -> list:
        
        patternASTJson = json.loads(pattern_json)
        rewriteASTJson = json.loads(rewrite_json)

        # traverse the AST jsons to get all branches (starting from root)
        patternBranches = RuleGenerator.branchesOfASTJson(patternASTJson, [])
        rewriteBranches = RuleGenerator.branchesOfASTJson(rewriteASTJson, [])

        # find the common branches (starting from root) in pattern and rewrite
        #
        ans = []
        while len(patternBranches) > 0:
            patternBranch = patternBranches.pop()
            for rewriteBranch in rewriteBranches:
                if patternBranch['key'] == rewriteBranch['key']:
                    if RuleGenerator.sameBranch(patternBranch['value'], rewriteBranch['value']):
                        rewriteBranches.remove(rewriteBranch)
                        ans.append(patternBranch)
                        break

        return ans
    
    # check if the given two branches are the same
    #   recursively traverse the entire branches
    #
    @staticmethod
    def sameBranch(left: Any, right: Any) -> bool:
        # Case-1: both branches are dict
        #
        if QueryRewriter.is_dict(left) and QueryRewriter.is_dict(right):
            return RuleGenerator.sameBranchDict(left, right)
        
        # Case-2: both nodes are list
        #
        if QueryRewriter.is_list(left) and QueryRewriter.is_list(right):
            return RuleGenerator.sameBranchList(left, right)
        
        # Case-3: both nodes are constants
        # 
        if QueryRewriter.is_constant(left) and QueryRewriter.is_constant(right):
            return RuleGenerator.sameBranchConstant(left, right)
        
        # Case-4: both nodes are dot expressions
        # 
        if QueryRewriter.is_dot_expression(left) and QueryRewriter.is_dot_expression(right):
            return RuleGenerator.sameBranchDotExpression(left, right)
        
        # Case-5: both nodes are Vars
        # 
        if QueryRewriter.is_var(left) and QueryRewriter.is_var(right):
            return left == right
        
        # Case-6: both nodes are VarLists
        # 
        if QueryRewriter.is_varList(left) and QueryRewriter.is_varList(right):
            return left == right
        
        # Case-7: both nodes are None (special case for removing parent only)
        #
        if left is None and right is None:
            return True
        
        # Other cases: return False
        return False
    
    # check if the given two dict branches are the same
    # 
    @staticmethod
    def sameBranchDict(left: dict, right: dict) -> bool:
        # if they have different keys, return False
        #
        if set(left.keys()) != set(right.keys()):
            return False
        
        # otherwise, traverse the keys,
        #   return False if any two child branches are not the same
        # 
        for k in left.keys():
            leftChild = left.get(k)
            rightChild = right.get(k)
            if not RuleGenerator.sameBranch(leftChild, rightChild):
                return False
        
        return True
    
    # check if the given two list branches are the same
    # 
    @staticmethod
    def sameBranchList(left: list, right: list) -> bool:
        # if they have different length, return False
        #
        if len(left) != len(right):
            return False
        
        # otherwise, traverse the elements in left,
        #   for each element, find its same branch element in right 
        # 
        remainingInRight = right.copy()
        for leftChild in left:
            find = False
            for rightChild in remainingInRight:
                # if found same branch for leftChild
                #
                if RuleGenerator.sameBranch(leftChild, rightChild):
                    remainingInRight.remove(rightChild)
                    find = True
                    break
            if not find:
                return False
        
        return True
    
    # check if the given two constant branches are the same
    #
    @staticmethod
    def sameBranchConstant(left: Any, right: Any) -> bool:
        if QueryRewriter.is_string(left) and QueryRewriter.is_string(right):
            return RuleGenerator.sameBranchString(left, right)
        if QueryRewriter.is_number(left) and QueryRewriter.is_number(right):
            return RuleGenerator.sameBranchNumber(left, right)
        return False
    
    # check if the given two string branches are the same
    #
    @staticmethod
    def sameBranchString(left: str, right: str) -> bool:
        if left.lower() == right.lower():
            return True
        return False
    
    # check if the given two number branches are the same
    #
    @staticmethod
    def sameBranchNumber(left: numbers, right: numbers) -> bool:
        if left == right:
            return True
        return False
    
    # check if the given two dot expression branches are the same
    #
    @staticmethod
    def sameBranchDotExpression(left: str, right: str) -> bool:
        leftChildren = left.split('.')
        rightChildren = right.split('.')
        # if they have different length
        if len(leftChildren) != 2 or len(rightChildren) != 2:
            return False
        
        if not RuleGenerator.sameBranchString(leftChildren[0], rightChildren[0]):
            return False
        if not RuleGenerator.sameBranchString(leftChildren[1], rightChildren[1]):
            return False
        
        return True
    
    # get set of branches (starting from root) in a rule pattern/rewrite's AST Json
    #   output format: [{'key': key, 'value': value}, ...]
    @staticmethod
    def branchesOfASTJson(astJson: Any, path: list) -> list:
        res = []

        # Case-1: dict
        #
        # a branch only occurs in a dict
        if QueryRewriter.is_dict(astJson):

            # special case: there is only one key in the AST Json
            #
            if len(astJson.keys()) == 1:
                key = list(astJson.keys())[0]
                children = astJson[key]

                # special case (a): the value is a list
                #   e.g., {'and': [{'gt': [...]}, {'eq':[...]}]}
                #
                if QueryRewriter.is_list(children):
                    # each element in the children list is a branch
                    #
                    for child in children:
                        if RuleGenerator.isBranch({key: [child]}):
                            res.append({'key': key, 'value': child})
                # special case (b): the value is not a list
                #   e.g., {'select': {'gt': [{'strpos': [{'lower': 'V1'}, {'literal': 'V2'}]}, 0]}}
                #     we should remove the parent 'select' 
                #       by adding a branch {key: select, value: None}
                #
                else:
                    res.append({'key': key, 'value': None})
            else:
                for key, value in astJson.items():
                    if RuleGenerator.isBranch({key: value}):
                        res.append({'key': key, 'value': value})
                
                # special cases: 
                #   (1) if {'select': ...} and {'where': ...} present, remove {'from': ...} branch
                #   (2) if only {'from': ...} presents, remove {'where': ...} branch
                #
                if 'select' in astJson.keys() and 'where' in astJson.keys():
                    res = [branch for branch in res if branch['key'] != 'from']
                if 'select' not in astJson.keys() and 'from' in astJson.keys():
                    res = [branch for branch in res if branch['key'] != 'where']
            
        
        return res
    
    # check if a subtree (starting from root) in rule pattern/rewrite's AST Json is a branch
    #   see comments in drop_branches() for the definition of a branch
    #
    @staticmethod
    def isBranch(astJson: dict) -> bool:

        # check if it has un-variablized tables
        #
        tables = RuleGenerator.tablesOfASTJson(astJson, [])
        if len(tables) > 0:
            return False

        # check if it has un-variablized columns
        #
        columns = RuleGenerator.columnsOfASTJson(astJson, [])
        # special case for {'select': {'all_columns': {}}}, which should be a branch
        #   columns = {'*'}
        #
        if len(columns) > 0:
            if len(columns) == 1 and list(columns)[0] == '*':
                return True
            return False
        
        # check if it has un-variablized literals
        #
        literals = RuleGenerator.literalsOfASTJson(astJson, [])
        if len(literals) > 0:
            return False
        
        # ignore this check for now
        # check if it has un-variablized subtrees
        #
        # subtrees = RuleGenerator.subtreesOfASTJson(astJson, [])
        # if len(subtrees) > 0:
        #     return False

        # check if it has un-merged variable lists
        #
        variableLists = RuleGenerator.variableListsOfASTJson(astJson, [])
        if len(variableLists) > 0:
            return False

        return True
    
    # drop the given branch in given rule and generate a new rule
    #
    @staticmethod
    def drop_branch(rule: dict, branch: dict) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)

        # Drop given branch in new rule
        #
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])
        new_rule_pattern_json = RuleGenerator.dropBranchOfASTJson(new_rule_pattern_json, [], branch)
        new_rule_rewrite_json = RuleGenerator.dropBranchOfASTJson(new_rule_rewrite_json, [], branch)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)

        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # drop given branch in a rule's pattern/rewrite AST Json
    #
    @staticmethod
    def dropBranchOfASTJson(astJson: Any, path: list, branch: dict) -> Any:
        
        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            # if there are > 2 keys in the AST Json
            #   remove the branch key directly
            #
            if len(astJson.keys()) > 1:
                del astJson[branch['key']]

                # special case: after removing the branch, the root has only one child which is not a list
                #   e.g., {'where': {'gt': [{'strpos': [{'lower': 'V1'}, {'literal': 'V2'}]}, 0]}}
                #   we should remove the root as well
                #
                # if len(astJson.keys()) == 1:
                #     key = list(astJson.keys())[0]
                #     if not QueryRewriter.is_list(astJson[key]):
                #         astJson = astJson[key]

            # special case: there is only one key in the AST Json
            # 
            elif len(astJson.keys()) == 1:
                children = astJson[branch['key']]

                # special case (a): the value is a list
                #   e.g., {'and': [{'gt': [...]}, {'eq':[...]}]}
                #   remove the branch value from the children list
                #
                if QueryRewriter.is_list(children):
                    astJson[branch['key']] = [value for value in children if not RuleGenerator.sameBranch(value, branch['value'])]
                
                    # special case: after removing the branch, the chidlren list has only one element
                    #   e.g., {'and': [{'gt': [{'strpos': [{'lower': 'V1'}, {'literal': 'V2'}]}, 0] }] }
                    #   we should remove the root as well
                    #
                    if len(astJson[branch['key']]) == 1:
                        astJson = astJson[branch['key']][0]

                # special case (b): the value is not a list
                #   e.g., {'select': {'gt': [{'strpos': [{'lower': 'V1'}, {'literal': 'V2'}]}, 0]}}
                #     we should remove the parent 'select' 
                #
                else:
                    astJson = children
        
        return astJson

    RuleTransformations = {
        'variablize_tables': variablize_tables,
        'variablize_columns' : variablize_columns,
        'variablize_literals' : variablize_literals,
        'variablize_subtrees' : variablize_subtrees,
        'merge_variables': merge_variables,
        'drop_branches': drop_branches,
    }

    # Generate the candidate rule graph for a given rewriting pair q0 -> q1
    #
    @staticmethod
    def generate_rule_graph(q0: str, q1: str) -> dict:
        
        # Generate seedRule from the given rewriting pair
        #
        # seedRule = RuleGenerator.generate_seed_rule(q0, q1)

        # Initialize seedRule from the given rewriting pair
        #
        seedRule = RuleGenerator.initialize_seed_rule(q0, q1)

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

    # Recommend simplified rules set that cover all examples
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
    def recommend_simple_rules(examples: list) -> list:
        globalVisited = {}
        ans = []
        uncoveredExamples = set(range(len(examples)))
        
        for num, example in enumerate(examples):
            if num not in uncoveredExamples:
                continue
            if uncoveredExamples:
                graphRoot = RuleGenerator.generate_minimal_rule(
                    example['q0'], example['q1'], globalVisited, examples, uncoveredExamples, num)
                if graphRoot:  # If a new rule is found that covers uncovered examples
                    ans.append(graphRoot)
            else:
                break  # All examples are covered

        return ans


    @staticmethod
    def generate_minimal_rule(q0: str, q1: str, visited: dict, examples: list, uncoveredExamples: set, num: int) -> dict:
        ans = {}

        seedRule = RuleGenerator.initialize_seed_rule(q0, q1)
        seedRuleFingerPrint = RuleGenerator.fingerPrint(seedRule)
        
        queue = [seedRule]
        visited[seedRuleFingerPrint] = seedRule
        seedRule['coveredExamples'] = RuleGenerator.coveredExamples(seedRule, examples)

        while queue and uncoveredExamples:
            baseRule = queue.pop(0)
            baseRule['children'] = []

            for transform in RuleGenerator.RuleTransformations.keys():
                childrenRules = getattr(RuleGenerator, transform)(baseRule)

                for childRule in childrenRules:
                    childRuleFingerPrint = RuleGenerator.fingerPrint(childRule)

                    # If the child rule is new, mark it as visited.
                    if childRuleFingerPrint not in visited:
                        visited[childRuleFingerPrint] = childRule
                        childRule['coveredExamples'] = RuleGenerator.coveredExamples(childRule, examples)
                        coveredExamplesSet = set(childRule['coveredExamples'])

                        # If the new rule covers any uncovered examples, update the uncovered examples set.
                        if uncoveredExamples.intersection(coveredExamplesSet):
                            uncoveredExamples -= coveredExamplesSet
                            queue.append(childRule)
                            baseRule['children'].append(childRule)

                            ans = childRule

                            if not uncoveredExamples:  # All examples are covered
                                return childRule
                    else:
                        baseRule['children'].append(visited[childRuleFingerPrint])

        return ans
    
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
            formatted_q1 = mosql.format(mosql.parse(q1))
            formatted_q1_test = mosql.format(mosql.parse(q1_test))
            if formatted_q1 == formatted_q1_test:
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
    
    # generalization function - generalize columns in a rule
    #
    @staticmethod
    def generalize_columns(rule: dict) -> dict:

        # 1. Get candidate columns from rule
        #
        columns = RuleGenerator.columns(rule['pattern_json'], rule['rewrite_json'])

        # 2. Make all candidate columns variables, and generate a new rule
        #
        return RuleGenerator.variablize_all_columns(rule, columns)
    
    # variablize all the given columns in given rule and generate a new rule
    #
    @staticmethod
    def variablize_all_columns(rule: dict, columns: list) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])

        # Traverse all columns
        for column in columns:

            # Find a variable name for the column
            #
            new_rule_mapping, newVarInternal = RuleGenerator.findNextVarInternal(new_rule_mapping)
            
            # Replace given column into newVarInternal in new rule
            #
            new_rule_pattern_json = RuleGenerator.replaceColumnsOfASTJson(new_rule_pattern_json, [], column, newVarInternal)
            new_rule_rewrite_json = RuleGenerator.replaceColumnsOfASTJson(new_rule_rewrite_json, [], column, newVarInternal)
            
            # TODO - add newVarInternal is a column constraint into new rule's constraints
        
        new_rule['mapping'] = json.dumps(new_rule_mapping)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)
        
        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # generalization function - generalize literals in a rule
    #
    @staticmethod
    def generalize_literals(rule: dict) -> dict:

        # 1. Get candidate literals from rule
        #
        literals = RuleGenerator.literals(rule['pattern_json'], rule['rewrite_json'])

        # 2. Make all candidate literals variables, and generate a new rule
        #
        return RuleGenerator.variablize_all_literals(rule, literals)
    
    # variablize all the given literals in given rule and generate a new rule
    #
    @staticmethod
    def variablize_all_literals(rule: dict, literals: list) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])

        # Traverse all literals
        for literal in literals:

            # Find a variable name for the literal
            #
            new_rule_mapping, newVarInternal = RuleGenerator.findNextVarInternal(new_rule_mapping)
            
            # Replace given literal into newVarInternal in new rule
            #
            new_rule_pattern_json = RuleGenerator.replaceLiteralsOfASTJson(new_rule_pattern_json, [], literal, newVarInternal)
            new_rule_rewrite_json = RuleGenerator.replaceLiteralsOfASTJson(new_rule_rewrite_json, [], literal, newVarInternal)
            
            # TODO - add newVarInternal is a literal constraint into new rule's constraints
        
        new_rule['mapping'] = json.dumps(new_rule_mapping)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)
        
        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # generalization function - generalize tables in a rule
    #
    @staticmethod
    def generalize_tables(rule: dict) -> dict:

        # 1. Get candidate tables from rule
        #
        tables = RuleGenerator.tables(rule['pattern_json'], rule['rewrite_json'])

        # 2. Make all candidate tables variables, and generate a new rule
        #
        return RuleGenerator.variablize_all_tables(rule, tables)
    
    # variablize all the given tables in given rule and generate a new rule
    #
    @staticmethod
    def variablize_all_tables(rule: dict, tables: list) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])

        for table in tables:
            # Find a variable name for the given table
            #
            new_rule_mapping, newVarInternal = RuleGenerator.findNextVarInternal(new_rule_mapping)

            # Replace given table into newVarInternal in new rule
            #
            new_rule_pattern_json = RuleGenerator.replaceTablesOfASTJson(new_rule_pattern_json, [], table, newVarInternal)
            new_rule_rewrite_json = RuleGenerator.replaceTablesOfASTJson(new_rule_rewrite_json, [], table, newVarInternal)

            # TODO - add newVarInternal is a table constraint into new rule's constraints

        new_rule['mapping'] = json.dumps(new_rule_mapping)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)
        
        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # generalization function - generalize subtrees in a rule
    #
    @staticmethod
    def generalize_subtrees(rule: dict) -> dict:

        # 1. Get candidate subtrees from rule
        #
        subtrees = RuleGenerator.subtrees(rule['pattern_json'], rule['rewrite_json'])

        # 2. Make all candidate subtrees variables, and generate a new rule
        #
        return RuleGenerator.variablize_all_subtrees(rule, subtrees)
    
    # variablize all the given subtrees in given rule and generate a new rule
    #
    @staticmethod
    def variablize_all_subtrees(rule: dict, subtrees: list) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])

        for subtree in subtrees:
            # Find a variable name for the given subtree
            #
            new_rule_mapping, newVarInternal = RuleGenerator.findNextVarInternal(new_rule_mapping)

            # Replace given subtree into newVarInternal in new rule
            #
            new_rule_pattern_json = RuleGenerator.replaceSubtreesOfASTJson(new_rule_pattern_json, [], subtree, newVarInternal)
            new_rule_rewrite_json = RuleGenerator.replaceSubtreesOfASTJson(new_rule_rewrite_json, [], subtree, newVarInternal)

        new_rule['mapping'] = json.dumps(new_rule_mapping)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)
        
        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # generalization function - generalize variables in a rule
    #
    @staticmethod
    def generalize_variables(rule: dict) -> dict:

        # 1. Get candidate variable lists from rule
        #
        variableLists = RuleGenerator.variable_lists(rule['pattern_json'], rule['rewrite_json'])

        # 2. Make all candidate variable lists VarLists, and generate a new rule
        #
        return RuleGenerator.merge_all_variable_lists(rule, variableLists)

    # merge all the given variable lists in given rule and generate a new rule
    #
    @staticmethod
    def merge_all_variable_lists(rule: dict, variableLists: list) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])

        for variableList in variableLists:
            # Find a VarList name for the given variable list
            #
            new_rule_mapping, newVarListInternal = RuleGenerator.findNextVarListInternal(new_rule_mapping)

            # Replace given variable list into newVarListInternal in new rule
            #
            new_rule_pattern_json = RuleGenerator.replaceVariableListsOfASTJson(new_rule_pattern_json, [], variableList, newVarListInternal)
            new_rule_rewrite_json = RuleGenerator.replaceVariableListsOfASTJson(new_rule_rewrite_json, [], variableList, newVarListInternal)

        new_rule['mapping'] = json.dumps(new_rule_mapping)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)
        
        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    # generalization function - generalize branches in a rule
    #
    @staticmethod
    def generalize_branches(rule: dict) -> dict:

        # 1. Get candidate branches from rule
        #
        branches = RuleGenerator.branches(rule['pattern_json'], rule['rewrite_json'])

        # 2. Drop all candidate branches, and generate a new rule
        #
        return RuleGenerator.drop_all_branches(rule, branches)
    
    # drop all the given branches in given rule and generate a new rule
    #
    @staticmethod
    def drop_all_branches(rule: dict, branches: list) -> dict:

        # create a new rule based on rule
        new_rule = RuleGenerator.copy_a_rule(rule)
        new_rule_mapping = json.loads(new_rule['mapping'])
        new_rule_pattern_json = json.loads(new_rule['pattern_json'])
        new_rule_rewrite_json = json.loads(new_rule['rewrite_json'])

        for branch in branches:

            # Drop given branch in new rule
            #
            new_rule_pattern_json = RuleGenerator.dropBranchOfASTJson(new_rule_pattern_json, [], branch)
            new_rule_rewrite_json = RuleGenerator.dropBranchOfASTJson(new_rule_rewrite_json, [], branch)

        new_rule['mapping'] = json.dumps(new_rule_mapping)
        new_rule['pattern_json'] = json.dumps(new_rule_pattern_json)
        new_rule['rewrite_json'] = json.dumps(new_rule_rewrite_json)
        
        # Deparse new rule's pattern_json/rewrite_json into pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.deparse(new_rule_pattern_json)
        new_rule['rewrite'] = RuleGenerator.deparse(new_rule_rewrite_json)

        # Dereplace vars from new rule's pattern/rewrite strings
        #
        new_rule['pattern'] = RuleGenerator.dereplaceVars(new_rule['pattern'], new_rule_mapping)
        new_rule['rewrite'] = RuleGenerator.dereplaceVars(new_rule['rewrite'], new_rule_mapping)

        return new_rule
    
    RuleGeneralizations = {
        'generalize_tables': generalize_tables,
        'generalize_columns' : generalize_columns,
        'generalize_literals' : generalize_literals,
        'generalize_subtrees': generalize_subtrees,
        'generalize_variables': generalize_variables,
        'generalize_branches': generalize_branches
    }

    # Generate a general rule given a rewriting pair q0 -> q1
    #
    @staticmethod
    def generate_general_rule(q0: str, q1: str) -> dict:
        
        # Generate seedRule from the given rewriting pair
        #
        # seedRule = RuleGenerator.generate_seed_rule(q0, q1)

        # Initialize seedRule from the given rewriting pair
        #
        seedRule = RuleGenerator.initialize_seed_rule(q0, q1)

        # Generalize the seedRule by applying all possible transformations 
        #   recursively until no more differences
        #
        generalRule = seedRule
        preRuleFingerprint = RuleGenerator.fingerPrint(generalRule)
        diff = True
        while diff:
            for generalization in RuleGenerator.RuleGeneralizations.keys():
                generalRule = getattr(RuleGenerator, generalization)(generalRule)
            newRuleFingerprint = RuleGenerator.fingerPrint(generalRule)
            if newRuleFingerprint == preRuleFingerprint:
                diff = False
            preRuleFingerprint = newRuleFingerprint
        
        return generalRule

    # Suggest rules for a given set of examples
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
    def suggest_rules(examples: list, exp: str='bf', k: int=1, m: int=5, profile: dict={}) -> list:

        start = time.time()

        ans = []

        # Initialize original examples's seed rules as the answer
        #
        for example in examples:
            ans.append(RuleGenerator.initialize_seed_rule(example['q0'], example['q1']))

        cnt_iterations = 0
        cnts_candidates = []
        while True:

            # Explore candidates based on current answer
            #
            candidates = RuleGenerator.explore_candidates(baseRules=ans, exp=exp, k=k, m=m)
            cnt_iterations += 1
            cnts_candidates.append(len(candidates))

            delta_lengths = [0] * len(candidates)
            to_be_replaced_rules = [[] for i in range(len(candidates))]

            for i in range(len(candidates)):

                candidate = candidates[i]

                # find rules in answer that can be replaced by candidate
                #
                to_be_replaced_rules[i] = RuleGenerator.coveredRules(candidate, ans, examples)

                # compute the length reduction if 'candidate' replace 'to_be_replaced' rules
                #
                delta_lengths[i] = sum([RuleGenerator.description_length(r) for r in to_be_replaced_rules[i]]) - RuleGenerator.description_length(candidate)
            
            # stop when no more reduction possible
            #
            if max(delta_lengths) <= 0:
                break

            # choose the candidate rule with the most length reduction
            #
            imax = delta_lengths.index(max(delta_lengths))
            icandidate = candidates[imax]

            ans = [r for r in ans if r not in to_be_replaced_rules[imax]]
            ans.append(icandidate)
        
        end = time.time()
        profile['time'] = end - start
        profile['cnt_iterations'] = cnt_iterations
        profile['cnts_candidates'] = cnts_candidates
        
        return ans
    
    # Compute a list of rules in the given baseRules 
    #   that can be covered by the given rule on the given examples
    #
    @staticmethod
    def coveredRules(rule: dict, baseRules: list, examples: list) -> list:

        # compute the covered examples indexes for each base rule
        #
        for baseRule in baseRules:
            if 'coveredExamples' not in baseRule.keys():
                baseRule['coveredExamples'] = RuleGenerator.coveredExamples(baseRule, examples)
        
        # compute the covered examples indexes for the given rule
        #
        if 'coveredExamples' not in rule.keys():
            rule['coveredExamples'] = RuleGenerator.coveredExamples(rule, examples)
        
        ans = []

        # compute the covered base rules:
        #   the covered examples indexes of a base rule is a subset of the covered examples indexes of the rule
        # 
        for baseRule in baseRules:
             if set(baseRule['coveredExamples']).issubset(set(rule['coveredExamples'])):
                ans.append(baseRule)
        
        return ans
    
    # Compute the description length of a given rule
    #
    @staticmethod
    def description_length(rule: dict) -> float:
        
        # the base length of a rule
        #
        base = 100.0
        # base = 500.0

        # the weight of a Var
        #
        w_var = 2.0

        # the weight of a VarList
        #
        w_varList = 5.0

        # count Vars
        #
        cnt_var = RuleGenerator.countVars(rule)

        # count VarLists
        #
        cnt_varList = RuleGenerator.countVarLists(rule)

        # count Invariables
        #
        cnt_invars = RuleGenerator.countInvariables(rule)

        length = base + (cnt_var * w_var + cnt_varList * w_varList) / cnt_invars

        return length
    
    # Count the Vars in a rule
    #
    @staticmethod
    def countVars(rule: dict) -> int:
        ans = 0
        for key, value in json.loads(rule['mapping']).items():
            if QueryRewriter.is_var(value):
                ans += 1
        return ans
    
    # Count the VarLists in a rule
    #
    @staticmethod
    def countVarLists(rule: dict) -> int:
        ans = 0
        for key, value in json.loads(rule['mapping']).items():
            if QueryRewriter.is_varList(value):
                ans += 1
        return ans
    
    # Count the invariables in a rule
    #   invariables include: keywords, constants, fixed table and column names, etc. 
    #   (In other words, all strings that are not Var or VarList)
    #
    @staticmethod
    def countInvariables(rule: dict) -> int:
        return RuleGenerator.countInvariablesASTJson(json.loads(rule['pattern_json'])) + RuleGenerator.countInvariablesASTJson(json.loads(rule['rewrite_json']))
    
    # Recursively count the invariables in a rule's pattern/rewrite's AST Json
    #
    @staticmethod
    def countInvariablesASTJson(astJson: Any) -> int:

        # Case-1: dict
        #
        if QueryRewriter.is_dict(astJson):
            cnt = 0
            for key, value in astJson.items():
                cnt += RuleGenerator.countInvariablesASTJson(key) + RuleGenerator.countInvariablesASTJson(value)
            return cnt

        # Case-2: list
        # 
        if QueryRewriter.is_list(astJson):
            cnt = 0
            for child in astJson:
                cnt += RuleGenerator.countInvariablesASTJson(child)
            return cnt

        # Case-3: constant
        if QueryRewriter.is_constant(astJson):
            return 1
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            parts = astJson.split('.')
            return RuleGenerator.countInvariablesASTJson(parts[0]) + RuleGenerator.countInvariablesASTJson(parts[1])
        
        # Other cases: Var or VarList
        #
        return 0
    
    # explore candidate rules for a given list of base rules
    #
    @staticmethod
    def explore_candidates(baseRules: list, exp: str, k: int, m: int) -> list:
        if exp == 'bf':
            return RuleGenerator.explore_candidates_bf(baseRules)
        elif exp == 'khn':
            return RuleGenerator.explore_candidates_khn(baseRules, k=k)
        elif exp == 'mpn':
            return RuleGenerator.explore_candidates_mpn(baseRules, m=m)
        
        return RuleGenerator.explore_candidates_bf(baseRules)
    
    # explore candidate rules for a given list of base rules
    #   (1) Brute-Force 
    #
    @staticmethod
    def explore_candidates_bf(baseRules: list) -> list:

        ans = []

        # Generate the candidate rules' graphs starting from all base rules
        #
        # Initialize queue with all the base rules
        #
        queue = []
        visited = {}
        for baseRule in baseRules:
            # Cache finger print in rule
            #
            if 'fingerPrint' not in baseRule.keys():
                baseRule['fingerPrint'] = RuleGenerator.fingerPrint(baseRule)
            visited[baseRule['fingerPrint']] = baseRule
            queue.append(baseRule)
            # put base rules in the candidate set as a corner case
            #
            ans.append(baseRule)
        
        # Breadth First Search
        #
        while len(queue) > 0:
            baseRule = queue.pop(0)
            # First time transform a rule
            #
            if 'transformed' not in baseRule.keys() or not baseRule['transformed']:
                baseRule['children'] = []
                # generate children from the baseRule
                #   by applying each transformation on baseRule
                #
                for transform in RuleGenerator.RuleTransformations.keys():
                    childrenRules = getattr(RuleGenerator, transform)(baseRule)
                    for childRule in childrenRules:
                        # Cache finger print in rule
                        #
                        childRule['fingerPrint'] = RuleGenerator.fingerPrint(childRule)
                        # if childRule has not been visited
                        #
                        if childRule['fingerPrint'] not in visited.keys():
                            visited[childRule['fingerPrint']] = childRule
                            queue.append(childRule)
                            baseRule['children'].append(childRule)
                            ans.append(childRule)
                        # else childRule has been visited (generated from an ealier baseRule)
                        #
                        else:
                            baseRule['children'].append(visited[childRule['fingerPrint']])
                baseRule['transformed'] = True
            # Rule already transformed
            #
            else:
                childrenRules = baseRule['children']
                for childRule in childrenRules:
                    # if childRule has not been visited
                    if childRule['fingerPrint'] not in visited.keys():
                        visited[childRule['fingerPrint']] = childRule
                        queue.append(childRule)
                        ans.append(childRule)
        
        return ans
    
    # explore candidate rules for a given list of base rules
    #   (2) k-hop neighbors 
    #
    @staticmethod
    def explore_candidates_khn(baseRules: list, k: int) -> list:

        ans = []

        # Generate the candidate rules' graphs starting from all base rules
        #
        # Initialize queue with all the base rules
        #
        queue = []
        visited = {}
        for baseRule in baseRules:
            # Cache finger print in rule
            #
            if 'fingerPrint' not in baseRule.keys():
                baseRule['fingerPrint'] = RuleGenerator.fingerPrint(baseRule)
            visited[baseRule['fingerPrint']] = baseRule
            # the format is (hop, rule)
            #
            queue.append((0, baseRule))
            # put base rules in the candidate set as a corner case
            #
            ans.append(baseRule)
        
        # Breadth First Search
        #   stop when reaching a hop > k
        #
        while len(queue) > 0:
            hop, baseRule = queue.pop(0)
            if hop > k:
                break
            # First time transform a rule
            #
            if 'children' not in baseRule.keys():
                baseRule['children'] = []
                # generate children from the baseRule
                #   by applying each transformation on baseRule
                #
                for transform in RuleGenerator.RuleTransformations.keys():
                    childrenRules = getattr(RuleGenerator, transform)(baseRule)
                    for childRule in childrenRules:
                        # Cache finger print in rule
                        #
                        childRule['fingerPrint'] = RuleGenerator.fingerPrint(childRule)
                        # if childRule has not been visited
                        #
                        if childRule['fingerPrint'] not in visited.keys():
                            visited[childRule['fingerPrint']] = childRule
                            queue.append((hop + 1, childRule))
                            baseRule['children'].append(childRule)
                            ans.append(childRule)
                        # else childRule has been visited (generated from an ealier baseRule)
                        #
                        else:
                            baseRule['children'].append(visited[childRule['fingerPrint']])
                baseRule['transformed'] = True
            # Rule already transformed
            #
            else:
                childrenRules = baseRule['children']
                for childRule in childrenRules:
                    # if childRule has not been visited
                    if childRule['fingerPrint'] not in visited.keys():
                        visited[childRule['fingerPrint']] = childRule
                        queue.append((hop + 1, childRule))
                        ans.append(childRule)
        
        return ans
    
    # explore candidate rules for a given list of base rules
    #   (3) m-promising neighbors 
    #
    @staticmethod
    def explore_candidates_mpn(baseRules: list, m: int) -> list:

        ans = []

        # Generate the candidate rules' graphs starting from all base rules
        #
        # Initialize ans with all the base rules
        #
        visited = {}
        for baseRule in baseRules:
            # Cache finger print in rule
            #
            if 'fingerPrint' not in baseRule.keys():
                baseRule['fingerPrint'] = RuleGenerator.fingerPrint(baseRule)
            visited[baseRule['fingerPrint']] = baseRule
            # Cache promising score in rule
            #
            if 'promisingScore' not in baseRule.keys():
                baseRule['promisingScore'] = RuleGenerator.promisingScore(baseRule, baseRules)
            # Put base rule in the candidate set
            #
            ans.append(baseRule)
        
        # Best First Search
        #   stop when reaching a |ans| >= m
        #
        explored = []
        while len(ans) < m:
            # Find the base rule in ans that has not been explored and has the max promising score
            #
            unexplored_ans = [r for r in ans if r['fingerPrint'] not in explored]
            # Corner case that all neighbors have been explored
            #
            if len(unexplored_ans) == 0:
                break
            # Sort the unexplored ans rules by promising score descending
            #
            unexplored_ans = sorted(unexplored_ans, key=lambda x:x['promisingScore'], reverse=True)
            # Pick the first unexplored ans rule (max promising score)
            #
            baseRule = unexplored_ans[0]
            explored.append(baseRule['fingerPrint'])
            
            # First time transform a rule
            #
            if 'children' not in baseRule.keys():
                baseRule['children'] = []
                # generate children from the baseRule
                #   by applying each transformation on baseRule
                #
                for transform in RuleGenerator.RuleTransformations.keys():
                    childrenRules = getattr(RuleGenerator, transform)(baseRule)
                    for childRule in childrenRules:
                        # Cache finger print in rule
                        #
                        childRule['fingerPrint'] = RuleGenerator.fingerPrint(childRule)
                        # if childRule has not been visited
                        #
                        if childRule['fingerPrint'] not in visited.keys():
                            visited[childRule['fingerPrint']] = childRule
                            # Cache promising score in rule
                            #
                            if 'promisingScore' not in childRule.keys():
                                childRule['promisingScore'] = RuleGenerator.promisingScore(childRule, baseRules)
                            baseRule['children'].append(childRule)
                            ans.append(childRule)
                        # else childRule has been visited (generated from an ealier baseRule)
                        #
                        else:
                            baseRule['children'].append(visited[childRule['fingerPrint']])
                baseRule['transformed'] = True
            # Rule already transformed
            #
            else:
                childrenRules = baseRule['children']
                for childRule in childrenRules:
                    # if childRule has not been visited
                    if childRule['fingerPrint'] not in visited.keys():
                        visited[childRule['fingerPrint']] = childRule
                        # Cache promising score in rule
                        #
                        if 'promisingScore' not in childRule.keys():
                            childRule['promisingScore'] = RuleGenerator.promisingScore(childRule, baseRules)
                        ans.append(childRule)
        
        return ans
    
    # Compute the promising score of a given rule on the given set of base rules
    #
    @staticmethod
    def promisingScore(rule: dict, baseRules: list) -> float:
        ans = 0.0

        for baseRule in baseRules:
            ans += RuleGenerator.description_length(baseRule) / (RuleGenerator.cntTransformations(rule, baseRule) + 1)
        
        ans += 1.0 / RuleGenerator.description_length(rule)

        return ans
    
    # Count the number of transformations to transform the given left rule to cover the given right rule
    #
    @staticmethod
    def cntTransformations(left: dict, right: dict) -> int:
        # The right rule is like a query pair. 
        #   We want the left rule pattern matches the pairs' original query,
        #     and rewrites it to the pair's rewritten query.
        # 
        # Note: TODO - We only check the patterns between left and right for now. 
        #
        leftRulePatternASTJson = json.loads(left['pattern_json'])
        rightRulePatternASTJson = json.loads(right['pattern_json'])
        ans = RuleGenerator.cntTransformationsASTJson(leftRulePatternASTJson, rightRulePatternASTJson)
        return ans
    
    # Recursively count the number of transformations to transform the given left pattern AST Json to cover the given right pattern AST Json
    #
    @staticmethod
    def cntTransformationsASTJson(left_node: Any, right_node: Any) -> int:

        # Case-1: treate left_node as the rule
        #
        # Similar to QueryRewriter's match function:
        #   Breadth-First-Search on the right pattern AST Json
        # 
        queue = [right_node]
        min_cnt_transformations = MAX_INT
        while len(queue) > 0:
            curr_node = queue.pop(0)
            cnt_transformations = RuleGenerator.cntTransformationsASTJsonNode(left_node, curr_node)
            min_cnt_transformations = min(min_cnt_transformations, cnt_transformations)
            if type(curr_node) is dict:
                for child in curr_node.values():
                    queue.append(child)
            elif type(curr_node) is list:
                for child in curr_node:
                    queue.append(child)
        
        # Case-2: try dropping branch on left_node
        # 
        # However, to transform the left rule to a more general form that covers the pair,
        #   one kind of transformations can be the drop_branch().
        #     Thus, we also need to enumerate possible subtrees of the left rule,
        #       count the transformations starting with the subtrees,
        #         and add up the drop_branch() operations to count the total transformations.
        #
        if type(left_node) is dict:
            for child in left_node.values():
                # Count if using this child to match the right_node (which means all other children are dropped as branches)
                #
                cnt_transformations = RuleGenerator.cntTransformationsASTJson(child, right_node)
                # Count all other branches in left_node should transform to match a Var
                #   such that it can be a branch to be dropped
                #
                cnt_remaining_transformations = 0
                for remaining_child in left_node.values():
                    if remaining_child != child:
                        # each remaining child should match a Var and then +1 transformation of dropping it as a branch
                        #
                        cnt_remaining_transformations += RuleGenerator.cntTransformationsASTJsonNode(remaining_child, 'V001') + 1
                min_cnt_transformations = min(min_cnt_transformations, cnt_transformations + cnt_remaining_transformations)
        elif type(left_node) is list:
            for child in left_node:
                # Count if using this child to match the right_node (which means all other children are dropped as branches)
                #
                cnt_transformations = RuleGenerator.cntTransformationsASTJson(child, right_node)
                # Count all other branches in left_node should transform to match a Var
                #   such that it can be a branch to be dropped
                #
                cnt_remaining_transformations = 0
                for remaining_child in left_node:
                    if remaining_child != child:
                        # each remaining child should match a Var and then +1 transformation of dropping it as a branch
                        #
                        cnt_remaining_transformations += RuleGenerator.cntTransformationsASTJsonNode(remaining_child, 'V001') + 1
                min_cnt_transformations = min(min_cnt_transformations, cnt_transformations + cnt_remaining_transformations)

        return min_cnt_transformations
    
    # Recursively count the number of transformations to transform 
    #   the given left pattern AST Json node to cover the given right pattern AST Json node
    #
    @staticmethod
    def cntTransformationsASTJsonNode(left_node: Any, right_node: Any) -> int:
        # Refer to QueryRewriter.match_node()
        #
        
        # Special case for value of 'select' and 'from':
        #   e.g., right_node = [{"value": "e1.name"}, {"value": "e1.age"}, {"value": "e2.salary"}]
        #         left_node = {"value": "VL1"}
        #   The idea is escalate the "VL1" from inside {"value": "VL1"} to outside
        # 
        if QueryRewriter.is_dict(left_node) and 'value' in left_node.keys() and QueryRewriter.is_varList(left_node['value']):
            return 0
        
        # Case-1: left_node is a Var
        # 
        if QueryRewriter.is_var(left_node):
            return RuleGenerator.cntTransformationsASTJsonVar(left_node, right_node)
        
        # Case-2: left_node is a VarList
        # 
        if QueryRewriter.is_varList(left_node):
            return RuleGenerator.cntTransformationsASTJsonVarList(left_node, right_node)
        
        # Case-3: left_node is a constant
        if QueryRewriter.is_constant(left_node):
            return RuleGenerator.cntTransformationsASTJsonConstant(left_node, right_node)
        
        # Case-4: left_node is a dict
        # 
        if QueryRewriter.is_dict(left_node):
            return RuleGenerator.cntTransformationsASTJsonDict(left_node, right_node)
                
        # Case-5: left_node is a list
        # 
        if QueryRewriter.is_list(left_node):
            return RuleGenerator.cntTransformationsASTJsonList(left_node, right_node)
            
        # Case-6: left_node is a dot expression
        #
        if QueryRewriter.is_dot_expression(left_node):
            return RuleGenerator.cntTransformationsASTJsonDotExpression(left_node, right_node)

        return 0

    # Count the number of transformations to transform 
    #   the given left pattern AST Json Var to cover the given right pattern AST Json node
    #
    @staticmethod
    def cntTransformationsASTJsonVar(left_node: str, right_node: Any) -> int:

        # Case-1: right_node is a Var
        # 
        if QueryRewriter.is_var(right_node):
            return 0
        
        # Case-2: right_node is a VarList
        # 
        if QueryRewriter.is_varList(right_node):
            # 1 transformation: <left> --[merge_variables]--> <<left>>
            return 1
        
        # Case-3: right_node is a constant
        if QueryRewriter.is_constant(right_node):
            return 0
        
        # Case-4: right_node is a dict
        # 
        if QueryRewriter.is_dict(right_node):
            return 0
                
        # Case-5: right_node is a list
        # 
        if QueryRewriter.is_list(right_node):
            # 1 transformation: <left> --[merge_variables]--> <<left>>
            return 1
            
        # Case-6: right_node is a dot expression
        #
        if QueryRewriter.is_dot_expression(right_node):
            return 0

        return 0
    
    # Count the number of transformations to transform 
    #   the given left pattern AST Json VarList to cover the given right pattern AST Json node
    #
    @staticmethod
    def cntTransformationsASTJsonVarList(left_node: str, right_node: Any) -> int:

        # VarList matches everything
        #
        return 0
    
    # Count the number of transformations to transform 
    #   the given left pattern AST Json Constant to cover the given right pattern AST Json node
    #
    @staticmethod
    def cntTransformationsASTJsonConstant(left_node: str or numbers.Number, right_node: Any) -> int:

        # Case-1: right_node is a Var
        # 
        if QueryRewriter.is_var(right_node):
            # 1 transformation: 'left' --[variablize_a_leaf]--> <left>
            return 1
        
        # Case-2: right_node is a VarList
        # 
        if QueryRewriter.is_varList(right_node):
            # 2 transformations: 'left' --[variablize_a_leaf]--> <left> --[merge_variables]--> <<left>>
            return 2
        
        # Case-3: right_node is a constant
        if QueryRewriter.is_constant(right_node):
            if QueryRewriter.is_string(left_node) and \
                QueryRewriter.is_string(right_node) and \
                    str(left_node).lower() == str(right_node).lower():
                return 0
            elif QueryRewriter.is_number(left_node) and \
                QueryRewriter.is_number(right_node) and \
                    left_node == right_node:
                return 0
            else:
                # 1 transformation: 'left' --[variablize_a_leaf]--> <left>
                return 1

        # Case-4: right_node is a dict
        # 
        if QueryRewriter.is_dict(right_node):
            # 1 transformation: 'left' --[variablize_a_leaf]--> <left>
            return 1
                
        # Case-5: right_node is a list
        # 
        if QueryRewriter.is_list(right_node):
            # 2 transformations: 'left' --[variablize_a_leaf]--> <left> --[merge_variables]--> <<left>>
            return 2
            
        # Case-6: right_node is a dot expression
        #
        if QueryRewriter.is_dot_expression(right_node):
            # 1 transformation: 'left' --[variablize_a_leaf]--> <left>
            return 1

        return 0
    
    # Recursively count the number of transformations to transform 
    #   the given left pattern AST Json Dict to cover the given right pattern AST Json node
    #
    @staticmethod
    def cntTransformationsASTJsonDict(left_node: dict, right_node: Any) -> int:

        # Case-1: right_node is a Var
        # 
        if QueryRewriter.is_var(right_node):
            # 1 ([variablize_a_leaf]) + height_of_left ([variablize_subtrees])
            return 1 + RuleGenerator.heightOf(left_node)
        
        # Case-2: right_node is a VarList
        # 
        if QueryRewriter.is_varList(right_node):
            # 1 ([variablize_a_leaf]) + height_of_left ([variablize_subtrees]) + 1 ([merge_variables])
            return 1 + RuleGenerator.heightOf(left_node) + 1
        
        # Case-3: right_node is a constant
        if QueryRewriter.is_constant(right_node):
            # 1 ([variablize_a_leaf]) + height_of_left ([variablize_subtrees])
            return 1 + RuleGenerator.heightOf(left_node)
        
        # Case-4: right_node is a dict
        # 
        if QueryRewriter.is_dict(right_node):
            # if keys can match
            if set(left_node.keys()) == set(right_node.keys()):
                ans = 0
                # recursively count each value matching node
                for key in left_node.keys():
                    ans += RuleGenerator.cntTransformationsASTJsonNode(left_node[key], right_node[key])
                return ans
            # otherwise
            else:
                # 1 ([variablize_a_leaf]) + height_of_left ([variablize_subtrees])
                return 1 + RuleGenerator.heightOf(left_node)
                
        # Case-5: right_node is a list
        # 
        if QueryRewriter.is_list(right_node):
            # 1 ([variablize_a_leaf]) + height_of_left ([variablize_subtrees]) + 1 ([merge_variables])
            return 1 + RuleGenerator.heightOf(left_node) + 1
            
        # Case-6: right_node is a dot expression
        #
        if QueryRewriter.is_dot_expression(right_node):
            # 1 ([variablize_a_leaf]) + height_of_left ([variablize_subtrees])
            return 1 + RuleGenerator.heightOf(left_node)

        return 0
    
    # Recursively count the number of transformations to transform 
    #   the given left pattern AST Json List to cover the given right pattern AST Json node
    #
    @staticmethod
    def cntTransformationsASTJsonList(left_node: list, right_node: Any) -> int:

        # First count the basic transformations from List to a VarList
        #  
        ans = 0
        for child in left_node:
            # each child of left_node should be variablized
            #
            ans += RuleGenerator.cntTransformationsASTJsonNode(child, 'V001')
        # + 1 transformation: [merge_variables]
        ans += 1

        # Case-1: right_node is a Var
        # 
        if QueryRewriter.is_var(right_node):
            return ans
        
        # Case-2: right_node is a VarList
        # 
        if QueryRewriter.is_varList(right_node):
            return ans
        
        # Case-3: right_node is a constant
        if QueryRewriter.is_constant(right_node):
            return ans
        
        # Case-4: right_node is a dict
        # 
        if QueryRewriter.is_dict(right_node):
            return ans
                
        # Case-5: right_node is a list
        # 
        if QueryRewriter.is_list(right_node):
            if len(left_node) == len(right_node):
                # recursively count each child in left_node matching a child in right_node
                #   and choose the min
                min_ans = MAX_INT
                for left_child in left_node:
                    for right_child in right_node:
                        ans = RuleGenerator.cntTransformationsASTJsonNode(left_child, right_child)
                        if len(left_node) - 1 == 1:
                            ans += RuleGenerator.cntTransformationsASTJsonNode([cl for cl in left_node if cl != left_child][0], [cr for cr in right_node if cr != right_child][0])
                        else:
                            ans += RuleGenerator.cntTransformationsASTJsonList([cl for cl in left_node if cl != left_child], [cr for cr in right_node if cr != right_child])
                        min_ans = min(min_ans, ans)
                return min_ans
            else:
                return ans

        # Case-6: right_node is a dot expression
        #
        if QueryRewriter.is_dot_expression(right_node):
            return ans

        return 0
    
    # Count the number of transformations to transform 
    #   the given left pattern AST Json dot expression to cover the given right pattern AST Json node
    #
    @staticmethod
    def cntTransformationsASTJsonDotExpression(left_node: Any, right_node: Any) -> int:

        # First count the basic transformations from dot expression to a Var
        #  
        # split the dot expression into two parts
        # 
        _table = '.'.join(left_node.split('.')[0:-1])
        _column = left_node.split('.')[-1]
        ans = 0
        if not QueryRewriter.is_var(_table):
            # 1 transformation: [variablize_a_leaf]
            ans += 1
        if not QueryRewriter.is_var(_column): 
            # 1 transformation: [variablize_a_leaf]
            ans += 1
        # + 1 transformation: [variablize_subtree]
        ans += 1

        # Case-1: right_node is a Var
        # 
        if QueryRewriter.is_var(right_node):
            return ans
        
        # Case-2: right_node is a VarList
        # 
        if QueryRewriter.is_varList(right_node):
            # + 1 transformation: [merge_variables]
            return ans + 1
        
        # Case-3: right_node is a constant
        if QueryRewriter.is_constant(right_node):
            return ans
        
        # Case-4: right_node is a dict
        # 
        if QueryRewriter.is_dict(right_node):
            return ans
                
        # Case-5: right_node is a list
        # 
        if QueryRewriter.is_list(right_node):
            # + 1 transformation: [merge_variables]
            return ans + 1
            
        # Case-6: right_node is a dot expression
        #
        if QueryRewriter.is_dot_expression(right_node):
            _table2 = '.'.join(right_node.split('.')[0:-1])
            _column2 = right_node.split('.')[-1]
            ans = 0
            if not QueryRewriter.is_var(_table) and _table != _table2:
                # 1 transformation: [variablize_a_leaf]
                ans += 1
            if not QueryRewriter.is_var(_column) and _column != _column2:
                 # 1 transformation: [variablize_a_leaf]
                ans += 1
            return ans

        return 0
    
    # Recursively compute the height of the given left pattern AST Json node
    #
    @staticmethod
    def heightOf(node: Any) -> int:
        ans = 0
        if QueryRewriter.is_var(node):
            ans = max(ans, 1)
        elif QueryRewriter.is_varList(node):
            ans = max(ans, 1)
        elif QueryRewriter.is_constant(node):
            ans = max(ans, 1)
        elif QueryRewriter.is_dict(node):
            for child in node.values():
                ans = max(ans, RuleGenerator.heightOf(child))
            ans += 1
        elif QueryRewriter.is_list(node):
            for child in node:
                ans = max(ans, RuleGenerator.heightOf(child))
            ans += 1
        elif QueryRewriter.is_dot_expression(node):
            ans = max(ans, 1)
        return ans
