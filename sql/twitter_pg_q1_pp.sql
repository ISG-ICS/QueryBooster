SELECT SUM(1) AS "cnt:tweets_5460F7F804494E7CB9FD188E329004C1:ok",
  "tweets"."state_name" AS "state_name"
FROM "public"."tweets" "tweets"
WHERE ((DATE_TRUNC('QUARTER', "tweets"."created_at") IN ((TIMESTAMP '2016-10-01 00:00:00.000'), (TIMESTAMP '2017-01-01 00:00:00.000'), (TIMESTAMP '2017-04-01 00:00:00.000'))) AND ("tweets"."text" LIKE '%iphone%'))
GROUP BY 2