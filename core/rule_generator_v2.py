from __future__ import annotations

import numbers
import re
from collections import defaultdict
from typing import Dict, Iterator, List, Optional, Set, Union

from core.ast.enums import NodeType
from core.ast.node import (
    ColumnNode,
    ElementVariableNode,
    FromNode,
    Node,
    QueryNode,
    SelectNode,
    SetVariableNode,
    TableNode,
    WhereNode,
)
from core.query_formatter import QueryFormatter
from core.rule_parser_v2 import Scope, VarType, VarTypesInfo


class RuleGeneratorV2:
    _PLACEHOLDER_NAME_RE = re.compile(r"^(x|y|a|t|tb|c|s|p)\d+$", re.IGNORECASE)

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
            out = re.sub(
                re.escape(internal_name),
                f"{marker_start}{external_name}{marker_end}",
                out,
            )
        return out

    @staticmethod
    def deparse(node: Node) -> str:
        full_query, scope = RuleGeneratorV2._extend_to_full_query(node)
        full_query, placeholder_mapping = RuleGeneratorV2._encode_vars_for_format(full_query)
        sql = QueryFormatter().format(full_query)
        for placeholder, user_var in placeholder_mapping.items():
            sql = sql.replace(placeholder, user_var)
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
                    and not RuleGeneratorV2._PLACEHOLDER_NAME_RE.match(node.name)
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
            if RuleGeneratorV2._PLACEHOLDER_NAME_RE.match(node.name):
                continue
            alias = node.alias if isinstance(node.alias, str) else node.name
            if RuleGeneratorV2._PLACEHOLDER_NAME_RE.match(alias):
                continue
            found.append({"value": node.name, "name": alias})
        return found

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
