SELECT DISTINCT
    UserId,
    FirstBadgeDate = (
        SELECT MIN(Date) 
          FROM Badges i 
         WHERE o.UserId = i.UserId
    )
FROM
    Badges o;
