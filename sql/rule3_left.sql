SELECT e1.name, 
        e1.age, 
        e2.salary 
  FROM employee e1, employee e2
  WHERE e1.id = e2.id
    AND e1.age > 17
    AND e2.salary > 35000;