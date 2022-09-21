select empno, firstnme, lastname, phoneno
  from employee
 where workdept in
       (select deptno
         from department
         where deptname = 'OPERATIONS');
