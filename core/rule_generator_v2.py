from __future__ import annotations

import copy
import numbers
import re
from collections import defaultdict
from typing import Dict, Iterator, List, Optional, Set, Tuple, Union

from core.ast.enums import NodeType
from core.ast.node import (
    CaseNode,
    ColumnNode,
    CompoundQueryNode,
    ElementVariableNode,
    FromNode,
    FunctionNode,
    GroupByNode,
    HavingNode,
    JoinNode,
    LimitNode,
    ListNode,
    LiteralNode,
    Node,
    OffsetNode,
    OrderByItemNode,
    OrderByNode,
    OperatorNode,
    QueryNode,
    SelectNode,
    SetVariableNode,
    SubqueryNode,
    TableNode,
    UnaryOperatorNode,
    WhenThenNode,
    WhereNode,
)
from core.query_parser import QueryParser
from core.query_formatter import QueryFormatter
from core.rule_parser_v2 import RuleParserV2, Scope, VarType, VarTypesInfo


class RuleGeneratorV2:
    _PLACEHOLDER_PREFIXES = ("x", "y")

    @staticmethod
    def varType(var: str) -> Optional[VarType]:
        if var.startswith(VarTypesInfo[VarType.SetVariable]["internalBase"]):
            return VarType.SetVariable
        if var.startswith(VarTypesInfo[VarType.ElementVariable]["internalBase"]):
            return VarType.ElementVariable
        return None

    @staticmethod
    def parse_validate_single(query: str) -> Tuple[bool, str, int]:
        return RuleGeneratorV2._parse_validate_impl(query, None)

    @staticmethod
    def parse_validate(pattern: str, rewrite: str) -> Tuple[bool, str, int]:
        return RuleGeneratorV2._parse_validate_impl(pattern, rewrite)

    @staticmethod
    def recommend_simple_rules(examples: List[Dict[str, str]]) -> List[Dict[str, object]]:
        fingerprint_to_examples: Dict[str, Set[int]] = defaultdict(set)
        fingerprint_to_rule: Dict[str, Dict[str, object]] = {}
        example_candidates: List[List[Tuple[str, Dict[str, object]]]] = []

        for index, example in enumerate(examples):
            seed = RuleGeneratorV2.initialize_seed_rule(example["q0"], example["q1"])
            candidates_with_fingerprints: List[Tuple[str, Dict[str, object]]] = []
            for rule in RuleGeneratorV2._recommendation_candidates(seed):
                fp = RuleGeneratorV2.fingerPrint(rule)
                candidates_with_fingerprints.append((fp, rule))
                fingerprint_to_examples[fp].add(index)
                current = fingerprint_to_rule.get(fp)
                if current is None or RuleGeneratorV2.numberOfVariables(rule) < RuleGeneratorV2.numberOfVariables(current):
                    fingerprint_to_rule[fp] = rule
            example_candidates.append(candidates_with_fingerprints)

        uncovered = set(range(len(examples)))
        ans: List[Dict[str, object]] = []
        for index, _example in enumerate(examples):
            if index not in uncovered:
                continue
            chosen: Optional[Dict[str, object]] = None
            remaining = set(uncovered)
            for fp, rule in example_candidates[index]:
                covered = fingerprint_to_examples.get(fp, set()).intersection(remaining)
                if not covered:
                    continue
                remaining -= covered
                chosen = fingerprint_to_rule.get(fp, rule)
                if not remaining:
                    break
            if chosen is not None:
                uncovered = remaining
                ans.append(chosen)
        return ans

    @staticmethod
    def _recommendation_signature(rule: Dict[str, object]) -> str:
        pattern_ast = rule.get("pattern_ast")
        rewrite_ast = rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        state = {
            "tables": {},
            "aliases": {},
        }
        pattern_sig = RuleGeneratorV2._recommendation_ast_signature(pattern_ast, state)
        rewrite_sig = RuleGeneratorV2._recommendation_ast_signature(rewrite_ast, state)
        return repr((pattern_sig, rewrite_sig))

    @staticmethod
    def _recommendation_ast_signature(node: Optional[Node], state: Dict[str, Dict[str, str]]) -> object:
        if node is None:
            return None

        def _table_token(name: Optional[str]) -> Optional[str]:
            if name is None:
                return None
            if RuleGeneratorV2._is_placeholder_name(name):
                return f"VAR:{RuleGeneratorV2._fingerPrint(name)}"
            mapped = state["tables"].get(name)
            if mapped is None:
                mapped = f"T{len(state['tables']) + 1}"
                state["tables"][name] = mapped
            return mapped

        def _alias_token(name: Optional[str]) -> Optional[str]:
            if name is None:
                return None
            if RuleGeneratorV2._is_placeholder_name(name):
                return f"VAR:{RuleGeneratorV2._fingerPrint(name)}"
            mapped = state["aliases"].get(name)
            if mapped is None:
                mapped = f"A{len(state['aliases']) + 1}"
                state["aliases"][name] = mapped
            return mapped

        if isinstance(node, QueryNode):
            return ("QUERY", tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in node.children))
        if isinstance(node, SelectNode):
            distinct_on = (
                RuleGeneratorV2._recommendation_ast_signature(node.distinct_on, state)
                if node.distinct_on is not None
                else None
            )
            items = [RuleGeneratorV2._recommendation_ast_signature(child, state) for child in node.children]
            return ("SELECT", node.distinct, distinct_on, tuple(items))
        if isinstance(node, FromNode):
            return ("FROM", tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in node.children))
        if isinstance(node, WhereNode):
            return ("WHERE", tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in node.children))
        if isinstance(node, GroupByNode):
            return ("GROUPBY", tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in node.children))
        if isinstance(node, HavingNode):
            return ("HAVING", tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in node.children))
        if isinstance(node, OrderByNode):
            return ("ORDERBY", tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in node.children))
        if isinstance(node, OrderByItemNode):
            inner = list(node.children)[0] if node.children else None
            return ("ORDERBY_ITEM", node.sort.value if node.sort else None, RuleGeneratorV2._recommendation_ast_signature(inner, state))
        if isinstance(node, LimitNode):
            value = node.limit
            if isinstance(value, str) and RuleGeneratorV2._is_placeholder_name(value):
                value = f"VAR:{RuleGeneratorV2._fingerPrint(value)}"
            return ("LIMIT", value)
        if isinstance(node, OffsetNode):
            value = node.offset
            if isinstance(value, str) and RuleGeneratorV2._is_placeholder_name(value):
                value = f"VAR:{RuleGeneratorV2._fingerPrint(value)}"
            return ("OFFSET", value)
        if isinstance(node, TableNode):
            return ("TABLE", _table_token(node.name), _alias_token(node.alias))
        if isinstance(node, SubqueryNode):
            inner = list(node.children)[0] if node.children else None
            return ("SUBQUERY", _alias_token(node.alias), RuleGeneratorV2._recommendation_ast_signature(inner, state))
        if isinstance(node, ColumnNode):
            name = node.name
            if RuleGeneratorV2._is_placeholder_name(name):
                name = f"VAR:{RuleGeneratorV2._fingerPrint(name)}"
            return ("COLUMN", name, _alias_token(node.alias), _alias_token(node.parent_alias))
        if isinstance(node, LiteralNode):
            return ("LITERAL", node.value, _alias_token(getattr(node, "alias", None)))
        if isinstance(node, FunctionNode):
            return (
                "FUNCTION",
                node.name,
                _alias_token(node.alias),
                tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in node.children),
            )
        if isinstance(node, JoinNode):
            children = list(node.children)
            return (
                "JOIN",
                node.join_type.value,
                tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in children),
            )
        if isinstance(node, UnaryOperatorNode):
            child = list(node.children)[0] if node.children else None
            return ("UNARY", node.name, RuleGeneratorV2._recommendation_ast_signature(child, state))
        if isinstance(node, OperatorNode):
            return (
                "OP",
                node.name,
                tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in node.children),
            )
        if isinstance(node, ElementVariableNode):
            return ("EVAR", RuleGeneratorV2._fingerPrint(node.name))
        if isinstance(node, SetVariableNode):
            return ("SVAR", RuleGeneratorV2._fingerPrint(node.name))
        if isinstance(node, CompoundQueryNode):
            return (
                "COMPOUND",
                node.is_all,
                RuleGeneratorV2._recommendation_ast_signature(node.left, state),
                RuleGeneratorV2._recommendation_ast_signature(node.right, state),
            )
        return (
            type(node).__name__,
            tuple(RuleGeneratorV2._recommendation_ast_signature(child, state) for child in getattr(node, "children", [])),
        )

    @staticmethod
    def _recommendation_candidates(seed: Dict[str, object]) -> List[Dict[str, object]]:
        candidates: List[Dict[str, object]] = []
        seed_sig = RuleGeneratorV2._recommendation_signature(seed)
        seen: Set[str] = {seed_sig}
        queue: List[Dict[str, object]] = [seed]
        max_candidates = 256

        while queue and len(candidates) < max_candidates:
            base_rule = queue.pop(0)
            for transform in (
                RuleGeneratorV2.variablize_tables,
                RuleGeneratorV2.variablize_columns,
                RuleGeneratorV2.variablize_literals,
                RuleGeneratorV2.variablize_subtrees,
                RuleGeneratorV2.merge_variables,
                RuleGeneratorV2.drop_branches,
            ):
                for child in transform(base_rule):
                    sig = RuleGeneratorV2._recommendation_signature(child)
                    if sig in seen:
                        continue
                    seen.add(sig)
                    candidates.append(child)
                    queue.append(child)
                    if len(candidates) >= max_candidates:
                        break
                if len(candidates) >= max_candidates:
                    break
        return candidates

    @staticmethod
    def generate_rule_graph(q0: str, q1: str) -> Dict[str, object]:
        seed_rule = RuleGeneratorV2.initialize_seed_rule(q0, q1)
        seed_fp = RuleGeneratorV2.fingerPrint(seed_rule)
        visited = {seed_fp: seed_rule}
        queue = [seed_rule]
        while queue:
            base_rule = queue.pop(0)
            base_rule["children"] = []
            for transform in (
                RuleGeneratorV2.variablize_tables,
                RuleGeneratorV2.variablize_columns,
                RuleGeneratorV2.variablize_literals,
                RuleGeneratorV2.variablize_subtrees,
                RuleGeneratorV2.merge_variables,
                RuleGeneratorV2.drop_branches,
            ):
                for child_rule in transform(base_rule):
                    child_fp = RuleGeneratorV2.fingerPrint(child_rule)
                    if child_fp not in visited:
                        visited[child_fp] = child_rule
                        queue.append(child_rule)
                        base_rule["children"].append(child_rule)
                    else:
                        base_rule["children"].append(visited[child_fp])
        return seed_rule

    @staticmethod
    def initialize_seed_rule(q0: str, q1: str) -> Dict[str, object]:
        parsed = RuleParserV2.parse(q0, q1)
        pattern = RuleGeneratorV2.deparse(copy.deepcopy(parsed.pattern_ast))
        rewrite = RuleGeneratorV2.deparse(copy.deepcopy(parsed.rewrite_ast))
        return {
            "pattern": pattern,
            "rewrite": rewrite,
            "pattern_ast": parsed.pattern_ast,
            "rewrite_ast": parsed.rewrite_ast,
            "source_pattern_ast": copy.deepcopy(parsed.pattern_ast),
            "source_rewrite_ast": copy.deepcopy(parsed.rewrite_ast),
            "source_pattern_sql": q0,
            "source_rewrite_sql": q1,
            "mapping": parsed.mapping,
            "constraints": "",
            "actions": "",
        }

    RuleGeneralizations = (
        "generalize_tables",
        "generalize_columns",
        "generalize_literals",
        "generalize_subtrees",
        "generalize_variables",
        "generalize_branches",
    )

    @staticmethod
    def generate_general_rule(q0: str, q1: str) -> Dict[str, object]:
        seed_rule = RuleGeneratorV2.initialize_seed_rule(q0, q1)
        general_rule = seed_rule
        visited_fingerprints: Set[str] = set()
        rule_fingerprint = RuleGeneratorV2.fingerPrint(general_rule)
        while rule_fingerprint not in visited_fingerprints:
            visited_fingerprints.add(rule_fingerprint)
            for generalization in RuleGeneratorV2.RuleGeneralizations:
                general_rule = getattr(RuleGeneratorV2, generalization)(general_rule)
            rule_fingerprint = RuleGeneratorV2.fingerPrint(general_rule)
        return general_rule

    @staticmethod
    def variablize_tables(rule: Dict[str, object]) -> List[Dict[str, object]]:
        pattern_ast = rule.get("pattern_ast")
        rewrite_ast = rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        return [RuleGeneratorV2.variablize_table(rule, table) for table in RuleGeneratorV2.tables(pattern_ast, rewrite_ast)]

    @staticmethod
    def variablize_columns(rule: Dict[str, object]) -> List[Dict[str, object]]:
        pattern_ast = rule.get("pattern_ast")
        rewrite_ast = rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        return [RuleGeneratorV2.variablize_column(rule, column) for column in RuleGeneratorV2.columns(pattern_ast, rewrite_ast)]

    @staticmethod
    def variablize_literals(rule: Dict[str, object]) -> List[Dict[str, object]]:
        pattern_ast = rule.get("pattern_ast")
        rewrite_ast = rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        return [RuleGeneratorV2.variablize_literal(rule, literal) for literal in RuleGeneratorV2.literals(pattern_ast, rewrite_ast)]

    @staticmethod
    def merge_variables(rule: Dict[str, object]) -> List[Dict[str, object]]:
        pattern_ast = rule.get("pattern_ast")
        rewrite_ast = rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        return [RuleGeneratorV2.merge_variable_list(rule, variable_list) for variable_list in RuleGeneratorV2.variable_lists(pattern_ast, rewrite_ast)]

    @staticmethod
    def drop_branches(rule: Dict[str, object]) -> List[Dict[str, object]]:
        pattern_ast = rule.get("pattern_ast")
        rewrite_ast = rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        return [RuleGeneratorV2.drop_branch(rule, branch) for branch in RuleGeneratorV2.branches(pattern_ast, rewrite_ast)]

    @staticmethod
    def generalize_tables(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        pattern_ast = new_rule.get("pattern_ast")
        rewrite_ast = new_rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        for table in RuleGeneratorV2.tables(pattern_ast, rewrite_ast):
            new_rule = RuleGeneratorV2.variablize_table(new_rule, table)
            pattern_ast = new_rule["pattern_ast"]  # type: ignore[assignment]
            rewrite_ast = new_rule["rewrite_ast"]  # type: ignore[assignment]
        return new_rule

    @staticmethod
    def generalize_columns(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        pattern_ast = new_rule.get("pattern_ast")
        rewrite_ast = new_rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        for column in RuleGeneratorV2.columns(pattern_ast, rewrite_ast):
            new_rule = RuleGeneratorV2.variablize_column(new_rule, column)
            pattern_ast = new_rule["pattern_ast"]  # type: ignore[assignment]
            rewrite_ast = new_rule["rewrite_ast"]  # type: ignore[assignment]
        return new_rule

    @staticmethod
    def generalize_literals(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        pattern_ast = new_rule.get("pattern_ast")
        rewrite_ast = new_rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        for literal in RuleGeneratorV2.literals(pattern_ast, rewrite_ast):
            new_rule = RuleGeneratorV2.variablize_literal(new_rule, literal)
            pattern_ast = new_rule["pattern_ast"]  # type: ignore[assignment]
            rewrite_ast = new_rule["rewrite_ast"]  # type: ignore[assignment]
        return new_rule

    @staticmethod
    def generalize_subtrees(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        pattern_ast = new_rule.get("pattern_ast")
        rewrite_ast = new_rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        for subtree in RuleGeneratorV2.subtrees(pattern_ast, rewrite_ast):
            new_rule = RuleGeneratorV2.variablize_subtree(new_rule, subtree)
            pattern_ast = new_rule["pattern_ast"]  # type: ignore[assignment]
            rewrite_ast = new_rule["rewrite_ast"]  # type: ignore[assignment]
        return new_rule

    @staticmethod
    def generalize_variables(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        pattern_ast = new_rule.get("pattern_ast")
        rewrite_ast = new_rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        for variable_list in RuleGeneratorV2.variable_lists(pattern_ast, rewrite_ast):
            if variable_list:
                new_rule = RuleGeneratorV2.merge_variable_list(new_rule, variable_list)
                pattern_ast = new_rule["pattern_ast"]  # type: ignore[assignment]
                rewrite_ast = new_rule["rewrite_ast"]  # type: ignore[assignment]
        return new_rule

    @staticmethod
    def generalize_branches(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        pattern_ast = new_rule.get("pattern_ast")
        rewrite_ast = new_rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        for branch in RuleGeneratorV2.branches(pattern_ast, rewrite_ast):
            new_rule = RuleGeneratorV2.drop_branch(new_rule, branch)
            pattern_ast = new_rule["pattern_ast"]  # type: ignore[assignment]
            rewrite_ast = new_rule["rewrite_ast"]  # type: ignore[assignment]
        return new_rule


    @staticmethod
    def dereplaceVars(sql: str, mapping: Dict[str, str]) -> str:
        out = sql
        for external_name, internal_name in mapping.items():
            var_type = RuleGeneratorV2.varType(internal_name)
            if var_type is None:
                continue
            marker_start = VarTypesInfo[var_type]["markerStart"]
            marker_end = VarTypesInfo[var_type]["markerEnd"]
            out = out.replace(internal_name, f"{marker_start}{external_name}{marker_end}")
        return out

    @staticmethod
    def deparse(node: Node) -> str:
        working = copy.deepcopy(node)
        full_query, scope = RuleGeneratorV2._extend_to_full_query(working)
        full_query, placeholder_mapping = RuleGeneratorV2._encode_vars_for_format(full_query)
        sql = QueryFormatter().format(full_query)
        for placeholder, user_var in placeholder_mapping.items():
            sql = sql.replace(placeholder, user_var)
        # mo_sql_parsing renders NATURAL JOIN as `, NATURAL JOIN(<table>)`
        # (extra leading comma, no space before paren). Mirror v1's
        # dereplaceVars fix-up here.
        sql = re.sub(r",\s*NATURAL\s+JOIN\s*\(", " NATURAL JOIN (", sql)
        sql = RuleGeneratorV2._normalize_placeholder_tokens(sql)
        sql = RuleGeneratorV2._wrap_xy_identifiers(sql)
        return RuleGeneratorV2._extract_partial_sql(sql, scope)

    @staticmethod
    def columns(pattern_ast: Node, rewrite_ast: Node) -> List[str]:
        del rewrite_ast  # kept for parity with v1 signature
        found: Set[str] = set()
        var_names = {
            n.name
            for n in RuleGeneratorV2._walk(pattern_ast)
            if isinstance(n, (ElementVariableNode, SetVariableNode))
        }
        for node in RuleGeneratorV2._walk(pattern_ast):
            if isinstance(node, ColumnNode):
                if (
                    node.name
                    and node.name not in var_names
                    and not RuleGeneratorV2._is_placeholder_name(node.name)
                ):
                    found.add(node.name)
        # Sort deterministically so generalize_columns is hash-seed independent.
        return sorted(found)

    @staticmethod
    def literals(pattern_ast: Node, rewrite_ast: Node) -> List[Union[str, numbers.Number]]:
        pattern_literals = RuleGeneratorV2._literal_counts(pattern_ast)
        rewrite_literals = RuleGeneratorV2._literal_counts(rewrite_ast)

        variablize_literals: List[Union[str, numbers.Number]] = [
            lit for lit, count in pattern_literals.items() if count > 1
        ] + [lit for lit, count in rewrite_literals.items() if count > 1]

        intersect_literals = set(pattern_literals.keys()).intersection(set(rewrite_literals.keys()))
        return list(set(variablize_literals).union(intersect_literals))

    @staticmethod
    def tables(pattern_ast: Node, rewrite_ast: Node) -> List[Dict[str, str]]:
        pattern_tables = RuleGeneratorV2._tables_of_ast(pattern_ast)
        rewrite_tables = RuleGeneratorV2._tables_of_ast(rewrite_ast)

        pattern_set: Dict[str, List[str]] = defaultdict(list)
        rewrite_set: Dict[str, List[str]] = defaultdict(list)

        for table in pattern_tables:
            value = table["value"]
            alias = table["name"]
            if alias not in pattern_set[value]:
                pattern_set[value].append(alias)

        for table in rewrite_tables:
            value = table["value"]
            alias = table["name"]
            if alias not in rewrite_set[value]:
                rewrite_set[value].append(alias)

        superset: List[Dict[str, str]] = []
        for value, pattern_aliases in pattern_set.items():
            rewrite_aliases = rewrite_set.get(value, [])
            merged_aliases = pattern_aliases + [a for a in rewrite_aliases if a not in pattern_aliases]
            for alias in merged_aliases:
                superset.append({"value": value, "name": alias})

        deduped: List[Dict[str, str]] = []
        seen = set()
        for table in superset:
            fingerprint = f"{table['value']}-{table['name']}"
            if fingerprint not in seen:
                deduped.append(table)
                seen.add(fingerprint)
        return deduped

    @staticmethod
    def variable_lists(pattern_ast: Node, rewrite_ast: Node) -> List[List[str]]:
        pattern_lists = [set(v) for v in RuleGeneratorV2._variable_lists_of_ast(pattern_ast)]
        rewrite_lists = [set(v) for v in RuleGeneratorV2._variable_lists_of_ast(rewrite_ast)]

        ans: List[List[str]] = []
        while pattern_lists:
            p = pattern_lists.pop()
            matched_idx: Optional[int] = None
            for idx, r in enumerate(rewrite_lists):
                inter = p.intersection(r)
                if inter:
                    ans.append(list(inter))
                    matched_idx = idx
                    break
            if matched_idx is not None:
                rewrite_lists.pop(matched_idx)
        return ans

    @staticmethod
    def subtrees(pattern_ast: Node, rewrite_ast: Node) -> List[Node]:
        pattern_subtrees = RuleGeneratorV2._subtrees_of_ast(pattern_ast)
        rewrite_subtrees = RuleGeneratorV2._subtrees_of_ast(rewrite_ast)
        ans: List[Node] = []
        while pattern_subtrees:
            pattern_subtree = pattern_subtrees.pop()
            for idx, rewrite_subtree in enumerate(rewrite_subtrees):
                if pattern_subtree == rewrite_subtree:
                    ans.append(pattern_subtree)
                    rewrite_subtrees.pop(idx)
                    break
        return ans

    @staticmethod
    def variablize_subtree(rule: Dict[str, object], subtree: Node) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule["mapping"])
        if not isinstance(mapping, dict):
            raise TypeError("rule['mapping'] must be a dict[str, str]")

        mapping, external_name, _placeholder_token = RuleGeneratorV2._find_next_element_variable(mapping)
        new_rule["mapping"] = mapping

        for key in ("pattern_ast", "rewrite_ast"):
            ast = new_rule.get(key)
            if not isinstance(ast, Node):
                raise TypeError(f"rule['{key}'] must be an AST Node")
            new_rule[key] = RuleGeneratorV2._replace_subtree_in_ast(ast, subtree, ElementVariableNode(external_name))

        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def variablize_subtrees(rule: Dict[str, object]) -> List[Dict[str, object]]:
        return [RuleGeneratorV2.variablize_subtree(rule, subtree) for subtree in RuleGeneratorV2.subtrees(rule["pattern_ast"], rule["rewrite_ast"])]  # type: ignore[arg-type,index]

    @staticmethod
    def merge_variable_list(rule: Dict[str, object], variable_list: List[str]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule["mapping"])
        if not isinstance(mapping, dict):
            raise TypeError("rule['mapping'] must be a dict[str, str]")

        mapping, set_name, _placeholder_token = RuleGeneratorV2._find_next_set_variable(mapping)
        new_rule["mapping"] = mapping

        var_set = set(variable_list)
        for key in ("pattern_ast", "rewrite_ast"):
            ast = new_rule.get(key)
            if not isinstance(ast, Node):
                raise TypeError(f"rule['{key}'] must be an AST Node")
            new_rule[key] = RuleGeneratorV2._merge_variable_list_in_ast(ast, var_set, set_name)

        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def branches(pattern_ast: Node, rewrite_ast: Node) -> List[Dict[str, object]]:
        pattern_branches = RuleGeneratorV2._branch_entries_of_ast(pattern_ast)
        rewrite_branches = RuleGeneratorV2._branch_entries_of_ast(rewrite_ast)
        out: List[Dict[str, object]] = []
        remaining = list(rewrite_branches)
        while pattern_branches:
            pb_public, pb_target = pattern_branches.pop()
            for idx, (rb_public, rb_target) in enumerate(remaining):
                if RuleGeneratorV2._branch_values_match(pb_public, rb_public, pb_target, rb_target):
                    out.append(pb_public)
                    remaining.pop(idx)
                    break
        return out

    @staticmethod
    def _branch_values_match(
        pb: Dict[str, object],
        rb: Dict[str, object],
        pb_target: object,
        rb_target: object,
    ) -> bool:
        if pb.get("key") != rb.get("key"):
            return False
        return RuleGeneratorV2._branch_targets_match(pb_target, rb_target)

    @staticmethod
    def _branch_targets_match(pb_target: object, rb_target: object) -> bool:
        if pb_target == rb_target:
            return True
        if isinstance(pb_target, Node) and isinstance(rb_target, Node):
            try:
                ps = RuleGeneratorV2.deparse(copy.deepcopy(pb_target))
                rs = RuleGeneratorV2.deparse(copy.deepcopy(rb_target))
            except Exception:
                return False
            return ps.lower() == rs.lower()
        return False

    @staticmethod
    def drop_branch(rule: Dict[str, object], branch: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        for key in ("pattern_ast", "rewrite_ast"):
            ast = new_rule.get(key)
            if not isinstance(ast, Node):
                raise TypeError(f"rule['{key}'] must be an AST Node")
            new_rule[key] = RuleGeneratorV2._drop_branch_in_ast(ast, branch)
        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def fingerPrint(rule: Dict[str, object]) -> str:
        ast = rule.get("pattern_ast")
        if not isinstance(ast, Node):
            raise TypeError("rule['pattern_ast'] must be an AST Node")
        pattern = RuleGeneratorV2.deparse(ast)
        return RuleGeneratorV2._fingerPrint(pattern)

    @staticmethod
    def _fingerPrint(fingerprint: str) -> str:
        out = fingerprint
        out = re.sub(r"'(<x\d+>)'", r"\1", out)
        out = re.sub(r"<x(\d+)>", "<x>", out)
        out = re.sub(r"<<y(\d+)>>", "<<y>>", out)
        out = re.sub(r"'<x(\d+)>'", "'<x>'", out)
        out = RuleGeneratorV2._normalize_placeholder_numbers(out, "<x", ">")
        out = RuleGeneratorV2._normalize_placeholder_numbers(out, "<<y", ">>")
        return out

    @staticmethod
    def unify_variable_names(q0: str, q1: str) -> Tuple[str, str]:
        # Unify placeholders by first appearance across q0 then q1:
        # <x9> -> <x1>, <x10> -> <x2>, <<x9>> -> <<x1>>, etc.
        mapping: Dict[str, str] = {}
        counter = 1

        def _scan_tokens(text: str) -> List[str]:
            tokens: List[str] = []
            i = 0
            while i < len(text):
                if text.startswith("<<", i):
                    j = text.find(">>", i + 2)
                    if j != -1:
                        token = text[i : j + 2]
                        inner = token[2:-2]
                        if inner and all(ch.isalnum() or ch == "_" for ch in inner):
                            tokens.append(token)
                            i = j + 2
                            continue
                if text[i] == "<":
                    j = text.find(">", i + 1)
                    if j != -1:
                        token = text[i : j + 1]
                        inner = token[1:-1]
                        if inner and all(ch.isalnum() or ch == "_" for ch in inner):
                            tokens.append(token)
                            i = j + 1
                            continue
                i += 1
            return tokens

        for token in _scan_tokens(q0) + _scan_tokens(q1):
            if token in mapping:
                continue
            if token.startswith("<<") and token.endswith(">>"):
                mapping[token] = f"<<x{counter}>>"
            else:
                mapping[token] = f"<x{counter}>"
            counter += 1

        def _replace_all(text: str) -> str:
            out: List[str] = []
            i = 0
            while i < len(text):
                if text.startswith("<<", i):
                    j = text.find(">>", i + 2)
                    if j != -1:
                        token = text[i : j + 2]
                        if token in mapping:
                            out.append(mapping[token])
                            i = j + 2
                            continue
                if text[i] == "<":
                    j = text.find(">", i + 1)
                    if j != -1:
                        token = text[i : j + 1]
                        if token in mapping:
                            out.append(mapping[token])
                            i = j + 1
                            continue
                out.append(text[i])
                i += 1
            return "".join(out)

        return _replace_all(q0), _replace_all(q1)

    @staticmethod
    def numberOfVariables(rule: Dict[str, object]) -> int:
        mapping = rule.get("mapping")
        if not isinstance(mapping, dict):
            raise TypeError("rule['mapping'] must be a dict[str, str]")
        return len(mapping.keys())

    @staticmethod
    def _lev_distance(a: str, b: str) -> int:
        if len(b) == 0:
            return len(a)
        if len(a) == 0:
            return len(b)
        if a[0] == b[0]:
            return RuleGeneratorV2._lev_distance(a[1:], b[1:])
        return 1 + min(
            RuleGeneratorV2._lev_distance(a[1:], b),
            RuleGeneratorV2._lev_distance(a, b[1:]),
            RuleGeneratorV2._lev_distance(a[1:], b[1:]),
        )

    @staticmethod
    def _parse_validate_impl(pattern: str, rewrite: Optional[str]) -> Tuple[bool, str, int]:
        scope_names = {
            Scope.SELECT: "SELECT",
            Scope.FROM: "FROM",
            Scope.WHERE: "WHERE",
            Scope.CONDITION: "CONDITION",
        }
        scope_prefix_lengths = {
            Scope.SELECT: 0,
            Scope.FROM: 9,
            Scope.WHERE: 16,
            Scope.CONDITION: 22,
        }

        wrong_bracket_pattern = RuleParserV2.find_malformed_brackets(pattern)
        if wrong_bracket_pattern > -1:
            return False, "mismatching brackets in query 1", wrong_bracket_pattern
        if rewrite is not None:
            wrong_bracket_rewrite = RuleParserV2.find_malformed_brackets(rewrite)
            if wrong_bracket_rewrite > -1:
                return False, "mismatching brackets in query 2", wrong_bracket_rewrite

        pattern_compact = pattern.replace("\n", "")
        rewrite_compact = rewrite.replace("\n", "") if rewrite is not None else None

        def _first_token(sql: str) -> str:
            parts = [part for part in sql.split(" ") if part]
            return parts[0] if parts else ""

        for keyword in ("SELECT", "FROM", "WHERE"):
            token = _first_token(pattern_compact)
            if token and RuleGeneratorV2._lev_distance(keyword, token) == 1:
                return False, f"possible spelling error at query 1{token} instead of {keyword}", 0
            if rewrite_compact is not None:
                token = _first_token(rewrite_compact)
                if token and RuleGeneratorV2._lev_distance(keyword, token) == 1:
                    return False, f"possible spelling error at query 2{token} instead of {keyword}", 0

        try:
            pattern_sql, rewrite_sql, mapping = RuleParserV2.replaceVars(pattern_compact, rewrite_compact or pattern_compact)
            pattern_full, pattern_scope = RuleParserV2.extendToFullSQL(pattern_sql)
            QueryParser().parse(pattern_full)
        except Exception as e:
            message = str(e)
            display_message = RuleGeneratorV2.dereplaceVars(message, mapping)
            match = re.search(r'[Ee]xpecting(.*)found "(.*)" \(at char (\d+)', display_message)
            if match:
                error_index = RuleGeneratorV2._legacy_parse_error_index(
                    int(match.group(3)),
                    pattern_scope,
                    pattern_full,
                    mapping,
                    scope_prefix_lengths,
                )
                return (
                    False,
                    "Error in first query, current Scope is "
                    + scope_names[pattern_scope]
                    + " if that is not intended check spelling at index 0. Expecting "
                    + match.group(1).strip()
                    + " found "
                    + match.group(2).strip(),
                    error_index,
                )
            return False, message, -1

        if rewrite is None:
            return True, "success", 0

        # Variables that appear only in rewrite can never be instantiated from pattern.
        pattern_vars = set(re.findall(r"<<\w+>>|<\w+>", pattern))
        for match in re.finditer(r"<<\w+>>|<\w+>", rewrite):
            if match.group(0) not in pattern_vars:
                return False, f"{match.group(0)}not in first rule", match.start()

        try:
            rewrite_full, rewrite_scope = RuleParserV2.extendToFullSQL(rewrite_sql)
            QueryParser().parse(rewrite_full)
            return True, "Success", 0
        except Exception as e:
            message = str(e)
            display_message = RuleGeneratorV2.dereplaceVars(message, mapping)
            match = re.search(r'[Ee]xpecting(.*)found "(.*)" \(at char (\d+)', display_message)
            if match:
                error_index = RuleGeneratorV2._legacy_parse_error_index(
                    int(match.group(3)),
                    rewrite_scope,
                    rewrite_full,
                    mapping,
                    scope_prefix_lengths,
                )
                return (
                    False,
                    "Error in second query, current Scope is "
                    + scope_names[rewrite_scope]
                    + " if that is not intended check spelling at index 0. Expecting "
                    + match.group(1).strip()
                    + " found "
                    + match.group(2).strip(),
                    error_index,
                )
            return False, message, -1

    @staticmethod
    def _legacy_parse_error_index(
        parser_char_index: int,
        scope: Scope,
        full_sql: str,
        mapping: Dict[str, str],
        scope_prefix_lengths: Dict[Scope, int],
    ) -> int:
        error_index = parser_char_index - scope_prefix_lengths[scope]
        prefix = full_sql[:parser_char_index]
        for internal_name in mapping.values():
            diff = RuleGeneratorV2._internal_name_legacy_length_diff(internal_name)
            if diff <= 0:
                continue
            error_index -= prefix.count(internal_name) * diff
        return error_index

    @staticmethod
    def _internal_name_legacy_length_diff(internal_name: str) -> int:
        if internal_name.startswith(VarTypesInfo[VarType.ElementVariable]["internalBase"]):
            legacy_name = "V" + internal_name[len(VarTypesInfo[VarType.ElementVariable]["internalBase"]):]
            return len(internal_name) - len(legacy_name)
        if internal_name.startswith(VarTypesInfo[VarType.SetVariable]["internalBase"]):
            legacy_name = "VL" + internal_name[len(VarTypesInfo[VarType.SetVariable]["internalBase"]):]
            return len(internal_name) - len(legacy_name)
        return 0

    @staticmethod
    def variablize_literal(rule: Dict[str, object], literal: Union[str, numbers.Number]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule["mapping"])
        if not isinstance(mapping, dict):
            raise TypeError("rule['mapping'] must be a dict[str, str]")

        mapping, external_name, placeholder_token = RuleGeneratorV2._find_next_element_variable(mapping)
        new_rule["mapping"] = mapping

        for key in ("pattern_ast", "rewrite_ast"):
            ast = new_rule.get(key)
            if not isinstance(ast, Node):
                raise TypeError(f"rule['{key}'] must be an AST Node")
            new_rule[key] = RuleGeneratorV2._replace_literal_in_ast(ast, literal, external_name, placeholder_token)

        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def variablize_column(rule: Dict[str, object], column: str) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule["mapping"])
        if not isinstance(mapping, dict):
            raise TypeError("rule['mapping'] must be a dict[str, str]")

        mapping, external_name, _placeholder_token = RuleGeneratorV2._find_next_element_variable(mapping)
        new_rule["mapping"] = mapping

        for key in ("pattern_ast", "rewrite_ast"):
            ast = new_rule.get(key)
            if not isinstance(ast, Node):
                raise TypeError(f"rule['{key}'] must be an AST Node")
            new_rule[key] = RuleGeneratorV2._replace_column_in_ast(ast, column, external_name)

        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def variablize_table(rule: Dict[str, object], table: Dict[str, str]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule["mapping"])
        if not isinstance(mapping, dict):
            raise TypeError("rule['mapping'] must be a dict[str, str]")

        target_value = table.get("value")
        target_name = table.get("name")
        if not isinstance(target_value, str) or not isinstance(target_name, str):
            raise TypeError("table must have string keys 'value' and 'name'")

        mapping, _external_name, placeholder_token = RuleGeneratorV2._find_next_element_variable(mapping)
        new_rule["mapping"] = mapping

        for key in ("pattern_ast", "rewrite_ast"):
            ast = new_rule.get(key)
            if not isinstance(ast, Node):
                raise TypeError(f"rule['{key}'] must be an AST Node")
            new_rule[key] = RuleGeneratorV2._replace_table_in_ast(
                ast,
                target_value=target_value,
                target_name=target_name,
                placeholder_token=placeholder_token,
            )

        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def _walk(node: Optional[Node]) -> Iterator[Node]:
        if node is None:
            return
        yield node
        children = getattr(node, "children", None)
        if not children:
            return
        for child in children:
            yield from RuleGeneratorV2._walk(child)

    @staticmethod
    def _extend_to_full_query(node: Node) -> tuple[Node, Scope]:
        if isinstance(node, CompoundQueryNode):
            return node, Scope.SELECT
        if isinstance(node, QueryNode):
            has_select = RuleGeneratorV2._query_has_clause(node, NodeType.SELECT)
            has_from = RuleGeneratorV2._query_has_clause(node, NodeType.FROM)
            has_where = RuleGeneratorV2._query_has_clause(node, NodeType.WHERE)

            if has_select:
                return node, Scope.SELECT

            if has_from:
                return QueryNode(
                    _select=SelectNode([ColumnNode("*")]),
                    _from=RuleGeneratorV2._first_clause(node, NodeType.FROM),
                    _where=RuleGeneratorV2._first_clause(node, NodeType.WHERE),
                    _group_by=RuleGeneratorV2._first_clause(node, NodeType.GROUP_BY),
                    _having=RuleGeneratorV2._first_clause(node, NodeType.HAVING),
                    _order_by=RuleGeneratorV2._first_clause(node, NodeType.ORDER_BY),
                    _limit=RuleGeneratorV2._first_clause(node, NodeType.LIMIT),
                    _offset=RuleGeneratorV2._first_clause(node, NodeType.OFFSET),
                ), Scope.FROM

            if has_where:
                return QueryNode(
                    _select=SelectNode([ColumnNode("*")]),
                    _from=FromNode([TableNode("t")]),
                    _where=RuleGeneratorV2._first_clause(node, NodeType.WHERE),
                    _group_by=RuleGeneratorV2._first_clause(node, NodeType.GROUP_BY),
                    _having=RuleGeneratorV2._first_clause(node, NodeType.HAVING),
                    _order_by=RuleGeneratorV2._first_clause(node, NodeType.ORDER_BY),
                    _limit=RuleGeneratorV2._first_clause(node, NodeType.LIMIT),
                    _offset=RuleGeneratorV2._first_clause(node, NodeType.OFFSET),
                ), Scope.WHERE

        return QueryNode(
            _select=SelectNode([ColumnNode("*")]),
            _from=FromNode([TableNode("t")]),
            _where=WhereNode([node]),
        ), Scope.CONDITION

    @staticmethod
    def _first_clause(query: QueryNode, node_type: NodeType) -> Optional[Node]:
        for child in query.children:
            if child.type == node_type:
                return child
        return None

    @staticmethod
    def _query_has_clause(query: QueryNode, node_type: NodeType) -> bool:
        return RuleGeneratorV2._first_clause(query, node_type) is not None

    @staticmethod
    def _join_extra_source_count(join: JoinNode) -> int:
        left = join.left_table
        if isinstance(left, JoinNode):
            return 1 + RuleGeneratorV2._join_extra_source_count(left)
        return 1

    @staticmethod
    def _extract_partial_sql(full_sql: str, scope: Scope) -> str:
        if scope == Scope.SELECT:
            return full_sql
        if scope == Scope.FROM:
            return full_sql.replace("SELECT * ", "", 1)
        if scope == Scope.WHERE:
            return full_sql.replace("SELECT * FROM t ", "", 1)
        return full_sql.replace("SELECT * FROM t WHERE ", "", 1)

    @staticmethod
    def _literal_counts(ast: Node) -> Dict[Union[str, numbers.Number], int]:
        counts: Dict[Union[str, numbers.Number], int] = {}
        for node in RuleGeneratorV2._walk(ast):
            if node.type != NodeType.LITERAL:
                continue
            value = getattr(node, "value", None)
            if isinstance(value, str):
                normalized = value.replace("%", "")
                if RuleGeneratorV2._is_placeholder_name(normalized):
                    continue
                counts[normalized] = counts.get(normalized, 0) + 1
            elif isinstance(value, numbers.Number):
                counts[value] = counts.get(value, 0) + 1
        return counts

    @staticmethod
    def _tables_of_ast(ast: Node) -> List[Dict[str, str]]:
        found: List[Dict[str, str]] = []
        for node in RuleGeneratorV2._walk(ast):
            if not isinstance(node, TableNode):
                continue
            if not isinstance(node.name, str):
                continue
            if RuleGeneratorV2._is_placeholder_name(node.name):
                continue
            alias = node.alias if isinstance(node.alias, str) else node.name
            if RuleGeneratorV2._is_placeholder_name(alias):
                continue
            found.append({"value": node.name, "name": alias})
        return found

    @staticmethod
    def _find_next_element_variable(mapping: Dict[str, str]) -> Tuple[Dict[str, str], str, str]:
        max_external = 0
        max_internal = 0
        for external_name, internal_name in mapping.items():
            external_num = RuleGeneratorV2._suffix_int(external_name, "x")
            if external_num is not None:
                max_external = max(max_external, external_num)
            internal_num = RuleGeneratorV2._suffix_int(internal_name, "EV")
            if internal_num is not None:
                max_internal = max(max_internal, internal_num)

        next_external = f"x{max_external + 1}"
        next_internal = f"EV{str(max_internal + 1).zfill(3)}"
        mapping[next_external] = next_internal
        placeholder_token = f"__rv_{next_external}__"
        return mapping, next_external, placeholder_token

    @staticmethod
    def _find_next_set_variable(mapping: Dict[str, str]) -> Tuple[Dict[str, str], str, str]:
        max_external = 0
        max_internal = 0
        for external_name, internal_name in mapping.items():
            external_num = RuleGeneratorV2._suffix_int(external_name, "y")
            if external_num is not None:
                max_external = max(max_external, external_num)
            internal_num = RuleGeneratorV2._suffix_int(internal_name, "SV")
            if internal_num is not None:
                max_internal = max(max_internal, internal_num)

        next_external = f"y{max_external + 1}"
        next_internal = f"SV{str(max_internal + 1).zfill(3)}"
        mapping[next_external] = next_internal
        placeholder_token = f"__rvs_{next_external}__"
        return mapping, next_external, placeholder_token

    @staticmethod
    def _merge_variable_list_in_ast(ast: Node, variable_set: Set[str], set_name: str) -> Node:
        def _process_and_chain(and_node: OperatorNode) -> Optional[Node]:
            # Flatten nested AND chains so that `(a AND b) AND c` is treated as
            # `[a, b, c]`, mirroring v1's flat `{'and': [...]}` representation.
            flat: List[Node] = []

            def _flatten(n: Node) -> None:
                if isinstance(n, OperatorNode) and n.name.lower() == "and":
                    for child in n.children:
                        if isinstance(child, Node):
                            _flatten(child)
                    return
                flat.append(n)

            _flatten(and_node)

            flat_var_names = {c.name for c in flat if isinstance(c, ElementVariableNode)}
            if not variable_set.issubset(flat_var_names):
                return None

            new_children: List[Node] = []
            pending = False
            for child in flat:
                if isinstance(child, ElementVariableNode) and child.name in variable_set:
                    if not pending:
                        new_children.append(SetVariableNode(set_name))
                        pending = True
                    continue
                new_children.append(child)

            if len(new_children) == 1:
                return new_children[0]
            result: Node = new_children[0]
            for child in new_children[1:]:
                result = OperatorNode(result, "AND", child)
            return result

        def _is_inside_and(parent: Optional[Node]) -> bool:
            return (
                parent is not None
                and isinstance(parent, OperatorNode)
                and parent.name.lower() == "and"
            )

        def _visit(node: Node, parent: Optional[Node]) -> Node:
            if isinstance(node, (SelectNode, GroupByNode)):
                # v1 collects variable lists only from SELECT/AND, but its
                # `replaceVariableListsOfASTJson` walks *every* list and
                # collapses any subset match. Mirror that for GROUP BY so a
                # singleton merged on the SELECT side also collapses the same
                # column ref in the GROUP BY clause.
                new_children: List[Node] = []
                pending = False
                changed = False
                for child in node.children:
                    variable_name: Optional[str] = None
                    if isinstance(child, ElementVariableNode):
                        variable_name = child.name
                    elif (
                        isinstance(child, ColumnNode)
                        and child.parent_alias is None
                        and RuleGeneratorV2._is_placeholder_name(child.name)
                    ):
                        variable_name = child.name

                    if variable_name is not None and variable_name in variable_set:
                        if not pending:
                            new_children.append(SetVariableNode(set_name))
                            pending = True
                            changed = True
                        continue

                    pending = False
                    new_children.append(child)
                if changed:
                    node.children = new_children
                return node

            if isinstance(node, WhereNode):
                if len(node.children) == 1 and isinstance(node.children[0], ElementVariableNode):
                    if node.children[0].name in variable_set:
                        node.children = [SetVariableNode(set_name)]
                        return node
                # Otherwise fall through and recurse into children.

            if isinstance(node, JoinNode) and node.on_condition is not None:
                oc = node.on_condition
                if isinstance(oc, ElementVariableNode) and oc.name in variable_set:
                    replacement = SetVariableNode(set_name)
                    node.on_condition = replacement
                    if len(node.children) > 2:
                        node.children[2] = replacement
                    return node

            if isinstance(node, LimitNode) and isinstance(node.limit, str) and node.limit in variable_set:
                node.limit = set_name
                return node

            if (
                isinstance(node, OperatorNode)
                and node.name.lower() == "and"
                and not _is_inside_and(parent)
            ):
                replaced = _process_and_chain(node)
                if replaced is not None:
                    return replaced

            if isinstance(node, JoinNode):
                had_on = node.on_condition is not None
                n_using = len(node.using) if node.using else 0
            children = getattr(node, "children", None)
            if isinstance(children, list):
                for idx, child in enumerate(children):
                    if isinstance(child, Node):
                        new_child = _visit(child, node)
                        if new_child is not child:
                            children[idx] = new_child
                            RuleGeneratorV2._resync_parallel_attrs(node, child, new_child)
            elif isinstance(children, set):
                new_set: Set[Node] = set()
                replacements: List[Tuple[Node, Node]] = []
                for child in children:
                    if isinstance(child, Node):
                        new_child = _visit(child, node)
                        new_set.add(new_child)
                        if new_child is not child:
                            replacements.append((child, new_child))
                    else:
                        new_set.add(child)  # type: ignore[arg-type]
                node.children = new_set
                for old, new in replacements:
                    RuleGeneratorV2._resync_parallel_attrs(node, old, new)

            if isinstance(node, JoinNode):
                RuleGeneratorV2._resync_join_attrs(node, had_on, n_using)
            elif isinstance(node, UnaryOperatorNode):
                node.operand = node.children[0]
            elif isinstance(node, CompoundQueryNode):
                node.left = node.children[0]
                node.right = node.children[1]

            return node

        return _visit(ast, None)

    @staticmethod
    def _replace_literal_in_ast(
        ast: Node,
        literal: Union[str, numbers.Number],
        external_name: str,
        placeholder_token: str,
    ) -> Node:
        for node in RuleGeneratorV2._walk(ast):
            if node.type != NodeType.LITERAL:
                continue
            value = getattr(node, "value", None)

            if isinstance(literal, str) and isinstance(value, str):
                if value == literal:
                    node.value = placeholder_token  # type: ignore[attr-defined]
                elif value.replace("%", "") == literal:
                    node.value = value.replace(literal, placeholder_token)  # type: ignore[attr-defined]
                continue

            if isinstance(literal, numbers.Number) and isinstance(value, numbers.Number) and value == literal:
                replacement = ElementVariableNode(external_name)
                RuleGeneratorV2._replace_node_reference(ast, node, replacement)
        return ast

    @staticmethod
    def _replace_column_in_ast(ast: Node, column: str, external_name: str) -> Node:
        # Mirror v1 behavior: every column variabilization also rewrites any
        # remaining `*` (all_columns dict) to the same variable. This causes the
        # first column processed to share its variable with `*`. v1 only does
        # this for `*` inside a non-DISTINCT SELECT (mo_sql_parsing represents
        # those as `{'all_columns': {}}`); a `*` under SELECT DISTINCT is a
        # plain string in v1 and is only rewritten when column itself is `*`.
        non_distinct_select_star_ids: Set[int] = set()
        if column != "*":
            for node in RuleGeneratorV2._walk(ast):
                if isinstance(node, SelectNode) and not getattr(node, "distinct", False):
                    for child in node.children:
                        if isinstance(child, ColumnNode) and child.name == "*":
                            non_distinct_select_star_ids.add(id(child))
        for node in RuleGeneratorV2._walk(ast):
            if not isinstance(node, ColumnNode):
                continue
            if node.name == column:
                node.name = external_name
            elif (
                node.name == "*"
                and column != "*"
                and id(node) in non_distinct_select_star_ids
            ):
                node.name = external_name
        return ast

    @staticmethod
    def _replace_table_in_ast(
        ast: Node,
        target_value: str,
        target_name: str,
        placeholder_token: str,
    ) -> Node:
        # Mirror v1's `replaceTablesOfASTJson` special case: a bare-table
        # reference (no explicit alias, where alias == value) is also matched
        # when its value equals the target's value, even if `target_name`
        # disagrees. This lets a single table variable cover both an aliased
        # outer reference and a bare-named reference (e.g. inside a subquery)
        # of the same underlying table.
        match_aliases: Set[str] = set()
        for node in RuleGeneratorV2._walk(ast):
            if not isinstance(node, TableNode):
                continue
            current_alias = node.alias if isinstance(node.alias, str) else node.name
            if node.name == target_value and (
                current_alias == target_name or current_alias == node.name
            ):
                match_aliases.add(current_alias)
                node.name = placeholder_token
                node.alias = None

        if not match_aliases:
            return ast

        # Column refs may use either the alias (`t1.col`) or the table value
        # (`schema.table.col`); both should pick up the same variable. v1 also
        # rewrites column refs whose prefix matches `target_name` even when no
        # actual `TableNode` carries that alias (e.g. a subquery aliased the
        # same name as the underlying table on the other side of the rule).
        for node in RuleGeneratorV2._walk(ast):
            if (
                isinstance(node, ColumnNode)
                and isinstance(node.parent_alias, str)
                and (
                    node.parent_alias in match_aliases
                    or node.parent_alias == target_value
                    or node.parent_alias == target_name
                )
            ):
                node.parent_alias = placeholder_token
        return ast

    @staticmethod
    def _replace_node_reference(root: Node, target: Node, replacement: Node) -> None:
        for node in RuleGeneratorV2._walk(root):
            children = getattr(node, "children", None)
            replaced_here = False
            if isinstance(children, list):
                for idx, child in enumerate(children):
                    if child is target:
                        children[idx] = replacement
                        replaced_here = True
            elif isinstance(children, set):
                if target in children:
                    children.remove(target)
                    children.add(replacement)
                    replaced_here = True
            if replaced_here:
                RuleGeneratorV2._resync_parallel_attrs(node, target, replacement)
        if root is target:
            raise ValueError("Cannot replace root node directly; expected nested target.")

    @staticmethod
    def _resync_parallel_attrs(node: Node, target: Node, replacement: Node) -> None:
        # Many AST nodes mirror children into named attributes (e.g. CaseNode.
        # whens / else_val, WhenThenNode.when/then, JoinNode.on_condition).
        # The formatter and other helpers read those attrs directly, so
        # whenever we mutate `children` we must keep the parallel pointers in
        # sync. Walk the node's __dict__ and substitute any reference that
        # `is target` with `replacement`.
        for attr_name, attr_value in list(node.__dict__.items()):
            if attr_name == "children":
                continue
            if attr_value is target:
                setattr(node, attr_name, replacement)
            elif isinstance(attr_value, list):
                for idx, item in enumerate(attr_value):
                    if item is target:
                        attr_value[idx] = replacement
            elif isinstance(attr_value, tuple):
                if any(item is target for item in attr_value):
                    setattr(
                        node,
                        attr_name,
                        tuple(replacement if item is target else item for item in attr_value),
                    )

    @staticmethod
    def _is_placeholder_name(name: str) -> bool:
        lower = name.lower()
        if re.fullmatch(r"__rv_[xy]\d+__", lower):
            return True
        if re.fullmatch(r"__rvs_[xy]\d+__", lower):
            return True
        for prefix in RuleGeneratorV2._PLACEHOLDER_PREFIXES:
            if lower.startswith(prefix):
                suffix = lower[len(prefix):]
                if suffix.isdigit():
                    return True
        return False

    @staticmethod
    def _suffix_int(value: str, prefix: str) -> Optional[int]:
        if not value.lower().startswith(prefix.lower()):
            return None
        suffix = value[len(prefix):]
        if not suffix or not suffix.isdigit():
            return None
        return int(suffix)

    @staticmethod
    def _normalize_placeholder_tokens(sql: str) -> str:
        out = sql
        out = RuleGeneratorV2._replace_wrapped_tokens(out, "__rvs_", "__", "<<", ">>")
        out = RuleGeneratorV2._replace_wrapped_tokens(out, "__rv_", "__", "<", ">")
        return out

    @staticmethod
    def _variable_lists_of_ast(ast: Node) -> List[List[str]]:
        # AND chains parse left-associatively in v2 (e.g. `a AND b AND c` →
        # `(a AND b) AND c`). v1 sees them as a flat `{'and': [a, b, c]}`.
        # We mirror v1 by collecting variable lists only at top-most AND
        # operators (where the parent is not also AND) and flattening the
        # whole chain into a single list of placeholder names.
        out: List[List[str]] = []

        def _flatten_and(node: Node) -> List[str]:
            if isinstance(node, OperatorNode) and node.name.lower() == "and":
                names: List[str] = []
                for child in node.children:
                    names.extend(_flatten_and(child))
                return names
            if isinstance(node, ElementVariableNode):
                return [node.name]
            return []

        seen_and_ids: Set[int] = set()

        def _is_inside_and(parent: Optional[Node]) -> bool:
            return (
                parent is not None
                and isinstance(parent, OperatorNode)
                and parent.name.lower() == "and"
            )

        def _visit(node: Node, parent: Optional[Node] = None) -> None:
            if isinstance(node, SelectNode):
                if not getattr(node, "distinct", False):
                    names: List[str] = []
                    for child in node.children:
                        if isinstance(child, ElementVariableNode):
                            names.append(child.name)
                        elif (
                            isinstance(child, ColumnNode)
                            and child.parent_alias is None
                            and RuleGeneratorV2._is_placeholder_name(child.name)
                        ):
                            names.append(child.name)
                    if names:
                        out.append(names)
            elif (
                isinstance(node, OperatorNode)
                and node.name.lower() == "and"
                and not _is_inside_and(parent)
            ):
                names = _flatten_and(node)
                if names:
                    out.append(names)
                seen_and_ids.add(id(node))
            elif isinstance(node, WhereNode) and len(node.children) == 1 and isinstance(node.children[0], ElementVariableNode):
                out.append([node.children[0].name])
            elif isinstance(node, LimitNode) and isinstance(node.limit, str) and RuleGeneratorV2._is_placeholder_name(node.limit):
                out.append([node.limit])
            elif isinstance(node, JoinNode) and node.on_condition is not None:
                oc = node.on_condition
                if isinstance(oc, ElementVariableNode):
                    out.append([oc.name])

            children = getattr(node, "children", None)
            if children:
                for child in children:
                    if isinstance(child, Node):
                        _visit(child, node)

        _visit(ast)
        return out

    # ``_variable_lists_of_ast`` no longer uses the legacy linear loop, but the
    # following nested-list helpers remain for the pre-existing behavior in
    # ``_merge_variable_list_in_ast``.

    @staticmethod
    def _subtrees_of_ast(ast: Node) -> List[Node]:
        out: List[Node] = []
        seen: Set[str] = set()

        def _visit(node: Node, parent: Optional[Node] = None) -> None:
            if RuleGeneratorV2._is_subtree_candidate(node, parent):
                try:
                    key = RuleGeneratorV2.deparse(node)
                except Exception:
                    key = RuleGeneratorV2._structural_key(node)
                if key not in seen:
                    seen.add(key)
                    out.append(copy.deepcopy(node))
            children = getattr(node, "children", None)
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, Node):
                        _visit(child, node)
            elif isinstance(children, set):
                for child in children:
                    if isinstance(child, Node):
                        _visit(child, node)

        _visit(ast)
        return out

    @staticmethod
    def _structural_key(node: Node) -> str:
        parts: List[str] = [type(node).__name__]
        for attr in ("name", "value", "alias", "distinct", "parent_alias"):
            if hasattr(node, attr):
                parts.append(f"{attr}={getattr(node, attr)!r}")
        children = getattr(node, "children", None) or []
        if isinstance(children, (list, set)):
            child_keys: List[str] = []
            for child in list(children):
                if isinstance(child, Node):
                    child_keys.append(RuleGeneratorV2._structural_key(child))
                else:
                    child_keys.append(repr(child))
            parts.append("(" + ",".join(child_keys) + ")")
        return "|".join(parts)

    @staticmethod
    def _is_subtree_candidate(node: Node, parent: Optional[Node] = None) -> bool:
        if isinstance(
            node,
            (
                QueryNode,
                CompoundQueryNode,
                CaseNode,
                SelectNode,
                FromNode,
                WhereNode,
                GroupByNode,
                HavingNode,
                JoinNode,
                OrderByItemNode,
                OrderByNode,
                LimitNode,
                SubqueryNode,
                WhenThenNode,
            ),
        ):
            return False

        if isinstance(node, ColumnNode):
            # Mirror v1's `{'value': '...'}` wrapping for column refs that act
            # as standalone select/group-by/order-by items: those are subtree
            # candidates in v1 and get replaced; bare column refs inside
            # operators/functions (e.g. JOIN ON, WHERE, expressions) are not.
            if not RuleGeneratorV2._node_is_fully_variablized_column(node):
                return False
            return isinstance(parent, (SelectNode, GroupByNode, OrderByItemNode))

        if isinstance(node, SetVariableNode):
            # v1 wraps SELECT-position set vars as `{'value': VL}` (a subtree
            # dict). Mirror that so the SELECT/GROUP BY split iterations can
            # lift the set var into a fresh element var.
            if isinstance(parent, SelectNode):
                return True
            # v1 *also* wraps a fully-collapsed AND chain in WHERE / WHEN as
            # `{'and': [VL]}` (single-child AND). That ONLY happens when the
            # entire AND collapses to one set var, which in v2 means the set
            # var stands alone as a WHERE / WHEN predicate or as an OR-branch
            # (it took the place of an AND that had no other surviving
            # siblings). When the set var is mixed with other conjuncts under
            # an AND (like in `<<y>> AND <expr> AND <expr>`), v1's outer AND
            # list does *not* satisfy `isSubtree` (it has dict children), so
            # the set var stays a set var in v1 too — don't variabilize it
            # here.
            if isinstance(parent, (WhereNode, WhenThenNode)):
                return True
            if (
                isinstance(parent, OperatorNode)
                and parent.name.lower() == "or"
            ):
                return True
            return False

        if isinstance(node, LiteralNode):
            if isinstance(parent, ListNode):
                return False
            value = getattr(node, "value", None)
            if isinstance(value, str) and RuleGeneratorV2._is_placeholder_name(value):
                return True
            return False

        var_count = 0
        for child in getattr(node, "children", []) or []:
            if isinstance(child, (QueryNode, CompoundQueryNode, SelectNode, FromNode, WhereNode, JoinNode, SubqueryNode)):
                return False
            if isinstance(child, list):
                return False
            if isinstance(child, Node):
                if isinstance(child, (ElementVariableNode, SetVariableNode)):
                    var_count += 1
                    continue
                if isinstance(child, ColumnNode):
                    if RuleGeneratorV2._node_is_fully_variablized_column(child):
                        var_count += 1
                        continue
                    return False
                if isinstance(child, LiteralNode):
                    value = getattr(child, "value", None)
                    if isinstance(value, str):
                        normalized = value.replace("%", "")
                        if RuleGeneratorV2._is_placeholder_name(normalized):
                            var_count += 1
                    continue
                return False
        return var_count >= 1

    @staticmethod
    def _node_is_fully_variablized_column(node: ColumnNode) -> bool:
        if RuleGeneratorV2._is_placeholder_name(node.name):
            if node.parent_alias is None:
                return True
            return RuleGeneratorV2._is_placeholder_name(node.parent_alias)
        return False

    @staticmethod
    def _ast_contains_subtree(ast: Node, subtree: Node) -> bool:
        if ast == subtree:
            return True
        children = getattr(ast, "children", None)
        if isinstance(children, list):
            for child in children:
                if isinstance(child, Node) and RuleGeneratorV2._ast_contains_subtree(child, subtree):
                    return True
        elif isinstance(children, set):
            for child in children:
                if isinstance(child, Node) and RuleGeneratorV2._ast_contains_subtree(child, subtree):
                    return True
        return False

    @staticmethod
    def _flatten_and_terms(node: Node) -> List[Node]:
        if isinstance(node, OperatorNode) and node.name.upper() == "AND":
            out: List[Node] = []
            for child in node.children:
                if isinstance(child, Node):
                    out.extend(RuleGeneratorV2._flatten_and_terms(child))
            return out
        return [node]

    @staticmethod
    def _expand_source_with_alias_vars(node: Node, mapping: Dict[str, str], alias_table_map: Optional[Dict[str, str]] = None) -> Node:
        if isinstance(node, TableNode) and isinstance(node.name, str) and RuleGeneratorV2._is_placeholder_name(node.name) and node.alias is None:
            if alias_table_map is None:
                alias_table_map = {}
            table_name = alias_table_map.get(node.name)
            if table_name is None:
                mapping, table_name, _tok = RuleGeneratorV2._find_next_element_variable(mapping)
                alias_table_map[node.name] = table_name
            return TableNode(table_name, node.name)
        if isinstance(node, JoinNode):
            node.left_table = RuleGeneratorV2._expand_source_with_alias_vars(node.left_table, mapping, alias_table_map)  # type: ignore[arg-type]
            node.right_table = RuleGeneratorV2._expand_source_with_alias_vars(node.right_table, mapping, alias_table_map)  # type: ignore[arg-type]
            node.children[0] = node.left_table
            node.children[1] = node.right_table
        return node

    @staticmethod
    def _flatten_union_queries(node: Node) -> List[QueryNode]:
        if isinstance(node, QueryNode):
            return [node]
        if not isinstance(node, CompoundQueryNode):
            return []
        if getattr(node, "is_all", False):
            return []
        left_queries = RuleGeneratorV2._flatten_union_queries(node.children[0])
        right_queries = RuleGeneratorV2._flatten_union_queries(node.children[1])
        return left_queries + right_queries

    @staticmethod
    def _deparse_join_chain_with_using(join: JoinNode, using_col: str) -> Optional[str]:
        if join.on_condition is not None:
            return None
        left_sql = RuleGeneratorV2._deparse_join_left_with_using(join.left_table, using_col)
        right_sql = RuleGeneratorV2._deparse_table_factor(join.right_table)
        if left_sql is None or right_sql is None:
            return None
        join_keyword = str(getattr(join.join_type, "value", join.join_type) or "JOIN").upper()
        return f"{left_sql} {join_keyword} {right_sql} USING {using_col}"

    @staticmethod
    def _deparse_join_left_with_using(node: Node, using_col: str) -> Optional[str]:
        if isinstance(node, JoinNode):
            return RuleGeneratorV2._deparse_join_chain_with_using(node, using_col)
        return RuleGeneratorV2._deparse_table_factor(node)

    @staticmethod
    def _deparse_table_factor(node: Node) -> Optional[str]:
        if isinstance(node, TableNode):
            return RuleGeneratorV2.deparse(copy.deepcopy(node))
        if isinstance(node, SubqueryNode):
            return RuleGeneratorV2.deparse(copy.deepcopy(node))
        return None

    @staticmethod
    def _branch_entries_of_ast(ast: Node) -> List[Tuple[Dict[str, object], object]]:
        if isinstance(ast, QueryNode):
            out: List[Tuple[Dict[str, object], object]] = []
            select = RuleGeneratorV2._first_clause(ast, NodeType.SELECT)
            from_clause = RuleGeneratorV2._first_clause(ast, NodeType.FROM)
            where = RuleGeneratorV2._first_clause(ast, NodeType.WHERE)
            group_by = RuleGeneratorV2._first_clause(ast, NodeType.GROUP_BY)
            having = RuleGeneratorV2._first_clause(ast, NodeType.HAVING)
            order_by = RuleGeneratorV2._first_clause(ast, NodeType.ORDER_BY)
            limit = RuleGeneratorV2._first_clause(ast, NodeType.LIMIT)
            offset = RuleGeneratorV2._first_clause(ast, NodeType.OFFSET)
            # Treat SELECT and SELECT DISTINCT as separate keys (mirrors v1 mo_sql_parsing
            # which uses different keys 'select' vs 'select_distinct').
            select_is_distinct = isinstance(select, SelectNode) and bool(getattr(select, "distinct", False))
            plain_select = select if (select is not None and not select_is_distinct) else None
            is_select_only_wrapper = (
                select is not None
                and from_clause is None
                and where is None
                and all(clause is None for clause in (group_by, having, order_by, limit, offset))
            )
            if select is not None and (
                is_select_only_wrapper or RuleGeneratorV2._is_branch_clause("select", select)
            ):
                select_target: object = select
                if is_select_only_wrapper:
                    select_target = "__select_wrapper__"
                if isinstance(select, SelectNode) and len(select.children) == 1:
                    child = select.children[0]
                    if isinstance(child, SetVariableNode):
                        out.append(({"key": "select", "value": "set_variable"}, select_target))
                    elif isinstance(child, ColumnNode) and child.name == "*":
                        out.append(({"key": "select", "value": "all_columns"}, select_target))
                    else:
                        out.append(({"key": "select", "value": None}, select_target))
                else:
                    out.append(({"key": "select", "value": None}, select_target))
            is_from_only_wrapper = (
                from_clause is not None
                and select is None
                and where is None
                and all(clause is None for clause in (group_by, having, order_by, limit, offset))
            )
            if from_clause is not None and (
                is_from_only_wrapper or RuleGeneratorV2._is_branch_clause("from", from_clause)
            ):
                from_target: object = from_clause
                if is_from_only_wrapper:
                    from_target = "__from_wrapper__"
                if isinstance(from_clause, FromNode):
                    if any(isinstance(c, JoinNode) for c in from_clause.children):
                        out.append(({"key": "from", "value": "join_sources"}, from_target))
                    else:
                        out.append(({"key": "from", "value": "table_sources"}, from_target))
                else:
                    out.append(({"key": "from", "value": None}, from_target))
            is_where_only_wrapper = (
                where is not None
                and select is None
                and from_clause is None
                and all(clause is None for clause in (group_by, having, order_by, limit, offset))
            )
            if where is not None and (
                is_where_only_wrapper or RuleGeneratorV2._is_branch_clause("where", where)
            ):
                where_target: object = where
                if is_where_only_wrapper:
                    where_target = "__where_wrapper__"
                out.append(({"key": "where", "value": None}, where_target))
            if group_by is not None and RuleGeneratorV2._is_branch_clause("group_by", group_by):
                out.append(({"key": "group_by", "value": None}, group_by))
            if having is not None and RuleGeneratorV2._is_branch_clause("having", having):
                out.append(({"key": "having", "value": None}, having))
            if order_by is not None and RuleGeneratorV2._is_branch_clause("order_by", order_by):
                out.append(({"key": "order_by", "value": None}, order_by))
            if limit is not None and RuleGeneratorV2._is_branch_clause("limit", limit):
                out.append(({"key": "limit", "value": None}, limit))
            if offset is not None and RuleGeneratorV2._is_branch_clause("offset", offset):
                out.append(({"key": "offset", "value": None}, offset))

            # Mirror v1 special cases (select/where/from interactions). Note: v1 keys
            # 'select' and 'select_distinct' are distinct, so DISTINCT selects do not
            # count as 'select' for these rules.
            if plain_select is not None and where is not None:
                out = [entry for entry in out if entry[0]["key"] != "from"]
            if plain_select is None and from_clause is not None:
                out = [entry for entry in out if entry[0]["key"] != "where"]
            return out

        if isinstance(ast, OperatorNode) and ast.name.lower() in {"and", "or"}:
            out: List[Tuple[Dict[str, object], object]] = []
            for child in list(ast.children):
                wrapped = OperatorNode(copy.deepcopy(child), ast.name.upper())
                if RuleGeneratorV2._is_branch_node(wrapped):
                    out.append(({"key": ast.name.lower(), "value": child}, child))
            return out

        if isinstance(ast, OperatorNode):
            children = list(ast.children)
            if ast.name == "=" and len(children) == 2:
                return [({"key": "eq_rhs", "value": children[1]}, children[1])]

        return []

    @staticmethod
    def _is_branch_clause(key: str, clause: Node) -> bool:
        if key == "select":
            if isinstance(clause, SelectNode):
                if len(clause.children) == 1:
                    child = clause.children[0]
                    if isinstance(child, ColumnNode) and child.name == "*":
                        return True
                    if isinstance(child, SetVariableNode):
                        return True
                    return RuleGeneratorV2._is_branch_node(child)
                return RuleGeneratorV2._is_branch_node(clause)
            return False
        if key == "from":
            if isinstance(clause, FromNode):
                return RuleGeneratorV2._is_branch_node(clause)
            return False
        if key == "where":
            if isinstance(clause, WhereNode):
                if len(clause.children) == 1:
                    return RuleGeneratorV2._is_branch_node(clause.children[0])
                return RuleGeneratorV2._is_branch_node(clause)
            return RuleGeneratorV2._is_branch_node(clause)
        return RuleGeneratorV2._is_branch_node(clause)

    @staticmethod
    def _is_branch_node(node: Node) -> bool:
        if isinstance(node, FromNode):
            for child in node.children:
                if isinstance(child, TableNode):
                    if not RuleGeneratorV2._is_placeholder_name(child.name):
                        return False
                elif isinstance(child, JoinNode):
                    if not RuleGeneratorV2._is_branch_node(child):
                        return False
                else:
                    return False
            return True
        if isinstance(node, JoinNode):
            # A JOIN counts as a branch source when all of its operands and
            # the optional ON-condition contain nothing un-variablized.
            for child in node.children:
                if isinstance(child, TableNode):
                    if not RuleGeneratorV2._is_placeholder_name(child.name):
                        return False
                else:
                    if RuleGeneratorV2._tables_of_ast(copy.deepcopy(child)):
                        return False
                    cols = RuleGeneratorV2.columns(copy.deepcopy(child), copy.deepcopy(child))
                    if cols and not (len(cols) == 1 and cols[0] == "*"):
                        return False
                    if RuleGeneratorV2._literal_counts(copy.deepcopy(child)):
                        return False
                    if RuleGeneratorV2._variable_lists_of_ast(copy.deepcopy(child)):
                        return False
            return True
        if isinstance(node, WhereNode):
            predicates = list(node.children)
            if len(predicates) == 1:
                return RuleGeneratorV2._is_branch_node(predicates[0])
            return False
        if RuleGeneratorV2._tables_of_ast(copy.deepcopy(node)):
            return False
        columns = RuleGeneratorV2.columns(copy.deepcopy(node), copy.deepcopy(node))
        if columns:
            return len(columns) == 1 and columns[0] == "*"
        if RuleGeneratorV2._literal_counts(copy.deepcopy(node)):
            return False
        if RuleGeneratorV2._variable_lists_of_ast(copy.deepcopy(node)):
            return False
        return True

    @staticmethod
    def _drop_branch_in_ast(ast: Node, branch: Dict[str, object]) -> Node:
        if isinstance(ast, OperatorNode):
            key = branch.get("key")
            if key == "eq_rhs":
                children = list(ast.children)
                if ast.name == "=" and len(children) == 2 and children[1] == branch.get("value"):
                    return children[0]
            if key == ast.name.lower():
                children = list(ast.children)
                remaining = [child for child in children if child != branch.get("value")]
                if len(remaining) == 1:
                    return remaining[0]
                ast.children = remaining
                return ast
            return ast

        if not isinstance(ast, QueryNode):
            return ast
        key = branch.get("key")
        if key == "select":
            sel = RuleGeneratorV2._first_clause(ast, NodeType.SELECT)
            reduced = RuleGeneratorV2._query_without_clause(ast, NodeType.SELECT)
            if isinstance(reduced, QueryNode) and isinstance(sel, SelectNode):
                if not any(
                    RuleGeneratorV2._first_clause(reduced, t)
                    for t in (
                        NodeType.SELECT,
                        NodeType.FROM,
                        NodeType.WHERE,
                        NodeType.GROUP_BY,
                        NodeType.HAVING,
                        NodeType.ORDER_BY,
                        NodeType.LIMIT,
                        NodeType.OFFSET,
                    )
                ):
                    if len(sel.children) == 1:
                        return sel.children[0]
            return reduced
        if key == "from":
            from_clause = RuleGeneratorV2._first_clause(ast, NodeType.FROM)
            reduced = RuleGeneratorV2._query_without_clause(ast, NodeType.FROM)
            # When FROM is the only clause and contains a single subquery,
            # mirror v1 behavior of unwrapping `{from: <subquery>}` to the
            # subquery's inner query.
            if (
                isinstance(reduced, QueryNode)
                and len(reduced.children) == 0
                and isinstance(from_clause, FromNode)
                and len(from_clause.children) == 1
            ):
                source = next(iter(from_clause.children))
                if isinstance(source, SubqueryNode):
                    inner = next(iter(source.children), None)
                    if isinstance(inner, Node):
                        return inner
            return reduced
        if key == "where":
            reduced = RuleGeneratorV2._query_without_clause(ast, NodeType.WHERE)
            # If this was a WHERE-scope wrapper, unwrap back to condition expression.
            if isinstance(reduced, QueryNode) and len(reduced.children) == 0:
                wh = RuleGeneratorV2._first_clause(ast, NodeType.WHERE)
                if isinstance(wh, WhereNode) and len(wh.children) == 1:
                    return wh.children[0]
            return reduced
        if key == "group_by":
            return RuleGeneratorV2._query_without_clause(ast, NodeType.GROUP_BY)
        if key == "having":
            return RuleGeneratorV2._query_without_clause(ast, NodeType.HAVING)
        if key == "order_by":
            return RuleGeneratorV2._query_without_clause(ast, NodeType.ORDER_BY)
        if key == "limit":
            return RuleGeneratorV2._query_without_clause(ast, NodeType.LIMIT)
        if key == "offset":
            return RuleGeneratorV2._query_without_clause(ast, NodeType.OFFSET)
        return ast

    @staticmethod
    def _replace_subtree_in_ast(ast: Node, subtree: Node, replacement: Node, parent: Optional[Node] = None) -> Node:
        # Mirror v1's position-aware subtree replacement. In v1 a SELECT item
        # is wrapped in a `{'value': ...}` dict so column-ref strings appearing
        # in JOIN/ON/WHERE clauses are never matched by a SELECT-item subtree.
        # In v2 a `ColumnNode`/`LiteralNode` is the same node regardless of
        # context, so we additionally require the current position to be one
        # where the subtree would have been collected as a candidate.
        if ast == subtree and RuleGeneratorV2._is_subtree_candidate(ast, parent):
            return copy.deepcopy(replacement)
        if isinstance(ast, JoinNode):
            had_on = ast.on_condition is not None
            n_using = len(ast.using) if ast.using else 0
        children = getattr(ast, "children", None)
        if isinstance(children, list):
            for idx, child in enumerate(children):
                if isinstance(child, Node):
                    new_child = RuleGeneratorV2._replace_subtree_in_ast(child, subtree, replacement, ast)
                    if new_child is not child:
                        children[idx] = new_child
                        RuleGeneratorV2._resync_parallel_attrs(ast, child, new_child)
        elif isinstance(children, set):
            replacements: List[Tuple[Node, Node]] = []
            new_children: Set[Node] = set()
            for child in children:
                if isinstance(child, Node):
                    new_child = RuleGeneratorV2._replace_subtree_in_ast(child, subtree, replacement, ast)
                    new_children.add(new_child)
                    if new_child is not child:
                        replacements.append((child, new_child))
                else:
                    new_children.add(child)  # type: ignore[arg-type]
            ast.children = new_children
            for old, new in replacements:
                RuleGeneratorV2._resync_parallel_attrs(ast, old, new)

        if isinstance(ast, JoinNode):
            RuleGeneratorV2._resync_join_attrs(ast, had_on, n_using)
        elif isinstance(ast, UnaryOperatorNode):
            ast.operand = ast.children[0]
        elif isinstance(ast, CompoundQueryNode):
            ast.left = ast.children[0]
            ast.right = ast.children[1]
        elif isinstance(ast, SubqueryNode) and isinstance(ast.children, set):
            pass
        return ast

    @staticmethod
    def _resync_join_attrs(join: JoinNode, had_on: bool, n_using: int) -> None:
        children = list(join.children)
        if len(children) < 2:
            return
        join.left_table = children[0]  # type: ignore[assignment]
        join.right_table = children[1]  # type: ignore[assignment]
        rest = children[2:]
        if had_on and rest:
            join.on_condition = rest[0]  # type: ignore[assignment]
            using_rest = rest[1:]
        else:
            join.on_condition = None
            using_rest = rest
        if n_using and using_rest:
            join.using = list(using_rest[:n_using])
        else:
            join.using = None

    @staticmethod
    def _query_without_clause(query: QueryNode, clause_type: NodeType) -> QueryNode:
        return QueryNode(
            _select=None if clause_type == NodeType.SELECT else RuleGeneratorV2._first_clause(query, NodeType.SELECT),
            _from=None if clause_type == NodeType.FROM else RuleGeneratorV2._first_clause(query, NodeType.FROM),
            _where=None if clause_type == NodeType.WHERE else RuleGeneratorV2._first_clause(query, NodeType.WHERE),
            _group_by=None if clause_type == NodeType.GROUP_BY else RuleGeneratorV2._first_clause(query, NodeType.GROUP_BY),
            _having=None if clause_type == NodeType.HAVING else RuleGeneratorV2._first_clause(query, NodeType.HAVING),
            _order_by=None if clause_type == NodeType.ORDER_BY else RuleGeneratorV2._first_clause(query, NodeType.ORDER_BY),
            _limit=None if clause_type == NodeType.LIMIT else RuleGeneratorV2._first_clause(query, NodeType.LIMIT),
            _offset=None if clause_type == NodeType.OFFSET else RuleGeneratorV2._first_clause(query, NodeType.OFFSET),
        )

    @staticmethod
    def _wrap_xy_identifiers(sql: str) -> str:
        out: List[str] = []
        i = 0
        in_single_quote = False
        while i < len(sql):
            ch = sql[i]
            if ch == "'":
                in_single_quote = not in_single_quote
                out.append(ch)
                i += 1
                continue
            if in_single_quote:
                out.append(ch)
                i += 1
                continue

            if ch.isalpha() or ch == "_":
                j = i + 1
                while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                    j += 1
                token = sql[i:j]
                prev_char = sql[i - 1] if i > 0 else ""
                next_char = sql[j] if j < len(sql) else ""
                if not (prev_char == "<" and next_char == ">") and RuleGeneratorV2._is_placeholder_name(token):
                    if token.lower().startswith("y"):
                        out.append(f"<<{token}>>")
                    else:
                        out.append(f"<{token}>")
                else:
                    out.append(token)
                i = j
                continue

            out.append(ch)
            i += 1
        return "".join(out)

    @staticmethod
    def _replace_wrapped_tokens(
        text: str,
        prefix: str,
        suffix: str,
        open_marker: str,
        close_marker: str,
    ) -> str:
        out = text
        start = 0
        while True:
            i = out.find(prefix, start)
            if i < 0:
                break
            j = out.find(suffix, i + len(prefix))
            if j < 0:
                break
            inner = out[i + len(prefix):j]
            if inner and all(ch.isalnum() or ch == "_" for ch in inner):
                replacement = f"{open_marker}{inner}{close_marker}"
                out = out[:i] + replacement + out[j + len(suffix):]
                start = i + len(replacement)
            else:
                start = i + 1
        return out

    @staticmethod
    def _normalize_placeholder_numbers(text: str, start_token: str, end_token: str) -> str:
        out = text
        start = 0
        while True:
            i = out.find(start_token, start)
            if i < 0:
                break
            j = out.find(end_token, i + len(start_token))
            if j < 0:
                break
            inner = out[i + len(start_token):j]
            if inner.isdigit():
                out = out[: i + len(start_token)] + out[j:]
                start = i + len(start_token)
            else:
                start = j + len(end_token)
        return out

    @staticmethod
    def _encode_vars_for_format(node: Node) -> tuple[Node, Dict[str, str]]:
        placeholders: Dict[str, str] = {}

        def _visit(curr: Node) -> Node:
            if isinstance(curr, ElementVariableNode):
                placeholder = f"__rv_{curr.name}__"
                placeholders[placeholder] = f"<{curr.name}>"
                return ColumnNode(placeholder)
            if isinstance(curr, SetVariableNode):
                placeholder = f"__rvs_{curr.name}__"
                placeholders[placeholder] = f"<<{curr.name}>>"
                return ColumnNode(placeholder)

            children = getattr(curr, "children", None)
            if not children:
                return curr

            if isinstance(children, list):
                for idx, child in enumerate(children):
                    if isinstance(child, Node):
                        children[idx] = _visit(child)
            elif isinstance(children, set):
                new_set: Set[Node] = set()
                for child in children:
                    if isinstance(child, Node):
                        new_set.add(_visit(child))
                    else:
                        new_set.add(child)  # type: ignore[arg-type]
                curr.children = new_set
            return curr

        return _visit(node), placeholders
