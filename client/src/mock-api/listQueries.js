const defaultQueriesData = [
    {
        "id": 1,
        "timestamp": "2022-10-12 16:36:03",
        "latency": 3,
        "original_sql": `SELECT SUM(1) AS "cnt:tweets_5460F7F804494E7CB9FD188E329004C1:ok",
        CAST("tweets"."state_name" AS TEXT) AS "state_name"
 FROM "public"."tweets" "tweets"
 WHERE ((CAST(DATE_TRUNC('QUARTER', CAST("tweets"."created_at" AS DATE)) AS DATE) IN ((TIMESTAMP '2016-04-01 00:00:00.000'), (TIMESTAMP '2016-07-01 00:00:00.000'), (TIMESTAMP '2016-10-01 00:00:00.000'), (TIMESTAMP '2017-01-01 00:00:00.000')))
        AND (STRPOS(CAST(LOWER(CAST(CAST("tweets"."text" AS TEXT) AS TEXT)) AS TEXT), CAST('iphone' AS TEXT)) > 0))
 GROUP BY 2`,
        "rewritten_sql": `SELECT SUM(1) AS "cnt:tweets_5460F7F804494E7CB9FD188E329004C1:ok",
        tweets.state_name AS state_name
 FROM public.tweets AS tweets
 WHERE DATE_TRUNC('QUARTER', tweets.created_at) IN ((TIMESTAMP '2016-04-01 00:00:00.000'), (TIMESTAMP '2016-07-01 00:00:00.000'), (TIMESTAMP '2016-10-01 00:00:00.000'), (TIMESTAMP '2017-01-01 00:00:00.000'))
   AND tweets.text ILIKE '%iphone%'
 GROUP BY 2`
    },
    {
        "id": 0,
        "timestamp": "2022-10-12 16:31:42",
        "latency": 34,
        "original_sql": `SELECT SUM(1) AS "cnt:tweets_5460F7F804494E7CB9FD188E329004C1:ok",
        CAST("tweets"."state_name" AS TEXT) AS "state_name"
 FROM "public"."tweets" "tweets"
 WHERE ((CAST(DATE_TRUNC('QUARTER', CAST("tweets"."created_at" AS DATE)) AS DATE) IN ((TIMESTAMP '2017-10-01 00:00:00.000'), (TIMESTAMP '2018-01-01 00:00:00.000'), (TIMESTAMP '2018-04-01 00:00:00.000')))
        AND (STRPOS(CAST(LOWER(CAST(CAST("tweets"."text" AS TEXT) AS TEXT)) AS TEXT), CAST('iphone' AS TEXT)) > 0))
 GROUP BY 2`,
        "rewritten_sql": `SELECT SUM(1) AS "cnt:tweets_5460F7F804494E7CB9FD188E329004C1:ok",
        CAST(tweets.state_name AS TEXT) AS state_name
 FROM public.tweets AS tweets
 WHERE CAST(DATE_TRUNC('QUARTER', CAST(tweets.created_at AS DATE)) AS DATE) IN ((TIMESTAMP '2017-10-01 00:00:00.000'), (TIMESTAMP '2018-01-01 00:00:00.000'), (TIMESTAMP '2018-04-01 00:00:00.000'))
   AND STRPOS(CAST(LOWER(CAST(CAST(tweets.text AS TEXT) AS TEXT)) AS TEXT), CAST('iphone' AS TEXT)) > 0
 GROUP BY 2`
    }
];

export default defaultQueriesData