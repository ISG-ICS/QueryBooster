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

