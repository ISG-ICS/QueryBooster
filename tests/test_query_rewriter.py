from core.query_rewriter import QueryRewriter
from data.rules import get_rule
from mo_sql_parsing import parse
from mo_sql_parsing import format


def test_match_rule_remove_cast_date_1():
    rule = get_rule('remove_cast_date')
    assert rule is not None
    
    # match twice
    query = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_remove_cast_date_2():
    rule = get_rule('remove_cast_date')
    assert rule is not None

    # match once
    query = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_remove_cast_date_3():
    rule = get_rule('remove_cast_date')
    assert rule is not None

    # no match
    query = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', created_at) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;
    '''
    memo = {}
    assert not QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_replace_strpos_lower_1():
    rule = get_rule('replace_strpos_lower')
    assert rule is not None
    
    # match
    query = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(LOWER(text), 'iphone') > 0)
         GROUP  BY 2;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_replace_strpos_lower_2():
    rule = get_rule('replace_strpos_lower')
    assert rule is not None

    # no match
    query = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  text ILIKE '%iphone%'
         GROUP  BY 2;
    '''
    memo = {}
    assert not QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_remove_self_join_1():
    rule = get_rule('remove_self_join')
    assert rule is not None
    
    # match
    query = '''
        SELECT  e1.name, 
                e1.age, 
                e2.salary 
        FROM employee e1, employee e2
        WHERE e1.id = e2.id
        AND e1.age > 17
        AND e2.salary > 35000;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_remove_self_join_2():
    rule = get_rule('remove_self_join')
    assert rule is not None
    
    # no match
    query = '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000;
    '''
    memo = {}
    assert not QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_remove_self_join_3():
    rule = get_rule('remove_self_join')
    assert rule is not None
    
    # match
    query = '''
        SELECT  e1.age 
        FROM employee e1, employee e2
        WHERE e1.id = e2.id
        AND e1.age > 17;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_remove_self_join_advance_1():
    rule = get_rule('remove_self_join_advance')
    assert rule is not None
    
    # match
    query = '''
        SELECT  e1.name, 
                e1.age, 
                e2.salary 
        FROM employee e1, employee e2
        WHERE e1.id = e2.id
        AND e1.age > 17
        AND e2.salary > 35000;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_subquery_to_join_1():
    rule = get_rule('subquery_to_join')
    assert rule is not None
    
    # match
    query = '''
        select empno, firstnme, lastname, phoneno
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
        and 1=1;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_subquery_to_join_2():
    rule = get_rule('subquery_to_join')
    assert rule is not None
    
    # match
    query = '''
        select empno, firstnme, lastname, phoneno
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
        and age > 17;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_subquery_to_join_3():
    rule = get_rule('subquery_to_join')
    assert rule is not None
    
    # match
    query = '''
        select e.empno, e.firstnme, e.lastname, e.phoneno
        from employee e
        where e.workdept in
            (select d.deptno
                from department d
                where d.deptname = 'OPERATIONS')
        and e.age > 17;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_join_to_filter_1():
    rule = get_rule('join_to_filter')
    assert rule is not None
    
    # match
    query = '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1
        AND 1=1;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_join_to_filter_2():
    rule = get_rule('join_to_filter')
    assert rule is not None
    
    # match
    query = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminpermi0_.is_friendy = 1
            AND adminrolei2_.admin_role_id = 1;
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_test_rule_wetune_90():
    rule = get_rule('test_rule_wetune_90')
    assert rule is not None
    
    # match
    query = '''
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
            adminpermi0_.description AS descript2_4_,
            adminpermi0_.is_friendly AS is_frien3_4_,
            adminpermi0_.name AS name4_4_,
            adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
        INNER JOIN blc_admin_role_permission_xref allroles1_ ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        INNER JOIN blc_admin_role adminrolei2_ ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminpermi0_.is_friendly = 1
        AND adminrolei2_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT 50
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_match_rule_test_rule_calcite_testPushMinThroughUnion():
    rule = get_rule('test_rule_calcite_testPushMinThroughUnion')
    assert rule is not None
    
    # match
    query = '''
        SELECT t.ENAME,
            MIN(t.EMPNO)
        FROM
        (SELECT *
        FROM EMP AS EMP
        UNION ALL SELECT *
        FROM EMP AS EMP) AS t
        GROUP BY t.ENAME
    '''
    memo = {}
    assert QueryRewriter.match(parse(query), rule, memo)


def test_replace_rule_remove_cast_date():
    rule = get_rule('remove_cast_date')
    assert rule is not None
    
    # original query q0
    q0 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;
    '''
    memo = {}
    parsed_q0 = parse(q0)
    assert QueryRewriter.match(parsed_q0, rule, memo)
    parsed_q1 = QueryRewriter.replace(parsed_q0, rule, memo)

    # 1st round rewritten query q1
    q1 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;
    '''
    assert format(parse(q1)) == format(parsed_q1)
    memo = {}
    parsed_q1 = parse(q1)
    assert QueryRewriter.match(parsed_q1, rule, memo)
    parsed_q2 = QueryRewriter.replace(parsed_q1, rule, memo)

    # 2nd round rewritten query q2
    q2 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', created_at) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;
    '''
    assert format(parse(q2)) == format(parsed_q2)


def test_replace_rule_replace_strpos_lower():
    rule = get_rule('replace_strpos_lower')
    assert rule is not None
    
    # original query q0
    q0 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(LOWER(text), 'iphone') > 0)
         GROUP  BY 2;
    '''
    parsed_q0 = parse(q0)
    memo = {}
    assert QueryRewriter.match(parsed_q0, rule, memo)
    parsed_q1 = QueryRewriter.replace(parsed_q0, rule, memo)

    # rewritten query q1
    q1 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  ILIKE(text, '%iphone%')
         GROUP  BY 2;
    '''
    assert format(parse(q1)) == format(parsed_q1)


def test_replace_rule_remove_self_join():
    rule = get_rule('remove_self_join')
    assert rule is not None
    
    # original query q0
    q0 = '''
        SELECT  e1.name, 
                e1.age, 
                e2.salary 
        FROM employee e1, employee e2
        WHERE e1.id = e2.id
        AND e1.age > 17
        AND e2.salary > 35000;
    '''
    parsed_q0 = parse(q0)
    memo = {}
    assert QueryRewriter.match(parsed_q0, rule, memo)
    parsed_q1 = QueryRewriter.take_actions(parsed_q0, rule, memo)
    parsed_q1 = QueryRewriter.replace(parsed_q0, rule, memo)

    # rewritten query q1
    q1 = '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE 1=1
        AND e1.age > 17
        AND e1.salary > 35000;
    '''
    assert format(parse(q1)) == format(parsed_q1)


def test_rewrite_rule_remove_max_distinct():
    q0 = '''
        SELECT A, MAX(DISTINCT (SELECT B FROM R WHERE C = 0)), D
        FROM S;
    '''
    q1 = '''
        SELECT A, MAX((SELECT B FROM R WHERE C = 0)), D
        FROM S;
    '''
    rule_keys = ['remove_max_distinct']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_remove_cast_date():
    q0 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
        FROM  tweets 
        WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
        AND  (STRPOS(text, 'iphone') > 0)
        GROUP  BY 2;
    '''
    q1 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
        FROM  tweets 
        WHERE  DATE_TRUNC('QUARTER', created_at) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
        AND  (STRPOS(text, 'iphone') > 0)
        GROUP  BY 2;   
    '''
    rule_keys = ['remove_cast_date']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_replace_strpos_lower():
    q0 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
        FROM  tweets 
        WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
        AND  (STRPOS(LOWER(text), 'iphone') > 0)
        GROUP  BY 2;
    '''
    q1 = '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
        FROM  tweets 
        WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
        AND text ILIKE '%iphone%'
        GROUP  BY 2;
    '''
    rule_keys = ['replace_strpos_lower']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_remove_self_join():
    q0 = '''
        SELECT  e1.name, 
                e1.age, 
                e2.salary 
        FROM employee e1, employee e2
        WHERE e1.id = e2.id
        AND e1.age > 17
        AND e2.salary > 35000;
    '''
    q1 = '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE 1=1
        AND e1.age > 17
        AND e1.salary > 35000;
    '''
    rule_keys = ['remove_self_join']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_remove_self_join_2():
    q0 = '''
        SELECT e1.* 
        FROM employee e1, employee e2
        WHERE e1.id = e2.id
        AND e1.age > 17;
    '''
    q1 = '''
        SELECT e1.* 
        FROM employee e1
        WHERE 1=1
        AND e1.age > 17;
    '''
    rule_keys = ['remove_self_join']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_remove_self_join_advance_1():
    q0 = '''
        SELECT  e1.name, 
                e1.age, 
                e2.salary 
        FROM employee e1, employee e2
        WHERE e1.id = e2.id
        AND e1.age > 17
        AND e2.salary > 35000;
    '''
    q1 = '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE 1=1
        AND e1.age > 17
        AND e1.salary > 35000;
    '''
    rule_keys = ['remove_self_join_advance']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_subquery_to_join_1():
    q0 = '''
        select empno, firstnme, lastname, phoneno
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
        and 1=1;
    '''
    q1 = '''
        select distinct empno, firstnme, lastname, phoneno
        from employee, department
        where employee.workdept = department.deptno 
        and 1=1
        and deptname = 'OPERATIONS';
    '''
    rule_keys = ['subquery_to_join']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_subquery_to_join_1():
    q0 = '''
        select empno, firstnme, lastname, phoneno
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
        and 1=1;
    '''
    q1 = '''
        select distinct empno, firstnme, lastname, phoneno
        from employee, department
        where employee.workdept = department.deptno 
        and deptname = 'OPERATIONS'
        and 1=1;
    '''
    rule_keys = ['subquery_to_join']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_subquery_to_join_2():
    q0 = '''
        select empno, firstnme, lastname, phoneno
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
        and age > 17;
    '''
    q1 = '''
        select distinct empno, firstnme, lastname, phoneno
        from employee, department
        where employee.workdept = department.deptno 
        and deptname = 'OPERATIONS'
        and age > 17;
    '''
    rule_keys = ['subquery_to_join']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_subquery_to_join_3():
    q0 = '''
        select e.empno, e.firstnme, e.lastname, e.phoneno
        from employee e
        where e.workdept in
            (select d.deptno
                from department d
                where d.deptname = 'OPERATIONS')
        and e.age > 17;
    '''
    q1 = '''
        select distinct e.empno, e.firstnme, e.lastname, e.phoneno
        from employee e, department d
        where e.workdept = d.deptno 
        and d.deptname = 'OPERATIONS'
        and e.age > 17;
    '''
    rule_keys = ['subquery_to_join']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_1():
    q0 = '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1
        AND 1=1;
    '''
    q1 = '''
        SELECT *
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
        AND 1=1;
    '''
    rule_keys = ['join_to_filter']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_2():
    q0 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1
        AND    adminpermi0_.is_friendy = 1;
    '''
    q1 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1 
        AND    adminpermi0_.is_friendy = 1;
    '''
    rule_keys = ['join_to_filter']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_3():
    q0 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminpermi0_.is_friendy = 1 
        AND    adminrolei2_.admin_role_id = 1;
    '''
    q1 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1 
        AND    adminpermi0_.is_friendy = 1;
    '''
    rule_keys = ['join_to_filter']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_advance_1():
    q0 = '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1
        AND 1=1;
    '''
    q1 = '''
        SELECT *
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
        AND 1=1;
    '''
    rule_keys = ['join_to_filter_advance']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_advance_2():
    q0 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1
        AND    adminpermi0_.is_friendy = 1;
    '''
    q1 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1 
        AND    adminpermi0_.is_friendy = 1;
    '''
    rule_keys = ['join_to_filter_advance']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_advance_3():
    q0 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminpermi0_.is_friendy = 1 
        AND    adminrolei2_.admin_role_id = 1;
    '''
    q1 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1 
        AND    adminpermi0_.is_friendy = 1;
    '''
    rule_keys = ['join_to_filter_advance']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_partial_1():
    q0 = '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1;
    '''
    q1 = '''
        SELECT *
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1;
    '''
    rule_keys = ['join_to_filter_partial1']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_partial_2():
    q0 = '''
        SELECT  adminpermi0_.admin_permission_id AS admin_pe1_4_,
                adminpermi0_.description         AS descript2_4_,
                adminpermi0_.is_friendly         AS is_frien3_4_,
                adminpermi0_.name                AS name4_4_,
                adminpermi0_.permission_type     AS permissi5_4_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminpermi0_.is_friendly = 1
            AND adminrolei2_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT  50;
    '''
    q1 = '''
        SELECT  adminpermi0_.admin_permission_id AS admin_pe1_4_,
                adminpermi0_.description         AS descript2_4_,
                adminpermi0_.is_friendly         AS is_frien3_4_,
                adminpermi0_.name                AS name4_4_,
                adminpermi0_.permission_type     AS permissi5_4_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  adminpermi0_.is_friendly = 1
            AND allroles1_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT  50;
    '''
    rule_keys = ['join_to_filter_partial2']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_partial_3():
    q0 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminpermi0_.is_friendly = 1
            AND adminrolei2_.admin_role_id = 1;
    '''
    q1 = '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
            AND adminpermi0_.is_friendly = 1;
    '''
    rule_keys = ['join_to_filter_partial3']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_remove_1useless_innerjoin():
    q0 = '''
        SELECT o_auth_applications.id
        FROM   o_auth_applications
            INNER JOIN authorizations
                    ON o_auth_applications.id = authorizations.o_auth_application_id
        WHERE  authorizations.user_id = 1465 
    '''
    q1 = '''
        SELECT authorizations.o_auth_application_id 
        FROM   authorizations
        WHERE  authorizations.user_id = 1465 
    '''
    rule_keys = ['remove_1useless_innerjoin']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_test_rule_wetune_90():
    q0 = '''
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
            adminpermi0_.description AS descript2_4_,
            adminpermi0_.is_friendly AS is_frien3_4_,
            adminpermi0_.name AS name4_4_,
            adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
        INNER JOIN blc_admin_role_permission_xref allroles1_ ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        INNER JOIN blc_admin_role adminrolei2_ ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminpermi0_.is_friendly = 1
        AND adminrolei2_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT 50
    '''
    q1 = '''
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
            adminpermi0_.description AS descript2_4_,
            adminpermi0_.is_friendly AS is_frien3_4_,
            adminpermi0_.name AS name4_4_,
            adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
        INNER JOIN blc_admin_role_permission_xref allroles1_ ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE adminpermi0_.is_friendly = 1
        AND allroles1_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT 50
    '''
    rule_keys = ['test_rule_wetune_90']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_query_rule_wetune_90():
    q0 = '''
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
            adminpermi0_.description AS descript2_4_,
            adminpermi0_.is_friendly AS is_frien3_4_,
            adminpermi0_.name AS name4_4_,
            adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
        INNER JOIN blc_admin_role_permission_xref allroles1_ ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        INNER JOIN blc_admin_role adminrolei2_ ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminpermi0_.is_friendly = 1
        AND adminrolei2_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT 50
    '''
    q1 = '''
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
            adminpermi0_.description AS descript2_4_,
            adminpermi0_.is_friendly AS is_frien3_4_,
            adminpermi0_.name AS name4_4_,
            adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
        INNER JOIN blc_admin_role_permission_xref allroles1_ ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE adminpermi0_.is_friendly = 1
        AND allroles1_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT 50
    '''
    rule_keys = ['query_rule_wetune_90']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_stackoverflow_1():
    q0 = '''
        SELECT DISTINCT my_table.foo, your_table.boo
        FROM my_table, your_table
        WHERE my_table.num = 1 OR your_table.num = 2
        '''
    q1 = '''
        SELECT
            my_table.foo,
            your_table.boo
        FROM
            my_table,
            your_table
        WHERE
            my_table.num = 1
            OR your_table.num = 2
        GROUP BY
            my_table.foo,
            your_table.boo
            '''
    rule_keys = ['stackoverflow_1', 'remove_self_join']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_partial_matching_base_case1():
    q0 = '''
        SELECT *
        FROM A a
        LEFT JOIN B b ON a.id = b.cid
        WHERE
        b.cl1 = 's1' OR b.cl1 ='s2'
        '''
    q1 = '''
        SELECT *
        FROM A a
        LEFT JOIN B b ON a.id = b.cid
        WHERE
        b.cl1 IN ('s1', 's2')
        '''
    rule_keys = ['combine_or_to_in']
    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


# TODO: need to rewrite the query as  b.cl1 IN ('s3', 's1', 's2') instead of double parenthesis
def test_partial_matching_base_case2():
    q0 = '''
        SELECT *
        FROM b
        WHERE
        b.cl1 IN ('s1', 's2') OR b.cl1 ='s3'
        '''
    q1 = '''
        SELECT *
        FROM b
        WHERE
        b.cl1 IN ('s3', ('s1', 's2'))
        '''
    rule_keys = ['merge_or_to_in']
    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_partial_matching0(): 
    q0 = '''
        SELECT *
        FROM A a
        LEFT JOIN B b ON a.id = b.cid
        WHERE
        b.cl1 = 's1' OR b.cl1 = 's2' OR b.cl1 = 's3'
        '''
    q1 = '''
        SELECT *
        FROM A a
        LEFT JOIN B b ON a.id = b.cid
        WHERE
        b.cl1 IN ('s1', 's2') OR b.cl1 = 's3'
        '''
    rule_keys = ['combine_or_to_in']
    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_partial_matching4():
    q0 = '''
        select empno, firstname, lastname, phoneno
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
        and firstname like 'B%'
        '''
    q1 = '''
        select distinct empno, firstname, lastname, phoneno
        from employee, department
        where employee.workdept = department.deptno
        and deptname = 'OPERATIONS'
        and firstname like 'B%'
        '''
    rule_keys = ['partial_subquery_to_join']
    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


def test_remove_where_true():
    q0 = '''
        SELECT *
        FROM Emp
        WHERE age > age - 2;
        '''
    q1 = '''
        SELECT *
        FROM Emp
        '''

    rule_keys = ['remove_where_true']
    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


# TODO - TBI
# 
def test_rewrite_postgresql():
    # PostgreSQL query
    # 
    q0 = '''
        SELECT "tweets"."latitude" AS "latitude",
               "tweets"."longitude" AS "longitude"
          FROM "public"."tweets" "tweets"
         WHERE (("tweets"."latitude" >= -90) AND ("tweets"."latitude" <= 80) 
           AND ((("tweets"."longitude" >= -173.80000000000001) AND ("tweets"."longitude" <= 180)) OR ("tweets"."longitude" IS NULL)) 
           AND (CAST((DATE_TRUNC( \'day\', CAST("tweets"."created_at" AS DATE) ) + (-EXTRACT(DOW FROM "tweets"."created_at") * INTERVAL \'1 DAY\')) AS DATE) 
                = (TIMESTAMP \'2018-04-22 00:00:00.000\')) 
           AND (STRPOS(CAST(LOWER(CAST(CAST("tweets"."text" AS TEXT) AS TEXT)) AS TEXT),CAST(\'microsoft\' AS TEXT)) > 0))
           GROUP BY 1, 2
    '''
    q1 = '''
        SELECT "tweets"."latitude" AS "latitude",
               "tweets"."longitude" AS "longitude"
          FROM "public"."tweets" "tweets"
         WHERE (("tweets"."latitude" >= -90) AND ("tweets"."latitude" <= 80) 
           AND ((("tweets"."longitude" >= -173.80000000000001) AND ("tweets"."longitude" <= 180)) OR ("tweets"."longitude" IS NULL)) 
           AND ((DATE_TRUNC( \'day\', "tweets"."created_at" ) + (-EXTRACT(DOW FROM "tweets"."created_at") * INTERVAL \'1 DAY\')) 
                = (TIMESTAMP \'2018-04-22 00:00:00.000\')) 
           AND "tweets"."text" ILIKE \'%microsoft%\')
           GROUP BY 1, 2
    '''
    rule_keys = ['remove_cast_date', 'remove_cast_text', 'replace_strpos_lower']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


# TODO - TBI
# 
def test_rewrite_mysql():
    # Rule 101 and 102
    # MySQL query
    # 
    query = '''SELECT `tweets`.`latitude` AS `latitude`,
                    `tweets`.`longitude` AS `longitude`
               FROM `tweets`
              WHERE ((ADDDATE(DATE_FORMAT(`tweets`.`created_at`, '%Y-%m-01 00:00:00'), INTERVAL 0 SECOND) = TIMESTAMP('2017-03-01 00:00:00'))
                AND (LOCATE('iphone', LOWER(`tweets`.`text`)) > 0))
              GROUP BY 1, 2'''

