from core.query_rewriter import QueryRewriter
import json
from mo_sql_parsing import parse

def test_match():
    # Rule 1
    rule = {
        'id': 1,
        'key': 'remove_cast',
        'name': 'Remove Cast',
        'pattern': json.loads('{"cast": ["V1", {"date": {}}]}'),
        'constraints': 'TYPE(x) = DATE',
        'rewrite': json.loads('"V1"'),
        'actions': ''
    }
    
    # sql 1
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
        GROUP BY 2;
    '''
    assert QueryRewriter.match(parse(query), rule)

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
    assert QueryRewriter.match(parse(query), rule)


    # Rule 101 and 102
    # MySQL query
    # 
    query = '''SELECT `tweets`.`latitude` AS `latitude`,
                    `tweets`.`longitude` AS `longitude`
               FROM `tweets`
              WHERE ((ADDDATE(DATE_FORMAT(`tweets`.`created_at`, '%Y-%m-01 00:00:00'), INTERVAL 0 SECOND) = TIMESTAMP('2017-03-01 00:00:00'))
                AND (LOCATE('iphone', LOWER(`tweets`.`text`)) > 0))
              GROUP BY 1, 2'''

