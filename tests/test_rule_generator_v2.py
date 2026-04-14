from __future__ import annotations

from core.rule_generator_v2 import RuleGeneratorV2
from core.rule_parser_v2 import RuleParserV2, VarType


def test_varType_element_variable():
    assert RuleGeneratorV2.varType("EV001") == VarType.ElementVariable


def test_varType_set_variable():
    assert RuleGeneratorV2.varType("SV001") == VarType.SetVariable


def test_varType_unknown():
    assert RuleGeneratorV2.varType("V001") is None


def test_dereplaceVars_simple():
    pattern = "CAST(EV001 AS DATE)"
    rewrite = "EV001"
    mapping = {"x": "EV001"}

    assert RuleGeneratorV2.dereplaceVars(pattern, mapping) == "CAST(<x> AS DATE)"
    assert RuleGeneratorV2.dereplaceVars(rewrite, mapping) == "<x>"


def test_dereplaceVars_mixed_element_and_set_vars():
    pattern = """
        select SV001
          from EV001 EV002,
               EV003 EV004
         where EV002.EV005=EV004.EV006
           and SV002
    """
    mapping = {
        "x1": "EV001",
        "y1": "SV001",
        "x2": "EV002",
        "y2": "SV002",
        "x3": "EV003",
        "x4": "EV004",
        "x5": "EV005",
        "x6": "EV006",
    }

    dereplaced = RuleGeneratorV2.dereplaceVars(pattern, mapping)
    assert "<<y1>>" in dereplaced
    assert "<x2>.<x5>=<x4>.<x6>" in dereplaced
    assert "<<y2>>" in dereplaced


def test_deparse_condition_scope_expression():
    result = RuleParserV2.parse("CAST(<x> AS DATE)", "<x>")
    assert RuleGeneratorV2.deparse(result.pattern_ast) == "CAST(<x> AS DATE)"
    assert RuleGeneratorV2.deparse(result.rewrite_ast) == "<x>"


def test_columns_basic_function_rule():
    result = RuleParserV2.parse(
        "STRPOS(LOWER(text), 'iphone') > 0",
        "text ILIKE '%iphone%'",
    )
    columns = RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)
    assert set(columns) == {"text"}


def test_columns_basic_cast_rule():
    result = RuleParserV2.parse("CAST(state_name AS TEXT)", "state_name")
    columns = RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)
    assert set(columns) == {"state_name"}


def test_columns_excludes_variable_placeholders():
    result = RuleParserV2.parse(
        """
        select e1.name, e1.age, e2.salary
        from employee e1, employee e2
        where e1.<a1> = e2.<a1>
          and e1.age > 17
          and e2.salary > 35000
        """,
        """
        select e1.name, e1.age, e1.salary
        from employee e1
        where e1.age > 17
          and e1.salary > 35000
        """,
    )
    columns = RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)
    assert set(columns) == {"name", "age", "salary"}
