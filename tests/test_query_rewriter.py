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
        FROM   blc_admin_permission admipermi0_
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
        FROM   blc_admin_permission admipermi0_
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
        and 1=1
        and deptname = 'OPERATIONS';
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
        and age > 17
        and deptname = 'OPERATIONS';
    '''
    rule_keys = ['subquery_to_join']

    rules = [get_rule(k) for k in rule_keys]
    _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
    assert format(parse(q1)) == format(parse(_q1))


# TODO - Unify table name and alias, replace them as inter-changable entities
# 
# def test_rewrite_rule_subquery_to_join_3():
#     q0 = '''
#         select e.empno, e.firstnme, e.lastname, e.phoneno
#         from employee e
#         where e.workdept in
#             (select d.deptno
#                 from department d
#                 where d.deptname = 'OPERATIONS')
#         and e.age > 17;
#     '''
#     q1 = '''
#         select distinct e.empno, e.firstnme, e.lastname, e.phoneno
#         from employee e, department d
#         where e.workdept = d.deptno 
#         and e.age > 17
#         and d.deptname = 'OPERATIONS';
#     '''
#     rule_keys = ['subquery_to_join']

#     rules = [get_rule(k) for k in rule_keys]
#     _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
#     assert format(parse(q1)) == format(parse(_q1))


def test_rewrite_rule_join_to_filter_1():
    q0 = '''
        SELECT *
        FROM   blc_admin_permission admipermi0_
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
        FROM   blc_admin_permission admipermi0_
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


# TODO - Should pass when line 117 in query_rewriter.py is fixed.
#
# def test_rewrite_rule_join_to_filter_3():
#     q0 = '''
#         SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
#         FROM   blc_admin_permission admipermi0_
#             INNER JOIN blc_admin_role_permission_xref allroles1_
#                     ON adminpermi0_.admin_permission_id =
#                         allroles1_.admin_permission_id
#             INNER JOIN blc_admin_role adminrolei2_
#                     ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
#         WHERE  adminpermi0_.is_friendy = 1 
#         AND    adminrolei2_.admin_role_id = 1;
#     '''
#     q1 = '''
#         SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
#         FROM   blc_admin_permission AS adminpermi0_
#             INNER JOIN blc_admin_role_permission_xref AS allroles1_
#                     ON adminpermi0_.admin_permission_id =
#                         allroles1_.admin_permission_id
#         WHERE  allroles1_.admin_role_id = 1 
#         AND    adminpermi0_.is_friendy = 1;
#     '''
#     rule_keys = ['join_to_filter']

#     rules = [get_rule(k) for k in rule_keys]
#     _q1, _rewrite_path = QueryRewriter.rewrite(q0, rules)
#     assert format(parse(q1)) == format(parse(_q1))


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

