const defaultRewritingPathData = 
{
    "original_sql": `SELECT  SUM(1),
        CAST(state_name AS TEXT)
FROM  tweets 
WHERE  CAST(DATE_TRUNC('QUARTER', 
                        CAST(created_at AS DATE)) 
        AS DATE) IN 
            ((TIMESTAMP '2016-10-01 00:00:00.000'), 
            (TIMESTAMP '2017-01-01 00:00:00.000'), 
            (TIMESTAMP '2017-04-01 00:00:00.000'))
AND  (STRPOS(text, 'iphone') > 0)
GROUP  BY 2;`,
    "rewritings":
    [
        {
            "seq": 1,
            "rule": "Remove Cast Date",
            "rewritten_sql": `SELECT  SUM(1),
        CAST(state_name AS TEXT)
FROM  tweets 
WHERE  DATE_TRUNC('QUARTER', created_at) 
        IN 
            ((TIMESTAMP '2016-10-01 00:00:00.000'), 
            (TIMESTAMP '2017-01-01 00:00:00.000'), 
            (TIMESTAMP '2017-04-01 00:00:00.000'))
AND  (STRPOS(text, 'iphone') > 0)
GROUP  BY 2;`
        },
        {
            "seq": 2,
            "rule": "Replace Strpos Lower",
            "rewritten_sql": `SELECT  SUM(1),
       CAST(state_name AS TEXT)
FROM  tweets 
WHERE  DATE_TRUNC('QUARTER', created_at) 
       IN 
           ((TIMESTAMP '2016-10-01 00:00:00.000'), 
           (TIMESTAMP '2017-01-01 00:00:00.000'), 
           (TIMESTAMP '2017-04-01 00:00:00.000'))
AND  text ILIKE '%iphone%'
GROUP  BY 2;`
        }
    ]
};

export default defaultRewritingPathData;