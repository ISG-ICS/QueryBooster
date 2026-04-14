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


def test_literals_1():
    result = RuleParserV2.parse("STRPOS(LOWER(text), 'iphone') > 0", "ILIKE(text, '%iphone%')")
    assert set(RuleGeneratorV2.literals(result.pattern_ast, result.rewrite_ast)) == {"iphone"}


def test_literals_2():
    result = RuleParserV2.parse(
        """
        select e1.name, e1.age, e2.salary
        from employee e1, employee e2
        where e1.id = e2.id
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
    assert set(RuleGeneratorV2.literals(result.pattern_ast, result.rewrite_ast)) == {17, 35000}


def test_literals_3():
    result = RuleParserV2.parse(
        """
        SELECT *
        FROM blc_admin_permission adminpermi0_
          INNER JOIN blc_admin_role_permission_xref allroles1_
            ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
          INNER JOIN blc_admin_role adminrolei2_
            ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminrolei2_.admin_role_id = 1
        """,
        """
        SELECT *
        FROM blc_admin_permission AS adminpermi0_
          INNER JOIN blc_admin_role_permission_xref AS allroles1_
            ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE allroles1_.admin_role_id = 1
        """,
    )
    assert set(RuleGeneratorV2.literals(result.pattern_ast, result.rewrite_ast)) == {1}


def test_tables_1():
    result = RuleParserV2.parse("STRPOS(LOWER(text), 'iphone') > 0", "ILIKE(text, '%iphone%')")
    assert RuleGeneratorV2.tables(result.pattern_ast, result.rewrite_ast) == []


def test_tables_2():
    result = RuleParserV2.parse(
        """
        select e1.name, e1.age, e2.salary
        from employee e1, employee e2
        where e1.id = e2.id
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
    expected = {("employee", "e1"), ("employee", "e2")}
    actual = {(t["value"], t["name"]) for t in RuleGeneratorV2.tables(result.pattern_ast, result.rewrite_ast)}
    assert actual == expected


def test_tables_3_excludes_variable_tables():
    result = RuleParserV2.parse(
        """
        select <tb1>.name, <tb1>.age, <tb2>.salary
        from <tb1>, <tb2>
        where <tb1>.<a1> = <tb2>.<a1>
          and <tb1>.age > 17
          and <tb2>.salary > 35000
        """,
        """
        select <tb1>.name, <tb1>.age, <tb1>.salary
        from <tb1>
        where <tb1>.age > 17
          and <tb1>.salary > 35000
        """,
    )
    assert RuleGeneratorV2.tables(result.pattern_ast, result.rewrite_ast) == []


def test_tables_4_subquery_tables():
    result = RuleParserV2.parse(
        """
        select *
        from employee
        where workdept in (
            select deptno
            from department
            where deptname = 'OPERATIONS'
        )
        """,
        """
        select distinct *
        from employee, department
        where employee.workdept = department.deptno
          and department.deptname = 'OPERATIONS'
        """,
    )
    expected = {("employee", "employee"), ("department", "department")}
    actual = {(t["value"], t["name"]) for t in RuleGeneratorV2.tables(result.pattern_ast, result.rewrite_ast)}
    assert actual == expected
