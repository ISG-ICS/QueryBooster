SELECT DISTINCT
    o.UserId,
    FirstBadgeDate
FROM
    Badges o
    INNER JOIN 
        (SELECT UserId, 
                MIN(Date) as FirstBadgeDate 
           FROM Badges GROUP BY UserId
        ) i
    ON o.UserId = i.UserId;
