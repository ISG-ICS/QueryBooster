queries = [
    {
        'id': 1,
        'name': 'Remove Cast Date Match Twice',
        'pattern': '''
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
         GROUP  BY 2;
        ''',
        'rewrite': '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', created_at) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;   
        '''
    },

    {
        'id': 2,
        'name': 'Remove Cast Date Match Once',
        'pattern': '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;
        ''',
        'rewrite': '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', created_at) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;   
        '''
    },

    {
        'id': 3,
        'name': 'Remove Cast Date No Match',
        'pattern': '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', created_at) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;
        ''',
        'rewrite': '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', created_at) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(text, 'iphone') > 0)
         GROUP  BY 2;   
        '''
    },

    {
        'id': 4,
        'name': 'Replace Strpos Lower Match',
        'pattern': '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  (STRPOS(LOWER(text), 'iphone') > 0)
         GROUP  BY 2;
        ''',
        'rewrite': '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
        FROM  tweets 
        WHERE  CAST(DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                AS DATE) IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
        AND text ILIKE '%iphone%'
        GROUP  BY 2;
        '''
    },

    {
        'id': 5,
        'name': 'Replace Strpos Lower No Match',
        'pattern': '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  text ILIKE '%iphone%'
         GROUP  BY 2;
        ''',
        'rewrite': '''
        SELECT  SUM(1),
                CAST(state_name AS TEXT)
          FROM  tweets 
         WHERE  DATE_TRUNC('QUARTER', 
                                CAST(created_at AS DATE)) 
                IN 
                    ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                    (TIMESTAMP '2017-01-01 00:00:00.000'), 
                    (TIMESTAMP '2017-04-01 00:00:00.000'))
           AND  text ILIKE '%iphone%'
         GROUP  BY 2;
        '''
    },

    {
        'id': 6,
        'name': 'Remove Self Join Match',
        'pattern': '''
        SELECT  e1.name, 
                e1.age, 
                e2.salary 
        FROM employee e1, employee e2
        WHERE e1.id = e2.id
        AND e1.age > 17
        AND e2.salary > 35000;
        ''',
        'rewrite': '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE 1=1
        AND e1.age > 17
        AND e1.salary > 35000;
        '''
    },

    {
        'id': 7,
        'name': 'Remove Self Join No Match',
        'pattern': '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000;
        ''',
        'rewrite': '''
        SELECT  e1.name, 
                e1.age, 
                e1.salary 
        FROM employee e1
        WHERE e1.age > 17
        AND e1.salary > 35000;
        '''
    },

    {
        'id': 8,
        'name': 'Remove Self Join Match Simple',
        'pattern': '''
        SELECT  e1.age 
        FROM employee e1, employee e2
        WHERE e1.id = e2.id
        AND e1.age > 17;
        ''',
        'rewrite': '''
        SELECT  e1.age 
        FROM employee e1
        WHERE 1=1
        AND e1.age > 17;
        '''
    },

    {
        'id': 9,
        'name': 'Subquery to Join Match 1',
        'pattern': '''
        select empno, firstnme, lastname, phoneno
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
        and 1=1;
        ''',
        'rewrite': '''
        select distinct empno, firstnme, lastname, phoneno
        from employee, department
        where employee.workdept = department.deptno 
        and deptname = 'OPERATIONS'
        and 1=1;
        '''
    },

    {
        'id': 10,
        'name': 'Subquery to Join Match 2',
        'pattern': '''
        select empno, firstnme, lastname, phoneno
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
        and age > 17;
        ''',
        'rewrite': '''
        select distinct empno, firstnme, lastname, phoneno
        from employee, department
        where employee.workdept = department.deptno 
        and deptname = 'OPERATIONS'
        and age > 17;
        '''
    },

    {
        'id': 11,
        'name': 'Subquery to Join Match 3',
        'pattern': '''
        select e.empno, e.firstnme, e.lastname, e.phoneno
        from employee e
        where e.workdept in
            (select d.deptno
                from department d
                where d.deptname = 'OPERATIONS')
        and e.age > 17;
        ''',
        'rewrite': '''
        select distinct e.empno, e.firstnme, e.lastname, e.phoneno
        from employee e, department d
        where e.workdept = d.deptno 
        and d.deptname = 'OPERATIONS'
        and e.age > 17;
        '''
    },

    {
        'id': 12,
        'name': 'Join to Filter Match 1',
        'pattern': '''
        SELECT *
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminrolei2_.admin_role_id = 1
        AND 1=1;
        ''',
        'rewrite': '''
        SELECT *
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1
        AND 1=1;
        '''
    },

    {
        'id': 13,
        'name': 'Join to Filter Match 2',
        'pattern': '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission adminpermi0_
            INNER JOIN blc_admin_role_permission_xref allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
            INNER JOIN blc_admin_role adminrolei2_
                    ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE  adminpermi0_.is_friendy = 1
            AND adminrolei2_.admin_role_id = 1;
        ''',
        'rewrite': '''
        SELECT Count(adminpermi0_.admin_permission_id) AS col_0_0_
        FROM   blc_admin_permission AS adminpermi0_
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
                    ON adminpermi0_.admin_permission_id =
                        allroles1_.admin_permission_id
        WHERE  allroles1_.admin_role_id = 1 
        AND    adminpermi0_.is_friendy = 1;
        '''
    },

    {
        'id': 14,
        'name': 'Test Rule Wetune 90 Match',
        'pattern': '''
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
            adminpermi0_.description AS descript2_4_,
            adminpermi0_.is_friendly AS is_frien3_4_,
            adminpermi0_.name AS name4_4_,
            adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
        INNER JOIN blc_admin_role_permission_xref allroles1_ ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        INNER JOIN blc_admin_role adminrolei2_ ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
        WHERE adminpermi0_.is_friendly = 1
        AND adminrolei2_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT 50
        ''',
        'rewrite': '''
        SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
            adminpermi0_.description AS descript2_4_,
            adminpermi0_.is_friendly AS is_frien3_4_,
            adminpermi0_.name AS name4_4_,
            adminpermi0_.permission_type AS permissi5_4_
        FROM blc_admin_permission adminpermi0_
        INNER JOIN blc_admin_role_permission_xref allroles1_ ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
        WHERE adminpermi0_.is_friendly = 1
        AND allroles1_.admin_role_id = 1
        ORDER  BY adminpermi0_.description ASC
        LIMIT 50
        '''
    },

    {
        'id': 15,
        'name': 'Test Rule Calcite PushMinThroughUnion',
        'pattern': '''
        SELECT t.ENAME,
            MIN(t.EMPNO)
        FROM
        (SELECT *
        FROM EMP AS EMP
        UNION ALL SELECT *
        FROM EMP AS EMP) AS t
        GROUP BY t.ENAME
        ''',
        'rewrite': '''
        SELECT t6.ENAME, MIN(MIN(EMP.EMPNO))
        FROM (SELECT EMP.ENAME, MIN(EMP.EMPNO)
          FROM EMP
         GROUP BY EMP.ENAME
        UNION ALL SELECT EMP.ENAME, MIN(EMP.EMPNO)
          FROM EMP
         GROUP BY EMP.ENAME) AS t6
        GROUP BY t6.ENAME
        '''
    },

    {
        'id': 16,
        'name': 'Remove Max Distinct',
        'pattern': '''
        SELECT A, MAX(DISTINCT (SELECT B FROM R WHERE C = 0)), D
        FROM S;
        ''',
        'rewrite': '''
        SELECT A, MAX((SELECT B FROM R WHERE C = 0)), D
        FROM S;
        '''
    },

    {
        'id': 17,
        'name': 'Remove 1 Useless InnerJoin',
        'pattern': '''
        SELECT o_auth_applications.id
        FROM   o_auth_applications
            INNER JOIN authorizations
                    ON o_auth_applications.id = authorizations.o_auth_application_id
        WHERE  authorizations.user_id = 1465 
        ''',
        'rewrite': '''
        SELECT authorizations.o_auth_application_id 
        FROM   authorizations
        WHERE  authorizations.user_id = 1465 
        '''
    },

    {
        'id': 18,
        'name': 'Stackoverflow 1',
        'pattern': '''
        SELECT DISTINCT my_table.foo, your_table.boo
        FROM my_table, your_table
        WHERE my_table.num = 1 OR your_table.num = 2
        ''',
        'rewrite': '''
        SELECT
            my_table.foo,
            your_table.boo
        FROM
            my_table,
            your_table
        WHERE
            my_table.num = 1
            OR your_table.num = 2
        GROUP BY
            my_table.foo,
            your_table.boo
        '''
    },

    {
        'id': 19,
        'name': 'Partial Matching Base Case 1',
        'pattern': '''
        SELECT *
        FROM A a
        LEFT JOIN B b ON a.id = b.cid
        WHERE
        b.cl1 = 's1' OR b.cl1 ='s2'
        ''',
        'rewrite': '''
        SELECT *
        FROM A a
        LEFT JOIN B b ON a.id = b.cid
        WHERE
        b.cl1 IN ('s1', 's2')
        '''
    },

    {
        'id': 20,
        'name': 'Partial Matching Base Case 2',
        'pattern': '''
        SELECT *
        FROM b
        WHERE
        b.cl1 IN ('s1', 's2') OR b.cl1 ='s3'
        ''',
        'rewrite': '''
        SELECT *
        FROM b
        WHERE
        b.cl1 IN ('s3', 's1', 's2')
        '''
    },

    {
        'id': 21,
        'name': 'Partial Matching 0',
        'pattern': '''
        SELECT *
        FROM A a
        LEFT JOIN B b ON a.id = b.cid
        WHERE
        b.cl1 = 's1' OR b.cl1 = 's2' OR b.cl1 = 's3'
        ''',
        'rewrite': '''
        SELECT *
        FROM A a
        LEFT JOIN B b ON a.id = b.cid
        WHERE
        b.cl1 IN ('s1', 's2') OR b.cl1 = 's3'
        '''
    },

    {
        'id': 22,
        'name': 'Partial Matching 4',
        'pattern': '''
        select empno, firstname, lastname, phoneno
        from employee
        where workdept in
            (select deptno
                from department
                where deptname = 'OPERATIONS')
        and firstname like 'B%'
        ''',
        'rewrite': '''
        select distinct empno, firstname, lastname, phoneno
        from employee, department
        where employee.workdept = department.deptno
        and deptname = 'OPERATIONS'
        and firstname like 'B%'
        '''
    },

    {
        'id': 23,
        'name': 'Partial Keeps Remaining OR',
        'pattern': '''
        SELECT entities.data
        FROM entities
        WHERE entities._id IN (SELECT index_users_email._id 
                                FROM index_users_email
                                WHERE index_users_email.key = 'test')
        OR entities._id IN (SELECT index_users_profile_name._id 
                                FROM index_users_profile_name
                                WHERE index_users_profile_name.key = 'test')
        ''',
        'rewrite': '''
        SELECT entities.data
        FROM entities
        INNER JOIN index_users_email ON index_users_email._id = entities._id
        WHERE index_users_email.key = 'test'
        OR entities._id IN (SELECT index_users_profile_name._id 
                            FROM index_users_profile_name
                            WHERE index_users_profile_name.key = 'test')
        '''
    },

    {
        'id': 24,
        'name': 'Partial Keeps Remaining AND',
        'pattern': '''
        SELECT Empno
        FROM EMP
        WHERE EMPNO > 10 
        AND EMPNO <= 10
        AND EMPNAME LIKE '%Jason%'
        ''',
        'rewrite': '''
        SELECT Empno
        FROM EMP
        WHERE FALSE
        AND EMPNAME LIKE '%Jason%'
        '''
    },

    {
        'id': 25,
        'name': 'And On True',
        'pattern': '''
        SELECT people.name
        FROM people
        WHERE 1 AND 1
        ''',
        'rewrite': '''
        SELECT people.name
        FROM people
        '''
    },

    {
        'id': 26,
        'name': 'Multiple And On True',
        'pattern': '''
        SELECT name
        FROM people
        WHERE 1 = 1 AND 2 = 2
        ''',
        'rewrite': '''
        SELECT name
        FROM people
        '''
    },

    {
        'id': 27,
        'name': 'Remove Where True',
        'pattern': '''
        SELECT *
        FROM Emp
        WHERE age > age - 2;
        ''',
        'rewrite': '''
        SELECT *
        FROM Emp
        '''
    },

    {
        'id': 28,
        'name': 'Rewrite Skips Failed Partial',
        'pattern': '''
        SELECT * 
        FROM accounts 
        WHERE LOWER(accounts.firstname) = LOWER('Sam') 
            AND accounts.id IN (SELECT addresses.account_id 
                                            FROM addresses 
                                    WHERE LOWER(addresses.name) = LOWER('Street1'))         
            AND accounts.id IN (SELECT alternate_ids.account_id 
                                    FROM alternate_ids 
                                    WHERE alternate_ids.alternate_id_glbl = '5'); 
        ''',
        'rewrite': '''
        SELECT * 
        FROM accounts 
        JOIN addresses ON accounts.id = addresses.account_id
        JOIN alternate_ids ON accounts.id = alternate_ids.account_id
        WHERE LOWER(accounts.firstname) = LOWER('Sam') 
        AND LOWER(addresses.name) = LOWER('Street1') 
        AND alternate_ids.alternate_id_glbl = '5';
        '''
    },

    {
        'id': 29,
        'name': 'Full Matching',
        'pattern': '''
        SELECT entities.data FROM entities WHERE entities._id IN (SELECT index_users_email._id FROM index_users_email WHERE index_users_email.key = 'test')
        UNION
        SELECT entities.data FROM entities WHERE entities._id IN (SELECT index_users_profile_name._id FROM index_users_profile_name WHERE index_users_profile_name.key = 'test')
        ''',
        'rewrite': '''
        SELECT entities.data FROM entities INNER JOIN index_users_email ON index_users_email._id = entities._id WHERE index_users_email.key = 'test'
        UNION
        SELECT entities.data FROM entities INNER JOIN index_users_profile_name ON index_users_profile_name._id = entities._id WHERE index_users_profile_name.key = 'test'
        '''
    },

    {
        'id': 30,
        'name': 'Over Partial Matching',
        'pattern': '''
        SELECT * FROM table_name WHERE (table_name.title = 1 and table_name.grade = 2) OR (table_name.title = 2 and table_name.debt = 2 and table_name.grade = 3) OR (table_name.prog = 1 and table_name.title =1 and table_name.debt = 3)
        ''',
        'rewrite': '''
        SELECT * FROM table_name WHERE (table_name.title = 1 and table_name.grade = 2) OR (table_name.title = 2 and table_name.debt = 2 and table_name.grade = 3) OR (table_name.prog = 1 and table_name.title =1 and table_name.debt = 3)
        '''
    },

    {
        'id': 31,
        'name': 'Aggregation to Subquery',
        'pattern': '''
SELECT 
    t1.CPF,
    DATE(t1.data) AS data,
    CASE WHEN SUM(CASE WHEN t1.login_ok = true
                       THEN 1
                       ELSE 0
                  END) >= 1
         THEN true
         ELSE false
    END
FROM db_risco.site_rn_login AS t1
GROUP BY t1.CPF, DATE(t1.data)
        ''',
        'rewrite': '''
SELECT
    t1.CPF,
    t1.data    
FROM (
    SELECT 
        CPF, 
        DATE(data)
    FROM db_risco.site_rn_login
    WHERE login_ok = true
) t1
GROUP BY t1.CPF, t1.data
        '''
    },

    {
        'id': 32,
        'name': 'Spreadsheet ID 2',
        'pattern': '''
SELECT * 
FROM place 
WHERE "select" = TRUE
   OR exists (SELECT id 
              FROM bookmark 
              WHERE user IN (1,2,3,4) 
                AND bookmark.place = place.id) 
 LIMIT 10;
        ''',
        'rewrite': '''
SELECT * 
FROM (
    (SELECT * 
    FROM place 
    WHERE "select" = True 
    LIMIT 10) 
UNION 
    (SELECT * 
    FROM place 
    WHERE EXISTS 
        (SELECT 1 
        FROM bookmark 
        WHERE user IN (1, 2, 3, 4) 
        AND bookmark.place = place.id) 
    LIMIT 10))
LIMIT 10
        '''
    },

    {
        'id': 33,
        'name': 'Spreadsheet ID 3',
        'pattern': '''
SELECT EMPNO FROM EMP WHERE EMPNO > 10 AND EMPNO <= 10
        ''',
        'rewrite': '''
SELECT EMPNO FROM EMP WHERE FALSE
        '''
    },

    {
        'id': 34,
        'name': 'Spreadsheet ID 7',
        'pattern': '''
select * from 
a
left join b on a.id = b.cid 
where 
b.cl1 = 's1' 
or 
b.cl1 ='s2'
or
b.cl1 ='s3' 
        ''',
        'rewrite': '''
select * from 
a 
left join b on a.id = b.cid 
where 
b.cl1 in ('s1','s2','s3')
        '''
    },

    {
        'id': 35,
        'name': 'Spreadsheet ID 9',
        'pattern': '''
SELECT DISTINCT my_table.foo
FROM my_table
WHERE my_table.num = 1;
        ''',
        'rewrite': '''
SELECT my_table.foo
FROM my_table
WHERE my_table.num = 1
GROUP BY my_table.foo;
        '''
    },

    {
        'id': 36,
        'name': 'Spreadsheet ID 10',
        'pattern': '''
SELECT table1.wpis_id
FROM table1
WHERE table1.etykieta_id IN (
  SELECT table2.tag_id
  FROM table2
  WHERE table2.postac_id = 376476
  );
        ''',
        'rewrite': '''
SELECT table1.wpis_id 
FROM table1
INNER JOIN table2 on table2.tag_id = table1.etykieta_id
WHERE table2.postac_id = 376476
        '''
    },

    {
        'id': 37,
        'name': 'Spreadsheet ID 11',
        'pattern': '''
SELECT historicoestatusrequisicion_id, requisicion_id, estatusrequisicion_id, 
            comentario, fecha_estatus, usuario_id
            FROM historicoestatusrequisicion hist1
            WHERE requisicion_id IN
            (
            SELECT requisicion_id FROM historicoestatusrequisicion hist2
            WHERE usuario_id = 27 AND estatusrequisicion_id = 1
            )
            ORDER BY requisicion_id, estatusrequisicion_id
        ''',
        'rewrite': '''
SELECT hist1.historicoestatusrequisicion_id, hist1.requisicion_id, hist1.estatusrequisicion_id, hist1.comentario, hist1.fecha_estatus, hist1.usuario_id
            FROM historicoestatusrequisicion hist1
            JOIN historicoestatusrequisicion hist2 ON hist2.requisicion_id = hist1.requisicion_id
            WHERE hist2.usuario_id = 27 AND hist2.estatusrequisicion_id = 1
            ORDER BY hist1.requisicion_id, hist1.estatusrequisicion_id
        '''
    },

    {
        'id': 38,
        'name': 'Spreadsheet ID 12',
        'pattern': '''
SELECT po.id, 
       SUM(grouped_items.total_quantity) AS order_total_quantity
FROM purchase_orders po
LEFT JOIN (
  SELECT items.purchase_order_id, 
  SUM(items.quantity) AS item_total
  FROM items
  GROUP BY items.purchase_order_id
) grouped_items ON po.id = grouped_items.purchase_order_id
WHERE po.shop_id = 195
GROUP BY po.id
        ''',
        'rewrite': '''
SELECT po.id,
       (
           SELECT SUM(items.quantity)
           FROM items
           WHERE items.purchase_order_id = po.id
           GROUP BY items.purchase_order_id
       ) AS order_total_quantity
FROM purchase_orders po
WHERE shop_id = 195
GROUP BY po.id
        '''
    },

    {
        'id': 39,
        'name': 'Spreadsheet ID 15',
        'pattern': '''
SELECT *
FROM users u
WHERE u.id IN
    (SELECT s1.user_id
     FROM sessions s1
     WHERE s1.user_id <> 1234
       AND (s1.ip IN
              (SELECT s2.ip
               FROM sessions s2
               WHERE s2.user_id = 1234
               GROUP BY s2.ip)
            OR s1.cookie_identifier IN
              (SELECT s3.cookie_identifier
               FROM sessions s3
               WHERE s3.user_id = 1234
               GROUP BY s3.cookie_identifier))
     GROUP BY s1.user_id)
        ''',
        'rewrite': '''
SELECT *
FROM users u
WHERE EXISTS (
    SELECT
        NULL
    FROM sessions s1
    WHERE s1.user_id <> 1234
    AND u.id = s1.user_id
    AND EXISTS (
        SELECT
            NULL
        FROM sessions s2
        WHERE s2.user_id = 1234
        AND (s1.ip = s2.ip
          OR s1.cookie_identifier = s2.cookie_identifier
            )
        )
    )
        '''
    },

    {
        'id': 40,
        'name': 'Spreadsheet ID 18',
        'pattern': '''
SELECT DISTINCT ON (t.playerId) t.gzpId, t.pubCode, t.playerId,
       COALESCE (p.preferenceValue,'en'),
       s.segmentId 
FROM userPlayerIdMap t LEFT JOIN
     userPreferences p
     ON t.gzpId  = p.gzpId LEFT JOIN
     segment s
     ON t.gzpId = s.gzpId 
WHERE t.pubCode IN ('hyrmas','ayqioa','rj49as99') and
      t.provider IN ('FCM','ONE_SIGNAL') and
      s.segmentId IN (0,1,2,3,4,5,6) and
      p.preferenceValue IN ('en','hi') 
ORDER BY t.playerId desc;
        ''',
        'rewrite': '''
SELECT t.gzpId, t.pubCode, t.playerId,
       COALESCE((SELECT p.preferenceValue
                 FROM userPreferences p
                 WHERE t.gzpId = p.gzpId AND
                       p.preferenceValue IN ('en', 'hi')
                 LIMIT 1
                ), 'en'
               ),
       (SELECT s.segmentId 
        FROM segment s
        WHERE t.gzpId = s.gzpId AND
              s.segmentId IN (0, 1, 2, 3, 4, 5, 6)
        LIMIT 1
       )
FROM userPlayerIdMap t
WHERE t.pubCode IN ('hyrmas', 'ayqioa', 'rj49as99') and
      t.provider IN ('FCM', 'ONE_SIGNAL');
        '''
    },

    {
        'id': 41,
        'name': 'Spreadsheet ID 20',
        'pattern': '''
SELECT * FROM (SELECT * FROM (SELECT NULL FROM EMP) WHERE N IS NULL) WHERE N IS NULL
        ''',
        'rewrite': '''
SELECT NULL FROM EMP
        '''
    },

    {
        'id': 42,
        'name': 'PostgreSQL Test',
        'pattern': '''
        SELECT "tweets"."latitude" AS "latitude",
               "tweets"."longitude" AS "longitude"
          FROM "public"."tweets" "tweets"
         WHERE (("tweets"."latitude" >= -90) AND ("tweets"."latitude" <= 80) 
           AND ((("tweets"."longitude" >= -173.80000000000001) AND ("tweets"."longitude" <= 180)) OR ("tweets"."longitude" IS NULL)) 
           AND (CAST((DATE_TRUNC( 'day', CAST("tweets"."created_at" AS DATE) ) + (-EXTRACT(DOW FROM "tweets"."created_at") * INTERVAL '1 DAY')) AS DATE) 
                = (TIMESTAMP '2018-04-22 00:00:00.000')) 
           AND (STRPOS(CAST(LOWER(CAST(CAST("tweets"."text" AS TEXT) AS TEXT)) AS TEXT),CAST('microsoft' AS TEXT)) > 0))
           GROUP BY 1, 2
    ''',
        'rewrite': '''
        SELECT "tweets"."latitude" AS "latitude",
               "tweets"."longitude" AS "longitude"
          FROM "public"."tweets" "tweets"
         WHERE (("tweets"."latitude" >= -90) AND ("tweets"."latitude" <= 80) 
           AND ((("tweets"."longitude" >= -173.80000000000001) AND ("tweets"."longitude" <= 180)) OR ("tweets"."longitude" IS NULL)) 
           AND ((DATE_TRUNC( 'day', "tweets"."created_at" ) + (-EXTRACT(DOW FROM "tweets"."created_at") * INTERVAL '1 DAY')) 
                = (TIMESTAMP '2018-04-22 00:00:00.000')) 
           AND "tweets"."text" ILIKE '%microsoft%')
           GROUP BY 1, 2
    '''
    },

    {
        'id': 43,
        'name': 'MySQL Test',
        'pattern': '''
SELECT `tweets`.`latitude` AS `latitude`,
                    `tweets`.`longitude` AS `longitude`
               FROM `tweets`
              WHERE ((ADDDATE(DATE_FORMAT(`tweets`.`created_at`, '%Y-%m-01 00:00:00'), INTERVAL 0 SECOND) = TIMESTAMP('2017-03-01 00:00:00'))
                AND (LOCATE('iphone', LOWER(`tweets`.`text`)) > 0))
              GROUP BY 1, 2''',
        'rewrite': '''
SELECT `tweets`.`latitude` AS `latitude`,
                    `tweets`.`longitude` AS `longitude`
               FROM `tweets`
              WHERE ((DATE_FORMAT(`tweets`.`created_at`, '%Y-%m-01 00:00:00') = TIMESTAMP('2017-03-01 00:00:00'))
                AND (LOCATE('iphone', LOWER(`tweets`.`text`)) > 0))
              GROUP BY 1, 2'''
    }
]


def get_query(query_id: int) -> dict:
    return next(filter(lambda x: x["id"] == query_id, queries), None)
