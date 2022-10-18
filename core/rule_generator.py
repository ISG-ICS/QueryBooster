from typing import Any
from core.query_rewriter import QueryRewriter
from core.rule_parser import RuleParser, Scope
import mo_sql_parsing as mosql
import numbers


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

        # Extend subtree to full AST Json
        # 
        patternASTJson, patternScope = RuleGenerator.extendToFullASTJson(patternASTJson)
        rewriteASTJson, rewriteScope = RuleGenerator.extendToFullASTJson(rewriteASTJson)

        # Format full AST Json into SQL statement
        # 
        pattern = mosql.format(patternASTJson)
        rewrite = mosql.format(rewriteASTJson)

        # Extract partial SQL statement based on scope
        #
        pattern = RuleGenerator.extractPartialSQL(pattern, patternScope)
        rewrite = RuleGenerator.extractPartialSQL(rewrite, rewriteScope)

        return {'pattern': pattern, 'rewrite': rewrite}
    
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
        return node
    
    @staticmethod
    def extractPartialSQL(partialSQL: str, scope: Scope) -> str:
        return partialSQL
 