from typing import Any
import copy
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
    

    # Generate the candidate rule graph for a given seed rule
    #   e.g., a seed rule = {'pattern': "STRPOS(LOWER(text), 'iphone') > 0", 
    #                        'rewrite': "ILIKE(text, '%iphone%')"}
    #
    @staticmethod
    def generate_candidate_rule_graph(seedRule: dict) -> dict:
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

        res = []

        # 1. Get candidate columns from rule
        #
        columns = RuleGenerator.columns(rule['pattern_json'], rule['rewrite_json'])

        # 2. Traverse candidate columns, make one of them variable, and generate a new rule
        #
        for column in columns:
            res.append(RuleGenerator.variablize_column(rule, column))

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
    
    # recursively get set of columns in a rule pattern's AST Json
    #
    @staticmethod
    def columnsOfASTJson(patternASTJson: Any, path: list) -> set:
        res = set()

        # Case-1: dict
        #
        if QueryRewriter.is_dict(patternASTJson):
            for key, value in patternASTJson.items():
                # skip value of 'literal' as key
                if type(key) is str and key.lower() == 'literal':
                    continue
                # note: key can not be column, only traverse each value
                res.update(RuleGenerator.columnsOfASTJson(value, path + [key]))

        # Case-2: list
        # 
        if QueryRewriter.is_list(patternASTJson):
            for child in patternASTJson:
                res.update(RuleGenerator.columnsOfASTJson(child, path))

        # Case-3: string
        if QueryRewriter.is_string(patternASTJson):
            # skip case: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #            path = ['from', 'value'], patternASTJson = 'employee'
            #            path = ['from', 'name'], patternASTJson = 'e1'
            #
            if not (len(path) >=2 and path[-2] == 'from' and path[-1] == 'value') and \
               not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name'):
                res.add(patternASTJson)
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(patternASTJson):
            # skip case: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #            path = ['from', 'value'], patternASTJson = 'employee'
            #            path = ['from', 'name'], patternASTJson = 'e1'
            #
            if not (len(path) >=2 and path[-2] == 'from' and path[-1] == 'value') and \
               not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name'):
                candidate = patternASTJson.split('.')[-1]
                # skip case: e1.<a1>
                #
                if not QueryRewriter.is_var(candidate) and not QueryRewriter.is_varList(candidate):
                    res.add(candidate)
        
        return res
    
    
    # variablize the given column in given rule and generate a new rule
    #
    @staticmethod
    def variablize_column(rule: dict, column: str) -> dict:

        # create a new rule based on rule
        new_rule = copy.deepcopy(rule)

        # Find a variable name for the given column
        #   Traverse all var/varList mappings in rule
        #     Count the max number of var
        #
        new_rule_mapping = json.loads(new_rule['mapping'])
        maxVarNum = 0
        for varInternal in new_rule_mapping.values():
            if VarTypesInfo[VarType.VarList]['internalBase'] not in varInternal and VarTypesInfo[VarType.Var]['internalBase'] in varInternal:
                num = int(varInternal.split(VarTypesInfo[VarType.Var]['internalBase'], 1)[1])
                if num > maxVarNum:
                    maxVarNum = num
        newVarNum = maxVarNum + 1
        newVarInternal = VarTypesInfo[VarType.Var]['internalBase'] + str(newVarNum)
        newVarExternal = VarTypesInfo[VarType.Var]['externalBase'] + str(newVarNum)
        # add new map into mapping
        new_rule_mapping[newVarExternal] = newVarInternal
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
            # skip case: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #            path = ['from', 'value'], patternASTJson = 'employee'
            #            path = ['from', 'name'], patternASTJson = 'e1'
            #
            if not (len(path) >=2 and path[-2] == 'from' and path[-1] == 'value') and \
               not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name'):
                if astJson == column:
                    return var
        
        # Case-4: dot expression
        if QueryRewriter.is_dot_expression(astJson):
            # skip case: {'from': [{'value': 'employee', 'name': 'e1'}]}
            #            path = ['from', 'value'], patternASTJson = 'employee'
            #            path = ['from', 'name'], patternASTJson = 'e1'
            #
            if not (len(path) >=2 and path[-2] == 'from' and path[-1] == 'value') and \
               not (len(path) >= 2 and path[-2] == 'from' and path[-1] == 'name'):
                candidate = astJson.split('.')[-1]
                # skip case: e1.<a1>
                #
                if not QueryRewriter.is_var(candidate) and not QueryRewriter.is_varList(candidate):
                    if candidate == column:
                        return '.'.join(astJson.split('.')[0:-1] + [var])
        
        return astJson

    RuleTransformations = {
        'variablize_columns' : variablize_columns
    }
