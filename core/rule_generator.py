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

        # 4. Extract subtree from AST json based on scope
        patternASTJson = RuleParser.extractASTSubtree(q0ASTJson, q0Scope)
        rewriteASTJson = RuleParser.extractASTSubtree(q1ASTJson, q1Scope)

        return {'pattern': RuleGenerator.deparse(patternASTJson), 'rewrite': RuleGenerator.deparse(rewriteASTJson)}

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
    
    @staticmethod
    def fingerPrint(rule: dict) -> str:
        # use rule['pattern'] string as finger-print
        #   and get rid of the numbers inside each var/varList
        #   e.g., we want to treat these two generated rules as the same rule:
        #         rule 1: SELECT e1.<x1>, e1.<x2> FROM employee e1 WHERE e1.<x1> > 17 AND e1.<x2> > 35000
        #         rule 2: SELECT e1.<x2>, e1.<x1> FROM employee e1 WHERE e1.<x2> > 17 AND e1.<x1> > 35000
        return RuleGenerator._fingerPrint(rule['pattern'])
    
    @staticmethod
    def _fingerPrint(fingerPrint: str) -> str:
        #   get rid of the numbers inside each var/varList
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
    def findNextVarInternal(mapping: dict) -> tuple[dict, str]:
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
    def findNextVarListInternal(mapping: dict) -> tuple[dict, str]:
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

        # TODO - patternTables should be superset of rewriteTables
        #
        # deduplicate the list
        #
        fingerprints = set()
        ans = []
        for table in patternTables:
            if type(table['value']) is str and type(table['name']) is str:
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
        
        return res
    
    # variablize the given table in given rule and generate a new rule
    #
    @staticmethod
    def variablize_table(rule: dict, table: dict) -> dict:

        # create a new rule based on rule
        new_rule = copy.deepcopy(rule)

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
                # case-2: {'inner join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['inner join']
                #
                elif len(path) >= 1 and path[-1] == 'inner join':
                    if astJson['value'] == table['value'] and astJson['name'] == table['name']:
                        return var
                # case-3: {'left outer join': {'value': 'employee', 'name': 'e1'}}
                #         path = ['left outer join']
                #
                elif len(path) >= 1 and path[-1] == 'left outer join':
                    if astJson['value'] == table['value'] and astJson['name'] == table['name']:
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
            # case-4: table's alias occurs in select or where clause
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
            # key can not be keywords of [SELECT, FROM, WHERE, LIMIT, ORDERBY, SORT, INNER JOIN, LEFT OUTER JOIN]
            if key in ['select', 'from', 'where', 'limit', 'orderby', 'sort', 'inner join', 'left outer join']:
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
        new_rule = copy.deepcopy(rule)

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
            # special case for single Var under SELECT
            #
            if len(path) >= 1 and path[-1] in ['select']:
                res.append([astJson])
        
        return res
    
    # merge the given variable list in given rule and generate a new rule
    #
    @staticmethod
    def merge_variable_list(rule: dict, variableList: list) -> dict:

        # create a new rule based on rule
        new_rule = copy.deepcopy(rule)

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
                    return varList
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
                    # 
                    if varList not in res:
                        res.append(varList) 
                else:
                    res.append(RuleGenerator.replaceVariableListsOfASTJson(child, path, variableList, varList))

            return res

        # Case-3: var
        #
        if QueryRewriter.is_var(astJson):
            # special case for single Var under SELECT
            #
            if len(path) >= 1 and path[-1] in ['select']:
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

            # special case: there is only one key in the AST Json, and the value is a list
            #   e.g., {'and': [{'gt': [...]}, {'eq':[...]}]}
            #
            if len(astJson.keys()) == 1:
                key = list(astJson.keys())[0]
                children = astJson[key]
                if QueryRewriter.is_list(children):
                    # each element in the children list is a branch
                    #
                    for child in children:
                        if RuleGenerator.isBranch({key: [child]}):
                            res.append({'key': key, 'value': child})
            else:
                for key, value in astJson.items():
                    if RuleGenerator.isBranch({key: value}):
                        res.append({'key': key, 'value': value})
                
                # special cases: 
                #   (1) if {'select': ...} presents, remove {'from': ...} and {'where': ...} branches
                #   (2) if {'from': ...} presents, remove {'where': ...} branch
                #
                if 'select' in astJson.keys():
                    res = [branch for branch in res if branch['key'] != 'from' and branch['key'] != 'where']
                if 'from' in astJson.keys():
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
        if len(columns) > 0:
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
        new_rule = copy.deepcopy(rule)

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
                if len(astJson.keys()) == 1:
                    key = list(astJson.keys())[0]
                    if not QueryRewriter.is_list(astJson[key]):
                        astJson = astJson[key]

            # special case: there is only one key in the AST Json
            #   e.g., {'and': [{'gt': [...]}, {'eq':[...]}]}
            #   remove the branch value from the children list
            # 
            elif len(astJson.keys()) == 1:
                children = astJson[branch['key']]
                if QueryRewriter.is_list(children):
                    astJson[branch['key']] = [value for value in children if not RuleGenerator.sameBranch(value, branch['value'])]
                
                    # special case: after removing the branch, the chidlren list has only one element
                    #   e.g., {'and': [{'gt': [{'strpos': [{'lower': 'V1'}, {'literal': 'V2'}]}, 0] }] }
                    #   we should remove the root as well
                    #
                    if len(astJson[branch['key']]) == 1:
                        astJson = astJson[branch['key']][0]

                # this case should not happen
                #   astJson has only one key and the value of the key is not a list
                #
                else:
                    raise 'Exception: astJson has only one key and its value is not a list'
        
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
        new_rule = copy.deepcopy(rule)
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
        new_rule = copy.deepcopy(rule)
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
        new_rule = copy.deepcopy(rule)
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
        new_rule = copy.deepcopy(rule)
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
        new_rule = copy.deepcopy(rule)
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
    
    RuleGeneralizations = {
        'generalize_tables': generalize_tables,
        'generalize_columns' : generalize_columns,
        'generalize_literals' : generalize_literals,
        'generalize_subtrees': generalize_subtrees,
        'generalize_variables': generalize_variables
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

        # Parse seedRule's pattern and rewrite into SQL AST json
        #
        seedRule['pattern_json'], seedRule['rewrite_json'], seedRule['mapping'] = RuleParser.parse(seedRule['pattern'], seedRule['rewrite'])
        
        # Initially, seedRule has no constraints and actions
        #
        seedRule['constraints'], seedRule['constraints_json'], seedRule['actions'], seedRule['actions_json'] = '', '[]', '', '[]'

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

