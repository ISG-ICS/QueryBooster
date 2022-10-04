queries = [
    {
        'id': 0,
        'original': '''
            SELECT A, MAX(DISTINCT (SELECT B FROM R WHERE C = 0)), D
            FROM S;
        ''',
        'rewritten': [
            '''
                SELECT A, MAX((SELECT B FROM R WHERE C = 0)), D
                FROM S;
            '''
        ],
        'rule_ids': [0]
    },

    {
        'id': 1,
        'original': '''
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
        'rewritten': [
            '''
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
            '''
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
        ],
        'rule_ids': [1, 1]
    },

    {
        'id': 2,
        'original': '''
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
        'rewritten': [
            '''
                SELECT  SUM(1),
                        CAST(state_name AS TEXT)
                FROM  tweets 
                WHERE  CAST(DATE_TRUNC('QUARTER', 
                                        CAST(created_at AS DATE)) 
                        AS DATE) IN 
                            ((TIMESTAMP '2016-10-01 00:00:00.000'), 
                            (TIMESTAMP '2017-01-01 00:00:00.000'), 
                            (TIMESTAMP '2017-04-01 00:00:00.000'))
                AND  ILIKE(text, '%iphone%')
                GROUP  BY 2;
            '''
        ],
        'rule_ids': [2]
    },

    {
        'id': 3,
        'original': '''
            SELECT  e1.name, 
                    e1.age, 
                    e2.salary 
            FROM employee e1, employee e2
            WHERE e1.id = e2.id
            AND e1.age > 17
            AND e2.salary > 35000;
        ''',
        'rewritten': [
            '''
                SELECT  e1.name, 
                        e1.age, 
                        e1.salary 
                FROM employee e1
                WHERE 1=1
                AND e1.age > 17
                AND e1.salary > 35000;
            '''
        ],
        'rule_ids': [3]
    }
]

def get_query(id: int):
    return next(filter(lambda x: x['id'] == id, queries), None)