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
