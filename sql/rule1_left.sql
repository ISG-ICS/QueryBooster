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
