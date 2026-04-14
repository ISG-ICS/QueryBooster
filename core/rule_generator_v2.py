from __future__ import annotations

import copy
import numbers
from collections import defaultdict
from typing import Dict, Iterator, List, Optional, Set, Tuple, Union

from core.ast.enums import NodeType
from core.ast.node import (
    ColumnNode,
    ElementVariableNode,
    FromNode,
    LimitNode,
    Node,
    OperatorNode,
    QueryNode,
    SelectNode,
    SetVariableNode,
    TableNode,
    WhereNode,
)
from core.query_formatter import QueryFormatter
from core.rule_parser_v2 import Scope, VarType, VarTypesInfo


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
        full_query, scope = RuleGeneratorV2._extend_to_full_query(node)
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
        pattern_branches = RuleGeneratorV2._branches_of_ast(pattern_ast)
        rewrite_branches = RuleGeneratorV2._branches_of_ast(rewrite_ast)
        out: List[Dict[str, object]] = []
        remaining = list(rewrite_branches)
        while pattern_branches:
            pb = pattern_branches.pop()
            for idx, rb in enumerate(remaining):
                if pb["key"] == rb["key"] and pb["value"] == rb["value"]:
                    out.append(pb)
                    remaining.pop(idx)
                    break
        return out

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
        pattern = RuleGeneratorV2.deparse(copy.deepcopy(ast))
        return RuleGeneratorV2._fingerPrint(pattern)

    @staticmethod
    def _fingerPrint(fingerprint: str) -> str:
        out = fingerprint
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
    def _extend_to_full_query(node: Node) -> tuple[QueryNode, Scope]:
        if isinstance(node, QueryNode):
            has_select = RuleGeneratorV2._query_has_clause(node, NodeType.SELECT)
            has_from = RuleGeneratorV2._query_has_clause(node, NodeType.FROM)
            has_where = RuleGeneratorV2._query_has_clause(node, NodeType.WHERE)

            if has_select:
                return node, Scope.SELECT

            if has_from:
                return QueryNode(_select=SelectNode([ColumnNode("*")]), _from=RuleGeneratorV2._first_clause(node, NodeType.FROM), _where=RuleGeneratorV2._first_clause(node, NodeType.WHERE)), Scope.FROM

            if has_where:
                return QueryNode(
                    _select=SelectNode([ColumnNode("*")]),
                    _from=FromNode([TableNode("t")]),
                    _where=RuleGeneratorV2._first_clause(node, NodeType.WHERE),
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

            if isinstance(node, LimitNode) and isinstance(node.limit, str) and node.limit in variable_set:
                node.limit = set_name

            if isinstance(node, OperatorNode) and node.name.lower() == "and":
                ev_children = [c for c in node.children if isinstance(c, ElementVariableNode)]
                if ev_children and all(c.name in variable_set for c in ev_children):
                    node.children = [SetVariableNode(set_name)]
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
            if not isinstance(children, list):
                continue
            for idx, child in enumerate(children):
                if child is target:
                    children[idx] = replacement
                    if isinstance(node, WhereNode):
                        continue
        if root is target:
            raise ValueError("Cannot replace root node directly; expected nested target.")

    @staticmethod
    def _is_placeholder_name(name: str) -> bool:
        lower = name.lower()
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

        return out

    @staticmethod
    def _branches_of_ast(ast: Node) -> List[Dict[str, object]]:
        if not isinstance(ast, QueryNode):
            return []

        select = RuleGeneratorV2._first_clause(ast, NodeType.SELECT)
        from_clause = RuleGeneratorV2._first_clause(ast, NodeType.FROM)
        where = RuleGeneratorV2._first_clause(ast, NodeType.WHERE)
        out: List[Dict[str, object]] = []

        if isinstance(select, SelectNode):
            if len(select.children) == 1 and isinstance(select.children[0], SetVariableNode):
                out.append({"key": "select", "value": "set_variable"})
            elif len(select.children) == 1 and isinstance(select.children[0], ColumnNode) and select.children[0].name == "*":
                out.append({"key": "select", "value": "all_columns"})

        if isinstance(from_clause, FromNode):
            if all(isinstance(c, TableNode) for c in from_clause.children):
                out.append({"key": "from", "value": "table_sources"})

        if isinstance(where, WhereNode):
            out.append({"key": "where", "value": None})

        # Preserve v1 behavior: when both select and where exist, hide from-branch;
        # when no select but from exists, hide where-branch.
        keys = {b["key"] for b in out}
        if "select" in keys and "where" in keys:
            out = [b for b in out if b["key"] != "from"]
        if "select" not in keys and "from" in keys:
            out = [b for b in out if b["key"] != "where"]
        return out

    @staticmethod
    def _drop_branch_in_ast(ast: Node, branch: Dict[str, object]) -> Node:
        if not isinstance(ast, QueryNode):
            return ast
        key = branch.get("key")
        if key == "select":
            return RuleGeneratorV2._query_without_clause(ast, NodeType.SELECT)
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
        return ast

    @staticmethod
    def _query_without_clause(query: QueryNode, clause_type: NodeType) -> QueryNode:
        return QueryNode(
            _select=None if clause_type == NodeType.SELECT else RuleGeneratorV2._first_clause(query, NodeType.SELECT),
            _from=None if clause_type == NodeType.FROM else RuleGeneratorV2._first_clause(query, NodeType.FROM),
            _where=None if clause_type == NodeType.WHERE else RuleGeneratorV2._first_clause(query, NodeType.WHERE),
            _group_by=RuleGeneratorV2._first_clause(query, NodeType.GROUP_BY),
            _having=RuleGeneratorV2._first_clause(query, NodeType.HAVING),
            _order_by=RuleGeneratorV2._first_clause(query, NodeType.ORDER_BY),
            _limit=RuleGeneratorV2._first_clause(query, NodeType.LIMIT),
            _offset=RuleGeneratorV2._first_clause(query, NodeType.OFFSET),
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
            return curr

        return _visit(node), placeholders
