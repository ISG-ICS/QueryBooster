SELECT e1.name, 
       e1.age, 
       e1.salary 
  FROM employee e1
 WHERE e1.age > 17
   AND e1.salary > 35000;