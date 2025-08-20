from mo_sql_parsing import parse
from mo_sql_parsing import format
import copy
import numbers
import sqlparse
from typing import Any, Tuple
from enum import Enum

from core.rule_parser import VarType, VarTypesInfo


class MatchingMode(Enum):
    FULL_ONLY = "full_only"           # Only allow full matches (default)
    ALLOW_PARTIAL = "allow_partial"   # Allow partial matching at top level
    IN_PARTIAL = "in_partial"         # Already in partial context, no more partial matching


VarStart = VarTypesInfo[VarType.Var]['internalBase']
VarListStart = VarTypesInfo[VarType.VarList]['internalBase']

# TODO - Help users to handle special cases' by-default behaviors:
#        (1) A rule's pattern is always a partial-matching behavior:
#            Example1, pattern p1:  where <tb1>.<a1> = <tb2>.<a2>  
#                        should by-default means
#                      pattern p1': where <tb1>.<a1> = <tb2>.<a2> and <<p1>>
#               Reason:
#                 p1 should match query: ... where employee.dept_id = department.id
#                 p1 should also match query: ... where employee.dept_id = department.id and employee.age > 17
#            Example2, pattern p2:  select <a1>
#                        should by-default means
#                      pattern p2': select <a1>, <<s1>>
#               Reason:
#                  p2 should match query: select id from ...
#                  p2 should also match query: select id, age from ...
#            Essentially, it means, a variable declared in a rule's pattern is mainly for reference purpose 
#                                   when the rule needs to manipulate the variable in rewrite,
#                                   if not declared explicitly in a rule's pattern, everything else should be kept unchanged.
#            TODO - to implement the case (1), we need to add <<VarList>> variables to rules's select and where clause,
#                                              we also need add a constant predicate (1=1) to the where clause of a given query
#                                                to handle the coner case of only one predicate under where clause if not a 'and'-list. 
#
class QueryRewriter:

    # Reformat a query string to make sure it's consistent globally
    # 
    @staticmethod
    def reformat(query: str) -> str:
        return format(parse(query))

    # Beautify a query string
    # 
    @staticmethod
    def beautify(query: str) -> str:
        return sqlparse.format(query, reindent=True)

    # Rewrite query using the rules iteratively
    #   An example rule in rules list:
    #     rule = {
    #       'id': 1,
    #       'key': 'remove_cast',
    #       'name': 'Remove Cast',
    #       'pattern': json.loads('{"cast": ["V1", {"date": {}}]}'),
    #       'constraints': 'TYPE(x) = DATE',
    #       'rewrite': json.loads('"V1"'),
    #       'actions': ''
    #     }
    # 
    @staticmethod
    def rewrite(query: str, rules: list, iterate=True) -> Tuple[str, list]:
        
        query_ast = parse(query)

        rewriting_path = []

        # to break rewriting cycles
        #
        query_trace = set(query)
        cycle_found = False

        new_query = True
        while new_query is True:
            new_query = False
            # the current query has occurred before
            #
            if format(query_ast) in query_trace:
                cycle_found = True
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
                print("  [QueryRewriter] Cycle Found")
                print("rewriting_path:")
                print(rewriting_path)
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
            # otherwise, remember it
            else:
                query_trace.add(format(query_ast))
            
            # store the rule and memo applied
            rule_applied = None
            memo_applied = None
            
            # first pass: look for full matches (higher priority)
            for rule in rules:
                memo = {}
                if QueryRewriter.match(query_ast, rule, memo, MatchingMode.FULL_ONLY) and memo.get('rule') is query_ast:
                    rule_applied = rule
                    memo_applied = memo
                    break
            
            # second pass: if no full match found, look for partial matches (lower priority)
            if rule_applied is None:
                for rule in rules:
                    memo = {}
                    if QueryRewriter.match(query_ast, rule, memo, MatchingMode.ALLOW_PARTIAL):
                        rule_applied = rule
                        memo_applied = memo
                        break
            
            # apply the rule and found
            try:
                if rule_applied is not None:
                    query_ast = QueryRewriter.take_actions(query_ast, rule_applied, memo_applied)
                    query_ast = QueryRewriter.replace(query_ast, rule_applied, memo_applied)
                    rewriting_path.append([rule_applied['id'], format(query_ast)])
                    query_ast = parse(format(query_ast))
                    if not cycle_found and iterate:
                        new_query = True
            except:
                print(f"Failed to rewrite with rule: {rule}")
                continue

        return format(query_ast), rewriting_path
    
    # Traverse query AST tree, and check if rule->pattern matches any node of in query
    # 
    @staticmethod
    def match(query: Any, rule: dict, memo: dict, matching_mode: MatchingMode = MatchingMode.FULL_ONLY) -> bool:
        
        # Breadth-First-Search on query
        # 
        queue = [query]
        while len(queue) > 0:
            curr_node = queue.pop(0)
            if QueryRewriter.match_node(curr_node, rule['pattern_json'], rule, memo, matching_mode):
                # If we don't have early return on 'rule' along partial matching, we set the rule to current returned node
                if 'rule' not in memo.keys():
                    memo['rule'] = curr_node
                return True
            else:
                memo.clear()
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
    def match_node(query_node: Any, rule_node: Any, rule: dict, memo: dict, matching_mode: MatchingMode = MatchingMode.FULL_ONLY) -> bool:
        # TODO - Do the escalation in RuleParser
        # Special case for value of 'select' and 'from':
        #   e.g., query_node = [{"value": "e1.name"}, {"value": "e1.age"}, {"value": "e2.salary"}]
        #         rule_node = {"value": "VL1"}
        #   The idea is escalate the "VL1" from inside {"value": "VL1"} to outside
        # 
        if QueryRewriter.is_dict(rule_node) and 'value' in rule_node.keys():
            if QueryRewriter.is_varList(rule_node['value']):
                memo[rule_node['value']] = query_node
                return True
            # handle case when query_node = {'all_columns': {}} and rule_node = {"value": "V001"}
            # we want "V001" to match "all_columns"
            #
            if QueryRewriter.is_var(rule_node['value']) and QueryRewriter.is_dict(query_node) and 'all_columns' in query_node.keys(): 
                memo[rule_node['value']] = list(query_node.keys())[0]
                return True
        
        # Case-1: rule_node is a Var
        # 
        if QueryRewriter.is_var(rule_node):
            return QueryRewriter.match_var(query_node, rule_node, rule, memo, matching_mode)
        
        # Case-2: rule_node is a VarList, it can match anything
        # 
        if QueryRewriter.is_varList(rule_node):
            # TODO - resolve conflicts if one VarList matched more than once
            # 
            memo[rule_node] = query_node
            return True
        
        # Case-3: rule_node is a constant, it can match a constant
        if QueryRewriter.is_constant(rule_node):
            if QueryRewriter.is_constant(query_node):
                return QueryRewriter.match_constant(query_node, rule_node, rule, memo)
        
        # Case-4: rule_node is a dict, it can match a dict
        # 
        if QueryRewriter.is_dict(rule_node):
            if QueryRewriter.is_dict(query_node):
                if QueryRewriter.match_dict(query_node, rule_node, rule, memo, matching_mode):
                    return True
                
                # Partial Matching: Only allow if we're in ALLOW_PARTIAL mode
                # Handle any logical operator (and, or, etc.) that contains a list of clauses
                # Prevent semantic mismatches: if both query and rule are logical operators, they must match
                if (matching_mode == MatchingMode.ALLOW_PARTIAL and 
                    QueryRewriter.check_logical_operator_list(query_node)):
                    
                    # If rule pattern is also a logical operator, only allow if operators match
                    if (QueryRewriter.check_logical_operator_list(rule['pattern_json']) and
                        next(iter(query_node)) != next(iter(rule['pattern_json']))):
                        pass
                    else:
                        return QueryRewriter.partial_logical_match(query_node, rule_node, rule, memo)

                return False
                
        # Case-5: rule_node is a list, it can match a list
        # 
        if QueryRewriter.is_list(rule_node):
            if QueryRewriter.is_list(query_node):
                return QueryRewriter.match_list(query_node, rule_node, rule, memo, matching_mode)
            
        # Case-6: rule_node is a dot expression, it can match a dot expression
        if QueryRewriter.is_dot_expression(rule_node):
            if QueryRewriter.is_dot_expression(query_node):
                return QueryRewriter.match_dot_expression(query_node, rule_node, rule, memo, matching_mode)

        return False
    
    # Check if a dict node contains a logical operator with a list of clauses
    # 
    @staticmethod
    def check_logical_operator_list(query_node: dict) -> bool:
        if not query_node:
            return False
        
        # Check if there's exactly one key and its value is a list
        if len(query_node) == 1:
            key = next(iter(query_node))
            value = query_node[key]
            # Common logical operators in SQL ASTs
            logical_operators = ['and', 'or', 'not', 'union', 'intersect', 'except']
            return key in logical_operators and QueryRewriter.is_list(value)
        
        return False
    
    # Try partial matching for logical operations
    # 
    @staticmethod
    def partial_logical_match(query_node: dict, rule_node: Any, rule: dict, memo: dict) -> bool:
        # Extract the operator and its clauses
        op = next(iter(query_node))
        clauses = query_node[op]
        
        remain_clauses = []
        matched_any = False
        
        for clause in clauses:
            # Once we're doing partial matching, all recursive calls must be in IN_PARTIAL mode
            # This prevents nested partial matching within the anchored subtree
            if not QueryRewriter.match_node(clause, rule_node, rule, memo, MatchingMode.IN_PARTIAL):
                remain_clauses.append(clause)
            else:
                matched_any = True
                # Set memo['rule'] only if this rule_node is the top-level pattern
                if rule['pattern_json'] == rule_node:
                    memo['rule'] = clause
        
        # If we matched at least one clause, this is a successful partial match
        if matched_any:
            # Store the remaining non-matched clauses
            if len(remain_clauses) > 0:
                memo[op] = remain_clauses
            return True
        
        return False
    
    # Check if a Var rule_node matches the query_node
    # 
    @staticmethod
    def match_var(query_node: Any, rule_node: str, rule: dict, memo: dict, matching_mode: MatchingMode = MatchingMode.FULL_ONLY) -> bool:
        # Var has matched something before, compare the value of Var with the query_node
        #
        if rule_node in memo.keys():
            # value is the matched subtree represented by the Var
            value = memo[rule_node]
            if QueryRewriter.is_constant(value):
                if QueryRewriter.is_constant(query_node):
                    if value == query_node:
                        return True
                # Special case where a Var represents a table's alias
                #   e.g., V001 = 'e1'
                # and query_node is the table object (name and alias)
                #   e.g., {'value': 'employee', name: 'e1'}
                # Note: this case happens when a Var first matches table alias in the SELECT clause
                #       then it traverse the table object in FROM clause
                #
                elif QueryRewriter.is_dict(query_node):
                    if 'value' in query_node and 'name' in query_node:
                        if value == query_node['value'] or value == query_node['name']:
                            # replace the Var's value in memo to be the table object
                            memo[rule_node] = query_node
                            return True
                return False
            elif QueryRewriter.is_dot_expression(value):
                # TODO - Be more intelligent for the case 
                #        where table name and alias refer to the same column
                #        e.g, V1 = "e1.age", it should match "employee.age"
                #
                if QueryRewriter.is_dot_expression(query_node):
                    if value == query_node:
                        return True
                return False
            elif QueryRewriter.is_dict(value):
                # Special case when a dict Var can match a constant query_node
                #
                if QueryRewriter.is_constant(query_node):
                    # Special case where a Var represents a table along with its alias
                    #   e.g., V1 = {"value": "employee", "name": "e1"}
                    # and query_node is the table name or alias
                    #
                    if 'value' in value.keys() and 'name' in value.keys():
                        if value['value'] == query_node or value['name'] == query_node:
                            return True
                    return False
                elif QueryRewriter.is_dict(query_node):
                    return QueryRewriter.match_dict(query_node, value, rule, memo, matching_mode)
                else:
                    return False
            # TODO - This path should not happen
            else:
                return False
        else:
            # A Var can match a constant, a dot_expression, or a dict
            #
            if QueryRewriter.is_constant(query_node) or \
                QueryRewriter.is_dot_expression(query_node) or \
                QueryRewriter.is_dict(query_node):
                memo[rule_node] = query_node
                return True
            else:
                return False

    # Check if two strings of query_node and rule_node match each other
    # 
    @staticmethod
    def match_string(query_node: Any, rule_node: Any) -> bool:
        # TODO - handle the case where a rule has constant table names and aliases:
        #        try to store the mapping between a constant table name and its constant alias,
        #        then match a constant table name with a constant alias inter-changably.
        return type(query_node) is str and type(rule_node) is str and query_node.lower() == rule_node.lower()
    
    # Check if two numbers of query_node and rule_node match each other
    # 
    @staticmethod
    def match_number(query_node: Any, rule_node: Any) -> bool:
        return isinstance(query_node, numbers.Number) and isinstance(rule_node, numbers.Number) and query_node == rule_node

    # Check if the two constants of query_node and rule_node match each other
    # 
    @staticmethod
    def match_constant(query_node: Any, rule_node: Any, rule: dict, memo: dict) -> bool:
        return QueryRewriter.match_string(query_node, rule_node) \
            or QueryRewriter.match_number(query_node, rule_node)

    # Check if the two dot expressions of query_node and rule_node match each other
    # 
    @staticmethod
    def match_dot_expression(query_node: str, rule_node: str, rule: dict, memo: dict, matching_mode: MatchingMode = MatchingMode.FULL_ONLY) -> bool:
        query_nodes = query_node.split('.')
        rule_nodes = rule_node.split('.')
        # both have to be in the same format, i.e., "x.y"
        if len(query_nodes) != 2 or len(rule_nodes) != 2:
            return False
        # both positions have to match each other
        return QueryRewriter.match_node(query_nodes[0], rule_nodes[0], rule, memo, matching_mode) and \
            QueryRewriter.match_node(query_nodes[1], rule_nodes[1], rule, memo, matching_mode)

    # Check if the two dicts of query_node and rule_node match each other
    # TODO - We assume that keys in rule_node can NOT be Var or VarList
    #   - Each value in rule_node should match the value in query_node of the same key
    # 
    @staticmethod
    def match_dict(query_node: dict, rule_node: dict, rule: dict, memo: dict, matching_mode: MatchingMode = MatchingMode.FULL_ONLY) -> bool:
        for key, rule_val in rule_node.items():
            if key not in query_node:
                return False
            if not QueryRewriter.match_node(query_node[key], rule_val, rule, memo, matching_mode):
                return False
    

        # Complement the existence matching logic:
        #   In the matching process, as long as the key set in the rule_node is a subset of that in the query_node,
        #   the two nodes match.
        #     e.g., If the rule_node is "FROM <t> WHERE <x> = <y>" and the query_node is "SELECT * FROM emp WHERE id = 99",
        #           then the rule_node matches the query_node.
        #   However, to make the rewritten query correct, we need to add the additional branch "SELECT *" in query_node 
        #     to the rule_node, because the rewritten query is instantiated based on the rule_node's rewrite part.
        #   
        #   ** Basically, a rule_node dict can partially match a query_node dict, and the additional branches in query_node 
        #        needs to be carried out as they are to the rule_node
        #   
        #   Implementation: 
        #     Since the rewritten query is instantiated based on the 'rewrite_json' in the rule 
        #       but not the current rule_node (which is a decedent under the 'pattern_json" in the rule),
        #       we memorize the additional set of key-value pairs from the matched query_node inside the memo.
        #       Also, since the 'rewrite_json' and 'pattern_json' of a rule has no one-to-one mapping relation, 
        #       we use a fuzzy mapping way. We use the matched set of keys in rule_node as the key in the memo 
        #       and store the additional set of key-value pairs as the value.
        #         e.g., for the above example, we add one entry {'FROM,WHERE': {'SELECT': '*'}} into the memo
        #               to memorize that for the rule_node dict with 'FROM' and 'WHERE' keys inside, we should add the 
        #               additional set of key-value pairs {'SELECT':'*'} into the rule_node.
        #
        memo_key = ','.join(sorted(rule_node.keys()))
        memo_additional_key_value_pairs = {}
        for key in query_node.keys():
            if key not in rule_node.keys():
                memo_additional_key_value_pairs[key] = query_node[key]
        
        if memo_additional_key_value_pairs != {}:
            memo[memo_key] = memo_additional_key_value_pairs
        # Check child nodes for possible partial matches, and add in current logical operator's memo
        #   e.g., query_node = {"and": [{"key1": [...]}, {"key2": [...]}, {"key3": [...]}]}
        #         rule_node = {"and": [{"key1": [...]}, {"key2": [...]}]}
        #   After matching, we need to add the remaining {"key3": [...]} into the memo, so the memo becomes:
        #                memo = {"and": [{"key3": [...]}], ...}
        elif "partial_match_list" in memo.keys():
            memo[memo_key] = memo["partial_match_list"]
            del memo["partial_match_list"]

        return True
    
    # Check if the two lists of query_node and rule_node match each other
    # TODO - We assume that a list in query_node can ONLY contain constants and dicts
    #   - Part-1) Constants in rule_node should match constants in query_node
    #   - Part-2) The remaining constants and dicts in query_node should be matched by 
    #               dicts, Vars and VarList in rule_node
    # 
    @staticmethod
    def match_list(query_node: list, rule_node: list, rule: dict, memo: dict, matching_mode: MatchingMode = MatchingMode.FULL_ONLY) -> bool:
        # corner case
        # 
        if query_node is None and rule_node is None:
            return True
        if len(query_node) == 0 and len(rule_node) == 0:
            return True

        # corner case
        # 
        if len(rule_node) == 1 and QueryRewriter.is_varList(rule_node[0]):
            return QueryRewriter.match_node(query_node, rule_node[0], rule, memo, matching_mode)

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
        
        # If both remaining lists are empty, all constants matched and should return True
        if len(remaining_in_rule) == 0 and len(remaining_in_query) == 0:
            return True
        
        # - Part-2) The remaining dicts, Vars and VarList in rule_node should PARTIALLY
        #             match the remaining constants and dicts in query_node 
        # 
        # Exaust the combinations of different ways to match them
        #   For each element in remaining of rule_node:
        for rule_element in remaining_in_rule:
            for query_element in remaining_in_query:
                # Snapshot the memo's keys before try this combination
                memo_keys_snapshot = set(memo.keys())
                if QueryRewriter.match_node(query_element, rule_element, rule, memo, matching_mode):
                    query_list = remaining_in_query.copy()
                    query_list.remove(query_element)
                    rule_list = remaining_in_rule.copy()
                    rule_list.remove(rule_element)
                    if QueryRewriter.match_list(query_list, rule_list, rule, memo, matching_mode):
                        return True
                    else:
                        # Partial Matching for lists - only allow if in ALLOW_PARTIAL mode
                        # Mark remaining elements in query_list, 'partial_match_list' will be catched, added, and removed by the nearest parent
                        if matching_mode == MatchingMode.ALLOW_PARTIAL and rule_list == []:
                            memo['partial_match_list'] = query_list
                            return True
                        # The remaining rule_list doesn't match the remaining query_list
                        #   revert the memo keys that were incorrectly modified in match_node(query_element, rule_element, ...)
                        #
                        for key in set(memo.keys()) - set(memo_keys_snapshot):
                            del memo[key]

        return False

    # Check if a given node in AST is a Var
    # 
    @staticmethod
    def is_var(node: Any) -> bool:
        if type(node) is str and not QueryRewriter.is_dot_expression(node) and node.startswith(VarStart) and not node.startswith(VarListStart):
            return True
        else:
            return False
    
    # Check if a given node in AST is a VarList
    # 
    @staticmethod
    def is_varList(node: Any) -> bool:
        if type(node) is str and not QueryRewriter.is_dot_expression(node) and node.startswith(VarListStart):
            return True
        else:
            return False
    
    # Check if a given node in AST is a constant
    # 
    @staticmethod
    def is_constant(node: Any) -> bool:
        if QueryRewriter.is_string(node):
            return True
        if QueryRewriter.is_number(node):
            return True
        return False
    
    # Check if a given node in AST is a string
    # 
    @staticmethod
    def is_string(node: Any) -> bool:
        if type(node) is str:
            if not QueryRewriter.is_dot_expression(node) and not QueryRewriter.is_var(node) and not QueryRewriter.is_varList(node):
                return True
        return False
    
    # Check if a given node in AST is a number
    # 
    @staticmethod
    def is_number(node: Any) -> bool:
        if isinstance(node, numbers.Number):
            return True
        return False
    
    # Check if a given node in AST is a dot expression (e.g., 't1.a1')
    @staticmethod
    def is_dot_expression(node: Any) -> bool:
        if type(node) is str:
            if '.' in node:
                return True
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
    
    # Take actions on the query AST defined in the rule's actions
    # 
    @staticmethod
    def take_actions(query: Any, rule: dict, memo: dict) -> Any:
        
        for action in rule['actions_json']:
            func = action['function']
            # TODO - fetch functions by names dynamically in run time
            # 
            if func == 'substitute':
                variables = action['variables']
                if len(variables) == 3:
                    scope = variables[0]
                    source = memo[variables[1]]
                    target = memo[variables[2]]
                    # traverse the subtree of scope and substitute
                    memo[scope] = QueryRewriter.substitute(memo[scope], source, target)

        return query

    # Action: Substitute
    # 
    @staticmethod
    def substitute(sub_ast: Any, source: Any, target: Any) -> Any:
        # sub_ast is a string
        if type(sub_ast) == str:
            if '.' in sub_ast:
                return '.'.join([QueryRewriter.substitute(x, source, target) for x in sub_ast.split('.')])
            else:
                if sub_ast == source:
                    return target
                # handle case where source or target is a table (with name and alias),
                #   e.g., source = {'value': 'employee', 'name': 'e2'}
                #         target = {'value': 'employee', 'name': 'e1'}
                #
                if type(source) == dict:
                    if 'name' in source.keys() and sub_ast == source['name']:
                        if type(target) == str:
                            return target
                        elif type(target) == dict:
                            if 'name' in target.keys():
                                return target['name']
        
        # sub_ast is a number
        if isinstance(sub_ast, numbers.Number):
            if str(sub_ast) == source:
                return target
        
        # sub_ast is a dict
        if type(sub_ast) == dict:
            for key in sub_ast.keys():
                sub_ast[key] = QueryRewriter.substitute(sub_ast[key], source, target)
            return sub_ast
                
        # sub_ast is a list
        if type(sub_ast) == list:
            return [QueryRewriter.substitute(x, source, target) for x in sub_ast]
        
        return sub_ast

    # Replace the subtree of query AST matched by rule to rule's rewrite
    # 
    @staticmethod
    def replace(query: Any, rule: dict, memo: dict) -> Any:
        # Initialize set to track which memo keys have been processed for merging
        if '_merged_keys' not in memo:
            memo['_merged_keys'] = set()
            
        # Special case for value of 'select' and 'from':
        #   e.g., query = {"value": "VL1"}
        #         memo["VL1"] = [{"value": "e1.name"}, {"value": "e1.age"}, {"value": "e1.salary"}]
        #   The idea is escalate the "VL1" from inside {"value": "VL1"} to outside
        # 
        if QueryRewriter.is_dict(query) and 'value' in query.keys() and QueryRewriter.is_varList(query['value']):
            return memo[query['value']]

        # Special case for VarList in "and" list:
        #   e.g., query = [{...}, "VL2"]
        #         memo["VL2"] = [{"gt": [...]}, {"gt": [...]}]
        #   The idea is escalate the "VL2" from a list inside the list to merged into the outside list
        # 
        if QueryRewriter.is_list(query):
            for var in query:
                if QueryRewriter.is_varList(var):
                    if QueryRewriter.is_list(memo[var]):
                        query.remove(var)
                        query.extend(memo[var])

        # Special case, rewrite's Var in a string
        #   e.g., {"literal": "%V2%"}
        #                       ^
        #                       query
        # 
        if QueryRewriter.is_string(query):
            return QueryRewriter.replace_var_in_str(query, memo)
        
        # 1st case, find the matched part by the rule
        # 
        if query is memo['rule']:
            # replace query by rule's rewrite
            # 

            # Partial Matching Case: where memo['rule'] only contains the partial matched node
            # after rewrite, we need to manually put it back to the original operator clause
            if QueryRewriter.is_dict(query):
                if len(query) == 1 and (op := next(iter(query))) in memo.keys():
                    memo["full_rule"] = [op, memo[op]]

            original_query = query
            query = copy.deepcopy(rule['rewrite_json'])

            # For partial matching we must add back remaining clauses before the operator 
            # is overwritten by rewrite 
            # 
            # TODO - Consider using a special flag in memo to differentiate 
            # partial matching keys from variable names 
            all_keys = QueryRewriter.get_all_keys(original_query)
            ops_to_remove = set()

            if QueryRewriter.is_dict(query):
                for op in memo.keys():                    
                    if op not in all_keys:
                        continue
                            
                    if op in query:
                        # Match operator to clause in query (SELECT, FROM, etc)
                        # Ex. adding back remaining {value: EMPNO} in SELECT clause
                        current_value = query[op]
                        if QueryRewriter.is_list(current_value):
                            query[op] = current_value + memo[op]
                        else:
                            query[op] = [current_value] + memo[op]
                    elif 'where' in query and op:
                        # Add back remaining operators in WHERE
                        # Ex. adding back remaining AND clause to WHERE clause
                        rewritten_where = query['where']
                        query['where'] = {op: [rewritten_where] + memo[op]}
                    
                    # Remove remaining clauses from memo
                    ops_to_remove.add(op)
                
                for op in ops_to_remove:
                    del memo[op]
        
              
        # 2nd case, find rewrite's Var or VarList
        # 
        if QueryRewriter.is_var(query) or QueryRewriter.is_varList(query):
            # replace query by Var or VarList's value
            return memo[query]

        # Depth-First-Search on query
        # 
        if QueryRewriter.is_dict(query):       
            memo_key = ','.join(sorted(query.keys()))
            matching_memo_key = None

            # Only do merging if this memo_key hasn't been processed yet
            # Try exact match
            if memo_key in memo.keys() and memo_key not in memo['_merged_keys']:
                matching_memo_key = memo_key
            # If no exact match, look for a memo key that contains our query key as subset
            else:
                current_keys_set = set(query.keys())
                for key in memo.keys():
                    if (',' in key and key not in memo['_merged_keys']):
                        memo_keys_set = set(key.split(','))
                        if current_keys_set.issubset(memo_keys_set):
                            matching_memo_key = key
                            break
            
            # Use the matching key (exact or subset)
            if matching_memo_key:
                memo_additional_pairs = memo[matching_memo_key]
                if QueryRewriter.is_dict(memo_additional_pairs):
                    for key, value in memo_additional_pairs.items():
                        query[key] = value
                elif QueryRewriter.is_list(memo_additional_pairs):
                    # Make sure the merged pairs are unique
                    merged_pairs = []
                    for clause in query[matching_memo_key] + memo_additional_pairs:
                        if not any(QueryRewriter.deep_equal(clause, existing) for existing in merged_pairs):
                            merged_pairs.append(clause)        
                    query[matching_memo_key] = merged_pairs 
                
                # Mark this memo_key as processed to prevent re-merging
                memo['_merged_keys'].add(matching_memo_key)

            for key, child in query.items():
                query[key] = QueryRewriter.replace(child, rule, memo)

            # Partial Matching Case:
            # e.g. rule_node = {"key1": [...]}
            #      query_node = {"and": [{"key1": [...]}, {"key2": [...]}, {"key3": [...]}]}
            # We need to replace the matched rule_node to the rewrite, while still 'and' the remaining [{"key2": [...]},{"key3": [...]}] with the rewrite
            if 'full_rule' in memo.keys():
                query = {memo['full_rule'][0]: [query, memo['full_rule'][1]]}
                del memo['full_rule']

        if QueryRewriter.is_list(query):
            ans = []
            for child in query:
                # VarList expansion properly
                if QueryRewriter.is_varList(child):
                    # if the VarList maps to a list, extend ans with its elements
                    # e.g. memo['V1'] = ['s1', 's2']
                    if QueryRewriter.is_list(memo[child]):
                        ans.extend(memo[child])
                    else:
                        # if not a list, just append the value
                        # e.g. memo['V3'] = 's3'
                        ans.append(memo[child])
                else:
                    # regular replacement for non-VarList children
                    replaced_child = QueryRewriter.replace(child, rule, memo)
                    ans.append(replaced_child)
            
            # this handles the case where VarList expansion creates multiple literal elements
            # that need to be merged into a single literal list (common in IN clauses)
            # e.g. [{'literal': 's1'}, {'literal': 's2'}] to {'literal': ['s1', 's2']}
            if (len(ans) > 1 and 
                all(QueryRewriter.is_dict(item) and 'literal' in item for item in ans)):
                # collect all literal values
                all_literal_values = []
                for item in ans:
                    if QueryRewriter.is_list(item['literal']):
                        all_literal_values.extend(item['literal'])
                    else:
                        all_literal_values.append(item['literal'])
                
                # return a single literal dictionary with all values
                query = {'literal': all_literal_values}
            else:
                query = ans
        if QueryRewriter.is_dot_expression(query):
            children = query.split('.')
            ans = []
            for child in children:
                child = QueryRewriter.replace(child, rule, memo)
                # handle case where child is a var 
                # and replaced by a table dict (with name and alias)
                #   e.g., V001 = {'value': 'employee', 'name': 'e1'}
                #
                if type(child) == dict:
                    if 'name' in child.keys():
                        child = child['name']
                    elif 'value' in child.keys():
                        child = child['value']
                    else:
                        # TODO - should not have this path
                        pass
                # handle case where child is a var
                # and replaced by a dot_expression
                #   e.g., V002 = 'e1.age'
                #
                if QueryRewriter.is_dot_expression(child):
                    # only keep the column name after the dot
                    child = child.split('.')[-1]
                ans.append(child)
            query = '.'.join(ans)
        
        return query
    
    # Replace the Var in a string - a spectial case
    #   e.g., {"literal": "%V2%"}
    # 
    @staticmethod
    def replace_var_in_str(query: str, memo: dict) -> str:
        for key in memo.keys():
            if QueryRewriter.is_var(key):
                if key in query:
                    return query.replace(key, memo[key])
        return query
    
    # Check if given two objects are deep equal
    def deep_equal(a, b):
        if type(a) != type(b):
            return False
        if isinstance(a, dict):
            if a.keys() != b.keys():
                return False
            return all(QueryRewriter.deep_equal(a[k], b[k]) for k in a)
        elif isinstance(a, list):
            if len(a) != len(b):
                return False
            return all(QueryRewriter.deep_equal(x, y) for x, y in zip(a, b))
        else:
            return a == b

    @staticmethod
    def get_all_keys(obj):
        keys = set()
        if isinstance(obj, dict):
            keys.update(obj.keys())
            for value in obj.values():
                keys.update(QueryRewriter.get_all_keys(value))
        elif isinstance(obj, list):
            for item in obj:
                keys.update(QueryRewriter.get_all_keys(item))
        return keys