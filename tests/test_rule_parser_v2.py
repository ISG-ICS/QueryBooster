"""Tests for core.rule_parser_v2 — unit tests plus one test per rule in data/rules.py.

Catalog rule tests check three things:

1. **Full pipeline runs** — ``parse`` extends SQL, runs ``QueryParser``, substitutes EV/SV
   tokens back to ``ElementVariableNode`` / ``SetVariableNode``, and extracts the rule fragment. If anything
   in that chain breaks for a catalog shape, the test fails.

2. **Mapping matches ``replaceVars``** — ``RuleParserV2.parse`` is required to return the same
   ``mapping`` dict as ``replaceVars`` (external name → internal token). That is partly a
   contract with the implementation, but it still guards against ``parse`` accidentally
   returning a different mapping than preprocessing.

3. **AST variables are declared** — every ``ElementVariableNode`` / ``SetVariableNode`` in *both* fragment
   ASTs has a ``.name`` that appears in ``mapping``. That does *not* follow from (2) alone:
   it would fail if substitution attached the wrong identifier or leaked raw EV/SV tokens as
   column names. (Mapping may list extra names used only as table/column identifiers, so we
   do not require the reverse inclusion.)
"""

from __future__ import annotations

from typing import Iterator, Optional

import pytest

from core.ast.enums import NodeType
from core.ast.node import Node
from core.ast.node import (
    DataTypeNode,
    FromNode,
    FunctionNode,
    LiteralNode,
    OperatorNode,
    QueryNode,
    SelectNode,
    TableNode,
    ElementVariableNode,
    SetVariableNode,
    WhereNode,
)
from core.rule_parser_v2 import RuleParseResult, RuleParserV2, Scope
from data.rules import rules as RULES_CATALOG


def _rule_by_key(key: str) -> dict:
    return next(r for r in RULES_CATALOG if r["key"] == key)


def _walk_var_and_varset_names(node: Optional[Node]) -> Iterator[str]:
    if node is None:
        return
    if isinstance(node, ElementVariableNode):
        yield node.name
    elif isinstance(node, SetVariableNode):
        yield node.name
    ch = getattr(node, "children", None)
    if not ch:
        return
    for child in ch:
        yield from _walk_var_and_varset_names(child)


def _assert_varnodes_declared_in_mapping(result: RuleParseResult) -> None:
    """Every ElementVariableNode / SetVariableNode must use an external name listed in ``mapping``."""
    keys = set(result.mapping.keys())
    for tree in (result.pattern_ast, result.rewrite_ast):
        for name in _walk_var_and_varset_names(tree):
            assert name in keys, (
                f"AST has ElementVariableNode/SetVariableNode {name!r} but mapping keys are {sorted(keys)}"
            )


def _parse_and_assert_catalog_rule(rule: dict) -> None:
    pattern, rewrite = rule["pattern"], rule["rewrite"]
    _, _, expected_mapping = RuleParserV2.replaceVars(pattern, rewrite)
    result = RuleParserV2.parse(pattern, rewrite)
    assert isinstance(result, RuleParseResult)
    assert result.mapping == expected_mapping
    _assert_varnodes_declared_in_mapping(result)


def test_extendToFullSQL():
    # Same assertions as tests/test_rule_parser.py::test_extendToFullSQL
    pattern = "CAST(V1 AS DATE)"
    rewrite = "V1"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT * FROM t WHERE CAST(V1 AS DATE)"
    assert scope == Scope.CONDITION
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT * FROM t WHERE V1"
    assert scope == Scope.CONDITION

    pattern = "WHERE CAST(V1 AS DATE)"
    rewrite = "WHERE V1"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT * FROM t WHERE CAST(V1 AS DATE)"
    assert scope == Scope.WHERE
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT * FROM t WHERE V1"
    assert scope == Scope.WHERE

    pattern = "FROM lineitem"
    rewrite = "FROM v_lineitem"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT * FROM lineitem"
    assert scope == Scope.FROM
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT * FROM v_lineitem"
    assert scope == Scope.FROM

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

    pattern = "SELECT VL1 FROM lineitem"
    rewrite = "SELECT VL1 FROM v_lineitem"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT VL1 FROM lineitem"
    assert scope == Scope.SELECT
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT VL1 FROM v_lineitem"
    assert scope == Scope.SELECT

    pattern = "SELECT CAST(V1 AS DATE)"
    rewrite = "SELECT V1"
    pattern, scope = RuleParserV2.extendToFullSQL(pattern)
    assert pattern == "SELECT CAST(V1 AS DATE)"
    assert scope == Scope.SELECT
    rewrite, scope = RuleParserV2.extendToFullSQL(rewrite)
    assert rewrite == "SELECT V1"
    assert scope == Scope.SELECT


def test_replaceVars():
    pattern = "CAST(<x> AS DATE)"
    rewrite = "<x>"
    pattern, rewrite, mapping = RuleParserV2.replaceVars(pattern, rewrite)
    assert pattern == "CAST(EV001 AS DATE)"
    assert rewrite == "EV001"
    assert mapping == {"x": "EV001"}

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


def test_parse_rejects_malformed_brackets_in_pattern():
    pattern = """WHERE <x] > 11
            AND <x> a <= 11
            """
    with pytest.raises(ValueError, match=r"mismatching brackets in pattern at index 6"):
        RuleParserV2.parse(pattern, "<x>")


def test_parse_rejects_malformed_brackets_in_rewrite():
    pattern = "<x>"
    rewrite = """WHERE <x] > 11
            AND <x> a <= 11
            """
    with pytest.raises(ValueError, match=r"mismatching brackets in rewrite at index 6"):
        RuleParserV2.parse(pattern, rewrite)


def test_parse_ast_cast_rule():
    result = RuleParserV2.parse("CAST(<x> AS DATE)", "<x>")
    assert isinstance(result, RuleParseResult)
    assert result.mapping == {"x": "EV001"}
    assert isinstance(result.pattern_ast, FunctionNode)
    assert result.pattern_ast.name.lower() == "cast"
    cast_args = list(result.pattern_ast.children)
    assert isinstance(cast_args[0], ElementVariableNode) and cast_args[0].name == "x"
    assert isinstance(cast_args[1], DataTypeNode)
    assert isinstance(result.rewrite_ast, ElementVariableNode) and result.rewrite_ast.name == "x"


def test_parse_ast_select_list_varset():
    pattern = "select <<s1>> from lineitem where 1 = 1"
    rewrite = "select <<s1>> from lineitem where 1 = 1"
    result = RuleParserV2.parse(pattern, rewrite)
    assert isinstance(result.pattern_ast, QueryNode)
    select = next(c for c in result.pattern_ast.children if c.type == NodeType.SELECT)
    assert isinstance(select, SelectNode)
    first = list(select.children)[0]
    assert isinstance(first, SetVariableNode) and first.name == "s1"


def test_parse_ast_strpos_ilike_rule():
    result = RuleParserV2.parse(
        "STRPOS(LOWER(<x>), '<s>') > 0",
        "<x> ILIKE '%<s>%'",
    )
    assert result.mapping == {"x": "EV001", "s": "EV002"}
    assert isinstance(result.pattern_ast, OperatorNode)
    assert result.pattern_ast.name == ">"
    strpos = list(result.pattern_ast.children)[0]
    assert isinstance(strpos, FunctionNode) and strpos.name.upper() == "STRPOS"
    lower = list(strpos.children)[0]
    assert isinstance(lower, FunctionNode) and lower.name.lower() == "lower"
    assert isinstance(list(lower.children)[0], ElementVariableNode) and list(lower.children)[0].name == "x"
    assert isinstance(result.rewrite_ast, FunctionNode) and result.rewrite_ast.name.lower() == "ilike"
    ilike_args = list(result.rewrite_ast.children)
    assert isinstance(ilike_args[0], ElementVariableNode) and ilike_args[0].name == "x"
    assert isinstance(ilike_args[1], LiteralNode)


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


def test_parse_ast_from_scope():
    result = RuleParserV2.parse("FROM <t> li", "FROM <t> li")
    assert result.mapping == {"t": "EV001"}
    assert isinstance(result.pattern_ast, QueryNode)
    frm = next(c for c in result.pattern_ast.children if c.type == NodeType.FROM)
    assert isinstance(frm, FromNode)
    tab = list(frm.children)[0]
    assert isinstance(tab, TableNode) and tab.name == "t" and tab.alias == "li"


def test_brackets_1():
    pattern = '''WHERE <x] > 11
            AND <x> a <= 11
            '''
    index = RuleParserV2.find_malformed_brackets(pattern)
    assert index == 6


def test_brackets_2():
    pattern = '''WHERE <x} > 11
                AND <x> a <= 11
                '''
    index = RuleParserV2.find_malformed_brackets(pattern)
    assert index == 6


def test_parse_validator_3():
    pattern = '''WHERE <x) > 11
            AND <x> a <= 11
            '''
    index = RuleParserV2.find_malformed_brackets(pattern)
    assert index == 6


def test_parse_validator_4():
    pattern = '''WHERE [x> > 11
                AND <x> a <= 11
                '''
    index = RuleParserV2.find_malformed_brackets(pattern)
    assert index == 6


def test_parse_validator_5():
    pattern = '''WHERE (x> > 11
                AND <x> a <= 11
                '''
    index = RuleParserV2.find_malformed_brackets(pattern)
    assert index == 6


def test_parse_validator_6():
    pattern = '''WHERE {x> > 11
                AND <x> a <= 11
                '''
    index = RuleParserV2.find_malformed_brackets(pattern)
    assert index == 6


# --- data/rules.py catalog (one test per rule, same order as in rules.py) ---


def test_rule_remove_max_distinct():
    """Rule remove_max_distinct: Remove Max Distinct."""
    _parse_and_assert_catalog_rule(_rule_by_key("remove_max_distinct"))


def test_rule_remove_cast_date():
    """Rule remove_cast_date: Remove Cast Date."""
    _parse_and_assert_catalog_rule(_rule_by_key("remove_cast_date"))


def test_rule_remove_cast_text():
    """Rule remove_cast_text: Remove Cast Text."""
    _parse_and_assert_catalog_rule(_rule_by_key("remove_cast_text"))


def test_rule_replace_strpos_lower():
    """Rule replace_strpos_lower: Replace Strpos Lower."""
    _parse_and_assert_catalog_rule(_rule_by_key("replace_strpos_lower"))


def test_rule_remove_self_join():
    """Rule remove_self_join: Remove Self Join."""
    _parse_and_assert_catalog_rule(_rule_by_key("remove_self_join"))


def test_rule_remove_self_join_advance():
    """Rule remove_self_join_advance: Remove Self Join Advance."""
    _parse_and_assert_catalog_rule(_rule_by_key("remove_self_join_advance"))


def test_rule_subquery_to_join():
    """Rule subquery_to_join: Subquery to Join."""
    _parse_and_assert_catalog_rule(_rule_by_key("subquery_to_join"))


def test_rule_join_to_filter():
    """Rule join_to_filter: Join to Filter."""
    _parse_and_assert_catalog_rule(_rule_by_key("join_to_filter"))


def test_rule_join_to_filter_advance():
    """Rule join_to_filter_advance: Join to Filter Advance."""
    _parse_and_assert_catalog_rule(_rule_by_key("join_to_filter_advance"))


def test_rule_join_to_filter_partial1():
    """Rule join_to_filter_partial1: Join to Filter Partial 1."""
    _parse_and_assert_catalog_rule(_rule_by_key("join_to_filter_partial1"))


def test_rule_join_to_filter_partial2():
    """Rule join_to_filter_partial2: Join to Filter Partial 2."""
    _parse_and_assert_catalog_rule(_rule_by_key("join_to_filter_partial2"))


def test_rule_join_to_filter_partial3():
    """Rule join_to_filter_partial3: Join to Filter Partial 3."""
    _parse_and_assert_catalog_rule(_rule_by_key("join_to_filter_partial3"))


def test_rule_remove_1useless_innerjoin():
    """Rule remove_1useless_innerjoin: Remove 1 Useless InnerJoin."""
    _parse_and_assert_catalog_rule(_rule_by_key("remove_1useless_innerjoin"))


def test_rule_remove_where_true():
    """Rule remove_where_true: Remove Where True."""
    _parse_and_assert_catalog_rule(_rule_by_key("remove_where_true"))


def test_rule_nested_clause_to_inner_join():
    """Rule nested_clause_to_inner_join: Nested Clause to Inner Join."""
    _parse_and_assert_catalog_rule(_rule_by_key("nested_clause_to_inner_join"))


def test_rule_contradiction_gt_lte():
    """Rule contradiction_gt_lte: Contradiction gt/lte."""
    _parse_and_assert_catalog_rule(_rule_by_key("contradiction_gt_lte"))


def test_rule_subquery_to_joins():
    """Rule subquery_to_joins: Subquery to Joins."""
    _parse_and_assert_catalog_rule(_rule_by_key("subquery_to_joins"))


def test_rule_aggregation_to_filtered_subquery():
    """Rule aggregation_to_filtered_subquery: Aggregation to Filtered Subquery."""
    _parse_and_assert_catalog_rule(_rule_by_key("aggregation_to_filtered_subquery"))


def test_rule_spreadsheet_id_2():
    """Rule spreadsheet_id_2: Spreadsheet ID 2."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_2"))


def test_rule_spreadsheet_id_3():
    """Rule spreadsheet_id_3: Spreadsheet ID 3."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_3"))


def test_rule_spreadsheet_id_4():
    """Rule spreadsheet_id_4: Spreadsheet ID 4."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_4"))


def test_rule_spreadsheet_id_6():
    """Rule spreadsheet_id_6: Spreadsheet ID 6."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_6"))


def test_rule_spreadsheet_id_7():
    """Rule spreadsheet_id_7: Spreadsheet ID 7."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_7"))


def test_rule_spreadsheet_id_9():
    """Rule spreadsheet_id_9: Spreadsheet ID 9."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_9"))


def test_rule_spreadsheet_id_10():
    """Rule spreadsheet_id_10: Spreadsheet ID 10."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_10"))


def test_rule_spreadsheet_id_11():
    """Rule spreadsheet_id_11: Spreadsheet ID 11."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_11"))


def test_rule_spreadsheet_id_12():
    """Rule spreadsheet_id_12: Spreadsheet ID 12."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_12"))


def test_rule_spreadsheet_id_15():
    """Rule spreadsheet_id_15: Spreadsheet ID 15."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_15"))


def test_rule_spreadsheet_id_18():
    """Rule spreadsheet_id_18: Spreadsheet ID 18."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_18"))


def test_rule_spreadsheet_id_20():
    """Rule spreadsheet_id_20: Spreadsheet ID 20."""
    _parse_and_assert_catalog_rule(_rule_by_key("spreadsheet_id_20"))


def test_rule_test_rule_wetune_90():
    """Rule test_rule_wetune_90: Test Rule Wetune 90."""
    _parse_and_assert_catalog_rule(_rule_by_key("test_rule_wetune_90"))


def test_rule_query_rule_wetune_90():
    """Rule query_rule_wetune_90: Query Rule Wetune 90."""
    _parse_and_assert_catalog_rule(_rule_by_key("query_rule_wetune_90"))


def test_rule_test_rule_calcite_testPushMinThroughUnion():
    """Rule test_rule_calcite_testPushMinThroughUnion: Test Rule Calcite testPushMinThroughUnion."""
    _parse_and_assert_catalog_rule(_rule_by_key("test_rule_calcite_testPushMinThroughUnion"))


def test_rule_remove_adddate():
    """Rule remove_adddate: Remove Adddate."""
    _parse_and_assert_catalog_rule(_rule_by_key("remove_adddate"))


def test_rule_remove_timestamp():
    """Rule remove_timestamp: Remove Timestamp."""
    _parse_and_assert_catalog_rule(_rule_by_key("remove_timestamp"))


def test_rule_stackoverflow_1():
    """Rule stackoverflow_1: Stackoverflow 1."""
    _parse_and_assert_catalog_rule(_rule_by_key("stackoverflow_1"))


def test_rule_combine_or_to_in():
    """Rule combine_or_to_in: combine multiple or to in."""
    _parse_and_assert_catalog_rule(_rule_by_key("combine_or_to_in"))


def test_rule_combine_3_or_to_in():
    """Rule combine_3_or_to_in: combine multiple or to in (3-way)."""
    _parse_and_assert_catalog_rule(_rule_by_key("combine_3_or_to_in"))


def test_rule_merge_or_to_in():
    """Rule merge_or_to_in: merge or to in."""
    _parse_and_assert_catalog_rule(_rule_by_key("merge_or_to_in"))


def test_rule_merge_in_statements():
    """Rule merge_in_statements: merge statements with in condition."""
    _parse_and_assert_catalog_rule(_rule_by_key("merge_in_statements"))


def test_rule_multiple_merge_in():
    """Rule multiple_merge_in: multiple merge in."""
    _parse_and_assert_catalog_rule(_rule_by_key("multiple_merge_in"))


def test_rule_partial_subquery_to_join():
    """Rule partial_subquery_to_join: partial subquery to join."""
    _parse_and_assert_catalog_rule(_rule_by_key("partial_subquery_to_join"))


def test_rule_and_on_true():
    """Rule and_on_true: where TRUE and TRUE."""
    _parse_and_assert_catalog_rule(_rule_by_key("and_on_true"))


def test_rule_multiple_and_on_true():
    """Rule multiple_and_on_true: where TRUE and TRUE in set representation."""
    _parse_and_assert_catalog_rule(_rule_by_key("multiple_and_on_true"))


def test_rule_multiple_or_to_union():
    """Rule multiple_or_to_union: multiple or to union."""
    _parse_and_assert_catalog_rule(_rule_by_key("multiple_or_to_union"))
