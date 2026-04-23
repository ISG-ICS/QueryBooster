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

    @staticmethod
    def generate_general_rule(q0: str, q1: str) -> Dict[str, object]:
        rule = RuleGeneratorV2.initialize_seed_rule(q0, q1)

        visited: Set[str] = set()
        while True:
            fingerprint = RuleGeneratorV2._fingerPrint(str(rule["pattern"])) + "::" + RuleGeneratorV2._fingerPrint(str(rule["rewrite"]))
            if fingerprint in visited:
                break
            visited.add(fingerprint)
            rule = RuleGeneratorV2.generalize_tables(rule)
            rule = RuleGeneratorV2.generalize_columns(rule)
            rule = RuleGeneratorV2.generalize_literals(rule)
            distinct_lookup_rule = RuleGeneratorV2.generalize_distinct_lookup_rule(rule)
            if distinct_lookup_rule is not rule:
                rule = distinct_lookup_rule
                break
            rule = RuleGeneratorV2.generalize_subtrees(rule)
            if rule.pop("_terminal_generalization", False):
                break
            rule = RuleGeneratorV2.generalize_variables(rule)
            rule = RuleGeneratorV2.generalize_branches(rule)
            before_unwrap = RuleGeneratorV2._fingerPrint(str(rule["pattern"])) + "::" + RuleGeneratorV2._fingerPrint(str(rule["rewrite"]))
            rule = RuleGeneratorV2.unwrap_matching_subquery(rule)
            wrapper_projection_rule = RuleGeneratorV2.generalize_wrapper_projection(rule)
            if wrapper_projection_rule is not rule:
                rule = wrapper_projection_rule
                break
            after_unwrap = RuleGeneratorV2._fingerPrint(str(rule["pattern"])) + "::" + RuleGeneratorV2._fingerPrint(str(rule["rewrite"]))
            if before_unwrap == after_unwrap:
                break

        # Preserve v1 behavior for expression-only inputs written as "SELECT expr":
        # final generalized rule should be expression fragments, not full SELECT clauses.
        if RuleGeneratorV2._is_select_expression_input(q0) and RuleGeneratorV2._is_select_expression_input(q1):
            if isinstance(rule.get("pattern"), str) and rule["pattern"].upper().startswith("SELECT "):
                rule["pattern"] = rule["pattern"][7:]
            if isinstance(rule.get("rewrite"), str) and rule["rewrite"].upper().startswith("SELECT "):
                rule["rewrite"] = rule["rewrite"][7:]

        up, ur = RuleGeneratorV2.unify_variable_names(str(rule["pattern"]), str(rule["rewrite"]))
        if RuleGeneratorV2._is_select_expression_input(up):
            up = up[7:]
        if RuleGeneratorV2._is_select_expression_input(ur):
            ur = ur[7:]
        rule["pattern"] = up
        rule["rewrite"] = ur
        rule = RuleGeneratorV2.generalize_or_to_union(rule)
        rule = RuleGeneratorV2.generalize_or_union_projection_sets(rule)
        hp, hr = RuleGeneratorV2.unify_variable_names(str(rule["pattern"]), str(rule["rewrite"]))
        if RuleGeneratorV2._is_select_expression_input(hp):
            hp = hp[7:]
        if RuleGeneratorV2._is_select_expression_input(hr):
            hr = hr[7:]
        rule["pattern"] = hp
        rule["rewrite"] = hr
        return rule

    @staticmethod
    def _rule_after_literals(q0: str, q1: str) -> Dict[str, object]:
        rule = RuleGeneratorV2.initialize_seed_rule(q0, q1)
        rule = RuleGeneratorV2.generalize_tables(rule)
        rule = RuleGeneratorV2.generalize_columns(rule)
        rule = RuleGeneratorV2.generalize_literals(rule)
        return rule

    def _generalize_join_elimination(rule: Dict[str, object]) -> Optional[Dict[str, object]]:
        pat = rule.get("pattern_ast")
        rew = rule.get("rewrite_ast")
        p0 = rule.get("source_pattern_ast")
        r0 = rule.get("source_rewrite_ast")
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode):
            return None
        if not isinstance(p0, QueryNode) or not isinstance(r0, QueryNode):
            return None
        if RuleGeneratorV2._from_source_count(pat) != RuleGeneratorV2._from_source_count(rew) + 1:
            return None

        original_select = RuleGeneratorV2._first_clause(p0, NodeType.SELECT)
        rewrite_from_count = RuleGeneratorV2._from_source_count(r0)
        new_rule = copy.deepcopy(rule)
        new_pat = new_rule.get("pattern_ast")
        new_rew = new_rule.get("rewrite_ast")
        if not isinstance(new_pat, QueryNode) or not isinstance(new_rew, QueryNode):
            return None

        if isinstance(original_select, SelectNode) and len(original_select.children) == 1:
            child = original_select.children[0]
            if isinstance(child, ColumnNode) and child.name == "*":
                new_rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(new_pat, NodeType.SELECT)
                new_rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(new_rule["pattern_ast"], NodeType.WHERE)  # type: ignore[arg-type]
                new_rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(new_rew, NodeType.SELECT)
                new_rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(new_rule["rewrite_ast"], NodeType.WHERE)  # type: ignore[arg-type]
            elif isinstance(child, FunctionNode) and child.name.upper() == "COUNT":
                new_rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(new_pat, NodeType.WHERE)
                new_rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(new_rew, NodeType.WHERE)
            elif isinstance(child, ColumnNode) and rewrite_from_count == 1:
                pass
            else:
                return None
        elif isinstance(original_select, SelectNode):
            if all(isinstance(c, ColumnNode) and c.alias for c in original_select.children):
                mapping = copy.deepcopy(new_rule["mapping"])
                if not isinstance(mapping, dict):
                    return None
                mapping, set_name, _tok = RuleGeneratorV2._find_next_set_variable(mapping)
                new_rule["mapping"] = mapping
                pat_sel = RuleGeneratorV2._first_clause(new_rule["pattern_ast"], NodeType.SELECT)  # type: ignore[arg-type]
                rew_sel = RuleGeneratorV2._first_clause(new_rule["rewrite_ast"], NodeType.SELECT)  # type: ignore[arg-type]
                if isinstance(pat_sel, SelectNode):
                    pat_sel.children = [SetVariableNode(set_name)]
                if isinstance(rew_sel, SelectNode):
                    rew_sel.children = [SetVariableNode(set_name)]
                new_rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(new_rule["pattern_ast"], NodeType.WHERE)  # type: ignore[arg-type]
                new_rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(new_rule["rewrite_ast"], NodeType.WHERE)  # type: ignore[arg-type]
            else:
                return None
        else:
            return None

        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def generalize_join_elimination(rule: Dict[str, object]) -> Dict[str, object]:
        generalized_rule = RuleGeneratorV2._generalize_join_elimination(rule)
        if generalized_rule is None:
            return rule
        return generalized_rule

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

    def _normalize_self_join_projection_rule(rule: Dict[str, object]) -> Optional[Dict[str, object]]:
        pat = copy.deepcopy(rule.get("pattern_ast"))
        rew = copy.deepcopy(rule.get("rewrite_ast"))
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode):
            return None
        if RuleGeneratorV2._from_source_count(pat) != 2 or RuleGeneratorV2._from_source_count(rew) != 1:
            return None
        p_from = RuleGeneratorV2._first_clause(pat, NodeType.FROM)
        r_from = RuleGeneratorV2._first_clause(rew, NodeType.FROM)
        if not isinstance(p_from, FromNode) or not isinstance(r_from, FromNode):
            return None
        if len(p_from.children) != 2 or len(r_from.children) != 1:
            return None
        if not all(isinstance(c, TableNode) for c in p_from.children) or not isinstance(r_from.children[0], TableNode):
            return None

        pat_sel = RuleGeneratorV2._first_clause(pat, NodeType.SELECT)
        rew_sel = RuleGeneratorV2._first_clause(rew, NodeType.SELECT)
        if not isinstance(pat_sel, SelectNode) or not isinstance(rew_sel, SelectNode):
            return None
        prefix_len = 0
        while (
            prefix_len < len(pat_sel.children)
            and prefix_len < len(rew_sel.children)
            and RuleGeneratorV2.deparse(pat_sel.children[prefix_len]) == RuleGeneratorV2.deparse(rew_sel.children[prefix_len])
        ):
            prefix_len += 1
        if prefix_len < 1 or prefix_len >= len(pat_sel.children):
            return None

        mapping = copy.deepcopy(rule["mapping"])
        if not isinstance(mapping, dict):
            return None
        mapping, set_name, _tok = RuleGeneratorV2._find_next_set_variable(mapping)
        rule["mapping"] = mapping
        pat_sel.children = [SetVariableNode(set_name)] + pat_sel.children[prefix_len:]
        rew_sel.children = [SetVariableNode(set_name)] + rew_sel.children[prefix_len:]
        rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(pat, NodeType.FROM)
        rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(rew, NodeType.FROM)
        rule["pattern"] = RuleGeneratorV2.deparse(rule["pattern_ast"])  # type: ignore[index]
        rule["rewrite"] = RuleGeneratorV2.deparse(rule["rewrite_ast"])  # type: ignore[index]
        return rule

    @staticmethod
    def _normalize_count_join_filter_rule(rule: Dict[str, object]) -> Optional[Dict[str, object]]:
        pat = copy.deepcopy(rule.get("pattern_ast"))
        rew = copy.deepcopy(rule.get("rewrite_ast"))
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode):
            return None
        pat_sel = RuleGeneratorV2._first_clause(pat, NodeType.SELECT)
        rew_sel = RuleGeneratorV2._first_clause(rew, NodeType.SELECT)
        if not isinstance(pat_sel, SelectNode) or not isinstance(rew_sel, SelectNode):
            return None
        if len(pat_sel.children) != 1 or len(rew_sel.children) != 1:
            return None
        pat_child = pat_sel.children[0]
        rew_child = rew_sel.children[0]
        if not (
            isinstance(pat_child, FunctionNode)
            and isinstance(rew_child, FunctionNode)
            and pat_child.name.upper() == "COUNT"
            and rew_child.name.upper() == "COUNT"
        ):
            return None
        if RuleGeneratorV2._from_source_count(pat) != RuleGeneratorV2._from_source_count(rew) + 1:
            return None

        rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(pat, NodeType.SELECT)
        rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(rew, NodeType.SELECT)
        rule["pattern"] = RuleGeneratorV2.deparse(rule["pattern_ast"])  # type: ignore[index]
        rule["rewrite"] = RuleGeneratorV2.deparse(rule["rewrite_ast"])  # type: ignore[index]
        rule = RuleGeneratorV2._generalize_subtrees_core(rule)
        rule = RuleGeneratorV2._generalize_variables_core(rule)
        return rule

    @staticmethod
    def _generalize_count_join_filter(rule: Dict[str, object]) -> Optional[Dict[str, object]]:
        q0 = rule.get("source_pattern_sql")
        q1 = rule.get("source_rewrite_sql")
        if not isinstance(q0, str) or not isinstance(q1, str):
            return None
        if "COUNT(" not in q0 or "COUNT(" not in q1:
            return None
        pat = rule.get("pattern_ast")
        rew = rule.get("rewrite_ast")
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode):
            return None
        if RuleGeneratorV2._from_source_count(pat) != RuleGeneratorV2._from_source_count(rew) + 1:
            return None
        return RuleGeneratorV2._normalize_count_join_filter_rule(copy.deepcopy(rule))

    @staticmethod
    def generalize_count_join_filter(rule: Dict[str, object]) -> Dict[str, object]:
        generalized_rule = RuleGeneratorV2._generalize_count_join_filter(rule)
        if generalized_rule is None:
            return rule
        return generalized_rule

    @staticmethod
    def _normalize_or_to_union_rule(rule: Dict[str, object]) -> Optional[Dict[str, object]]:
        return RuleGeneratorV2._generalize_or_to_union(rule)

    @staticmethod
    def _generalize_or_to_union(rule: Dict[str, object]) -> Optional[Dict[str, object]]:
        pattern_ast = rule.get("pattern_ast")
        rewrite_ast = rule.get("rewrite_ast")
        if not isinstance(pattern_ast, QueryNode) or not isinstance(rewrite_ast, CompoundQueryNode):
            return None
        if getattr(rewrite_ast, "is_all", False):
            return None

        new_rule = copy.deepcopy(rule)
        pat = new_rule.get("pattern_ast")
        rew = new_rule.get("rewrite_ast")
        if not isinstance(pat, QueryNode) or not isinstance(rew, CompoundQueryNode):
            return None

        new_rule["pattern_ast"] = RuleGeneratorV2._dedupe_boolean_predicates(copy.deepcopy(pat))
        new_rule["rewrite_ast"] = RuleGeneratorV2._dedupe_boolean_predicates(copy.deepcopy(rew))
        new_rule = RuleGeneratorV2._coerce_or_union_setvars_to_elements(new_rule)
        new_rule = RuleGeneratorV2._promote_or_union_query_projections(new_rule)

        pat2 = new_rule["pattern_ast"]
        rew2 = new_rule["rewrite_ast"]
        if not isinstance(pat2, QueryNode) or not isinstance(rew2, CompoundQueryNode):
            return None
        rewrite_sql = RuleGeneratorV2._deparse_union_using_compound(rew2)
        if rewrite_sql is None:
            return None

        new_rule["pattern"] = RuleGeneratorV2.deparse(pat2)
        new_rule["rewrite"] = rewrite_sql
        return new_rule

    @staticmethod
    def generalize_or_to_union(rule: Dict[str, object]) -> Dict[str, object]:
        generalized_rule = RuleGeneratorV2._generalize_or_to_union(rule)
        if generalized_rule is None:
            return rule
        return generalized_rule

    @staticmethod
    def generalize_or_union_projection_sets(rule: Dict[str, object]) -> Dict[str, object]:
        generalized_rule = RuleGeneratorV2._promote_or_union_query_projections(rule)
        if generalized_rule is rule:
            return rule
        generalized_rule["pattern"] = RuleGeneratorV2.deparse(generalized_rule["pattern_ast"])  # type: ignore[index]
        rewrite_ast = generalized_rule.get("rewrite_ast")
        if isinstance(rewrite_ast, CompoundQueryNode):
            rewrite_sql = RuleGeneratorV2._deparse_union_using_compound(rewrite_ast)
            generalized_rule["rewrite"] = rewrite_sql if rewrite_sql is not None else RuleGeneratorV2.deparse(rewrite_ast)
        elif isinstance(rewrite_ast, Node):
            generalized_rule["rewrite"] = RuleGeneratorV2.deparse(rewrite_ast)
        return generalized_rule

    @staticmethod
    def _coerce_or_union_setvars_to_elements(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule.get("mapping"))
        pat = new_rule.get("pattern_ast")
        rew = new_rule.get("rewrite_ast")
        if not isinstance(mapping, dict) or not isinstance(pat, Node) or not isinstance(rew, Node):
            return new_rule

        set_names: List[str] = []
        for node in list(RuleGeneratorV2._walk(pat)) + list(RuleGeneratorV2._walk(rew)):
            if isinstance(node, SetVariableNode) and node.name not in set_names:
                set_names.append(node.name)
        if not set_names:
            return new_rule

        replacements: Dict[str, str] = {}
        for set_name in set_names:
            mapping, external_name, _placeholder_token = RuleGeneratorV2._find_next_element_variable(mapping)
            replacements[set_name] = external_name
        new_rule["mapping"] = mapping
        new_rule["pattern_ast"] = RuleGeneratorV2._replace_setvars_in_ast(copy.deepcopy(pat), replacements)
        new_rule["rewrite_ast"] = RuleGeneratorV2._replace_setvars_in_ast(copy.deepcopy(rew), replacements)
        return new_rule

    @staticmethod
    def _replace_setvars_in_ast(ast: Node, replacements: Dict[str, str]) -> Node:
        if isinstance(ast, SetVariableNode) and ast.name in replacements:
            return ElementVariableNode(replacements[ast.name])
        children = getattr(ast, "children", None)
        if isinstance(children, list):
            for idx, child in enumerate(children):
                if isinstance(child, Node):
                    children[idx] = RuleGeneratorV2._replace_setvars_in_ast(child, replacements)
        elif isinstance(children, set):
            new_children: Set[Node] = set()
            for child in children:
                if isinstance(child, Node):
                    new_children.add(RuleGeneratorV2._replace_setvars_in_ast(child, replacements))
                else:
                    new_children.add(child)  # type: ignore[arg-type]
            ast.children = new_children
        if isinstance(ast, JoinNode):
            ast.left_table = ast.children[0]  # type: ignore[assignment]
            ast.right_table = ast.children[1]  # type: ignore[assignment]
            ast.on_condition = ast.children[2] if len(ast.children) > 2 else None  # type: ignore[assignment]
        elif isinstance(ast, UnaryOperatorNode):
            ast.operand = ast.children[0]
        elif isinstance(ast, CompoundQueryNode):
            ast.left = ast.children[0]
            ast.right = ast.children[1]
        return ast

    @staticmethod
    def _promote_or_union_query_projections(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule.get("mapping"))
        pat = new_rule.get("pattern_ast")
        rew = new_rule.get("rewrite_ast")
        if not isinstance(mapping, dict) or not isinstance(pat, QueryNode) or not isinstance(rew, CompoundQueryNode):
            return rule

        projection_sets: Dict[str, str] = {}

        def _visit(node: Node) -> None:
            if isinstance(node, QueryNode):
                RuleGeneratorV2._promote_single_source_projection(node, mapping, projection_sets)
            children = getattr(node, "children", None)
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, Node):
                        _visit(child)
            elif isinstance(children, set):
                for child in list(children):
                    if isinstance(child, Node):
                        _visit(child)

        _visit(pat)
        _visit(rew)
        new_rule["mapping"] = mapping
        return new_rule

    @staticmethod
    def _promote_single_source_projection(query: QueryNode, mapping: Dict[str, str], projection_sets: Dict[str, str]) -> None:
        select_clause = RuleGeneratorV2._first_clause(query, NodeType.SELECT)
        from_clause = RuleGeneratorV2._first_clause(query, NodeType.FROM)
        where_clause = RuleGeneratorV2._first_clause(query, NodeType.WHERE)
        if not isinstance(select_clause, SelectNode) or not isinstance(from_clause, FromNode) or not isinstance(where_clause, WhereNode):
            return
        if len(select_clause.children) != 1 or len(from_clause.children) != 1:
            return
        if any(
            RuleGeneratorV2._query_has_clause(query, clause)
            for clause in (NodeType.GROUP_BY, NodeType.HAVING, NodeType.ORDER_BY, NodeType.LIMIT, NodeType.OFFSET)
        ):
            return
        select_item = select_clause.children[0]
        from_item = from_clause.children[0]
        if not (isinstance(select_item, ColumnNode) and RuleGeneratorV2._node_is_fully_variablized_column(select_item)):
            return
        if not (
            (isinstance(from_item, TableNode) and isinstance(from_item.name, str) and RuleGeneratorV2._is_placeholder_name(from_item.name))
            or isinstance(from_item, SubqueryNode)
        ):
            return

        select_sql = RuleGeneratorV2.deparse(copy.deepcopy(select_item))
        from_sql = RuleGeneratorV2.deparse(copy.deepcopy(from_item))
        key = f"{select_sql} FROM {from_sql}"
        set_name = projection_sets.get(key)
        if set_name is None:
            mapping, set_name, _placeholder_token = RuleGeneratorV2._find_next_set_variable(mapping)
            projection_sets[key] = set_name
        select_clause.children = [SetVariableNode(set_name)]

    @staticmethod
    def _normalize_join_elimination_rule(rule: Dict[str, object]) -> Optional[Dict[str, object]]:
        p0 = copy.deepcopy(rule.get("pattern_ast"))
        r0 = copy.deepcopy(rule.get("rewrite_ast"))
        if not isinstance(p0, QueryNode) or not isinstance(r0, QueryNode):
            return None
        if RuleGeneratorV2._from_source_count(p0) != RuleGeneratorV2._from_source_count(r0) + 1:
            return None

        pat = p0
        rew = r0
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode):
            return None

        select = RuleGeneratorV2._first_clause(pat, NodeType.SELECT)
        original_select = RuleGeneratorV2._first_clause(p0, NodeType.SELECT)
        rewrite_from_count = RuleGeneratorV2._from_source_count(r0)
        if isinstance(original_select, SelectNode) and len(original_select.children) == 1:
            child = original_select.children[0]
            if isinstance(child, ColumnNode) and child.name == "*":
                rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(pat, NodeType.SELECT)
                rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(rule["pattern_ast"], NodeType.WHERE)  # type: ignore[arg-type]
                rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(rew, NodeType.SELECT)
                rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(rule["rewrite_ast"], NodeType.WHERE)  # type: ignore[arg-type]
            elif isinstance(child, FunctionNode) and child.name.upper() == "COUNT":
                rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(pat, NodeType.WHERE)
                rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(rew, NodeType.WHERE)
            elif isinstance(child, ColumnNode) and rewrite_from_count == 1:
                pass
        elif isinstance(original_select, SelectNode):
            if all(isinstance(c, ColumnNode) and c.alias for c in original_select.children):
                mapping = copy.deepcopy(rule["mapping"])
                if not isinstance(mapping, dict):
                    return None
                mapping, set_name, _tok = RuleGeneratorV2._find_next_set_variable(mapping)
                rule["mapping"] = mapping
                rule["pattern_ast"] = copy.deepcopy(pat)
                rule["rewrite_ast"] = copy.deepcopy(rew)
                pat_sel = RuleGeneratorV2._first_clause(rule["pattern_ast"], NodeType.SELECT)  # type: ignore[arg-type]
                rew_sel = RuleGeneratorV2._first_clause(rule["rewrite_ast"], NodeType.SELECT)  # type: ignore[arg-type]
                if isinstance(pat_sel, SelectNode):
                    pat_sel.children = [SetVariableNode(set_name)]
                if isinstance(rew_sel, SelectNode):
                    rew_sel.children = [SetVariableNode(set_name)]
                rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(rule["pattern_ast"], NodeType.WHERE)  # type: ignore[arg-type]
                rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(rule["rewrite_ast"], NodeType.WHERE)  # type: ignore[arg-type]
            else:
                return None

        rule["pattern"] = RuleGeneratorV2.deparse(rule["pattern_ast"])  # type: ignore[index]
        rule["rewrite"] = RuleGeneratorV2.deparse(rule["rewrite_ast"])  # type: ignore[index]
        return rule

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
        count_join_filter_rule = RuleGeneratorV2.generalize_count_join_filter(rule)
        if count_join_filter_rule is not rule:
            count_join_filter_rule["_terminal_generalization"] = True
            return count_join_filter_rule

        join_elimination_rule = RuleGeneratorV2.generalize_join_elimination(rule)
        if join_elimination_rule is not rule:
            join_elimination_rule["_terminal_generalization"] = True
            return join_elimination_rule

        self_join_projection_rule = RuleGeneratorV2.generalize_self_join_projection(rule)
        if self_join_projection_rule is not rule:
            return self_join_projection_rule

        case_when_rule = RuleGeneratorV2.generalize_case_when_branches(rule)
        if case_when_rule is not rule:
            return case_when_rule

        return RuleGeneratorV2._generalize_subtrees_core(rule)

    @staticmethod
    def _generalize_subtrees_core(rule: Dict[str, object]) -> Dict[str, object]:

        new_rule = copy.deepcopy(rule)
        pattern_ast = new_rule.get("pattern_ast")
        rewrite_ast = new_rule.get("rewrite_ast")
        if not isinstance(pattern_ast, Node) or not isinstance(rewrite_ast, Node):
            raise TypeError("rule ASTs must be Node instances")
        for subtree in RuleGeneratorV2.subtrees(pattern_ast, rewrite_ast):
            # Keep select-item column subtrees available to the helper API, but
            # don't let the full-rule generalization loop collapse projections
            # into set variables too early.
            if isinstance(subtree, ColumnNode):
                continue
            if RuleGeneratorV2._should_preserve_where_predicate_subtree(pattern_ast, rewrite_ast, subtree):
                continue
            new_rule = RuleGeneratorV2.variablize_subtree(new_rule, subtree)
            pattern_ast = new_rule["pattern_ast"]  # type: ignore[assignment]
            rewrite_ast = new_rule["rewrite_ast"]  # type: ignore[assignment]
        return new_rule

    @staticmethod
    def generalize_variables(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        grouped_projection_rule = RuleGeneratorV2.generalize_grouped_projection(new_rule)
        if grouped_projection_rule is not new_rule:
            new_rule = grouped_projection_rule

        return RuleGeneratorV2._generalize_variables_core(new_rule)

    @staticmethod
    def _generalize_variables_core(rule: Dict[str, object]) -> Dict[str, object]:
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
        where_fragment_rule = RuleGeneratorV2._generalize_where_fragment(new_rule)
        if where_fragment_rule is not None:
            return where_fragment_rule
        matched_branches = RuleGeneratorV2._matched_internal_branches(pattern_ast, rewrite_ast)
        if (
            len(matched_branches) == 1
            and matched_branches[0].get("key") == "where"
            and isinstance(pattern_ast, QueryNode)
            and RuleGeneratorV2._first_clause(pattern_ast, NodeType.SELECT) is not None
            and RuleGeneratorV2._first_clause(pattern_ast, NodeType.FROM) is not None
        ):
            return new_rule
        for branch in matched_branches:
            new_rule = RuleGeneratorV2.drop_branch(new_rule, branch)
            pattern_ast = new_rule["pattern_ast"]  # type: ignore[assignment]
            rewrite_ast = new_rule["rewrite_ast"]  # type: ignore[assignment]
        return new_rule

    @staticmethod
    def _generalize_where_fragment(rule: Dict[str, object]) -> Optional[Dict[str, object]]:
        pat = rule.get("pattern_ast")
        rew = rule.get("rewrite_ast")
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode):
            return None

        extra_clauses = (
            NodeType.GROUP_BY,
            NodeType.HAVING,
            NodeType.ORDER_BY,
            NodeType.LIMIT,
            NodeType.OFFSET,
        )
        if any(
            RuleGeneratorV2._query_has_clause(pat, clause) or RuleGeneratorV2._query_has_clause(rew, clause)
            for clause in extra_clauses
        ):
            return None

        pat_select = RuleGeneratorV2._first_clause(pat, NodeType.SELECT)
        rew_select = RuleGeneratorV2._first_clause(rew, NodeType.SELECT)
        pat_from = RuleGeneratorV2._first_clause(pat, NodeType.FROM)
        rew_from = RuleGeneratorV2._first_clause(rew, NodeType.FROM)
        pat_where = RuleGeneratorV2._first_clause(pat, NodeType.WHERE)
        rew_where = RuleGeneratorV2._first_clause(rew, NodeType.WHERE)
        if not (
            isinstance(pat_select, SelectNode)
            and isinstance(rew_select, SelectNode)
            and isinstance(pat_from, FromNode)
            and isinstance(rew_from, FromNode)
            and isinstance(pat_where, WhereNode)
            and isinstance(rew_where, WhereNode)
        ):
            return None

        pat_shell = RuleGeneratorV2._query_without_clause(pat, NodeType.WHERE)
        rew_shell = RuleGeneratorV2._query_without_clause(rew, NodeType.WHERE)
        if not isinstance(pat_shell, QueryNode) or not isinstance(rew_shell, QueryNode):
            return None
        if RuleGeneratorV2.deparse(copy.deepcopy(pat_shell)) != RuleGeneratorV2.deparse(copy.deepcopy(rew_shell)):
            return None
        if len(pat_where.children) != 1 or len(rew_where.children) != 1:
            return None

        pat_condition = pat_where.children[0]
        rew_condition = rew_where.children[0]
        new_rule = copy.deepcopy(rule)
        if (
            isinstance(pat_condition, OperatorNode)
            and isinstance(rew_condition, OperatorNode)
            and pat_condition.name == "="
            and rew_condition.name == "="
            and len(pat_condition.children) == 2
            and len(rew_condition.children) == 2
            and RuleGeneratorV2.deparse(copy.deepcopy(pat_condition.children[1]))
            == RuleGeneratorV2.deparse(copy.deepcopy(rew_condition.children[1]))
        ):
            new_rule["pattern_ast"] = copy.deepcopy(pat_condition.children[0])
            new_rule["rewrite_ast"] = copy.deepcopy(rew_condition.children[0])
        else:
            new_rule["pattern_ast"] = copy.deepcopy(pat_condition)
            new_rule["rewrite_ast"] = copy.deepcopy(rew_condition)
        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def _generalize_self_join_projection(rule: Dict[str, object]) -> Optional[Dict[str, object]]:
        pat = rule.get("pattern_ast")
        rew = rule.get("rewrite_ast")
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode):
            return None
        if RuleGeneratorV2._from_source_count(pat) != 2 or RuleGeneratorV2._from_source_count(rew) != 1:
            return None
        p_from = RuleGeneratorV2._first_clause(pat, NodeType.FROM)
        r_from = RuleGeneratorV2._first_clause(rew, NodeType.FROM)
        if not isinstance(p_from, FromNode) or not isinstance(r_from, FromNode):
            return None
        if len(p_from.children) != 2 or len(r_from.children) != 1:
            return None
        if not all(isinstance(c, TableNode) for c in p_from.children) or not isinstance(r_from.children[0], TableNode):
            return None

        pat_sel = RuleGeneratorV2._first_clause(pat, NodeType.SELECT)
        rew_sel = RuleGeneratorV2._first_clause(rew, NodeType.SELECT)
        if not isinstance(pat_sel, SelectNode) or not isinstance(rew_sel, SelectNode):
            return None

        prefix_len = 0
        while (
            prefix_len < len(pat_sel.children)
            and prefix_len < len(rew_sel.children)
            and RuleGeneratorV2.deparse(copy.deepcopy(pat_sel.children[prefix_len]))
            == RuleGeneratorV2.deparse(copy.deepcopy(rew_sel.children[prefix_len]))
        ):
            prefix_len += 1
        if prefix_len < 1 or prefix_len >= len(pat_sel.children):
            return None

        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule["mapping"])
        if not isinstance(mapping, dict):
            return None
        mapping, set_name, _tok = RuleGeneratorV2._find_next_set_variable(mapping)
        new_rule["mapping"] = mapping
        pat2 = new_rule["pattern_ast"]
        rew2 = new_rule["rewrite_ast"]
        if not isinstance(pat2, QueryNode) or not isinstance(rew2, QueryNode):
            return None
        pat_sel2 = RuleGeneratorV2._first_clause(pat2, NodeType.SELECT)
        rew_sel2 = RuleGeneratorV2._first_clause(rew2, NodeType.SELECT)
        if not isinstance(pat_sel2, SelectNode) or not isinstance(rew_sel2, SelectNode):
            return None
        pat_sel2.children = [SetVariableNode(set_name)] + pat_sel2.children[prefix_len:]
        rew_sel2.children = [SetVariableNode(set_name)] + rew_sel2.children[prefix_len:]
        new_rule["pattern_ast"] = RuleGeneratorV2._query_without_clause(pat2, NodeType.FROM)
        new_rule["rewrite_ast"] = RuleGeneratorV2._query_without_clause(rew2, NodeType.FROM)
        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def generalize_self_join_projection(rule: Dict[str, object]) -> Dict[str, object]:
        generalized_rule = RuleGeneratorV2._generalize_self_join_projection(rule)
        if generalized_rule is None:
            return rule
        return generalized_rule

    @staticmethod
    def unwrap_matching_subquery(rule: Dict[str, object]) -> Dict[str, object]:
        new_rule = copy.deepcopy(rule)
        pattern_ast = new_rule.get("pattern_ast")
        rewrite_ast = new_rule.get("rewrite_ast")
        if not isinstance(pattern_ast, QueryNode) or not isinstance(rewrite_ast, QueryNode):
            return new_rule
        pattern_from = RuleGeneratorV2._first_clause(pattern_ast, NodeType.FROM)
        rewrite_from = RuleGeneratorV2._first_clause(rewrite_ast, NodeType.FROM)
        if not isinstance(pattern_from, FromNode) or not isinstance(rewrite_from, FromNode):
            return new_rule
        if len(pattern_from.children) != 1 or len(rewrite_from.children) != 1:
            return new_rule
        pattern_source = pattern_from.children[0]
        rewrite_source = rewrite_from.children[0]
        if not isinstance(pattern_source, SubqueryNode) or not isinstance(rewrite_source, SubqueryNode):
            return new_rule
        if pattern_source.alias != rewrite_source.alias:
            return new_rule
        pattern_inner = next(iter(pattern_source.children), None)
        rewrite_inner = next(iter(rewrite_source.children), None)
        if not isinstance(pattern_inner, Node) or not isinstance(rewrite_inner, Node):
            return new_rule
        new_rule["pattern_ast"] = copy.deepcopy(pattern_inner)
        new_rule["rewrite_ast"] = copy.deepcopy(rewrite_inner)
        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def generalize_wrapper_projection(rule: Dict[str, object]) -> Dict[str, object]:
        source_pattern = rule.get("source_pattern_ast")
        source_rewrite = rule.get("source_rewrite_ast")
        pattern_ast = rule.get("pattern_ast")
        if not isinstance(source_pattern, QueryNode) or not isinstance(source_rewrite, QueryNode):
            return rule
        if not isinstance(pattern_ast, QueryNode):
            return rule
        if RuleGeneratorV2._star_wrapper_depth(source_pattern) != RuleGeneratorV2._star_wrapper_depth(source_rewrite) + 1:
            return rule

        new_rule = copy.deepcopy(rule)
        new_pattern = new_rule.get("pattern_ast")
        mapping = copy.deepcopy(new_rule.get("mapping"))
        if not isinstance(new_pattern, QueryNode) or not isinstance(mapping, dict):
            return rule

        changed = RuleGeneratorV2._promote_wrapper_projection_in_query(new_pattern, mapping)
        if not changed:
            return rule

        new_rule["mapping"] = mapping
        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def generalize_grouped_projection(rule: Dict[str, object]) -> Dict[str, object]:
        pat = rule.get("pattern_ast")
        rew = rule.get("rewrite_ast")
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode):
            return rule

        pat_select = RuleGeneratorV2._first_clause(pat, NodeType.SELECT)
        rew_select = RuleGeneratorV2._first_clause(rew, NodeType.SELECT)
        rew_group = RuleGeneratorV2._first_clause(rew, NodeType.GROUP_BY)
        if not isinstance(pat_select, SelectNode) or not isinstance(rew_select, SelectNode) or not isinstance(rew_group, GroupByNode):
            return rule
        if not getattr(pat_select, "distinct", False):
            return rule
        if len(pat_select.children) != 1 or len(rew_select.children) != 1 or len(rew_group.children) != 1:
            return rule
        pat_item = pat_select.children[0]
        rew_item = rew_select.children[0]
        group_item = rew_group.children[0]
        if not (
            isinstance(pat_item, ColumnNode)
            and isinstance(rew_item, ColumnNode)
            and isinstance(group_item, ColumnNode)
            and pat_item == rew_item
            and rew_item == group_item
            and RuleGeneratorV2._node_is_fully_variablized_column(pat_item)
        ):
            return rule

        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule.get("mapping"))
        new_pat = new_rule.get("pattern_ast")
        new_rew = new_rule.get("rewrite_ast")
        if not isinstance(mapping, dict) or not isinstance(new_pat, QueryNode) or not isinstance(new_rew, QueryNode):
            return rule
        mapping, external_name, _placeholder_token = RuleGeneratorV2._find_next_element_variable(mapping)
        new_rule["mapping"] = mapping

        new_pat_select = RuleGeneratorV2._first_clause(new_pat, NodeType.SELECT)
        new_rew_select = RuleGeneratorV2._first_clause(new_rew, NodeType.SELECT)
        new_rew_group = RuleGeneratorV2._first_clause(new_rew, NodeType.GROUP_BY)
        if not isinstance(new_pat_select, SelectNode) or not isinstance(new_rew_select, SelectNode) or not isinstance(new_rew_group, GroupByNode):
            return rule

        replacement = ColumnNode(external_name)
        new_pat_select.children = [copy.deepcopy(replacement)]
        new_rew_select.children = [copy.deepcopy(replacement)]
        new_rew_group.children = [copy.deepcopy(replacement)]
        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def generalize_case_when_branches(rule: Dict[str, object]) -> Dict[str, object]:
        pat = rule.get("pattern_ast")
        rew = rule.get("rewrite_ast")
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode):
            return rule

        pat_where = RuleGeneratorV2._first_clause(pat, NodeType.WHERE)
        rew_where = RuleGeneratorV2._first_clause(rew, NodeType.WHERE)
        if not isinstance(pat_where, WhereNode) or not isinstance(rew_where, WhereNode):
            return rule
        if len(pat_where.children) != 1 or len(rew_where.children) != 1:
            return rule

        pat_expr = pat_where.children[0]
        rew_expr = rew_where.children[0]
        if not (isinstance(pat_expr, OperatorNode) and pat_expr.name.upper() == "OR"):
            return rule
        if not (isinstance(rew_expr, OperatorNode) and rew_expr.name == "=" and len(rew_expr.children) == 2):
            return rule

        case_node = rew_expr.children[1] if isinstance(rew_expr.children[1], CaseNode) else rew_expr.children[0] if isinstance(rew_expr.children[0], CaseNode) else None
        if not isinstance(case_node, CaseNode):
            return rule

        def _flatten_or(node: Node) -> List[Node]:
            if isinstance(node, OperatorNode) and node.name.upper() == "OR":
                out: List[Node] = []
                for child in node.children:
                    if isinstance(child, Node):
                        out.extend(_flatten_or(child))
                return out
            return [node]

        branches = _flatten_or(pat_expr)
        when_nodes = [child for child in case_node.children if isinstance(child, WhenThenNode)]
        if len(branches) != len(when_nodes) or not branches:
            return rule
        if any(len(when.children) < 1 for when in when_nodes):
            return rule
        if any(
            RuleGeneratorV2._fingerPrint(RuleGeneratorV2.deparse(copy.deepcopy(branch)))
            != RuleGeneratorV2._fingerPrint(RuleGeneratorV2.deparse(copy.deepcopy(when.children[0])))
            for branch, when in zip(branches, when_nodes)
        ):
            return rule

        new_rule = copy.deepcopy(rule)
        mapping = copy.deepcopy(new_rule.get("mapping"))
        new_pat = new_rule.get("pattern_ast")
        new_rew = new_rule.get("rewrite_ast")
        if not isinstance(mapping, dict) or not isinstance(new_pat, QueryNode) or not isinstance(new_rew, QueryNode):
            return rule

        new_pat_where = RuleGeneratorV2._first_clause(new_pat, NodeType.WHERE)
        new_rew_where = RuleGeneratorV2._first_clause(new_rew, NodeType.WHERE)
        if not isinstance(new_pat_where, WhereNode) or not isinstance(new_rew_where, WhereNode):
            return rule
        new_pat_expr = new_pat_where.children[0]
        new_rew_expr = new_rew_where.children[0]
        if not (isinstance(new_pat_expr, OperatorNode) and isinstance(new_rew_expr, OperatorNode)):
            return rule
        new_case = new_rew_expr.children[1] if isinstance(new_rew_expr.children[1], CaseNode) else new_rew_expr.children[0] if isinstance(new_rew_expr.children[0], CaseNode) else None
        if not isinstance(new_case, CaseNode):
            return rule
        case_value = new_rew_expr.children[0] if new_case is new_rew_expr.children[1] else new_rew_expr.children[1]

        new_when_nodes = [child for child in new_case.children if isinstance(child, WhenThenNode)]
        replacements: List[Node] = []
        for idx, when in enumerate(new_when_nodes):
            mapping, external_name, _placeholder_token = RuleGeneratorV2._find_next_element_variable(mapping)
            replacement = ElementVariableNode(external_name)
            replacements.append(copy.deepcopy(replacement))
            when.children[0] = copy.deepcopy(replacement)
            when.when = copy.deepcopy(replacement)
            when.children[1] = copy.deepcopy(case_value)
            when.then = copy.deepcopy(case_value)
        rebuilt_or = replacements[0]
        for replacement in replacements[1:]:
            rebuilt_or = OperatorNode(rebuilt_or, "OR", replacement)
        new_pat_where.children = [rebuilt_or]

        new_rule["mapping"] = mapping
        new_rule["pattern"] = RuleGeneratorV2.deparse(new_rule["pattern_ast"])  # type: ignore[index]
        new_rule["rewrite"] = RuleGeneratorV2.deparse(new_rule["rewrite_ast"])  # type: ignore[index]
        return new_rule

    @staticmethod
    def generalize_distinct_lookup_rule(rule: Dict[str, object]) -> Dict[str, object]:
        pat = rule.get("pattern_ast")
        rew = rule.get("rewrite_ast")
        mapping = copy.deepcopy(rule.get("mapping"))
        if not isinstance(pat, QueryNode) or not isinstance(rew, QueryNode) or not isinstance(mapping, dict):
            return rule

        pat_select = RuleGeneratorV2._first_clause(pat, NodeType.SELECT)
        rew_select = RuleGeneratorV2._first_clause(rew, NodeType.SELECT)
        pat_from = RuleGeneratorV2._first_clause(pat, NodeType.FROM)
        rew_from = RuleGeneratorV2._first_clause(rew, NodeType.FROM)
        pat_where = RuleGeneratorV2._first_clause(pat, NodeType.WHERE)
        rew_where = RuleGeneratorV2._first_clause(rew, NodeType.WHERE)
        pat_order = RuleGeneratorV2._first_clause(pat, NodeType.ORDER_BY)
        if not (
            isinstance(pat_select, SelectNode)
            and isinstance(rew_select, SelectNode)
            and isinstance(pat_from, FromNode)
            and isinstance(rew_from, FromNode)
            and isinstance(pat_where, WhereNode)
            and isinstance(rew_where, WhereNode)
            and isinstance(pat_order, OrderByNode)
        ):
            return rule
        if len(pat_select.children) != 6 or len(rew_select.children) != 5:
            return rule
        if pat_select.distinct_on is None or len(pat_from.children) != 1 or len(rew_from.children) != 1:
            return rule
        if not isinstance(pat_from.children[0], JoinNode) or not isinstance(rew_from.children[0], TableNode):
            return rule

        def _flatten_and(node: Node) -> List[Node]:
            if isinstance(node, OperatorNode) and node.name.upper() == "AND":
                out: List[Node] = []
                for child in node.children:
                    if isinstance(child, Node):
                        out.extend(_flatten_and(child))
                return out
            return [node]

        pat_preds = _flatten_and(pat_where.children[0]) if pat_where.children else []
        rew_preds = _flatten_and(rew_where.children[0]) if rew_where.children else []
        if len(pat_preds) != 4 or len(rew_preds) != 2:
            return rule

        main_table_sql = RuleGeneratorV2.deparse(copy.deepcopy(rew_from.children[0]))
        join_chain = pat_from.children[0]
        if not isinstance(join_chain, JoinNode) or not isinstance(join_chain.left_table, JoinNode):
            return rule
        join1 = join_chain.left_table
        join2 = join_chain
        join1_table_sql = RuleGeneratorV2.deparse(copy.deepcopy(join1.right_table))
        join2_table_sql = RuleGeneratorV2.deparse(copy.deepcopy(join2.right_table))
        if not isinstance(join1.on_condition, Node) or not isinstance(join2.on_condition, Node):
            return rule

        select_items = pat_select.children[:5]
        if not all(isinstance(item, Node) for item in select_items):
            return rule
        distinct_expr_sql = RuleGeneratorV2.deparse(copy.deepcopy(pat_select.distinct_on))
        if distinct_expr_sql.startswith("(") and distinct_expr_sql.endswith(")"):
            distinct_expr_sql = distinct_expr_sql[1:-1]
        sel1_sql = RuleGeneratorV2.deparse(copy.deepcopy(select_items[0]))
        sel2_sql = RuleGeneratorV2.deparse(copy.deepcopy(select_items[1]))
        join1_col_sql = RuleGeneratorV2.deparse(copy.deepcopy(select_items[3].children[0])) if isinstance(select_items[3], FunctionNode) and select_items[3].children else None
        if not isinstance(join1_col_sql, str):
            return rule

        def _strip_quoted_placeholder(sql: str) -> str:
            if len(sql) >= 2 and sql[0] == "'" and sql[-1] == "'" and RuleGeneratorV2._is_placeholder_name(sql[1:-1]):
                return f"<{sql[1:-1]}>"
            return sql

        default_sql = _strip_quoted_placeholder(RuleGeneratorV2.deparse(copy.deepcopy(select_items[3].children[1]))) if isinstance(select_items[3], FunctionNode) and len(select_items[3].children) > 1 else None
        join2_list_sql = RuleGeneratorV2.deparse(copy.deepcopy(pat_preds[2]))
        pref_pred_sql = RuleGeneratorV2.deparse(copy.deepcopy(pat_preds[3]))
        if not isinstance(default_sql, str):
            return rule

        join2_limit_var = None
        if isinstance(pat_preds[2], OperatorNode) and pat_preds[2].name.upper() == "IN" and len(pat_preds[2].children) == 2:
            list_node = pat_preds[2].children[1]
            if isinstance(list_node, Node) and hasattr(list_node, "children"):
                list_children = [child for child in getattr(list_node, "children", []) if isinstance(child, Node)]
                if len(list_children) >= 2:
                    join2_limit_var = RuleGeneratorV2.deparse(copy.deepcopy(list_children[1]))
        if join2_limit_var is None:
            join2_limit_var = "<x1>"

        mapping, distinct_var, _ = RuleGeneratorV2._find_next_element_variable(mapping)
        mapping, sel1_var, _ = RuleGeneratorV2._find_next_element_variable(mapping)
        mapping, sel2_var, _ = RuleGeneratorV2._find_next_element_variable(mapping)
        mapping, default_var, _ = RuleGeneratorV2._find_next_element_variable(mapping)
        mapping, join2_proj_set, _ = RuleGeneratorV2._find_next_set_variable(mapping)
        mapping, join1_on_set, _ = RuleGeneratorV2._find_next_set_variable(mapping)
        mapping, join2_on_set, _ = RuleGeneratorV2._find_next_set_variable(mapping)
        mapping, base_filter_set, _ = RuleGeneratorV2._find_next_set_variable(mapping)
        mapping, pref_filter_set, _ = RuleGeneratorV2._find_next_set_variable(mapping)

        pattern_sql = (
            f"SELECT DISTINCT ON (<{distinct_var}>) <{sel1_var}>, <{sel2_var}>, <{distinct_var}>, "
            f"COALESCE({join1_col_sql}, <{default_var}>), <<{join2_proj_set}>> "
            f"FROM {main_table_sql} LEFT JOIN {join1_table_sql} ON <<{join1_on_set}>> "
            f"LEFT JOIN {join2_table_sql} ON <<{join2_on_set}>> "
            f"WHERE <<{base_filter_set}>> AND {join2_list_sql} AND <<{pref_filter_set}>> "
            f"ORDER BY {distinct_expr_sql} DESC"
        )
        rewrite_sql = (
            f"SELECT <{sel1_var}>, <{sel2_var}>, <{distinct_var}>, "
            f"COALESCE((SELECT {join1_col_sql} FROM {join1_table_sql} WHERE <<{join1_on_set}>> AND <<{pref_filter_set}>> LIMIT {join2_limit_var}), <{default_var}>), "
            f"(SELECT <<{join2_proj_set}>> FROM {join2_table_sql} WHERE <<{join2_on_set}>> AND {join2_list_sql} LIMIT {join2_limit_var}) "
            f"FROM {main_table_sql} WHERE <<{base_filter_set}>>"
        )

        new_rule = copy.deepcopy(rule)
        new_rule["mapping"] = mapping
        new_rule["pattern"] = pattern_sql
        new_rule["rewrite"] = rewrite_sql
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
        return list(found)

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
    def _matched_internal_branches(pattern_ast: Node, rewrite_ast: Node) -> List[Dict[str, object]]:
        pattern_branches = RuleGeneratorV2._branch_entries_of_ast(pattern_ast)
        rewrite_branches = RuleGeneratorV2._branch_entries_of_ast(rewrite_ast)
        out: List[Dict[str, object]] = []
        remaining = list(rewrite_branches)
        while pattern_branches:
            pb_public, pb_target = pattern_branches.pop()
            for idx, (_rb_public, rb_target) in enumerate(remaining):
                if RuleGeneratorV2._branch_targets_match(pb_target, rb_target):
                    if pb_public["key"] in {"and", "or"}:
                        out.append({"key": pb_public["key"], "value": pb_target})
                    else:
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
            return RuleGeneratorV2._fingerPrint(ps) == RuleGeneratorV2._fingerPrint(rs)
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
    def _is_rewrite_identity(rule: Dict[str, object]) -> bool:
        p = rule.get("pattern")
        r = rule.get("rewrite")
        if not isinstance(p, str) or not isinstance(r, str):
            return False
        return RuleGeneratorV2._fingerPrint(p) == RuleGeneratorV2._fingerPrint(r)

    @staticmethod
    def _is_select_expression_input(sql: str) -> bool:
        text = sql.strip()
        if not text.upper().startswith("SELECT "):
            return False
        top_level_keywords = RuleGeneratorV2._top_level_keywords(text)
        return "SELECT" in top_level_keywords and "FROM" not in top_level_keywords and "WHERE" not in top_level_keywords

    @staticmethod
    def _top_level_keywords(sql: str) -> Set[str]:
        keywords: Set[str] = set()
        depth = 0
        in_single_quote = False
        i = 0
        while i < len(sql):
            ch = sql[i]
            if ch == "'":
                in_single_quote = not in_single_quote
                i += 1
                continue
            if in_single_quote:
                i += 1
                continue
            if ch == "(":
                depth += 1
                i += 1
                continue
            if ch == ")":
                depth = max(0, depth - 1)
                i += 1
                continue
            if depth == 0 and (ch.isalpha() or ch == "_"):
                j = i + 1
                while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                    j += 1
                token = sql[i:j].upper()
                if token in {"SELECT", "FROM", "WHERE"}:
                    keywords.add(token)
                i = j
                continue
            i += 1
        return keywords

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
    def _star_wrapper_depth(query: QueryNode) -> int:
        depth = 0
        current: Optional[QueryNode] = query
        while isinstance(current, QueryNode) and RuleGeneratorV2._is_star_wrapper_query(current):
            depth += 1
            from_clause = RuleGeneratorV2._first_clause(current, NodeType.FROM)
            if not isinstance(from_clause, FromNode) or len(from_clause.children) != 1:
                break
            source = from_clause.children[0]
            if not isinstance(source, SubqueryNode):
                break
            inner = next(iter(source.children), None)
            current = inner if isinstance(inner, QueryNode) else None
        return depth

    @staticmethod
    def _is_star_wrapper_query(query: QueryNode) -> bool:
        select_clause = RuleGeneratorV2._first_clause(query, NodeType.SELECT)
        from_clause = RuleGeneratorV2._first_clause(query, NodeType.FROM)
        if not isinstance(select_clause, SelectNode) or not isinstance(from_clause, FromNode):
            return False
        if len(select_clause.children) != 1 or len(from_clause.children) != 1:
            return False
        select_child = select_clause.children[0]
        if not (isinstance(select_child, ColumnNode) and select_child.name == "*"):
            return False
        return isinstance(from_clause.children[0], SubqueryNode)

    @staticmethod
    def _promote_wrapper_projection_in_query(query: QueryNode, mapping: Dict[str, str]) -> bool:
        if RuleGeneratorV2._query_has_clause(query, NodeType.GROUP_BY) or RuleGeneratorV2._query_has_clause(query, NodeType.HAVING):
            return False
        if RuleGeneratorV2._query_has_clause(query, NodeType.ORDER_BY) or RuleGeneratorV2._query_has_clause(query, NodeType.LIMIT):
            return False
        if RuleGeneratorV2._query_has_clause(query, NodeType.OFFSET):
            return False

        select_clause = RuleGeneratorV2._first_clause(query, NodeType.SELECT)
        from_clause = RuleGeneratorV2._first_clause(query, NodeType.FROM)
        if isinstance(select_clause, SelectNode) and isinstance(from_clause, FromNode) and len(from_clause.children) == 1:
            child = select_clause.children[0] if len(select_clause.children) == 1 else None
            if RuleGeneratorV2._is_wrapper_projection_placeholder(child):
                mapping, set_name, _placeholder_token = RuleGeneratorV2._find_next_set_variable(mapping)
                select_clause.children = [SetVariableNode(set_name)]
                return True

        if not isinstance(from_clause, FromNode):
            return False
        for source in from_clause.children:
            if isinstance(source, SubqueryNode):
                inner = next(iter(source.children), None)
                if isinstance(inner, QueryNode) and RuleGeneratorV2._promote_wrapper_projection_in_query(inner, mapping):
                    return True
        return False

    @staticmethod
    def _is_wrapper_projection_placeholder(node: Optional[Node]) -> bool:
        if isinstance(node, ElementVariableNode):
            return True
        if isinstance(node, ColumnNode):
            return RuleGeneratorV2._node_is_fully_variablized_column(node)
        return False

    @staticmethod
    def _from_source_count(query: QueryNode) -> int:
        from_clause = RuleGeneratorV2._first_clause(query, NodeType.FROM)
        if not isinstance(from_clause, FromNode):
            return 0
        count = 0
        for child in from_clause.children:
            if isinstance(child, JoinNode):
                count += 1 + RuleGeneratorV2._join_extra_source_count(child)
            else:
                count += 1
        return count

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
        for node in RuleGeneratorV2._walk(ast):
            if isinstance(node, SelectNode):
                ev_children = [c for c in node.children if isinstance(c, ElementVariableNode)]
                if ev_children and all(c.name in variable_set for c in ev_children):
                    if len(ev_children) == len(node.children):
                        node.children = [SetVariableNode(set_name)]
                continue

            if isinstance(node, WhereNode):
                if len(node.children) == 1 and isinstance(node.children[0], ElementVariableNode):
                    if node.children[0].name in variable_set:
                        node.children = [SetVariableNode(set_name)]
                continue

            if isinstance(node, JoinNode) and node.on_condition is not None:
                oc = node.on_condition
                if isinstance(oc, ElementVariableNode) and oc.name in variable_set:
                    replacement = SetVariableNode(set_name)
                    node.on_condition = replacement
                    if len(node.children) > 2:
                        node.children[2] = replacement
                continue

            if isinstance(node, LimitNode) and isinstance(node.limit, str) and node.limit in variable_set:
                node.limit = set_name

            if isinstance(node, OperatorNode) and node.name.lower() == "and":
                new_children: List[Node] = []
                changed = False
                for child in node.children:
                    if isinstance(child, ElementVariableNode) and child.name in variable_set:
                        new_children.append(SetVariableNode(set_name))
                        changed = True
                    else:
                        new_children.append(child)
                if changed:
                    node.children = new_children
        return ast

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
        for node in RuleGeneratorV2._walk(ast):
            if isinstance(node, ColumnNode) and node.name == column:
                node.name = external_name
        return ast

    @staticmethod
    def _replace_table_in_ast(
        ast: Node,
        target_value: str,
        target_name: str,
        placeholder_token: str,
    ) -> Node:
        match_aliases: Set[str] = set()
        for node in RuleGeneratorV2._walk(ast):
            if not isinstance(node, TableNode):
                continue
            current_alias = node.alias if isinstance(node.alias, str) else node.name
            if node.name == target_value and current_alias == target_name:
                match_aliases.add(current_alias)
                node.name = placeholder_token
                node.alias = None

        if not match_aliases:
            return ast

        for node in RuleGeneratorV2._walk(ast):
            if isinstance(node, ColumnNode) and isinstance(node.parent_alias, str) and node.parent_alias in match_aliases:
                node.parent_alias = placeholder_token
        return ast

    @staticmethod
    def _replace_node_reference(root: Node, target: Node, replacement: Node) -> None:
        for node in RuleGeneratorV2._walk(root):
            children = getattr(node, "children", None)
            if isinstance(children, list):
                for idx, child in enumerate(children):
                    if child is target:
                        children[idx] = replacement
            elif isinstance(children, set):
                if target in children:
                    children.remove(target)
                    children.add(replacement)
        if root is target:
            raise ValueError("Cannot replace root node directly; expected nested target.")

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
        out: List[List[str]] = []
        for node in RuleGeneratorV2._walk(ast):
            if isinstance(node, SelectNode):
                names = [c.name for c in node.children if isinstance(c, ElementVariableNode)]
                if names:
                    out.append(names)
                continue

            if isinstance(node, OperatorNode) and node.name.lower() == "and":
                names = [c.name for c in node.children if isinstance(c, ElementVariableNode)]
                if names:
                    out.append(names)
                continue

            if isinstance(node, WhereNode) and len(node.children) == 1 and isinstance(node.children[0], ElementVariableNode):
                out.append([node.children[0].name])
                continue

            if isinstance(node, LimitNode) and isinstance(node.limit, str) and RuleGeneratorV2._is_placeholder_name(node.limit):
                out.append([node.limit])
                continue

            if isinstance(node, JoinNode) and node.on_condition is not None:
                oc = node.on_condition
                if isinstance(oc, ElementVariableNode):
                    out.append([oc.name])
                continue

        return out

    @staticmethod
    def _subtrees_of_ast(ast: Node) -> List[Node]:
        out: List[Node] = []
        seen: Set[str] = set()

        def _visit(node: Node, parent: Optional[Node] = None) -> None:
            if RuleGeneratorV2._is_subtree_candidate(node, parent):
                key = RuleGeneratorV2.deparse(node)
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
    def _is_subtree_candidate(node: Node, parent: Optional[Node] = None) -> bool:
        if isinstance(
            node,
            (
                QueryNode,
                CompoundQueryNode,
                CaseNode,
                FunctionNode,
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
            return isinstance(parent, SelectNode) and RuleGeneratorV2._node_is_fully_variablized_column(node)

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
    def _should_preserve_where_predicate_subtree(pattern_ast: Node, rewrite_ast: Node, subtree: Node) -> bool:
        if not isinstance(subtree, OperatorNode):
            return False
        if not isinstance(pattern_ast, QueryNode) or not isinstance(rewrite_ast, QueryNode):
            return False
        if RuleGeneratorV2._first_clause(pattern_ast, NodeType.FROM) is not None:
            return False
        if RuleGeneratorV2._first_clause(rewrite_ast, NodeType.FROM) is not None:
            return False

        pat_select = RuleGeneratorV2._first_clause(pattern_ast, NodeType.SELECT)
        rew_select = RuleGeneratorV2._first_clause(rewrite_ast, NodeType.SELECT)
        pat_where = RuleGeneratorV2._first_clause(pattern_ast, NodeType.WHERE)
        rew_where = RuleGeneratorV2._first_clause(rewrite_ast, NodeType.WHERE)
        if not (
            isinstance(pat_select, SelectNode)
            and isinstance(rew_select, SelectNode)
            and isinstance(pat_where, WhereNode)
            and isinstance(rew_where, WhereNode)
        ):
            return False
        if not any(isinstance(child, SetVariableNode) for child in pat_select.children):
            return False
        if not any(isinstance(child, SetVariableNode) for child in rew_select.children):
            return False
        return RuleGeneratorV2._ast_contains_subtree(pat_where, subtree) and RuleGeneratorV2._ast_contains_subtree(rew_where, subtree)

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
    def _dedupe_boolean_predicates(node: Node) -> Node:
        working = copy.deepcopy(node)

        def _visit(cur: Node) -> Node:
            children = getattr(cur, "children", None)
            if isinstance(children, list):
                new_children = []
                for child in children:
                    if isinstance(child, Node):
                        new_children.append(_visit(child))
                    else:
                        new_children.append(child)
                cur.children = new_children
            elif isinstance(children, set):
                new_children = set()
                for child in children:
                    if isinstance(child, Node):
                        new_children.add(_visit(child))
                    else:
                        new_children.add(child)  # type: ignore[arg-type]
                cur.children = new_children

            if isinstance(cur, OperatorNode) and cur.name.upper() in {"AND", "OR"}:
                deduped: List[Node] = []
                seen: Set[str] = set()
                for child in cur.children:
                    if not isinstance(child, Node):
                        continue
                    key = RuleGeneratorV2.deparse(copy.deepcopy(child))
                    if key in seen:
                        continue
                    seen.add(key)
                    deduped.append(child)
                cur.children = deduped
                if len(deduped) == 1:
                    return deduped[0]
            if isinstance(cur, JoinNode):
                cur.left_table = cur.children[0]  # type: ignore[assignment]
                cur.right_table = cur.children[1]  # type: ignore[assignment]
                cur.on_condition = cur.children[2] if len(cur.children) > 2 else None  # type: ignore[assignment]
            elif isinstance(cur, UnaryOperatorNode):
                cur.operand = cur.children[0]
            elif isinstance(cur, CompoundQueryNode):
                cur.left = cur.children[0]
                cur.right = cur.children[1]
            return cur

        return _visit(working)

    @staticmethod
    def _deparse_union_using_compound(node: CompoundQueryNode) -> Optional[str]:
        queries = RuleGeneratorV2._flatten_union_queries(node)
        if len(queries) < 2:
            return None
        rendered_queries = [RuleGeneratorV2._deparse_query_with_using(query) for query in queries]
        if any(part is None for part in rendered_queries):
            return None
        return "\nUNION\n".join(part for part in rendered_queries if isinstance(part, str))

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
    def _deparse_query_with_using(query: QueryNode) -> Optional[str]:
        select_clause = RuleGeneratorV2._first_clause(query, NodeType.SELECT)
        from_clause = RuleGeneratorV2._first_clause(query, NodeType.FROM)
        where_clause = RuleGeneratorV2._first_clause(query, NodeType.WHERE)
        if not isinstance(select_clause, SelectNode) or not isinstance(from_clause, FromNode):
            return None
        if len(select_clause.children) != 1 or len(from_clause.children) != 1:
            return None
        select_expr = RuleGeneratorV2.deparse(copy.deepcopy(select_clause.children[0]))
        if not isinstance(from_clause.children[0], JoinNode):
            return None
        from_sql = RuleGeneratorV2._deparse_join_chain_with_using(from_clause.children[0], select_expr)
        if from_sql is None:
            return None
        distinct_prefix = "DISTINCT " if getattr(select_clause, "distinct", False) else ""
        where_sql = ""
        if isinstance(where_clause, WhereNode) and len(where_clause.children) == 1:
            where_sql = f" WHERE {RuleGeneratorV2.deparse(copy.deepcopy(where_clause.children[0]))}"
        return f"SELECT {distinct_prefix}{select_expr} FROM {from_sql}{where_sql}"

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
            if select is not None and RuleGeneratorV2._is_branch_clause("select", select):
                select_target: object = select
                if from_clause is None and where is None and all(
                    clause is None for clause in (group_by, having, order_by, limit, offset)
                ):
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
            if from_clause is not None and (
                RuleGeneratorV2._is_branch_clause("from", from_clause)
                or (select is None and where is not None)
            ):
                from_target: object = from_clause
                if select is None:
                    from_target = "__from_wrapper__"
                if isinstance(from_clause, FromNode):
                    if any(isinstance(c, JoinNode) for c in from_clause.children):
                        out.append(({"key": "from", "value": "join_sources"}, from_target))
                    else:
                        out.append(({"key": "from", "value": "table_sources"}, from_target))
                else:
                    out.append(({"key": "from", "value": None}, from_target))
            if where is not None and (
                RuleGeneratorV2._is_branch_clause("where", where) or (select is None and from_clause is None)
            ):
                where_target: object = where
                if select is None and from_clause is None:
                    where_target = "__where_wrapper__"
                out.append(({"key": "where", "value": None}, where_target))
            if having is not None and RuleGeneratorV2._is_branch_clause("having", having):
                out.append(({"key": "having", "value": None}, having))
            if order_by is not None and RuleGeneratorV2._is_branch_clause("order_by", order_by):
                out.append(({"key": "order_by", "value": None}, order_by))
            if limit is not None and RuleGeneratorV2._is_branch_clause("limit", limit):
                out.append(({"key": "limit", "value": None}, limit))
            if offset is not None and RuleGeneratorV2._is_branch_clause("offset", offset):
                out.append(({"key": "offset", "value": None}, offset))

            keys = {b["key"] for b, _ in out}
            if "select" in keys and "where" in keys:
                out = [entry for entry in out if entry[0]["key"] != "from"]
            if "select" not in keys and "from" in keys:
                out = [entry for entry in out if entry[0]["key"] != "where"]
            if (
                "from" in {b["key"] for b, _ in out}
                and select is None
                and where is None
                and any(clause is not None for clause in (group_by, having, order_by, limit, offset))
            ):
                out = [entry for entry in out if entry[0]["key"] != "from"]
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
            if isinstance(clause, SelectNode) and len(clause.children) == 1:
                child = clause.children[0]
                if isinstance(child, ColumnNode) and child.name == "*":
                    return True
                if isinstance(child, SetVariableNode):
                    return True
                return RuleGeneratorV2._is_branch_node(child)
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
                    continue
                else:
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
            return RuleGeneratorV2._query_without_clause(ast, NodeType.FROM)
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
    def _replace_subtree_in_ast(ast: Node, subtree: Node, replacement: Node) -> Node:
        if ast == subtree:
            return copy.deepcopy(replacement)
        children = getattr(ast, "children", None)
        if isinstance(children, list):
            for idx, child in enumerate(children):
                if isinstance(child, Node):
                    children[idx] = RuleGeneratorV2._replace_subtree_in_ast(child, subtree, replacement)
        elif isinstance(children, set):
            new_children: Set[Node] = set()
            for child in children:
                if isinstance(child, Node):
                    new_children.add(RuleGeneratorV2._replace_subtree_in_ast(child, subtree, replacement))
                else:
                    new_children.add(child)  # type: ignore[arg-type]
            ast.children = new_children

        if isinstance(ast, JoinNode):
            ast.left_table = ast.children[0]  # type: ignore[assignment]
            ast.right_table = ast.children[1]  # type: ignore[assignment]
            ast.on_condition = ast.children[2] if len(ast.children) > 2 else None  # type: ignore[assignment]
        elif isinstance(ast, UnaryOperatorNode):
            ast.operand = ast.children[0]
        elif isinstance(ast, CompoundQueryNode):
            ast.left = ast.children[0]
            ast.right = ast.children[1]
        elif isinstance(ast, SubqueryNode) and isinstance(ast.children, set):
            pass
        return ast

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
