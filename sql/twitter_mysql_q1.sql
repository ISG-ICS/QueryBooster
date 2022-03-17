SELECT `tweets`.`latitude` AS `latitude`,
       `tweets`.`longitude` AS `longitude`
FROM `tweets`
WHERE ((ADDDATE(DATE_FORMAT(`tweets`.`created_at`, '%Y-%m-01 00:00:00'), INTERVAL 0 SECOND) = TIMESTAMP('2017-03-01 00:00:00'))
       AND (LOCATE('iphone', LOWER(`tweets`.`text`)) > 0))
GROUP BY 1,
         2