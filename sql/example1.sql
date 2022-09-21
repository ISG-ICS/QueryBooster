SELECT  S.name, B.make, B.model 
FROM  Sailors S, Reserves R, Boats B
WHERE  S.id = R.sid
AND  R.bid = B.id
AND  R.date = '2001-12-25'
AND  B.color = 'red';
