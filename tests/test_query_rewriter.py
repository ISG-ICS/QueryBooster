from core.query_rewriter import QueryRewriter
import json
from mo_sql_parsing import parse
from mo_sql_parsing import format


def test_match_rule_1():
    rule = {
        'id': 1,
        'key': 'remove_cast',
        'name': 'Remove Cast',
        'pattern': json.loads('{"cast": ["V1", {"date": {}}]}'),
        'constraints': 'TYPE(x) = DATE',
        'rewrite': json.loads('"V1"'),
        'actions': ''
    }
    
    # original query
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

    # 1st round rewritten query
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

    # 2nd round rewritten query
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


def test_match_rule_2():
    rule = {
        'id': 2,
        'key': 'replace_strpos',
        'name': 'Replace Strpos',
        'pattern': json.loads('{"gt": [{"strpos": [{"lower": "V1"}, {"literal": "V2"}]}, 0]}'),
        'constraints': 'IS(y) = CONSTANT and TYPE(y) = STRING',
        'rewrite': json.loads('{"ilike": ["V1", {"literal": "%V2%"}]}'),
        'actions': ''
    }
    
    # original query
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

    # rewritten query
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


def test_replace_rule_1():
    rule = {
        'id': 1,
        'key': 'remove_cast',
        'name': 'Remove Cast',
        'pattern': json.loads('{"cast": ["V1", {"date": {}}]}'),
        'constraints': 'TYPE(x) = DATE',
        'rewrite': json.loads('"V1"'),
        'actions': ''
    }
    
    # original query
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
    parsed_original_query = parse(query)
    assert QueryRewriter.match(parsed_original_query, rule, memo)
    parsed_rewritten_query = QueryRewriter.replace(parsed_original_query, rule, memo)

    # 1st round rewritten query
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
    assert format(parse(query)) == format(parsed_rewritten_query)
    memo = {}
    parsed_original_query = parse(query)
    assert QueryRewriter.match(parsed_original_query, rule, memo)
    parsed_rewritten_query = QueryRewriter.replace(parsed_original_query, rule, memo)

    # 2nd round rewritten query
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
    assert format(parse(query)) == format(parsed_rewritten_query)


def test_replace_rule_2():
    rule = {
        'id': 2,
        'key': 'replace_strpos',
        'name': 'Replace Strpos',
        'pattern': json.loads('{"gt": [{"strpos": [{"lower": "V1"}, {"literal": "V2"}]}, 0]}'),
        'constraints': 'IS(y) = CONSTANT and TYPE(y) = STRING',
        'rewrite': json.loads('{"ilike": ["V1", {"literal": "%V2%"}]}'),
        'actions': ''
    }
    
    # original query
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
    parsed_original_query = parse(query)
    memo = {}
    assert QueryRewriter.match(parsed_original_query, rule, memo)
    parsed_rewritten_query = QueryRewriter.replace(parsed_original_query, rule, memo)

    # rewritten query
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
           AND  ILIKE(text, '%iphone%')
         GROUP  BY 2;
    '''
    assert format(parse(query)) == format(parsed_rewritten_query)


# TODO - TBI
# 
def test_rewrite_postgresql():
    # Rule 1 and 2
    # PostgreSQL query
    # 
    query = '''
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
    assert 1 == 1


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

