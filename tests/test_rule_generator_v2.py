from __future__ import annotations

from core.ast.enums import NodeType
from core.ast.node import QueryNode
from core.rule_generator_v2 import RuleGeneratorV2
from core.rule_parser_v2 import RuleParserV2, VarType


def _build_rule(pattern: str, rewrite: str):
    parsed = RuleParserV2.parse(pattern, rewrite)
    return {
        "pattern": pattern,
        "rewrite": rewrite,
        "pattern_ast": parsed.pattern_ast,
        "rewrite_ast": parsed.rewrite_ast,
        "mapping": parsed.mapping,
        "constraints": "",
        "actions": "",
    }


def _has_clause(query: QueryNode, clause_type: NodeType) -> bool:
    return any(child.type == clause_type for child in query.children)


def _norm_sql(sql: str) -> str:
    return " ".join(sql.split())


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


def test_dereplaceVars_1():
    assert RuleGeneratorV2.dereplaceVars("CAST(EV001 AS DATE)", {"x": "EV001"}) == "CAST(<x> AS DATE)"
    assert RuleGeneratorV2.dereplaceVars("EV001", {"x": "EV001"}) == "<x>"


def test_dereplaceVars_2():
    pattern = """
        select SV001
          from EV001 EV002,
               EV003 EV004
         where EV002.EV005=EV004.EV006
           and SV002
    """
    rewrite = """
        select SV001
          from EV001 EV002
         where SV002
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
    assert RuleGeneratorV2.dereplaceVars(pattern, mapping) == """
        select <<y1>>
          from <x1> <x2>,
               <x3> <x4>
         where <x2>.<x5>=<x4>.<x6>
           and <<y2>>
    """
    assert RuleGeneratorV2.dereplaceVars(rewrite, mapping) == """
        select <<y1>>
          from <x1> <x2>
         where <<y2>>
    """


def test_deparse_condition_scope_expression():
    result = RuleParserV2.parse("CAST(<x> AS DATE)", "<x>")
    assert RuleGeneratorV2.deparse(result.pattern_ast) == "CAST(<x> AS DATE)"
    assert RuleGeneratorV2.deparse(result.rewrite_ast) == "<x>"


def test_deparse_1():
    result = RuleParserV2.parse("CAST(V1 AS DATE)", "V1")
    assert RuleGeneratorV2.deparse(result.pattern_ast) == "CAST(V1 AS DATE)"
    assert RuleGeneratorV2.deparse(result.rewrite_ast) == "V1"


def test_deparse_2():
    result = RuleParserV2.parse("STRPOS(LOWER(V1), 'V2') > 0", "V1 ILIKE '%V2%'")
    assert RuleGeneratorV2.deparse(result.pattern_ast) == "STRPOS(LOWER(V1), 'V2') > 0"
    assert RuleGeneratorV2.deparse(result.rewrite_ast) == "V1 ILIKE '%V2%'"


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


def test_columns_1():
    result = RuleParserV2.parse("STRPOS(LOWER(text), 'iphone') > 0", "ILIKE(text, '%iphone%')")
    assert set(RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)) == {"text"}


def test_columns_2():
    result = RuleParserV2.parse("CAST(state_name AS TEXT)", "state_name")
    assert set(RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)) == {"state_name"}


def test_columns_excludes_variable_placeholders():
    result = RuleParserV2.parse(
        """
        select e1.name, e1.age, e2.salary
        from employee e1, employee e2
        where e1.<x1> = e2.<x1>
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


def test_columns_4():
    result = RuleParserV2.parse(
        """
        select e1.name, e1.age, e2.salary
        from employee e1, employee e2
        where e1.<x1> = e2.<x1>
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
    assert set(RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)) == {"name", "age", "salary"}


def test_columns_3():
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
    assert set(RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)) == {"name", "age", "salary", "id"}


def test_columns_5():
    result = RuleParserV2.parse(
        """
        select e1.*
        from employee e1, employee e2
        where e1.id = e2.id
          and e1.age > 17
          and e2.salary > 35000
        """,
        """
        select e1.*
        from employee e1
        where e1.age > 17
          and e1.salary > 35000
        """,
    )
    assert set(RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)) == {"*", "id", "age", "salary"}


def test_columns_6():
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
        from employee emp, department dept
        where emp.workdept = dept.deptno
          and dept.deptname = 'OPERATIONS'
        """,
    )
    assert set(RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)) == {"*", "workdept", "deptno", "deptname"}


def test_columns_7():
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
    assert set(RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)) == {"*", "admin_permission_id", "admin_role_id"}


def test_columns_8():
    result = RuleParserV2.parse(
        """
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
               adminpermi0_.description AS descript2_4_,
               adminpermi0_.is_friendly AS is_frien3_4_,
               adminpermi0_.name AS name4_4_,
               adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
          INNER JOIN blc_admin_role_permission_xref allroles1_
            ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
          INNER JOIN blc_admin_role adminrolei2_
            ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminpermi0_.is_friendly = 1
          AND adminrolei2_.admin_role_id = 1
        ORDER BY adminpermi0_.description ASC
        LIMIT 50
        """,
        """
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
               adminpermi0_.description AS descript2_4_,
               adminpermi0_.is_friendly AS is_frien3_4_,
               adminpermi0_.name AS name4_4_,
               adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
          INNER JOIN blc_admin_role_permission_xref allroles1_
            ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE adminpermi0_.is_friendly = 1
          AND allroles1_.admin_role_id = 1
        ORDER BY adminpermi0_.description ASC
        LIMIT 50
        """,
    )
    assert set(RuleGeneratorV2.columns(result.pattern_ast, result.rewrite_ast)) == {
        "admin_permission_id",
        "description",
        "is_friendly",
        "name",
        "permission_type",
        "admin_role_id",
    }


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


def test_tables_3():
    result = RuleParserV2.parse(
        """
        select <x1>.name, <x1>.age, <x2>.salary
        from <x1>, <x2>
        where <x1>.<x3> = <x2>.<x3>
          and <x1>.age > 17
          and <x2>.salary > 35000
        """,
        """
        select <x1>.name, <x1>.age, <x1>.salary
        from <x1>
        where <x1>.age > 17
          and <x1>.salary > 35000
        """,
    )
    assert RuleGeneratorV2.tables(result.pattern_ast, result.rewrite_ast) == []


def test_tables_3_excludes_variable_tables():
    result = RuleParserV2.parse(
        """
        select <x1>.name, <x1>.age, <x2>.salary
        from <x1>, <x2>
        where <x1>.<x3> = <x2>.<x3>
          and <x1>.age > 17
          and <x2>.salary > 35000
        """,
        """
        select <x1>.name, <x1>.age, <x1>.salary
        from <x1>
        where <x1>.age > 17
          and <x1>.salary > 35000
        """,
    )
    assert RuleGeneratorV2.tables(result.pattern_ast, result.rewrite_ast) == []


def test_tables_4():
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
    actual = {(t["value"], t["name"]) for t in RuleGeneratorV2.tables(result.pattern_ast, result.rewrite_ast)}
    assert actual == {("employee", "employee"), ("department", "department")}


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


def test_tables_5():
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
    actual = {(t["value"], t["name"]) for t in RuleGeneratorV2.tables(result.pattern_ast, result.rewrite_ast)}
    assert actual == {
        ("blc_admin_permission", "adminpermi0_"),
        ("blc_admin_role_permission_xref", "allroles1_"),
        ("blc_admin_role", "adminrolei2_"),
    }


def test_tables_6():
    result = RuleParserV2.parse(
        """
        SELECT Count(*)
        FROM (SELECT 1 AS one
              FROM group_histories
              WHERE group_histories.group_id = 2578
                AND group_histories.action = 2
              ORDER BY group_histories.created_at DESC
              LIMIT 25 offset 0) subquery_for_count
        """,
        """
        SELECT Count(*)
        FROM (SELECT 1 AS one
              FROM group_histories
              WHERE group_histories.group_id = 2578
                AND group_histories.action = 2
              LIMIT 25 offset 0) AS subquery_for_count
        """,
    )
    actual = {(t["value"], t["name"]) for t in RuleGeneratorV2.tables(result.pattern_ast, result.rewrite_ast)}
    assert actual == {("group_histories", "group_histories")}


def test_variablize_literal_1():
    rule = _build_rule("STRPOS(LOWER(text), 'iphone') > 0", "text ILIKE '%iphone%'")
    out = RuleGeneratorV2.variablize_literal(rule, "iphone")
    assert out["pattern"] == "STRPOS(LOWER(text), '<x1>') > 0"
    assert out["rewrite"] == "text ILIKE '%<x1>%'"


def test_variablize_literal_2():
    rule = _build_rule(
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
    out = RuleGeneratorV2.variablize_literal(rule, 17)
    assert "e1.age > <x1>" in out["pattern"]
    assert "e1.age > <x1>" in out["rewrite"]


def test_variablize_column_1():
    rule = _build_rule("CAST(created_at AS DATE)", "created_at")
    out = RuleGeneratorV2.variablize_column(rule, "created_at")
    assert out["pattern"] == "CAST(<x1> AS DATE)"
    assert out["rewrite"] == "<x1>"


def test_variablize_column_2():
    rule = _build_rule("STRPOS(LOWER(text), 'iphone') > 0", "text ILIKE '%iphone%'")
    out = RuleGeneratorV2.variablize_column(rule, "text")
    assert out["pattern"] == "STRPOS(LOWER(<x1>), 'iphone') > 0"
    assert out["rewrite"] == "<x1> ILIKE '%iphone%'"


def test_variablize_column_3():
    rule = _build_rule(
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
    out = RuleGeneratorV2.variablize_column(rule, "id")
    assert _norm_sql(out["pattern"]) == _norm_sql(
        "SELECT e1.name, e1.age, e2.salary FROM employee AS e1, employee AS e2 WHERE e1.<x1> = e2.<x1> AND e1.age > 17 AND e2.salary > 35000"
    )
    assert _norm_sql(out["rewrite"]) == _norm_sql(
        "SELECT e1.name, e1.age, e1.salary FROM employee AS e1 WHERE e1.age > 17 AND e1.salary > 35000"
    )


def test_variablize_column_4():
    rule = _build_rule(
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
        from employee emp, department dept
        where emp.workdept = dept.deptno
          and dept.deptname = 'OPERATIONS'
        """,
    )
    out = RuleGeneratorV2.variablize_column(rule, "*")
    assert _norm_sql(out["pattern"]) == _norm_sql(
        "SELECT <x1> FROM employee WHERE workdept IN (SELECT deptno FROM department WHERE deptname = 'OPERATIONS')"
    )
    assert _norm_sql(out["rewrite"]) == _norm_sql(
        "SELECT DISTINCT <x1> FROM employee AS emp, department AS dept WHERE emp.workdept = dept.deptno AND dept.deptname = 'OPERATIONS'"
    )


def test_variablize_table_1():
    rule = _build_rule(
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
    out = RuleGeneratorV2.variablize_table(rule, {"value": "employee", "name": "e1"})
    assert "FROM <x1>, employee AS e2" in out["pattern"] or "FROM <x1>, employee e2" in out["pattern"]
    assert "<x1>.id = e2.id" in out["pattern"]
    assert ("FROM <x1>" in out["rewrite"]) or ("FROM x1" in out["rewrite"])


def test_variablize_table_2():
    rule = _build_rule(
        """
        SELECT <x1>.name, <x1>.age, e2.salary
        FROM <x1>, employee AS e2
        WHERE <x1>.id = e2.id
          AND <x1>.age > 17
          AND e2.salary > 35000
        """,
        """
        SELECT <x1>.name, <x1>.age, <x1>.salary
        FROM <x1>
        WHERE <x1>.age > 17
          AND <x1>.salary > 35000
        """,
    )
    out = RuleGeneratorV2.variablize_table(rule, {"value": "employee", "name": "e2"})
    assert "FROM <x1>, <x2>" in out["pattern"]
    assert "<x1>.id = <x2>.id" in out["pattern"]
    assert "<x2>.salary > 35000" in out["pattern"]
    assert "FROM <x1>" in out["rewrite"]


def test_variablize_table_3():
    rule = _build_rule(
        """
        SELECT COUNT(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM blc_admin_permission adminpermi0_
          INNER JOIN blc_admin_role_permission_xref allroles1_
            ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
          INNER JOIN blc_admin_role adminrolei2_
            ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminpermi0_.is_friendly = 1
          AND adminrolei2_.admin_role_id = 1
        """,
        """
        SELECT COUNT(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM blc_admin_permission AS adminpermi0_
          INNER JOIN blc_admin_role_permission_xref AS allroles1_
            ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE allroles1_.admin_role_id = 1
          AND adminpermi0_.is_friendly = 1
        """,
    )
    out = RuleGeneratorV2.variablize_table(
        rule, {"value": "blc_admin_permission", "name": "adminpermi0_"}
    )
    assert "FROM <x1>" in out["pattern"]
    assert "JOIN blc_admin_role_permission_xref AS allroles1_" in out["pattern"]
    assert "<x1>.admin_permission_id = allroles1_.admin_permission_id" in out["pattern"]
    assert "<x1>.is_friendly = 1" in out["pattern"]
    assert "FROM <x1>" in out["rewrite"]


def test_subtrees_1():
    result = RuleParserV2.parse("STRPOS(LOWER(text), 'iphone') > 0", "text ILIKE '%iphone%'")
    assert RuleGeneratorV2.subtrees(result.pattern_ast, result.rewrite_ast) == []


def test_subtrees_2():
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
    assert RuleGeneratorV2.subtrees(result.pattern_ast, result.rewrite_ast) == []


def test_subtrees_3():
    result = RuleParserV2.parse(
        """
        select <x1>.name, <x1>.age, <x2>.salary
        from <x1>, <x2>
        where <x1>.<x3> = <x2>.<x3>
          and <x1>.age > 17
          and <x2>.salary > 35000
        """,
        """
        select <x1>.name, <x1>.age, <x1>.salary
        from <x1>
        where <x1>.age > 17
          and <x1>.salary > 35000
        """,
    )
    assert RuleGeneratorV2.subtrees(result.pattern_ast, result.rewrite_ast) == []


def test_subtrees_4():
    result = RuleParserV2.parse(
        """
        select <x1>.<x2>, <x1>.age, <x3>.salary
        from <x1>, <x3>
        where <x1>.<x4> = <x3>.<x4>
          and <x1>.age > 17
          and <x3>.salary > 35000
        """,
        """
        select <x1>.<x2>, <x1>.age, <x1>.salary
        from <x1>
        where <x1>.age > 17
          and <x1>.salary > 35000
        """,
    )
    assert [RuleGeneratorV2.deparse(t) for t in RuleGeneratorV2.subtrees(result.pattern_ast, result.rewrite_ast)] == ["<x1>.<x2>"]


def test_subtrees_5():
    result = RuleParserV2.parse(
        """
        SELECT <x1>.<x7> AS admin_pe1_4_, <x1>.<x6> AS descript2_4_, <x1>.<x8> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x4> AS permissi5_4_
        FROM <x1>
        INNER JOIN <x2> ON <x1>.<x7> = <x2>.<x7>
        INNER JOIN <x3> ON <x2>.<x5> = <x3>.<x5>
        WHERE <x1>.<x8> = <x10>
        AND <x3>.<x5> = <x10>
        ORDER BY <x1>.<x6> ASC
        LIMIT <x11>
        """,
        """
        SELECT <x1>.<x7> AS admin_pe1_4_, <x1>.<x6> AS descript2_4_, <x1>.<x8> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x4> AS permissi5_4_
        FROM <x1>
        INNER JOIN <x2> ON <x1>.<x7> = <x2>.<x7>
        WHERE <x1>.<x8> = <x10>
        AND <x2>.<x5> = <x10>
        ORDER BY <x1>.<x6> ASC
        LIMIT <x11>
        """,
    )
    actual = set(RuleGeneratorV2.deparse(t) for t in RuleGeneratorV2.subtrees(result.pattern_ast, result.rewrite_ast))
    assert actual == {
        "<x1>.<x8> = <x10>",
        "<x1>.<x7> = <x2>.<x7>",
        "<x1>.<x4>",
        "<x1>.<x9>",
        "<x1>.<x8>",
        "<x1>.<x6>",
        "<x1>.<x7>",
    }


def test_variablize_subtree_1():
    rule = _build_rule(
        """
        select <x1>.<x2>, <x1>.age, <x3>.salary
        from <x1>, <x3>
        where <x1>.<x4> = <x3>.<x4>
          and <x1>.age > 17
          and <x3>.salary > 35000
        """,
        """
        select <x1>.<x2>, <x1>.age, <x1>.salary
        from <x1>
        where <x1>.age > 17
          and <x1>.salary > 35000
        """,
    )
    subtree = RuleGeneratorV2.subtrees(rule["pattern_ast"], rule["rewrite_ast"])[0]
    out = RuleGeneratorV2.variablize_subtree(rule, subtree)
    assert _norm_sql(out["pattern"]) == _norm_sql(
        "SELECT <x5>, <x1>.age, <x3>.salary FROM <x1>, <x3> WHERE <x1>.<x4> = <x3>.<x4> AND <x1>.age > 17 AND <x3>.salary > 35000"
    )
    assert _norm_sql(out["rewrite"]) == _norm_sql(
        "SELECT <x5>, <x1>.age, <x1>.salary FROM <x1> WHERE <x1>.age > 17 AND <x1>.salary > 35000"
    )


def test_variablize_subtrees_1():
    rule = _build_rule(
        """
        SELECT <x1>.<x7> AS admin_pe1_4_, <x1>.<x6> AS descript2_4_, <x1>.<x8> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x4> AS permissi5_4_
        FROM <x1>
        INNER JOIN <x2> ON <x1>.<x7> = <x2>.<x7>
        INNER JOIN <x3> ON <x2>.<x5> = <x3>.<x5>
        WHERE <x1>.<x8> = <x10>
        AND <x3>.<x5> = <x10>
        ORDER BY <x1>.<x6> ASC
        LIMIT <x11>
        """,
        """
        SELECT <x1>.<x7> AS admin_pe1_4_, <x1>.<x6> AS descript2_4_, <x1>.<x8> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x4> AS permissi5_4_
        FROM <x1>
        INNER JOIN <x2> ON <x1>.<x7> = <x2>.<x7>
        WHERE <x1>.<x8> = <x10>
        AND <x2>.<x5> = <x10>
        ORDER BY <x1>.<x6> ASC
        LIMIT <x11>
        """,
    )
    children = RuleGeneratorV2.variablize_subtrees(rule)
    assert len(children) == 7


def test_variable_lists_1():
    result = RuleParserV2.parse(
        """
        SELECT <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        INNER JOIN <x2> ON <x13>
        INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
        WHERE <x12>
        AND <x3>.<x4> = <x10>
        ORDER BY <x1>.<x9> ASC
        LIMIT <x11>
        """,
        """
        SELECT <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        INNER JOIN <x2> ON <x13>
        WHERE <x12>
        AND <x2>.<x4> = <x10>
        ORDER BY <x1>.<x9> ASC
        LIMIT <x11>
        """,
    )
    variable_lists = RuleGeneratorV2.variable_lists(result.pattern_ast, result.rewrite_ast)
    normalized = {",".join(sorted(v)) for v in variable_lists}
    assert "x14,x15,x16,x17,x18" in normalized
    assert "x12" in normalized
    assert "x11" in normalized


def test_variable_lists_2():
    result = RuleParserV2.parse(
        """
        SELECT <x11>
        FROM <x1>
        INNER JOIN <x2> ON <x9>
        INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
        WHERE <x8>
        AND <x3>.<x4> = <x7>
        """,
        """
        SELECT <x11>
        FROM <x1>
        INNER JOIN <x2> ON <x9>
        WHERE <x2>.<x4> = <x7>
        AND <x8>
        """,
    )
    variable_lists = RuleGeneratorV2.variable_lists(result.pattern_ast, result.rewrite_ast)
    normalized = {",".join(sorted(v)) for v in variable_lists}
    assert "x11" in normalized
    assert "x8" in normalized


def test_variable_lists_3():
    result = RuleParserV2.parse(
        """
        SELECT <x19>, <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        LEFT OUTER JOIN <x2> ON <x13>
        LEFT OUTER JOIN <x3> ON <x2>.<x11> = <x3>.<x4>
        WHERE <x3>.<x4> = <x12>
        """,
        """
        SELECT <x19>, <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        LEFT OUTER JOIN <x2> ON <x13>
        WHERE <x2>.<x11> = <x12>
        """,
    )
    variable_lists = RuleGeneratorV2.variable_lists(result.pattern_ast, result.rewrite_ast)
    normalized = {tuple(sorted(v)) for v in variable_lists}
    assert ("x13",) in normalized
    assert ("x14", "x15", "x16", "x17", "x18", "x19") in normalized


def test_merge_variable_list_1():
    rule = _build_rule(
        """
        SELECT <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        INNER JOIN <x2> ON <x13>
        INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
        WHERE <x12>
        AND <x3>.<x4> = <x10>
        ORDER BY <x1>.<x9> ASC
        LIMIT <x11>
        """,
        """
        SELECT <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        INNER JOIN <x2> ON <x13>
        WHERE <x12>
        AND <x2>.<x4> = <x10>
        ORDER BY <x1>.<x9> ASC
        LIMIT <x11>
        """,
    )
    out = RuleGeneratorV2.merge_variable_list(rule, ["x18", "x17", "x16", "x15", "x14"])
    assert "SELECT <<y1>>" in out["pattern"]
    assert "SELECT <<y1>>" in out["rewrite"]


def test_merge_variable_list_2():
    rule = _build_rule(
        """
        SELECT <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        INNER JOIN <x2> ON <x13>
        INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4>
        WHERE <x12>
        AND <x3>.<x4> = <x10>
        ORDER BY <x1>.<x9> ASC
        LIMIT <x11>
        """,
        """
        SELECT <x18>, <x17>, <x16>, <x15>, <x14>
        FROM <x1>
        INNER JOIN <x2> ON <x13>
        WHERE <x12>
        AND <x2>.<x4> = <x10>
        ORDER BY <x1>.<x9> ASC
        LIMIT <x11>
        """,
    )
    out = RuleGeneratorV2.merge_variable_list(rule, ["x11"])
    assert "LIMIT <<y1>>" in out["pattern"]
    assert "LIMIT <<y1>>" in out["rewrite"]


def test_branches_1():
    result = RuleParserV2.parse(
        "SELECT <<x>> FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        "SELECT <<x>> FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
    )
    branches = RuleGeneratorV2.branches(result.pattern_ast, result.rewrite_ast)
    assert {"key": "select", "value": "set_variable"} in branches


def test_branches_2():
    result = RuleParserV2.parse(
        "FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        "FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
    )
    branches = RuleGeneratorV2.branches(result.pattern_ast, result.rewrite_ast)
    assert {"key": "from", "value": "table_sources"} in branches


def test_branches_3():
    result = RuleParserV2.parse(
        "WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        "WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
    )
    branches = RuleGeneratorV2.branches(result.pattern_ast, result.rewrite_ast)
    assert {"key": "where", "value": None} in branches


def test_branches_4():
    result = RuleParserV2.parse(
        "CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        "created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
    )
    branches = RuleGeneratorV2.branches(result.pattern_ast, result.rewrite_ast)
    actual = {(b["key"], RuleGeneratorV2.deparse(b["value"])) for b in branches}
    assert actual == {("eq_rhs", "TIMESTAMP('2016-10-01 00:00:00.000')")}


def test_branches_5():
    result = RuleParserV2.parse(
        "SELECT * FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        "SELECT * FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
    )
    branches = RuleGeneratorV2.branches(result.pattern_ast, result.rewrite_ast)
    actual = {(b["key"], b["value"]) for b in branches if isinstance(b["value"], str)}
    assert ("select", "all_columns") in actual


def test_drop_branch_1():
    rule = _build_rule(
        "SELECT <<x>> FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        "SELECT <<x>> FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
    )
    out = RuleGeneratorV2.drop_branch(rule, {"key": "select", "value": "set_variable"})
    parsed = RuleParserV2.parse(out["pattern"], out["rewrite"])
    assert isinstance(parsed.pattern_ast, QueryNode)
    assert isinstance(parsed.rewrite_ast, QueryNode)
    assert _has_clause(parsed.pattern_ast, NodeType.SELECT) is False
    assert _has_clause(parsed.rewrite_ast, NodeType.SELECT) is False
    assert _has_clause(parsed.pattern_ast, NodeType.FROM) is True
    assert _has_clause(parsed.rewrite_ast, NodeType.FROM) is True
    assert _has_clause(parsed.pattern_ast, NodeType.WHERE) is True
    assert _has_clause(parsed.rewrite_ast, NodeType.WHERE) is True


def test_drop_branch_2():
    rule = _build_rule(
        "FROM <t> WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        "FROM <t> WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
    )
    out = RuleGeneratorV2.drop_branch(rule, {"key": "from", "value": "table_sources"})
    parsed = RuleParserV2.parse(out["pattern"], out["rewrite"])
    assert isinstance(parsed.pattern_ast, QueryNode)
    assert isinstance(parsed.rewrite_ast, QueryNode)
    assert _has_clause(parsed.pattern_ast, NodeType.SELECT) is False
    assert _has_clause(parsed.rewrite_ast, NodeType.SELECT) is False
    assert _has_clause(parsed.pattern_ast, NodeType.FROM) is False
    assert _has_clause(parsed.rewrite_ast, NodeType.FROM) is False
    assert _has_clause(parsed.pattern_ast, NodeType.WHERE) is True
    assert _has_clause(parsed.rewrite_ast, NodeType.WHERE) is True


def test_drop_branch_3():
    rule = _build_rule(
        "WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        "WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
    )
    out = RuleGeneratorV2.drop_branch(rule, {"key": "where", "value": None})
    parsed = RuleParserV2.parse(out["pattern"], out["rewrite"])
    assert not isinstance(parsed.pattern_ast, QueryNode)
    assert not isinstance(parsed.rewrite_ast, QueryNode)


def test_drop_branch_4():
    rule = _build_rule(
        "CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
        "created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
    )
    branch = RuleGeneratorV2.branches(rule["pattern_ast"], rule["rewrite_ast"])[0]
    out = RuleGeneratorV2.drop_branch(rule, branch)
    assert _norm_sql(out["pattern"]) == _norm_sql("CAST(created_at AS DATE)")
    assert _norm_sql(out["rewrite"]) == _norm_sql("created_at")


def test_fingerprint_normalizes_numbered_placeholders():
    rule = _build_rule("SELECT <x9>, <x2> FROM <x10> WHERE <<y4>>", "SELECT <x9> FROM <x10> WHERE <<y4>>")
    fp = RuleGeneratorV2.fingerPrint(rule)
    assert "<x>" in fp
    assert "<<y>>" in fp
    assert "<x9>" not in fp
    assert "<<y4>>" not in fp


def test_fingerprint_same_for_renamed_variables():
    rule1 = _build_rule("CAST(<x1> AS DATE)", "<x1>")
    rule2 = _build_rule("CAST(<x7> AS DATE)", "<x7>")
    assert RuleGeneratorV2.fingerPrint(rule1) == RuleGeneratorV2.fingerPrint(rule2)


def test_unify_variable_names_1():
    q0 = "FROM <<x9>> INNER JOIN <x10> ON <<x9>>.<x5> = <x10>.<x6>"
    q1 = "FROM <x10>"
    a, b = RuleGeneratorV2.unify_variable_names(q0, q1)
    assert a == "FROM <<x1>> INNER JOIN <x2> ON <<x1>>.<x3> = <x2>.<x4>"
    assert b == "FROM <x2>"


def test_unify_variable_names_2():
    q0 = "<x2> <<x1>>"
    q1 = "<x2>"
    a, b = RuleGeneratorV2.unify_variable_names(q0, q1)
    assert a == "<x1> <<x2>>"
    assert b == "<x1>"


def test_unify_variable_names_3():
    q0 = "<x> <<x1>> <x> <x> <y>"
    q1 = "<x> <<x1>> <y>"
    a, b = RuleGeneratorV2.unify_variable_names(q0, q1)
    assert a == "<x1> <<x2>> <x1> <x1> <x3>"
    assert b == "<x1> <<x2>> <x3>"


def test_number_of_variables():
    rule = _build_rule("SELECT <x1>, <<y1>> FROM <x2>", "SELECT <x1>, <<y1>> FROM <x2>")
    assert RuleGeneratorV2.numberOfVariables(rule) == 3


def test_generate_general_rule_1():
    rule = RuleGeneratorV2.generate_general_rule("SELECT CAST(created_at AS DATE)", "SELECT created_at")
    assert rule["pattern"] == "CAST(<x1> AS DATE)"
    assert rule["rewrite"] == "<x1>"


def test_generate_general_rule_2():
    rule = RuleGeneratorV2.generate_general_rule(
        "SELECT STRPOS(LOWER(text), 'iphone') > 0",
        "SELECT ILIKE(text, '%iphone%')",
    )
    assert rule["pattern"] == "STRPOS(LOWER(<x1>), '<x2>') > 0"
    assert rule["rewrite"] == "<x1> ILIKE '%<x2>%'"


def test_generate_general_rule_8():
    q0 = "SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'"
    q1 = "SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'"
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    assert RuleGeneratorV2._fingerPrint(rule["pattern"]) == RuleGeneratorV2._fingerPrint("CAST(<x1> AS DATE)")
    assert RuleGeneratorV2._fingerPrint(rule["rewrite"]) == RuleGeneratorV2._fingerPrint("<x1>")


def test_generate_general_rule_3():
    q0 = """
        select e1.name, e1.age, e2.salary
        from employee e1,
            employee e2
        where e1.id = e2.id
        and e1.age > 17
        and e2.salary > 35000
    """
    q1 = """
        SELECT e1.name, e1.age, e1.salary
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    got_p, got_r = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    exp_p, exp_r = RuleGeneratorV2.unify_variable_names(
        "SELECT <<x1>>, <x2>.<x3> WHERE <x1>.<x4> = <x2>.<x4> AND <x1>.<x5> > <x6> AND <x2>.<x3> > <x7>",
        "SELECT <<x1>>, <x1>.<x3> WHERE <x1>.<x5> > <x6> AND <x1>.<x3> > <x7>",
    )
    assert _norm_sql(got_p) == _norm_sql(exp_p)
    assert _norm_sql(got_r) == _norm_sql(exp_r)


def test_generate_general_rule_4():
    q0 = """
        SELECT *
        FROM blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminrolei2_.admin_role_id = 1
    """
    q1 = """
        SELECT *
        FROM blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE allroles1_.admin_role_id = 1
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    got_p, got_r = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    exp_p, exp_r = RuleGeneratorV2.unify_variable_names(
        "FROM <x1> INNER JOIN <x2> ON <x1>.<x3> = <x2>.<x3> INNER JOIN <x4> ON <x2>.<x5> = <x4>.<x5>",
        "FROM <x1> INNER JOIN <x2> ON <x1>.<x3> = <x2>.<x3>",
    )
    assert _norm_sql(got_p) == _norm_sql(exp_p)
    assert _norm_sql(got_r) == _norm_sql(exp_r)


def test_generate_general_rule_5():
    q0 = """
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
               adminpermi0_.description AS descript2_4_,
               adminpermi0_.is_friendly AS is_frien3_4_,
               adminpermi0_.name AS name4_4_,
               adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminpermi0_.is_friendly = 1
          AND adminrolei2_.admin_role_id = 1
        ORDER BY adminpermi0_.description ASC
        LIMIT 50
    """
    q1 = """
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
               adminpermi0_.description AS descript2_4_,
               adminpermi0_.is_friendly AS is_frien3_4_,
               adminpermi0_.name AS name4_4_,
               adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE adminpermi0_.is_friendly = 1
          AND allroles1_.admin_role_id = 1
        ORDER BY adminpermi0_.description ASC
        LIMIT 50
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    got_p, got_r = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    exp_p, exp_r = RuleGeneratorV2.unify_variable_names(
        "SELECT <<x1>> FROM <x2> INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4> INNER JOIN <x5> ON <x3>.<x6> = <x5>.<x6> ORDER BY <x2>.<x7> ASC LIMIT 50",
        "SELECT <<x1>> FROM <x2> INNER JOIN <x3> ON <x2>.<x4> = <x3>.<x4> ORDER BY <x2>.<x7> ASC LIMIT 50",
    )
    assert _norm_sql(got_p) == _norm_sql(exp_p)
    assert _norm_sql(got_r) == _norm_sql(exp_r)


def test_generate_general_rule_6():
    q0 = """
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminpermi0_.is_friendly = 1
          AND adminrolei2_.admin_role_id = 1
    """
    q1 = """
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE allroles1_.admin_role_id = 1
          AND adminpermi0_.is_friendly = 1
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    got_p, got_r = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    exp_p, exp_r = RuleGeneratorV2.unify_variable_names(
        "SELECT COUNT(<x1>.<x2>) AS col_0_0_ FROM <x1> INNER JOIN <x3> ON <x1>.<x2> = <x3>.<x2> INNER JOIN <x4> ON <x3>.<x5> = <x4>.<x5>",
        "SELECT COUNT(<x1>.<x2>) AS col_0_0_ FROM <x1> INNER JOIN <x3> ON <x1>.<x2> = <x3>.<x2>",
    )
    assert _norm_sql(got_p) == _norm_sql(exp_p)
    assert _norm_sql(got_r) == _norm_sql(exp_r)


def test_generate_general_rule_7():
    q0 = """
        SELECT o_auth_applications.id
        FROM o_auth_applications
            INNER JOIN authorizations
                ON o_auth_applications.id = authorizations.o_auth_application_id
        WHERE authorizations.user_id = 1465
    """
    q1 = """
        SELECT authorizations.o_auth_application_id
        FROM authorizations AS authorizations
        WHERE authorizations.user_id = 1465
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    got_p, got_r = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    exp_p, exp_r = RuleGeneratorV2.unify_variable_names(
        "SELECT <x1>.<x2> FROM <x1> INNER JOIN <x3> ON <x1>.<x2> = <x3>.<x4> WHERE <x3>.<x5> = <x6>",
        "SELECT <x3>.<x4> FROM <x3> WHERE <x3>.<x5> = <x6>",
    )
    assert _norm_sql(got_p) == _norm_sql(exp_p)
    assert _norm_sql(got_r) == _norm_sql(exp_r)


def test_generate_general_rule_9():
    q0 = """
        SELECT SUM(1), CAST(state_name AS TEXT)
        FROM tweets
        WHERE CAST(DATE_TRUNC('QUARTER', CAST(created_at AS DATE)) AS DATE) IN
              ((TIMESTAMP '2016-10-01 00:00:00.000'),
               (TIMESTAMP '2017-01-01 00:00:00.000'),
               (TIMESTAMP '2017-04-01 00:00:00.000'))
          AND (STRPOS(LOWER(text), 'iphone') > 0)
        GROUP BY 2
    """
    q1 = """
        SELECT SUM(1), CAST(state_name AS TEXT)
        FROM tweets
        WHERE CAST(DATE_TRUNC('QUARTER', CAST(created_at AS DATE)) AS DATE) IN
              ((TIMESTAMP '2016-10-01 00:00:00.000'),
               (TIMESTAMP '2017-01-01 00:00:00.000'),
               (TIMESTAMP '2017-04-01 00:00:00.000'))
          AND text ILIKE '%iphone%'
        GROUP BY 2
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    got_p, got_r = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    exp_p, exp_r = RuleGeneratorV2.unify_variable_names(
        "SELECT SUM(<x1>), CAST(<x2> AS TEXT) WHERE CAST(DATE_TRUNC('<x3>', CAST(<x4> AS DATE)) AS DATE) IN (TIMESTAMP('<x5>'), TIMESTAMP('<x6>'), TIMESTAMP('<x7>')) AND STRPOS(LOWER(<x8>), '<x9>') > 0 GROUP BY <x10>",
        "SELECT SUM(<x1>), CAST(<x2> AS TEXT) WHERE CAST(DATE_TRUNC('<x3>', CAST(<x4> AS DATE)) AS DATE) IN (TIMESTAMP('<x5>'), TIMESTAMP('<x6>'), TIMESTAMP('<x7>')) AND <x8> ILIKE '%<x9>%' GROUP BY <x10>",
    )
    assert _norm_sql(got_p) == _norm_sql(exp_p)
    assert _norm_sql(got_r) == _norm_sql(exp_r)


def test_generate_general_rule_10():
    q0 = """
        select *
        from employee
        where workdept in
            (select deptno from department where deptname = 'OPERATIONS')
    """
    q1 = """
        select distinct *
        from employee, department
        where employee.workdept = department.deptno
          and department.deptname = 'OPERATIONS'
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    assert RuleGeneratorV2._fingerPrint(rule["pattern"]) == RuleGeneratorV2._fingerPrint(
        "SELECT <x3> FROM <x1> WHERE <x6> IN (SELECT <x5> FROM <x2> WHERE <x4> = <x8>)"
    )
    assert RuleGeneratorV2._fingerPrint(rule["rewrite"]) == RuleGeneratorV2._fingerPrint(
        "SELECT DISTINCT <x3> FROM <x1>, <x2> WHERE <x1>.<x6> = <x2>.<x5> AND <x2>.<x4> = <x8>"
    )


def test_generate_general_rule_11():
    q0 = """
        SELECT Count(*)
        FROM (SELECT 1 AS one
              FROM group_histories
              WHERE group_histories.group_id = 2578
                AND group_histories.action = 2
              ORDER BY group_histories.created_at DESC
              LIMIT 25 offset 0) subquery_for_count
    """
    q1 = """
        SELECT Count(*)
        FROM (SELECT 1 AS one
              FROM group_histories
              WHERE group_histories.group_id = 2578
                AND group_histories.action = 2
              LIMIT 25 offset 0) AS subquery_for_count
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    assert RuleGeneratorV2._fingerPrint(rule["pattern"]) == RuleGeneratorV2._fingerPrint(
        "FROM <x1> ORDER BY <x1>.<x2> DESC"
    )
    assert RuleGeneratorV2._fingerPrint(rule["rewrite"]) == RuleGeneratorV2._fingerPrint("FROM <x1>")


def test_generate_general_rule_12():
    q0 = "SELECT student.ids from student WHERE student.id = 100 AND student.abc = 100"
    q1 = "SELECT student.id from student WHERE student.id = 100"
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "SELECT <x1>.<x2> FROM <x1> WHERE <<x3>> AND <x1>.<x4> = <x5>"
    assert q1_rule == "SELECT <x1>.<x6> FROM <x1> WHERE <<x3>>"


def test_generate_general_rule_13():
    q0 = """
        SELECT COUNT(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM blc_admin_permission adminpermi0_
        INNER JOIN blc_admin_role_permission_xref allroles1_
          ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        INNER JOIN blc_admin_role adminrolei2_
          ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminpermi0_.is_friendly = 1 AND adminrolei2_.admin_role_id = 1
    """
    q1 = """
        SELECT COUNT(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM blc_admin_permission AS adminpermi0_
        INNER JOIN blc_admin_role_permission_xref AS allroles1_
          ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE allroles1_.admin_role_id = 1 AND adminpermi0_.is_friendly = 1
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    p, r = RuleGeneratorV2.unify_variable_names(
        "FROM <x1> INNER JOIN <x2> ON <<x3>> INNER JOIN <x4> ON <x2>.<x5> = <x4>.<x5> WHERE <<x6>> AND <x4>.<x5> = <x7>",
        "FROM <x1> INNER JOIN <x2> ON <<x3>> WHERE <x2>.<x5> = <x7> AND <<x6>>",
    )
    assert _norm_sql(q0_rule) == _norm_sql(p)
    assert _norm_sql(q1_rule) == _norm_sql(r)


def test_generate_general_rule_14():
    q0 = """select distinct c.customer_id from table1 c join table2 l on c.customer_id = l.customer_id join table3 cal on c.customer_id = cal.customer_id WHERE (l.customer_group_id = 'loyalty' and c.loyalty_number = '123456789') or (cal.account_id = '123456789' and cal.account_type  = 'loyalty')"""
    q1 = """SELECT customer_id FROM table1 c JOIN table2 l USING (customer_id) JOIN table3 cal USING (customer_id) WHERE l.customer_group_id = 'loyalty' AND c.loyalty_number = '123456789' UNION SELECT customer_id FROM table1 c JOIN table2 l USING (customer_id) JOIN table3 cal USING (customer_id) WHERE cal.account_id = '123456789' AND cal.account_type  = 'loyalty'"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert _norm_sql(q0_rule) == _norm_sql("SELECT DISTINCT <x1>.<x2> FROM <x1> JOIN <x3> ON <x1>.<x2> = <x3>.<x2> JOIN <x4> ON <x1>.<x2> = <x4>.<x2> WHERE <x5> OR <x6>")
    assert _norm_sql(q1_rule) == _norm_sql("SELECT <x2> FROM <x1> JOIN <x3> USING <x2> JOIN <x4> USING <x2> WHERE <x5> UNION SELECT <x2> FROM <x1> JOIN <x3> USING <x2> JOIN <x4> USING <x2> WHERE <x6>")


def test_generate_general_rule_15():
    q0 = "select * from A a left join B b on a.id = b.cid where b.cl1 = 's1' or b.cl1 ='s2' or b.cl1 ='s3'"
    q1 = "select * from A a left join B b  on a.id = b.cid where b.cl1 in ('s1','s2','s3')"
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "<x1>.<x2> = '<x3>' OR <x1>.<x2> = '<x4>' OR <x1>.<x2> = '<x5>'"
    assert q1_rule == "<x1>.<x2> IN ('<x3>', '<x4>', '<x5>')"


def test_generate_general_rule_16():
    q0 = """SELECT historicoestatusrequisicion_id, requisicion_id, estatusrequisicion_id, comentario, fecha_estatus, usuario_id FROM historicoestatusrequisicion hist1 WHERE requisicion_id IN (SELECT requisicion_id FROM historicoestatusrequisicion hist2 WHERE usuario_id = 27 AND estatusrequisicion_id = 1) ORDER BY requisicion_id, estatusrequisicion_id"""
    q1 = """SELECT hist1.historicoestatusrequisicion_id, hist1.requisicion_id, hist1.estatusrequisicion_id, hist1.comentario, hist1.fecha_estatus, hist1.usuario_id FROM historicoestatusrequisicion hist1 JOIN historicoestatusrequisicion hist2 ON hist2.requisicion_id = hist1.requisicion_id WHERE hist2.usuario_id = 27 AND hist2.estatusrequisicion_id = 1 ORDER BY hist1.requisicion_id, hist1.estatusrequisicion_id"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert _norm_sql(q0_rule) == _norm_sql("SELECT <x1>, <x2>, <x3>, <x4>, <x5>, <x6> FROM <x7> WHERE <x2> IN (SELECT <x2> FROM <x8> WHERE <x6> = <x9> AND <x3> = <x10>) ORDER BY <x2>, <x3>")
    assert _norm_sql(q1_rule) == _norm_sql("SELECT <x7>.<x1>, <x7>.<x2>, <x7>.<x3>, <x7>.<x4>, <x7>.<x5>, <x7>.<x6> FROM <x7> JOIN <x8> ON <x8>.<x2> = <x7>.<x2> WHERE <x8>.<x6> = <x9> AND <x8>.<x3> = <x10> ORDER BY <x7>.<x2>, <x7>.<x3>")


def test_generate_general_rule_17():
    q0 = """select wpis_id from spoleczniak_oznaczone where etykieta_id in( select tag_id from spoleczniak_subskrypcje where postac_id = 376476 )"""
    q1 = """select spoleczniak_oznaczone.wpis_id from spoleczniak_oznaczone inner join spoleczniak_subskrypcje on spoleczniak_subskrypcje.tag_id = spoleczniak_oznaczone.etykieta_id where spoleczniak_subskrypcje.postac_id = 376476"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert _norm_sql(q0_rule) == _norm_sql("SELECT <x1> FROM <x2> WHERE <x3> IN (SELECT <x4> FROM <x5> WHERE <x6> = <x7>)")
    assert _norm_sql(q1_rule) == _norm_sql("SELECT <x2>.<x1> FROM <x2> INNER JOIN <x5> ON <x5>.<x4> = <x2>.<x3> WHERE <x5>.<x6> = <x7>")


def test_generate_general_rule_18():
    q0 = "SELECT EMP.EMPNO FROM EMP WHERE EMP.EMPNO > 10 AND EMP.EMPNO <= 10"
    q1 = "SELECT EMPNO FROM EMP WHERE FALSE"
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    assert rule["pattern"] == "SELECT <x1>.<x2> FROM <x1> WHERE <x1>.<x2> > <x3> AND <x1>.<x2> <= <x3>"
    assert rule["rewrite"] == "SELECT <x2> FROM <x1> WHERE False"


def test_generate_general_rule_19():
    q0 = "SELECT max(id) FROM Emp"
    q1 = "SELECT max(DISTINCT id) FROM Emp"
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "MAX(<x1>)"
    assert q1_rule == "MAX(DISTINCT <x1>)"


def test_generate_general_rule_20():
    q0 = """
        SELECT *
        FROM accounts
        WHERE LOWER(accounts.firstname) = LOWER('Sam')
          AND accounts.id IN (
              SELECT addresses.account_id
              FROM addresses
              WHERE LOWER(addresses.name) = LOWER('Street1')
          )
          AND accounts.id IN (
              SELECT alternate_ids.account_id
              FROM alternate_ids
              WHERE alternate_ids.alternate_id_glbl = '5'
          )
    """
    q1 = """
        SELECT *
        FROM accounts
        JOIN addresses ON accounts.id = addresses.account_id
        JOIN alternate_ids ON accounts.id = alternate_ids.account_id
        WHERE LOWER(accounts.firstname) = LOWER('Sam')
          AND LOWER(addresses.name) = LOWER('Street1')
          AND alternate_ids.alternate_id_glbl = '5'
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert _norm_sql(q0_rule) == _norm_sql(
        "FROM <x1> WHERE LOWER(<x1>.<x2>) = LOWER('<x3>') AND <x1>.<x4> IN (SELECT <x5>.<x6> FROM <x5> WHERE LOWER(<x5>.<x7>) = LOWER('<x8>')) AND <x1>.<x4> IN (SELECT <x9>.<x6> FROM <x9> WHERE <<x10>>)"
    )
    assert _norm_sql(q1_rule) == _norm_sql(
        "FROM <x1> JOIN <x5> ON <x1>.<x4> = <x5>.<x6> JOIN <x9> ON <x1>.<x4> = <x9>.<x6> WHERE LOWER(<x1>.<x2>) = LOWER('<x3>') AND LOWER(<x5>.<x7>) = LOWER('<x8>') AND <<x10>>"
    )


def test_generate_general_rule_21():
    q0 = """
        SELECT product.name, category.description, category.category_id
        FROM product NATURAL JOIN category
        WHERE product.price > 100
          AND product.category_id = 4
    """
    q1 = """
        SELECT product.name, category.description, category.category_id
        FROM product INNER JOIN category ON product.category_id = category.category_id
        WHERE product.price > 100
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert _norm_sql(q0_rule) == _norm_sql(
        "SELECT <x1>.<x2>, <x3>.<x4>, <x3>.<x5> FROM <x1> JOIN <x3> WHERE <<x6>> AND <x1>.<x5> = 4"
    )
    assert _norm_sql(q1_rule) == _norm_sql(
        "SELECT <x1>.<x2>, <x3>.<x4>, <x3>.<x5> FROM <x1> INNER JOIN <x3> ON <x1>.<x5> = <x3>.<x5> WHERE <<x6>>"
    )


def test_generate_general_rule_22():
    q0 = """
        SELECT
            t1.CPF,
            DATE(t1.data),
            CASE WHEN SUM(CASE WHEN t1.login_ok = true THEN 1 ELSE 0 END) >= 1
                 THEN true
                 ELSE false
            END
        FROM db_risco.site_rn_login AS t1
        GROUP BY t1.CPF, DATE(t1.data)
    """
    q1 = """
        SELECT
            t1.CPF,
            t1.data
        FROM (
            SELECT CPF, DATE(data)
            FROM db_risco.site_rn_login
            WHERE login_ok = true
        ) t1
        GROUP BY t1.CPF, t1.data
    """
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert _norm_sql(q0_rule) == _norm_sql(
        "SELECT <x1>.<x2>, DATE(<x1>.<x3>), CASE WHEN SUM(CASE WHEN <x1>.<x4> = <x5> THEN 1 ELSE 0 END) >= <x5> THEN True ELSE False END FROM <x1> GROUP BY <x1>.<x2>, DATE(<x1>.<x3>)"
    )
    assert _norm_sql(q1_rule) == _norm_sql(
        "SELECT t1.<x2>, t1.<x3> FROM (SELECT <x2>, DATE(<x3>) FROM <x6> WHERE <x4> = <x5>) AS t1 GROUP BY t1.<x2>, t1.<x3>"
    )


def test_recommend_simple_rules_1():
    examples = [
        {
            "q0": "SELECT * FROM employee WHERE workdept IN (SELECT deptno FROM department WHERE deptname = 'OPERATIONS')",
            "q1": "SELECT DISTINCT * FROM employee, department where employee.workdept = department.deptno AND department.deptname = 'OPERATIONS'",
        }
    ]
    rules = RuleGeneratorV2.recommend_simple_rules(examples)
    assert _norm_sql(rules[0]["pattern"]) == _norm_sql(
        "SELECT * FROM <x1> WHERE workdept IN (SELECT deptno FROM department WHERE deptname = 'OPERATIONS')"
    )
    assert _norm_sql(rules[0]["rewrite"]) == _norm_sql(
        "SELECT DISTINCT * FROM <x1>, department WHERE <x1>.workdept = department.deptno AND department.deptname = 'OPERATIONS'"
    )


def test_recommend_simple_rules_2():
    examples = [
        {
            "q0": "SELECT Count(*) FROM   (SELECT 1 AS one FROM   group_histories WHERE  group_histories.group_id = 2578 AND group_histories.action = 2 ORDER  BY group_histories.created_at DESC LIMIT  25 offset 0) subquery_for_count",
            "q1": "SELECT Count(*) FROM   (SELECT 1 AS one FROM   group_histories WHERE  group_histories.group_id = 2578 AND group_histories.action = 2 LIMIT  25 offset 0) AS subquery_for_count",
        },
        {
            "q0": "SELECT Count(*) FROM   (SELECT 1 AS one FROM   gh WHERE  gh.group_id = 2578 AND gh.action = 2 ORDER  BY gh.created_at DESC LIMIT  25 offset 0) subquery_for_count",
            "q1": "SELECT Count(*) FROM   (SELECT 1 AS one FROM   gh WHERE  gh.group_id = 2578 AND gh.action = 2 LIMIT  25 offset 0) AS subquery_for_count",
        },
    ]
    rules = RuleGeneratorV2.recommend_simple_rules(examples)
    assert _norm_sql(rules[0]["pattern"]) == _norm_sql(
        "SELECT COUNT(*) FROM (SELECT 1 AS one FROM <x1> WHERE <x1>.group_id = 2578 AND <x1>.action = 2 ORDER BY <x1>.created_at DESC LIMIT 25 OFFSET 0) AS subquery_for_count"
    )
    assert _norm_sql(rules[0]["rewrite"]) == _norm_sql(
        "SELECT COUNT(*) FROM (SELECT 1 AS one FROM <x1> WHERE <x1>.group_id = 2578 AND <x1>.action = 2 LIMIT 25 OFFSET 0) AS subquery_for_count"
    )


def test_recommend_simple_rules_3():
    examples = [
        {"q0": "SELECT CAST(create_at as DATE)", "q1": "SELECT create_at"},
        {"q0": "SELECT CAST(create_at1 as DATE)", "q1": "SELECT create_at1"},
        {"q0": "SELECT STRPOS(LOWER(text), 'iphone') > 0", "q1": "SELECT ILIKE(text, '%iphone%')"},
        {"q0": "SELECT STRPOS(LOWER(text1), 'iphone') > 0", "q1": "SELECT ILIKE(text1, '%iphone%')"},
        {"q0": "SELECT STRPOS(LOWER(text), 'iphone1') > 0", "q1": "SELECT ILIKE(text, '%iphone1%')"},
    ]
    rules = RuleGeneratorV2.recommend_simple_rules(examples)
    assert _norm_sql(rules[0]["pattern"]) == _norm_sql("SELECT CAST(<x1> AS DATE)")
    assert _norm_sql(rules[0]["rewrite"]) == _norm_sql("SELECT <x1>")
    assert _norm_sql(rules[1]["pattern"]) == _norm_sql("SELECT STRPOS(LOWER(text), '<x1>') > 0")
    assert _norm_sql(rules[1]["rewrite"]) == _norm_sql("SELECT text ILIKE '%<x1>%'")


def test_recommend_simple_rules_4():
    examples = [
        {
            "q0": "SELECT e1.name, e1.age, e2.salary FROM employee e1, employee e2 WHERE e1.id = e2.id AND e1.age > 17 AND e2.salary > 35000",
            "q1": "SELECT e1.name, e1.age, e1.salary FROM employee e1 WHERE e1.age > 17 AND e1.salary > 35000",
        },
        {
            "q0": "SELECT e1.name, e1.ages, e2.salary FROM employee e1, employee e2 WHERE e1.id = e2.id AND e1.ages > 17 AND e2.salary > 35000",
            "q1": "SELECT e1.name, e1.ages, e1.salary FROM employee e1 WHERE e1.ages > 17 AND e1.salary > 35000",
        },
        {
            "q0": "SELECT * FROM t WHERE CAST(created_at AS DATE) = TIMESTAMP '2016-10-01 00:00:00.000'",
            "q1": "SELECT * FROM t WHERE created_at = TIMESTAMP '2016-10-01 00:00:00.000'",
        },
        {
            "q0": "SELECT s.ids from s WHERE s.x = 100 AND s.abc = 100",
            "q1": "SELECT s.x from s WHERE s.x = 100",
        },
        {
            "q0": "SELECT student.ids from student WHERE student.id = 100 AND student.abc = 100",
            "q1": "SELECT student.id from student WHERE student.id = 100",
        },
    ]
    rules = RuleGeneratorV2.recommend_simple_rules(examples)
    assert _norm_sql(rules[0]["pattern"]) == _norm_sql(
        "SELECT e1.name, e1.<x1>, e2.salary FROM employee AS e1, employee AS e2 WHERE e1.id = e2.id AND e1.<x1> > 17 AND e2.salary > 35000"
    )
    assert _norm_sql(rules[0]["rewrite"]) == _norm_sql(
        "SELECT e1.name, e1.<x1>, e1.salary FROM employee AS e1 WHERE e1.<x1> > 17 AND e1.salary > 35000"
    )
    assert _norm_sql(rules[1]["pattern"]) == _norm_sql(
        "SELECT * FROM <x1> WHERE CAST(created_at AS DATE) = TIMESTAMP('2016-10-01 00:00:00.000')"
    )
    assert _norm_sql(rules[1]["rewrite"]) == _norm_sql(
        "SELECT * FROM <x1> WHERE created_at = TIMESTAMP('2016-10-01 00:00:00.000')"
    )
    assert _norm_sql(rules[2]["pattern"]) == _norm_sql(
        "SELECT <x1>.ids FROM <x1> WHERE <x1>.<x2> = 100 AND <x1>.abc = 100"
    )
    assert _norm_sql(rules[2]["rewrite"]) == _norm_sql(
        "SELECT <x1>.<x2> FROM <x1> WHERE <x1>.<x2> = 100"
    )


def test_parse_validator_1():
    success1, _err1, _idx1 = RuleGeneratorV2.parse_validate_single("CAST(<x> AS DATE)")
    success2, _err2, _idx2 = RuleGeneratorV2.parse_validate_single("<x>")
    success3, _err3, _idx3 = RuleGeneratorV2.parse_validate("CAST(<x> AS DATE)", "<x>")
    assert success1 is True
    assert success2 is True
    assert success3 is True


def test_parse_validator_2():
    success, errormessage, index = RuleGeneratorV2.parse_validate("CAST(<x> AS DATE)", "<y>")
    assert success is False
    assert index == 0
    assert "not in first rule" in errormessage


def test_parse_validator_3():
    success1, errormessage1, index1 = RuleGeneratorV2.parse_validate_single("CAST(<x> AS DATEE)")
    success2, errormessage2, index2 = RuleGeneratorV2.parse_validate("CAST(<x> AS DATEE)", "<x>")
    assert success1 is False
    assert index1 == 13
    assert "DATEE" in errormessage1
    assert success2 is False
    assert index2 == 13
    assert "DATEE" in errormessage2


def test_parse_validator_4():
    success1, errormessage1, index1 = RuleGeneratorV2.parse_validate_single("CA NT(<x> AS DATE)")
    success2, errormessage2, index2 = RuleGeneratorV2.parse_validate("CA NT(<x> AS DATE)", "<x>")
    assert success1 is False
    assert index1 == 3
    assert "NT" in errormessage1
    assert success2 is False
    assert index2 == 3
    assert "NT" in errormessage2


def test_parse_validator_5():
    pattern = """SELECT <x>
            FROM <y>
            WHERE <x> > 10
            AND <x> <= 10
            """
    rewrite = """SELECT <x>
            FROM <x>
            WHERE FALSE
            """
    success1, _err1, index1 = RuleGeneratorV2.parse_validate_single(pattern)
    success2, _err2, index2 = RuleGeneratorV2.parse_validate_single(rewrite)
    success3, _err3, index3 = RuleGeneratorV2.parse_validate(pattern, rewrite)
    assert success1 is True and index1 == 0
    assert success2 is True and index2 == 0
    assert success3 is True and index3 == 0


def test_parse_validator_6():
    pattern = """FRUM <y>
            WHERE <x> > 10
            AND <x> <= 10
            """
    rewrite = """FROM <y>
            WHERE FALSE
            """
    success1, errormessage1, index1 = RuleGeneratorV2.parse_validate_single(pattern)
    success2, errormessage2, index2 = RuleGeneratorV2.parse_validate(pattern, rewrite)
    assert success1 is False and index1 == 0 and "spelling" in errormessage1
    assert success2 is False and index2 == 0 and "spelling" in errormessage2


def test_parse_validator_7():
    pattern = """WHURE <x> > 10
            AND <x> <= 10
            """
    rewrite = """WHERE FALSE"""
    success1, errormessage1, index1 = RuleGeneratorV2.parse_validate_single(pattern)
    success2, errormessage2, index2 = RuleGeneratorV2.parse_validate(pattern, rewrite)
    assert success1 is False and index1 == 0 and "spelling" in errormessage1
    assert success2 is False and index2 == 0 and "spelling" in errormessage2


def test_parse_validator_8():
    pattern = """SELUCT <x>
            FROM <y>
            WHERE <x> >> 10
            AND <x> <= 10
            """
    rewrite = """SELECT <x>
            FROM <y>
            WHERE FALSE
            """
    success1, errormessage1, index1 = RuleGeneratorV2.parse_validate_single(pattern)
    success2, errormessage2, index2 = RuleGeneratorV2.parse_validate(pattern, rewrite)
    assert success1 is False and index1 == 0 and "spelling" in errormessage1
    assert success2 is False and index2 == 0 and "spelling" in errormessage2


def test_parse_validator_9():
    pattern = """FRUM <x>, EN END"""
    rewrite = """FROM <x>"""
    success1, errormessage1, index1 = RuleGeneratorV2.parse_validate_single(pattern)
    success2, errormessage2, index2 = RuleGeneratorV2.parse_validate(pattern, rewrite)
    assert success1 is False and index1 == 0 and "spelling" in errormessage1
    assert success2 is False and index2 == 0 and "spelling" in errormessage2


def test_parse_validator_10():
    pattern = """WHERE <x> > 11 5 10
            AND <x> <= 11
            """
    rewrite = """WHERE FALSE"""
    success1, errormessage1, index1 = RuleGeneratorV2.parse_validate_single(pattern)
    success2, errormessage2, index2 = RuleGeneratorV2.parse_validate(pattern, rewrite)
    assert success1 is False and index1 == 16 and "5 10" in errormessage1
    assert success2 is False and index2 == 16 and "5 10" in errormessage2


def test_parse_validator_13():
    pattern = """WHERE a <4x> > 11
            AND <x> a <= 11
            """
    rewrite = """WHERE FALSE"""
    success1, errormessage1, index1 = RuleGeneratorV2.parse_validate_single(pattern)
    success2, errormessage2, index2 = RuleGeneratorV2.parse_validate(pattern, rewrite)
    assert success1 is False and index1 == 8 and "<4x>" in errormessage1
    assert success2 is False and index2 == 8 and "<4x>" in errormessage2


def test_parse_validator_14():
    success1, _err1, _idx1 = RuleGeneratorV2.parse_validate_single("CAST(<x3> AS TEXT)")
    success2, _err2, _idx2 = RuleGeneratorV2.parse_validate_single("<x3>")
    success3, _err3, _idx3 = RuleGeneratorV2.parse_validate("CAST(<x3> AS TEXT)", "<x3>")
    assert success1 is True
    assert success2 is True
    assert success3 is True


def test_generate_rule_graph_0():
    q0 = "CAST(created_at AS DATE)"
    q1 = "created_at"
    root_rule = RuleGeneratorV2.generate_rule_graph(q0, q1)
    assert isinstance(root_rule, dict)
    children = root_rule["children"]
    assert len(children) == 1
    child_rule = children[0]
    assert child_rule["pattern"] == "CAST(<x1> AS DATE)"
    assert child_rule["rewrite"] == "<x1>"


def test_generate_spreadsheet_id_3():
    q0 = "SELECT EMPNO FROM EMP WHERE EMPNO > 10 AND EMPNO <= 10"
    q1 = "SELECT EMPNO FROM EMP WHERE FALSE"
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "<x1> > <x2> AND <x1> <= <x2>"
    assert q1_rule == "False"


def test_generate_spreadsheet_id_4():
    q0 = """SELECT entities.data FROM entities WHERE
  entities._id IN (SELECT index_users_email._id FROM index_users_email WHERE index_users_email.key = 'test')
 OR
  entities._id in (SELECT index_users_profile_name._id FROM index_users_profile_name WHERE index_users_profile_name.key = 'test')"""
    q1 = """SELECT entities.data FROM entities
WHERE entities._id IN
 ( SELECT index_users_email._id
   FROM index_users_email
   WHERE index_users_email.key = 'test'
 )
UNION
SELECT entities.data FROM entities
WHERE entities._id in
 ( SELECT index_users_profile_name._id
   FROM index_users_profile_name
   WHERE index_users_profile_name.key = 'test'
 )"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert _norm_sql(q0_rule) == _norm_sql(
        "SELECT <<x1>> FROM <x2> WHERE <x2>.<x3> IN (SELECT <<x4>> FROM <x5> WHERE <<x6>>) OR <x2>.<x3> IN (SELECT <<x7>> FROM <x8> WHERE <<x9>>)"
    )
    assert _norm_sql(q1_rule) == _norm_sql(
        "SELECT <<x1>> FROM <x2> WHERE <x2>.<x3> IN (SELECT <<x4>> FROM <x5> WHERE <<x6>>) UNION SELECT <<x1>> FROM <x2> WHERE <x2>.<x3> IN (SELECT <<x7>> FROM <x8> WHERE <<x9>>)"
    )


def test_generate_spreadsheet_id_6():
    q0 = """SELECT *
FROM
    table_name
 WHERE
    (table_name.title = 1 and table_name.grade = 2)
 OR
    (table_name.title = 2 and table_name.debt = 2 and table_name.grade = 3)
 OR
     (table_name.prog = 1 and table_name.title =1 and table_name.debt = 3)"""
    q1 = """SELECT *
FROM
    table_name
 WHERE
     1 = case
           when table_name.title = 1 and table_name.grade = 2 then 1
           when table_name.title = 2 and table_name.debt = 2 and table_name.grade = 3 then 1
           when table_name.prog = 1 and table_name.title = 1 and table_name.debt = 3 then 1
        else 0
     end"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "<x1> OR <x2> OR <x3>"
    assert q1_rule == "<x4> = CASE WHEN <x1> THEN <x4> WHEN <x2> THEN <x4> WHEN <x3> THEN <x4> ELSE 0 END"


def test_generate_spreadsheet_id_7():
    q0 = """select * from
a
left join b on a.id = b.cid
where
b.cl1 = 's1'
or
b.cl1 ='s2'
or
b.cl1 ='s3' """
    q1 = """select * from
a
left join b on a.id = b.cid
where
b.cl1 in ('s1','s2','s3')"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "<x1>.<x2> = '<x3>' OR <x1>.<x2> = '<x4>' OR <x1>.<x2> = '<x5>'"
    assert q1_rule == "<x1>.<x2> IN ('<x3>', '<x4>', '<x5>')"


def test_generate_spreadsheet_id_9():
    q0 = """SELECT DISTINCT my_table.foo
FROM my_table
WHERE my_table.num = 1;"""
    q1 = """SELECT my_table.foo
FROM my_table
WHERE my_table.num = 1
GROUP BY my_table.foo;"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "SELECT DISTINCT <x1> FROM <x2> WHERE <<x3>>"
    assert q1_rule == "SELECT <x1> FROM <x2> WHERE <<x3>> GROUP BY <x1>"


def test_generate_spreadsheet_id_10():
    q0 = """SELECT table1.wpis_id
FROM table1
WHERE table1.etykieta_id IN (
  SELECT table2.tag_id
  FROM table2
  WHERE table2.postac_id = 376476
  );"""
    q1 = """SELECT table1.wpis_id
FROM table1
INNER JOIN table2 on table2.tag_id = table1.etykieta_id
WHERE table2.postac_id = 376476"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "FROM <x1> WHERE <x1>.<x2> IN (SELECT <x3>.<x4> FROM <x3> WHERE <<x5>>)"
    assert q1_rule == "FROM <x1> INNER JOIN <x3> ON <x3>.<x4> = <x1>.<x2> WHERE <<x5>>"


def test_generate_spreadsheet_id_11():
    q0 = """SELECT historicoestatusrequisicion_id, requisicion_id, estatusrequisicion_id,
            comentario, fecha_estatus, usuario_id
            FROM historicoestatusrequisicion hist1
            WHERE requisicion_id IN
            (
            SELECT requisicion_id FROM historicoestatusrequisicion hist2
            WHERE usuario_id = 27 AND estatusrequisicion_id = 1
            )
            ORDER BY requisicion_id, estatusrequisicion_id"""
    q1 = """SELECT hist1.historicoestatusrequisicion_id, hist1.requisicion_id, hist1.estatusrequisicion_id, hist1.comentario, hist1.fecha_estatus, hist1.usuario_id
            FROM historicoestatusrequisicion hist1
            JOIN historicoestatusrequisicion hist2 ON hist2.requisicion_id = hist1.requisicion_id
            WHERE hist2.usuario_id = 27 AND hist2.estatusrequisicion_id = 1
            ORDER BY hist1.requisicion_id, hist1.estatusrequisicion_id"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "SELECT <x1>, <x2>, <x3>, <x4>, <x5>, <x6> FROM <x7> WHERE <x2> IN (SELECT <x2> FROM <x8> WHERE <x6> = <x9> AND <x3> = <x10>) ORDER BY <x2>, <x3>"
    assert q1_rule == "SELECT <x7>.<x1>, <x7>.<x2>, <x7>.<x3>, <x7>.<x4>, <x7>.<x5>, <x7>.<x6> FROM <x7> JOIN <x8> ON <x8>.<x2> = <x7>.<x2> WHERE <x8>.<x6> = <x9> AND <x8>.<x3> = <x10> ORDER BY <x7>.<x2>, <x7>.<x3>"


def test_generate_spreadsheet_id_15():
    q0 = """SELECT *
FROM users u
WHERE u.id IN
    (SELECT s1.user_id
     FROM sessions s1
     WHERE s1.user_id <> 1234
       AND (s1.ip IN
              (SELECT s2.ip
               FROM sessions s2
               WHERE s2.user_id = 1234
               GROUP BY s2.ip)
            OR s1.cookie_identifier IN
              (SELECT s3.cookie_identifier
               FROM sessions s3
               WHERE s3.user_id = 1234
               GROUP BY s3.cookie_identifier))
     GROUP BY s1.user_id)"""
    q1 = """SELECT *
FROM users u
WHERE EXISTS (
    SELECT
        NULL
    FROM sessions s1
    WHERE s1.user_id <> 1234
    AND u.id = s1.user_id
    AND EXISTS (
        SELECT
            NULL
        FROM sessions s2
        WHERE s2.user_id = 1234
        AND (s1.ip = s2.ip
          OR s1.cookie_identifier = s2.cookie_identifier
            )
        )
    )"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "<x1>.<x2> IN (SELECT <x3>.<x4> FROM <x3> WHERE <<x5>> AND (<x3>.<x6> IN (SELECT <x7>.<x6> FROM <x7> WHERE <<x8>> GROUP BY <x7>.<x6>) OR <x3>.<x9> IN (SELECT <x10>.<x9> FROM <x10> WHERE <x10>.<x4> = <x11> GROUP BY <x10>.<x9>)) GROUP BY <x3>.<x4>)"
    assert q1_rule == "EXISTS (SELECT NULL FROM <x3> WHERE <<x5>> AND <x1>.<x2> = <x3>.<x4> AND EXISTS (SELECT NULL FROM <x7> WHERE <<x8>> AND (<x3>.<x6> = <x7>.<x6> OR <x3>.<x9> = <x7>.<x9>)))"


def test_generate_spreadsheet_id_18():
    q0 = """SELECT DISTINCT ON (t.playerId) t.gzpId, t.pubCode, t.playerId,
       COALESCE (p.preferenceValue,'en'),
       s.segmentId
FROM userPlayerIdMap t LEFT JOIN
     userPreferences p
     ON t.gzpId  = p.gzpId LEFT JOIN
     segment s
     ON t.gzpId = s.gzpId
WHERE t.pubCode IN ('hyrmas','ayqioa','rj49as99') and
      t.provider IN ('FCM','ONE_SIGNAL') and
      s.segmentId IN (0,1,2,3,4,5,6) and
      p.preferenceValue IN ('en','hi')
ORDER BY t.playerId desc;"""
    q1 = """SELECT t.gzpId, t.pubCode, t.playerId,
       COALESCE((SELECT p.preferenceValue
                 FROM userPreferences p
                 WHERE t.gzpId = p.gzpId AND
                       p.preferenceValue IN ('en', 'hi')
                 LIMIT 1
                ), 'en'
               ),
       (SELECT s.segmentId
        FROM segment s
        WHERE t.gzpId = s.gzpId AND
              s.segmentId IN (0, 1, 2, 3, 4, 5, 6)
        LIMIT 1
       )
FROM userPlayerIdMap t
WHERE t.pubCode IN ('hyrmas', 'ayqioa', 'rj49as99') and
      t.provider IN ('FCM', 'ONE_SIGNAL');"""
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "SELECT DISTINCT ON (<x1>) <x2>, <x3>, <x1>, COALESCE(<x4>.<x5>, <x6>), <<x7>> FROM <x8> LEFT JOIN <x4> ON <<x9>> LEFT JOIN <x10> ON <<x11>> WHERE <<x12>> AND <x10>.<x13> IN (<x14>, <x15>, <x16>, <x17>, <x18>, <x19>, <x20>) AND <<x21>> ORDER BY <x8>.<x22> DESC"
    assert q1_rule == "SELECT <x2>, <x3>, <x1>, COALESCE((SELECT <x4>.<x5> FROM <x4> WHERE <<x9>> AND <<x21>> LIMIT <x15>), <x6>), (SELECT <<x7>> FROM <x10> WHERE <<x11>> AND <x10>.<x13> IN (<x14>, <x15>, <x16>, <x17>, <x18>, <x19>, <x20>) LIMIT <x15>) FROM <x8> WHERE <<x12>>"


def test_generate_spreadsheet_id_20():
    q0 = "SELECT * FROM (SELECT * FROM (SELECT NULL FROM EMP) WHERE N IS NULL) WHERE N IS NULL"
    q1 = "SELECT * FROM (SELECT NULL FROM EMP) WHERE N IS NULL"
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "SELECT <<x1>> FROM (SELECT NULL FROM <x2>) WHERE <<x3>>"
    assert q1_rule == "SELECT NULL FROM <x2>"


def test_generate_spreadsheet_id_21():
    q0 = "SELECT * FROM (SELECT * FROM EMP AS t WHERE t.N IS NULL) AS t0 WHERE t0.N IS NULL"
    q1 = "SELECT * FROM EMP AS t WHERE t.N IS NULL"
    rule = RuleGeneratorV2.generate_general_rule(q0, q1)
    q0_rule, q1_rule = RuleGeneratorV2.unify_variable_names(rule["pattern"], rule["rewrite"])
    assert q0_rule == "FROM (SELECT <<x1>> FROM <x2> WHERE <<x3>>) AS t0 WHERE t0.<x4> IS NULL"
    assert q1_rule == "FROM <x2> WHERE <<x3>>"
