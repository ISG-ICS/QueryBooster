from __future__ import annotations

import re
from typing import Iterator, List, Optional

import pytest

from core.ast.enums import NodeType
from core.ast.node import (
    CaseNode,
    ColumnNode,
    DataTypeNode,
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
    OperatorNode,
    OrderByItemNode,
    OrderByNode,
    QueryNode,
    SelectNode,
    SubqueryNode,
    TableNode,
    UnaryOperatorNode,
    ElementVariableNode,
    SetVariableNode,
    WhenThenNode,
    WhereNode,
)
from core.rule_parser_v2 import RuleParseResult, RuleParserV2, Scope, VarType, VarTypesInfo
from data.rules import rules as RULES_CATALOG


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

_TOKEN_RE = re.compile(r"^(EV|SV)\d{3}$")


def _walk(node: Optional[Node]) -> Iterator[Node]:
    """Depth-first walk of the AST."""
    if node is None:
        return
    yield node
    ch = getattr(node, "children", None)
    if ch:
        for child in ch:
            yield from _walk(child)


def _walk_var_names(node: Optional[Node]) -> Iterator[str]:
    """Yield names of all ElementVariableNode / SetVariableNode in the tree."""
    for n in _walk(node):
        if isinstance(n, (ElementVariableNode, SetVariableNode)):
            yield n.name


def _find_first(node: Optional[Node], cls: type) -> Optional[Node]:
    """Find first node of given type in the tree."""
    for n in _walk(node):
        if isinstance(n, cls):
            return n
    return None


def _find_all(node: Optional[Node], cls: type) -> List[Node]:
    """Find all nodes of given type in the tree."""
    return [n for n in _walk(node) if isinstance(n, cls)]


def _assert_varnodes_declared(result: RuleParseResult) -> None:
    """Every ElementVariableNode / SetVariableNode must use an external name in ``mapping``."""
    keys = set(result.mapping.keys())
    for tree_label, tree in [("pattern", result.pattern_ast), ("rewrite", result.rewrite_ast)]:
        for name in _walk_var_names(tree):
            assert name in keys, (
                f"{tree_label} AST has variable node {name!r} but mapping keys are {sorted(keys)}"
            )


def _assert_no_internal_tokens(result: RuleParseResult) -> None:
    """No EV00x / SV00x tokens should survive in identifier-bearing AST fields."""
    internal_tokens = set(result.mapping.values())

    for tree_label, tree in [("pattern", result.pattern_ast), ("rewrite", result.rewrite_ast)]:
        for n in _walk(tree):
            if isinstance(n, ColumnNode):
                assert not _TOKEN_RE.match(n.name), (
                    f"{tree_label} AST has raw internal token {n.name!r} as ColumnNode.name"
                )
                if isinstance(n.alias, str):
                    assert not _TOKEN_RE.match(n.alias), (
                        f"{tree_label} AST has raw internal token {n.alias!r} as ColumnNode.alias"
                    )
                if n.parent_alias in internal_tokens:
                    assert not _TOKEN_RE.match(n.parent_alias), (
                        f"{tree_label} AST has raw internal token {n.parent_alias!r} "
                        f"as ColumnNode.parent_alias"
                    )

            if isinstance(n, TableNode) and isinstance(n.name, str):
                assert not _TOKEN_RE.match(n.name), (
                    f"{tree_label} AST has raw internal token {n.name!r} as TableNode.name"
                )
                if isinstance(n.alias, str):
                    assert not _TOKEN_RE.match(n.alias), (
                        f"{tree_label} AST has raw internal token {n.alias!r} as TableNode.alias"
                    )

            if isinstance(n, SubqueryNode) and isinstance(n.alias, str):
                assert not _TOKEN_RE.match(n.alias), (
                    f"{tree_label} AST has raw internal token {n.alias!r} as SubqueryNode.alias"
                )

            if isinstance(n, FunctionNode) and isinstance(n.alias, str):
                assert not _TOKEN_RE.match(n.alias), (
                    f"{tree_label} AST has raw internal token {n.alias!r} as FunctionNode.alias"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# extendToFullSQL
# ═══════════════════════════════════════════════════════════════════════════════

def test_extendToFullSQL():
    # CONDITION scope
    pattern = "CAST(V1 AS DATE)"
    rewrite = "V1"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT * FROM t WHERE CAST(V1 AS DATE)"
    assert scope == Scope.CONDITION
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT * FROM t WHERE V1"
    assert scope == Scope.CONDITION

    # WHERE scope
    pattern = "WHERE CAST(V1 AS DATE)"
    rewrite = "WHERE V1"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT * FROM t WHERE CAST(V1 AS DATE)"
    assert scope == Scope.WHERE
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT * FROM t WHERE V1"
    assert scope == Scope.WHERE

    # FROM scope
    pattern = "FROM lineitem"
    rewrite = "FROM v_lineitem"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT * FROM lineitem"
    assert scope == Scope.FROM
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT * FROM v_lineitem"
    assert scope == Scope.FROM

    # SELECT scope with FROM and WHERE
    pattern = """
        select VL1
          from V1 V2, 
               V3 V4
         where V2.V6=V4.V8
           and VL2
    """
    rewrite = """
        select VL1 
          from V1 V2
         where VL2
    """
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == """
        select VL1
          from V1 V2, 
               V3 V4
         where V2.V6=V4.V8
           and VL2
    """
    assert scope == Scope.SELECT
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == """
        select VL1 
          from V1 V2
         where VL2
    """
    assert scope == Scope.SELECT

    # SELECT scope with FROM
    pattern = "SELECT VL1 FROM lineitem"
    rewrite = "SELECT VL1 FROM v_lineitem"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT VL1 FROM lineitem"
    assert scope == Scope.SELECT
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT VL1 FROM v_lineitem"
    assert scope == Scope.SELECT

    # SELECT scope with only SELECT
    pattern = "SELECT CAST(V1 AS DATE)"
    rewrite = "SELECT V1"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT CAST(V1 AS DATE)"
    assert scope == Scope.SELECT
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT V1"
    assert scope == Scope.SELECT


def test_extendToFullSQL_subquery_not_confused():
    """Subquery inside parens shouldn't cause false FROM/SELECT scope detection."""
    sql, scope = RuleParserV2.extendToFullSQL(
        "x IN (SELECT id FROM sub WHERE flag = 1)"
    )
    assert scope == Scope.CONDITION


def test_extendToFullSQL_from_with_subquery_in_where():
    sql, scope = RuleParserV2.extendToFullSQL(
        "FROM t WHERE x IN (SELECT id FROM sub)"
    )
    assert scope == Scope.FROM


def test_extendToFullSQL_case_insensitive():
    sql, scope = RuleParserV2.extendToFullSQL("from my_table where x = 1")
    assert scope == Scope.FROM


# ═══════════════════════════════════════════════════════════════════════════════
# replaceVars
# ═══════════════════════════════════════════════════════════════════════════════

def test_replaceVars():
    # Single element var
    pattern = "CAST(<x> AS DATE)"
    rewrite = "<x>"
    pattern, rewrite, mapping = RuleParserV2.replaceVars(pattern, rewrite)
    assert pattern == "CAST(EV001 AS DATE)"
    assert rewrite == "EV001"
    assert mapping == {"x": "EV001"}

    # Multiple var and varList case
    pattern = """
        select <<s1>>
          from <tb1> <t1>, 
               <tb2> <t2>
         where <t1>.<a1>=<t2>.<a2>
           and <<p1>>
    """
    rewrite = """
        select <<s1>> 
          from <tb1> <t1>
         where <<p1>>
    """
    pattern, rewrite, mapping = RuleParserV2.replaceVars(pattern, rewrite)
    assert pattern == """
        select SV001
          from EV001 EV002, 
               EV003 EV004
         where EV002.EV005=EV004.EV006
           and SV002
    """
    assert rewrite == """
        select SV001 
          from EV001 EV002
         where SV002
    """
    assert mapping == {
        "s1": "SV001",
        "p1": "SV002",
        "tb1": "EV001",
        "t1": "EV002",
        "tb2": "EV003",
        "t2": "EV004",
        "a1": "EV005",
        "a2": "EV006",
    }


def test_replaceVars_distinct_names():
    """Set vars and element vars with different names get separate tokens."""
    p, r, m = RuleParserV2.replaceVars(
        "SELECT <<cols>> FROM <tbl> WHERE <<preds>>",
        "SELECT <<cols>> FROM <tbl> WHERE <<preds>>",
    )
    assert m["cols"] == "SV001"
    assert m["preds"] == "SV002"
    assert m["tbl"] == "EV001"


def test_replaceVars_multiple_unique_tokens():
    p, r, m = RuleParserV2.replaceVars("<a> + <b> + <c>", "<a> + <b> + <c>")
    assert len(set(m.values())) == 3
    assert all(v.startswith("EV") for v in m.values())


def test_replaceVars_same_var_in_both():
    """Same variable name in pattern and rewrite maps to the same token."""
    p, r, m = RuleParserV2.replaceVars("<x> = <y>", "<y> = <x>")
    assert m["x"] in p and m["x"] in r
    assert m["y"] in p and m["y"] in r


# ═══════════════════════════════════════════════════════════════════════════════
# find_malformed_brackets
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("bad_pattern,expected_index", [
    ("WHERE <x] > 11 AND <x> a <= 11", 6),
    ("WHERE <x} > 11 AND <x> a <= 11", 6),
    ("WHERE <x) > 11 AND <x> a <= 11", 6),
    ("WHERE [x> > 11 AND <x> a <= 11", 6),
    ("WHERE (x> > 11 AND <x> a <= 11", 6),
    ("WHERE {x> > 11 AND <x> a <= 11", 6),
])
def test_find_malformed_brackets(bad_pattern, expected_index):
    assert RuleParserV2.find_malformed_brackets(bad_pattern) == expected_index


def test_well_formed_brackets_return_negative():
    assert RuleParserV2.find_malformed_brackets("<x> = <y>") == -1
    assert RuleParserV2.find_malformed_brackets("<<x>> AND <<y>>") == -1


# ═══════════════════════════════════════════════════════════════════════════════
# parse() — CONDITION scope: deep AST structure
# ═══════════════════════════════════════════════════════════════════════════════

def test_parse_ast_cast_rule():
    """CAST(<x> AS DATE) -> FunctionNode(cast, [ElementVariableNode, DataTypeNode])"""
    result = RuleParserV2.parse("CAST(<x> AS DATE)", "<x>")
    assert isinstance(result, RuleParseResult)
    assert result.mapping == {"x": "EV001"}
    assert isinstance(result.pattern_ast, FunctionNode)
    assert result.pattern_ast.name.lower() == "cast"
    cast_args = list(result.pattern_ast.children)
    assert len(cast_args) == 2
    assert isinstance(cast_args[0], ElementVariableNode) and cast_args[0].name == "x"
    assert isinstance(cast_args[1], DataTypeNode)
    assert isinstance(result.rewrite_ast, ElementVariableNode) and result.rewrite_ast.name == "x"


def test_parse_ast_strpos_ilike_rule():
    """STRPOS(LOWER(<x>), '<s>') > 0 — deep operator / function / variable structure."""
    result = RuleParserV2.parse(
        "STRPOS(LOWER(<x>), '<s>') > 0",
        "<x> ILIKE '%<s>%'",
    )
    assert result.mapping == {"x": "EV001", "s": "EV002"}
    # Pattern: > operator
    pat = result.pattern_ast
    assert isinstance(pat, OperatorNode) and pat.name == ">"
    ch = list(pat.children)
    assert isinstance(ch[0], FunctionNode) and ch[0].name.upper() == "STRPOS"
    assert isinstance(ch[1], LiteralNode) and ch[1].value == 0
    # STRPOS -> LOWER -> ElementVariableNode
    strpos_args = list(ch[0].children)
    lower = strpos_args[0]
    assert isinstance(lower, FunctionNode) and lower.name.lower() == "lower"
    assert isinstance(list(lower.children)[0], ElementVariableNode)
    assert list(lower.children)[0].name == "x"
    assert isinstance(strpos_args[1], LiteralNode)
    # Rewrite: ILIKE
    rew = result.rewrite_ast
    assert isinstance(rew, FunctionNode) and rew.name.lower() == "ilike"
    ilike_args = list(rew.children)
    assert isinstance(ilike_args[0], ElementVariableNode) and ilike_args[0].name == "x"
    assert isinstance(ilike_args[1], LiteralNode)
    assert ilike_args[1].value == "%s%"


def test_substitute_placeholders_limit_offset_string_tokens():
    """Directly exercise LIMIT/OFFSET token replacement for string payloads."""
    lim = RuleParserV2._substitute_placeholders(  # type: ignore[arg-type]
        LimitNode("EV001"), {"EV001": "x"}
    )
    off = RuleParserV2._substitute_placeholders(  # type: ignore[arg-type]
        OffsetNode("EV002"), {"EV002": "y"}
    )
    assert isinstance(lim, LimitNode) and lim.limit == "x"
    assert isinstance(off, OffsetNode) and off.offset == "y"


def test_parse_substitutes_alias_fields():
    """Column/function/subquery aliases should not leak EV/SV internal tokens."""
    result = RuleParserV2.parse(
        "SELECT SUM(<x>) AS <f_alias>, t.c AS <c_alias> FROM (SELECT <x> FROM <t>) AS <sq_alias>, <t> t",
        "SELECT SUM(<x>) AS <f_alias>, t.c AS <c_alias> FROM (SELECT <x> FROM <t>) AS <sq_alias>, <t> t",
    )
    assert isinstance(result, RuleParseResult)
    assert result.mapping["f_alias"].startswith("EV")
    assert result.mapping["c_alias"].startswith("EV")
    assert result.mapping["sq_alias"].startswith("EV")
    _assert_no_internal_tokens(result)


def test_parse_ast_max_distinct():
    """MAX(DISTINCT <x>) -> MAX(<x>)"""
    result = RuleParserV2.parse("MAX(DISTINCT <x>)", "MAX(<x>)")
    assert isinstance(result.pattern_ast, FunctionNode) and result.pattern_ast.name.lower() == "max"
    assert isinstance(result.rewrite_ast, FunctionNode) and result.rewrite_ast.name.lower() == "max"
    assert "x" in list(_walk_var_names(result.pattern_ast))
    assert "x" in list(_walk_var_names(result.rewrite_ast))


def test_parse_ast_contradiction():
    """<x2> > <x3> AND <x2> <= <x3> -> FALSE"""
    result = RuleParserV2.parse("<x2> > <x3> AND <x2> <= <x3>", "FALSE")
    assert isinstance(result.pattern_ast, OperatorNode) and result.pattern_ast.name.lower() == "and"
    _assert_varnodes_declared(result)
    _assert_no_internal_tokens(result)


def test_parse_ast_combine_or_to_in():
    """<x> = <y> OR <x> = <z> -> <x> IN (<y>, <z>)"""
    result = RuleParserV2.parse("<x> = <y> OR <x> = <z>", "<x> IN (<y>, <z>)")
    assert isinstance(result.pattern_ast, OperatorNode)
    assert isinstance(result.rewrite_ast, (OperatorNode, FunctionNode))
    _assert_varnodes_declared(result)
    _assert_no_internal_tokens(result)


def test_parse_ast_or_to_case():
    """OR chain -> CASE WHEN — verifies CaseNode with 3 whens + else."""
    result = RuleParserV2.parse(
        "<x21> OR <x20> OR <x19>",
        "1 = CASE WHEN <x21> THEN 1 WHEN <x20> THEN 1 WHEN <x19> THEN 1 ELSE 0 END",
    )
    _assert_varnodes_declared(result)
    _assert_no_internal_tokens(result)
    case_nodes = _find_all(result.rewrite_ast, CaseNode)
    assert len(case_nodes) >= 1, "Rewrite should contain a CaseNode"
    case = case_nodes[0]
    assert len(case.whens) == 3
    assert case.else_val is not None


# ═══════════════════════════════════════════════════════════════════════════════
# parse() — WHERE scope
# ═══════════════════════════════════════════════════════════════════════════════

def test_parse_ast_where_scope():
    result = RuleParserV2.parse("WHERE <x> = 1", "WHERE <x> = 1")
    assert result.mapping == {"x": "EV001"}
    assert isinstance(result.pattern_ast, QueryNode)
    wh = next(c for c in result.pattern_ast.children if c.type == NodeType.WHERE)
    assert isinstance(wh, WhereNode)
    pred = list(wh.children)[0]
    assert isinstance(pred, OperatorNode) and pred.name == "="
    lhs, rhs = list(pred.children)
    assert isinstance(lhs, ElementVariableNode) and lhs.name == "x"
    assert isinstance(rhs, LiteralNode) and rhs.value == 1


def test_parse_where_scope_strips_select_and_from():
    """WHERE scope extraction should produce no SelectNode or FromNode."""
    result = RuleParserV2.parse("WHERE <a> > <b>", "WHERE <a> > <b>")
    assert isinstance(result.pattern_ast, QueryNode)
    assert _find_first(result.pattern_ast, SelectNode) is None
    assert _find_first(result.pattern_ast, FromNode) is None


# ═══════════════════════════════════════════════════════════════════════════════
# parse() — FROM scope
# ═══════════════════════════════════════════════════════════════════════════════

def test_parse_ast_from_scope():
    result = RuleParserV2.parse("FROM <t> li", "FROM <t> li")
    assert result.mapping == {"t": "EV001"}
    assert isinstance(result.pattern_ast, QueryNode)
    frm = next(c for c in result.pattern_ast.children if c.type == NodeType.FROM)
    assert isinstance(frm, FromNode)
    tab = list(frm.children)[0]
    assert isinstance(tab, TableNode) and tab.name == "t" and tab.alias == "li"


def test_parse_from_scope_strips_select():
    """FROM scope extraction should produce no SelectNode."""
    result = RuleParserV2.parse("FROM <t>", "FROM <t>")
    assert isinstance(result.pattern_ast, QueryNode)
    assert _find_first(result.pattern_ast, SelectNode) is None


def test_parse_from_scope_with_where():
    """FROM <x1> WHERE ... — pattern keeps WHERE, rewrite without WHERE drops it."""
    result = RuleParserV2.parse(
        "FROM <x1> WHERE <x2> > <x2> - 2",
        "FROM <x1>",
    )
    assert isinstance(result.pattern_ast, QueryNode)
    assert _find_first(result.pattern_ast, FromNode) is not None
    assert _find_first(result.pattern_ast, WhereNode) is not None


def test_parse_from_scope_with_join():
    """FROM with INNER JOIN should produce JoinNode."""
    result = RuleParserV2.parse(
        "FROM <x1> INNER JOIN <x2> ON <x1>.<a1> = <x2>.<a2>",
        "FROM <x1> INNER JOIN <x2> ON <x1>.<a1> = <x2>.<a2>",
    )
    assert isinstance(result.pattern_ast, QueryNode)
    assert len(_find_all(result.pattern_ast, JoinNode)) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# parse() — SELECT scope: complex rules
# ═══════════════════════════════════════════════════════════════════════════════

def test_parse_ast_select_list_varset():
    """SetVariableNode in the SELECT list."""
    result = RuleParserV2.parse(
        "select <<s1>> from lineitem where 1 = 1",
        "select <<s1>> from lineitem where 1 = 1",
    )
    assert isinstance(result.pattern_ast, QueryNode)
    select = next(c for c in result.pattern_ast.children if c.type == NodeType.SELECT)
    assert isinstance(select, SelectNode)
    first = list(select.children)[0]
    assert isinstance(first, SetVariableNode) and first.name == "s1"


def test_parse_self_join_rule():
    """Remove Self Join: 2 tables in pattern, 1 in rewrite, SetVariableNodes present."""
    result = RuleParserV2.parse(
        """select <<s1>>
          from <tb1> <t1>, <tb1> <t2>
         where <t1>.<a1>=<t2>.<a1> and <<p1>>""",
        """select <<s1>>
          from <tb1> <t1>
         where 1=1 and <<p1>>""",
    )
    _assert_varnodes_declared(result)
    _assert_no_internal_tokens(result)
    assert len(_find_all(result.pattern_ast, TableNode)) >= 2
    assert len(_find_all(result.rewrite_ast, TableNode)) >= 1
    pat_svs = [n for n in _walk(result.pattern_ast) if isinstance(n, SetVariableNode)]
    assert len(pat_svs) >= 2  # s1 and p1


def test_parse_subquery_to_join_rule():
    """IN (SELECT ...) pattern has SubqueryNode; comma-join rewrite does not."""
    result = RuleParserV2.parse(
        """select <<s1>> from <tb1>
         where <a1> in (select <a2> from <tb2> where <<p2>>)
           and <<p1>>""",
        """select distinct <<s1>> from <tb1>, <tb2>
         where <tb1>.<a1> = <tb2>.<a2>
           and <<p1>> and <<p2>>""",
    )
    _assert_varnodes_declared(result)
    _assert_no_internal_tokens(result)
    assert len(_find_all(result.pattern_ast, SubqueryNode)) >= 1
    assert len(_find_all(result.rewrite_ast, SubqueryNode)) == 0


def test_parse_join_to_filter_rule():
    """Double INNER JOIN pattern has more JoinNodes than single INNER JOIN rewrite."""
    result = RuleParserV2.parse(
        """select <<s1>>
          from <tb1> <t1>
            inner join <tb2> <t2> on <t1>.<a1> = <t2>.<a2>
            inner join <tb3> <t3> on <t2>.<a3> = <t3>.<a4>
         where <t3>.<a4> = <c1> and <<p1>>""",
        """select <<s1>>
          from <tb1> <t1>
            inner join <tb2> <t2> on <t1>.<a1> = <t2>.<a2>
         where <t2>.<a3> = <c1> and <<p1>>""",
    )
    _assert_varnodes_declared(result)
    _assert_no_internal_tokens(result)
    assert len(_find_all(result.pattern_ast, JoinNode)) > len(
        _find_all(result.rewrite_ast, JoinNode)
    )


def test_parse_distinct_on():
    """DISTINCT ON should be preserved in the SelectNode."""
    result = RuleParserV2.parse(
        "SELECT DISTINCT ON (<x1>) <x2>, <x1> FROM <x3>",
        "SELECT <x2>, <x1> FROM <x3>",
    )
    _assert_varnodes_declared(result)
    pat_sel = _find_first(result.pattern_ast, SelectNode)
    assert pat_sel is not None
    assert pat_sel.distinct or getattr(pat_sel, "distinct_on", None) is not None


def test_parse_order_by_and_limit():
    """ORDER BY and LIMIT should produce their respective node types."""
    result = RuleParserV2.parse(
        "SELECT <x1> FROM <x2> ORDER BY <x1> ASC LIMIT <x3>",
        "SELECT <x1> FROM <x2> ORDER BY <x1> ASC LIMIT <x3>",
    )
    _assert_varnodes_declared(result)
    assert _find_first(result.pattern_ast, OrderByNode) is not None
    assert _find_first(result.pattern_ast, OrderByItemNode) is not None
    assert _find_first(result.pattern_ast, LimitNode) is not None


def test_parse_distinct_to_group_by():
    """SELECT DISTINCT -> GROUP BY rewrite."""
    result = RuleParserV2.parse(
        "SELECT DISTINCT <<x2>> FROM <<x1>> WHERE <<y1>>",
        "SELECT <<x2>> FROM <<x1>> WHERE <<y1>> GROUP BY <<x2>>",
    )
    _assert_varnodes_declared(result)
    _assert_no_internal_tokens(result)
    assert _find_first(result.rewrite_ast, GroupByNode) is not None
    pat_sel = _find_first(result.pattern_ast, SelectNode)
    if pat_sel is not None:
        assert pat_sel.distinct is True


def test_parse_set_variable_in_select_and_where():
    """SetVariableNode should appear in both SELECT and WHERE."""
    result = RuleParserV2.parse(
        "SELECT <<cols>> FROM tbl WHERE <<preds>>",
        "SELECT <<cols>> FROM tbl WHERE <<preds>>",
    )
    sv_names = {n.name for n in _walk(result.pattern_ast) if isinstance(n, SetVariableNode)}
    assert "cols" in sv_names
    assert "preds" in sv_names


# ═══════════════════════════════════════════════════════════════════════════════
# Column + parent_alias substitution
# ═══════════════════════════════════════════════════════════════════════════════

def test_qualified_column_both_parts_substituted():
    """<t1>.<a1> — both parent_alias and name should become external names."""
    result = RuleParserV2.parse("<t1>.<a1> = 1", "<t1>.<a1> = 1")
    _assert_varnodes_declared(result)
    _assert_no_internal_tokens(result)
    cols = _find_all(result.pattern_ast, ColumnNode)
    qualified = [c for c in cols if c.parent_alias is not None]
    assert len(qualified) >= 1
    for c in qualified:
        assert c.parent_alias in result.mapping
        assert c.name in result.mapping


def test_qualified_column_only_parent_alias_is_var():
    """<t1>.fixed_col — only the alias is a variable; the column name is a literal."""
    result = RuleParserV2.parse("<t1>.created_at = 1", "<t1>.created_at = 1")
    _assert_no_internal_tokens(result)
    cols = _find_all(result.pattern_ast, ColumnNode)
    qualified = [c for c in cols if c.parent_alias is not None]
    assert len(qualified) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Error paths
# ═══════════════════════════════════════════════════════════════════════════════

def test_invalid_sql_raises():
    """Completely invalid SQL should raise during parse."""
    with pytest.raises(Exception):
        RuleParserV2.parse("!!NOT_VALID_SQL!!", "<x>")


def test_deeply_nested_parens():
    """Deeply nested expressions should not confuse scope detection."""
    result = RuleParserV2.parse(
        "(((<x> + <y>) * <z>) > 0)",
        "(<x> + <y>) * <z> > 0",
    )
    _assert_varnodes_declared(result)


# ═══════════════════════════════════════════════════════════════════════════════
# No internal token leak — parametrized across shapes
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("pattern,rewrite", [
    ("CAST(<x> AS DATE)", "<x>"),
    ("STRPOS(LOWER(<x>), '<s>') > 0", "<x> ILIKE '%<s>%'"),
    ("MAX(DISTINCT <x>)", "MAX(<x>)"),
    ("<x> = <y> OR <x> = <z>", "<x> IN (<y>, <z>)"),
    ("WHERE <x> = 1", "WHERE <x> = 1"),
    ("FROM <t>", "FROM <t>"),
])
def test_no_internal_tokens_survive(pattern, rewrite):
    result = RuleParserV2.parse(pattern, rewrite)
    _assert_no_internal_tokens(result)
    _assert_varnodes_declared(result)


# ═══════════════════════════════════════════════════════════════════════════════
# Mapping consistency — parse() vs replaceVars()
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("pattern,rewrite", [
    ("CAST(<x> AS DATE)", "<x>"),
    ("STRPOS(LOWER(<x>), '<s>') > 0", "<x> ILIKE '%<s>%'"),
    ("SELECT <<cols>> FROM <tbl> WHERE <<preds>>", "SELECT <<cols>> FROM <tbl> WHERE <<preds>>"),
])
def test_parse_mapping_matches_replaceVars(pattern, rewrite):
    _, _, expected = RuleParserV2.replaceVars(pattern, rewrite)
    result = RuleParserV2.parse(pattern, rewrite)
    assert result.mapping == expected


# ═══════════════════════════════════════════════════════════════════════════════
# Variable coverage
# ═══════════════════════════════════════════════════════════════════════════════

def test_rewrite_vars_subset_of_pattern():
    """For simple rules, rewrite variables are a subset of pattern variables."""
    result = RuleParserV2.parse("CAST(<x> AS DATE)", "<x>")
    assert set(_walk_var_names(result.rewrite_ast)) <= set(_walk_var_names(result.pattern_ast))


def test_identity_rule_same_vars():
    """An identity rewrite has the same variable set in both trees."""
    result = RuleParserV2.parse("<x> = <y>", "<x> = <y>")
    assert set(_walk_var_names(result.pattern_ast)) == set(_walk_var_names(result.rewrite_ast))


# ═══════════════════════════════════════════════════════════════════════════════
# VarType / VarTypesInfo metadata
# ═══════════════════════════════════════════════════════════════════════════════

def test_element_var_markers():
    info = VarTypesInfo[VarType.ElementVariable]
    assert info["markerStart"] == "<"
    assert info["markerEnd"] == ">"
    assert info["internalBase"] == "EV"


def test_set_var_markers():
    info = VarTypesInfo[VarType.SetVariable]
    assert info["markerStart"] == "<<"
    assert info["markerEnd"] == ">>"
    assert info["internalBase"] == "SV"


# ═══════════════════════════════════════════════════════════════════════════════
# data/rules.py catalog — parametrized over all rules
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "rule",
    RULES_CATALOG,
    ids=[r["key"] for r in RULES_CATALOG],
)
class TestCatalogRules:

    def test_parse_succeeds(self, rule):
        """Full parse pipeline completes without error."""
        result = RuleParserV2.parse(rule["pattern"], rule["rewrite"])
        assert isinstance(result, RuleParseResult)
        assert result.pattern_ast is not None
        assert result.rewrite_ast is not None

    def test_mapping_matches_replaceVars(self, rule):
        """parse() returns the same mapping as replaceVars()."""
        _, _, expected = RuleParserV2.replaceVars(rule["pattern"], rule["rewrite"])
        result = RuleParserV2.parse(rule["pattern"], rule["rewrite"])
        assert result.mapping == expected

    def test_varnodes_declared_in_mapping(self, rule):
        """Every variable node in the AST uses an external name present in mapping."""
        result = RuleParserV2.parse(rule["pattern"], rule["rewrite"])
        _assert_varnodes_declared(result)

    def test_no_internal_tokens_leak(self, rule):
        """No EV00x / SV00x tokens survive as raw identifiers."""
        result = RuleParserV2.parse(rule["pattern"], rule["rewrite"])
        _assert_no_internal_tokens(result)