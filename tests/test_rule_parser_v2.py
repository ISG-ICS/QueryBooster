"""Tests for core.rule_parser_v2 — mirrors tests in test_rule_parser.py plus AST (VarNode) paths."""

import pytest

from core.ast.enums import NodeType
from core.ast.node import (
    DataTypeNode,
    FromNode,
    FunctionNode,
    LiteralNode,
    OperatorNode,
    QueryNode,
    SelectNode,
    TableNode,
    VarNode,
    VarSetNode,
    WhereNode,
)
from core.rule_parser_v2 import RuleParseResult, RuleParserV2, Scope


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
    assert pattern == "CAST(V001 AS DATE)"
    assert rewrite == "V001"
    assert mapping == {"x": "V001"}

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
        select VL001
          from V001 V002, 
               V003 V004
         where V002.V005=V004.V006
           and VL002
    """
    assert rewrite == """
        select VL001 
          from V001 V002
         where VL002
    """
    assert mapping == {
        "s1": "VL001",
        "p1": "VL002",
        "tb1": "V001",
        "t1": "V002",
        "tb2": "V003",
        "t2": "V004",
        "a1": "V005",
        "a2": "V006",
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
    assert result.pattern_scope == Scope.CONDITION
    assert result.rewrite_scope == Scope.CONDITION
    assert result.mapping == {"x": "V001"}
    assert isinstance(result.pattern_ast, FunctionNode)
    assert result.pattern_ast.name.lower() == "cast"
    cast_args = list(result.pattern_ast.children)
    assert isinstance(cast_args[0], VarNode) and cast_args[0].name == "x"
    assert isinstance(cast_args[1], DataTypeNode)
    assert isinstance(result.rewrite_ast, VarNode) and result.rewrite_ast.name == "x"


def test_parse_ast_select_list_varset():
    pattern = "select <<s1>> from lineitem where 1 = 1"
    rewrite = "select <<s1>> from lineitem where 1 = 1"
    result = RuleParserV2.parse(pattern, rewrite)
    assert result.pattern_scope == Scope.SELECT
    assert isinstance(result.pattern_ast, QueryNode)
    select = next(c for c in result.pattern_ast.children if c.type == NodeType.SELECT)
    assert isinstance(select, SelectNode)
    first = list(select.children)[0]
    assert isinstance(first, VarSetNode) and first.name == "s1"


def test_parse_ast_strpos_ilike_rule():
    result = RuleParserV2.parse(
        "STRPOS(LOWER(<x>), '<s>') > 0",
        "<x> ILIKE '%<s>%'",
    )
    assert result.mapping == {"x": "V001", "s": "V002"}
    assert result.pattern_scope == Scope.CONDITION
    assert result.rewrite_scope == Scope.CONDITION
    assert isinstance(result.pattern_ast, OperatorNode)
    assert result.pattern_ast.name == ">"
    strpos = list(result.pattern_ast.children)[0]
    assert isinstance(strpos, FunctionNode) and strpos.name.upper() == "STRPOS"
    lower = list(strpos.children)[0]
    assert isinstance(lower, FunctionNode) and lower.name.lower() == "lower"
    assert isinstance(list(lower.children)[0], VarNode) and list(lower.children)[0].name == "x"
    assert isinstance(result.rewrite_ast, FunctionNode) and result.rewrite_ast.name.lower() == "ilike"
    ilike_args = list(result.rewrite_ast.children)
    assert isinstance(ilike_args[0], VarNode) and ilike_args[0].name == "x"
    assert isinstance(ilike_args[1], LiteralNode)


def test_parse_ast_where_scope():
    result = RuleParserV2.parse("WHERE <x> = 1", "WHERE <x> = 1")
    assert result.pattern_scope == Scope.WHERE
    assert result.rewrite_scope == Scope.WHERE
    assert result.mapping == {"x": "V001"}
    assert isinstance(result.pattern_ast, QueryNode)
    wh = next(c for c in result.pattern_ast.children if c.type == NodeType.WHERE)
    assert isinstance(wh, WhereNode)
    pred = list(wh.children)[0]
    assert isinstance(pred, OperatorNode) and pred.name == "="
    lhs, rhs = list(pred.children)
    assert isinstance(lhs, VarNode) and lhs.name == "x"
    assert isinstance(rhs, LiteralNode) and rhs.value == 1


def test_parse_ast_from_scope():
    result = RuleParserV2.parse("FROM <t> li", "FROM <t> li")
    assert result.pattern_scope == Scope.FROM
    assert result.rewrite_scope == Scope.FROM
    assert result.mapping == {"t": "V001"}
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