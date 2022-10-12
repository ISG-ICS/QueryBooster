from core.query_patcher import QueryPatcher


def test_patch_ilike():
    q0 = "SELECT * FROM tweets WHERE ILIKE(text, '%iphone%')"
    q1 = "SELECT * FROM tweets WHERE text ILIKE '%iphone%'"
    assert q1 == QueryPatcher.patch_ilike(q0)


def test_patch_timestamp_1():
    q0 = '''
        SELECT tweets.state_name AS state_name
        FROM public.tweets AS tweets
        WHERE DATE_TRUNC('QUARTER', tweets.created_at) = TIMESTAMP('2017-04-01 00:00:00.000')
        AND tweets.text ILIKE '%iphone%'
        GROUP BY 1
    '''
    q1 = '''
        SELECT tweets.state_name AS state_name
        FROM public.tweets AS tweets
        WHERE DATE_TRUNC('QUARTER', tweets.created_at) = (TIMESTAMP '2017-04-01 00:00:00.000')
        AND tweets.text ILIKE '%iphone%'
        GROUP BY 1
    '''
    assert q1 == QueryPatcher.patch_timestamp(q0)


def test_patch_timestamp_2():
    q0 = "SELECT SUM(1), CAST(state_name AS TEXT) FROM tweets WHERE DATE_TRUNC('QUARTER', created_at) IN (TIMESTAMP('2016-10-01 00:00:00.000'), TIMESTAMP('2017-01-01 00:00:00.000'), TIMESTAMP('2017-04-01 00:00:00.000')) AND STRPOS(text, 'iphone') > 0 GROUP BY 2"
    q1 = "SELECT SUM(1), CAST(state_name AS TEXT) FROM tweets WHERE DATE_TRUNC('QUARTER', created_at) IN ((TIMESTAMP '2016-10-01 00:00:00.000'), (TIMESTAMP '2017-01-01 00:00:00.000'), (TIMESTAMP '2017-04-01 00:00:00.000')) AND STRPOS(text, 'iphone') > 0 GROUP BY 2"
    assert q1 == QueryPatcher.patch_timestamp(q0)