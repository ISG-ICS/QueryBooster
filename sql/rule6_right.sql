SELECT UserId,
       MIN(Date) as FirstBadgeDate
FROM
    Badges
GROUP BY UserId;
