select distinct empno, firstnme, lastname, phoneno
  from employee emp, department dept
 where emp.workdept = dept.deptno 
   and dept.deptname = 'OPERATIONS';