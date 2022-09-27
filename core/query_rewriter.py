import json
import numbers
from mo_sql_parsing import parse
from mo_sql_parsing import format
from typing import Any

from core.data_manager import DataManager
from core.rule_parser import VarType, VarTypesInfo


VarStart = VarTypesInfo[VarType.Var]['internalBase']
VarListStart = VarTypesInfo[VarType.VarList]['internalBase']


class QueryRewriter:

    @staticmethod
    def rewrite(query: str, dm: DataManager, database: str) -> str:
        
        # fetch enabled rules order by id ascending
        enabled_rules = QueryRewriter.fetch_enabled_rules(dm, database)
        
        query_ast = parse(query)

        new_query = True
        while new_query is True:
            for rule in enabled_rules:
                if QueryRewriter.match(query_ast, rule):
                    query_ast = QueryRewriter.replace(query_ast, rule)
                    new_query = True
                    break
            new_query = False

        return format(query_ast)
    
    @staticmethod
    def fetch_enabled_rules(dm: DataManager, database: str) -> list:
        enabled_rules = dm.enabled_rules(database)
        res = []
        for enabled_rule in enabled_rules:
            res.append({
                'id': enabled_rule[0],
                'key': enabled_rule[1],
                'name': enabled_rule[2],
                'pattern': json.loads(enabled_rule[3]),
                'constraints': enabled_rule[4],
                'rewrite': json.loads(enabled_rule[5]),
                'actions': enabled_rule[6]
            })
        return res
    
    # Traverse query AST tree, and check if rule->pattern matches any node of in query
    # 
    @staticmethod
    def match(query: Any, rule: dict) -> bool:
        
        # Breadth-First-Search on query
        # 
        queue = [query]
        while len(queue) > 0:
            curr_node = queue.pop(0)
            if QueryRewriter.match_node(curr_node, rule['pattern'], rule):
                return True
            if type(curr_node) is dict:
                for child in curr_node.values():
                    queue.append(child)
            elif type(curr_node) is list:
                for child in curr_node:
                    queue.append(child)
        return False
    
    # Recursively check if the query_node matches the rule_node for the given rule
    # 
    @staticmethod
    def match_node(query_node: Any, rule_node: Any, rule: dict) -> bool:
        
        # Case-1: rule_node is a Var, it can match a constant or a dict
        # 
        if QueryRewriter.is_var(rule_node):
            if QueryRewriter.is_constant(query_node) or QueryRewriter.is_dict(query_node):
                return True
        
        # Case-2: rule_node is a VarList, it can match a list
        # 
        if QueryRewriter.is_varList(rule_node):
            if QueryRewriter.is_list(query_node):
                return True
        
        # Case-3: rule_node is a constant, it can match a constant
        if QueryRewriter.is_constant(rule_node):
            if QueryRewriter.is_constant(query_node):
                return QueryRewriter.match_constant(query_node, rule_node, rule)
        
        # Case-4: rule_node is a dict, it can match a dict
        # 
        if QueryRewriter.is_dict(rule_node):
            if QueryRewriter.is_dict(query_node):
                return QueryRewriter.match_dict(query_node, rule_node, rule)
                
        # Case-5: rule_node is a list, it can match a list
        # 
        if QueryRewriter.is_list(rule_node):
            if QueryRewriter.is_list(query_node):
                return QueryRewriter.match_list(query_node, rule_node, rule)
        
        # spectial case for value of 'select':
        #   query_node = [{"value": "e1.name"}, {"value": "e1.age"}, {"value": "e2.salary"}]
        #   rule_node = {"value": "VL1"}
        return False

    # Check if two strings of query_node and rule_node match each other
    # 
    @staticmethod
    def match_string(query_node: Any, rule_node: Any) -> bool:
        return type(query_node) is str and type(rule_node) is str and query_node.lower() == rule_node.lower()
    
    # Check if two numbers of query_node and rule_node match each other
    # 
    @staticmethod
    def match_number(query_node: Any, rule_node: Any) -> bool:
        return type(query_node) is numbers and type(rule_node) is numbers and query_node == rule_node

    # Check if the two constants of query_node and rule_node match each other
    # 
    @staticmethod
    def match_constant(query_node: Any, rule_node: Any, rule: dict) -> bool:
        return QueryRewriter.match_string(query_node, rule_node) \
            or QueryRewriter.match_number(query_node, rule_node)

    # Check if the two dicts of query_node and rule_node match each other
    # TODO - We assume that keys in rule_node can NOT be Var or VarList
    #   - Each value in rule_node should match the value in query_node of the same key
    # 
    @staticmethod
    def match_dict(query_node: dict, rule_node: dict, rule: dict) -> bool:
        for key in rule_node.keys():
            if key in query_node.keys():
                if not QueryRewriter.match_node(query_node[key], rule_node[key], rule):
                    return False
            else:
                return False
        return True
    
    # Check if the two lists of query_node and rule_node match each other
    # TODO - We assume that a list in query_node can ONLY contain constants and dicts
    #   - Part-1) Constants in rule_node should match constants in query_node
    #   - Part-2) The remaining constants and dicts in query_node should be matched by 
    #               dicts, Vars and VarList in rule_node
    # 
    @staticmethod
    def match_list(query_node: list, rule_node: list, rule: dict) -> bool:
        # coner case
        # 
        if query_node is None and rule_node is None:
            return True
        if len(query_node) == 0 and len(rule_node) == 0:
            return True

        # - Part-1) Constants in rule_node should match constants in query_node
        # 
        # 1.1) Find constants and remaining in rule_node
        # 
        constants_in_rule = [] 
        remaining_in_rule = []
        for element in rule_node:
            if QueryRewriter.is_constant(element):
                constants_in_rule.append(element)
            else:
                remaining_in_rule.append(element)
        
        # 1.2) Match constants in rule_node to query_node
        #        and find remaining in query_node
        remaining_in_query = query_node.copy()
        for constant in constants_in_rule:
            if constant not in query_node:
                return False
            else:
                remaining_in_query.remove(constant)
        
        # - Part-2) The remaining dicts, Vars and VarList in rule_node should
        #             match the remaining constants and dicts in query_node 
        # 
        # Exaust the combinations of different ways to match them
        #   For each element in remaining of rule_node:
        for rule_element in remaining_in_rule:
            for query_element in remaining_in_query:
                if QueryRewriter.match_node(query_element, rule_element, rule):
                    query_list = remaining_in_query.copy()
                    query_list.remove(query_element)
                    rule_list = remaining_in_rule.copy()
                    rule_list.remove(rule_element)
                    if QueryRewriter.match_list(query_list, rule_list, rule):
                        return True
        return False

    # Check if a given node in AST is a Var
    # 
    @staticmethod
    def is_var(node: Any) -> bool:
        if type(node) is str and node.startswith(VarStart) and not node.startswith(VarListStart):
            return True
        else:
            return False
    
    # Check if a given node in AST is a VarList
    # 
    @staticmethod
    def is_varList(node: Any) -> bool:
        if isinstance(node, str) and node.startswith(VarListStart):
            return True
        else:
            return False
    
    # Check if a given node in AST is a constant
    # 
    @staticmethod
    def is_constant(node: Any) -> bool:
        if type(node) in [str, numbers.Number] and \
            not QueryRewriter.is_var(node) and \
            not QueryRewriter.is_varList(node):
            return True
        else:
            return False
    
    # Check if a given node in AST is a dict
    # 
    @staticmethod
    def is_dict(node: Any) -> bool:
        return type(node) is dict
    
    # Check if a given node in AST is a list
    # 
    @staticmethod
    def is_list(node: Any) -> bool:
        return type(node) is list

    # Replace the subtree of query AST matched by rule to rule's rewrite
    # 
    @staticmethod
    def replace(query: Any, rule: dict) -> Any:
        # TODO - TBI
        return query
