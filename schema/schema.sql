CREATE TABLE IF NOT EXISTS rules(
    id INTEGER PRIMARY KEY,
    key VARCHAR(255) UNIQUE,
    name VARCHAR(2048) NOT NULL,
    pattern TEXT,
    constraints TEXT,
    rewrite TEXT,
    actions TEXT,
    user_id TEXT,
    CONSTRAINT fk_rules
        FOREIGN KEY (user_id)
        REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS internal_rules(
    rule_id INTEGER UNIQUE,
    pattern_json TEXT,
    constraints_json TEXT,
    rewrite_json TEXT,
    actions_json TEXT,
    CONSTRAINT fk_rules 
        FOREIGN KEY (rule_id) 
        REFERENCES rules(id) 
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS users(
    id TEXT PRIMARY KEY,
    email TEXT
);

CREATE TABLE IF NOT EXISTS applications(
    id INTEGER PRIMARY KEY,
    name TEXT,
    guid TEXT,
    user_id TEXT,
    CONSTRAINT fk_users
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS enabled(
    application_id INTEGER,
    rule_id INTEGER,
    PRIMARY KEY (application_id, rule_id),
    CONSTRAINT fk_applications
        FOREIGN KEY (application_id) 
        REFERENCES applications(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_rules 
        FOREIGN KEY (rule_id) 
        REFERENCES rules(id) 
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS queries(
    id INTEGER PRIMARY KEY,
    guid TEXT,
    appguid TEXT,
    timestamp TEXT,
    query_time_ms REAL,
    original_sql TEXT,
    sql TEXT
);

CREATE TABLE IF NOT EXISTS rewriting_paths(
    query_id INTEGER,
    seq INTEGER,
    rule_id INTEGER,
    rewritten_sql TEXT,
    PRIMARY KEY (query_id, seq),
    CONSTRAINT fk_queries 
        FOREIGN KEY (query_id) 
        REFERENCES queries(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rules 
        FOREIGN KEY (rule_id) 
        REFERENCES rules(id) 
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS suggestions(
    query_id INTEGER UNIQUE,
    query_time_ms REAL,
    rewritten_sql TEXT,
    CONSTRAINT fk_queries 
        FOREIGN KEY (query_id) 
        REFERENCES queries(id) 
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS suggestion_rewriting_paths(
    query_id INTEGER,
    seq INTEGER,
    rule_id INTEGER,
    rewritten_sql TEXT,
    PRIMARY KEY (query_id, seq),
    CONSTRAINT fk_queries 
        FOREIGN KEY (query_id) 
        REFERENCES suggestions(query_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rules 
        FOREIGN KEY (rule_id) 
        REFERENCES rules(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tables(
    id INTEGER PRIMARY KEY,
    application_id INTEGER,
    name TEXT,
    CONSTRAINT fk_applications 
        FOREIGN KEY (application_id) 
        REFERENCES applications(id) 
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS columns(
    id INTEGER PRIMARY KEY,
    table_id INTEGER,
    name TEXT,
    type TEXT,
    CONSTRAINT fk_tables
        FOREIGN KEY (table_id) 
        REFERENCES tables(id) 
        ON DELETE CASCADE
);

DROP VIEW IF EXISTS query_log;
CREATE VIEW query_log AS
SELECT q.id AS id,
       q.timestamp AS timestamp,
       (CASE WHEN q.sql = q.original_sql THEN 'NO' 
             WHEN q.sql != q.original_sql THEN 'YES'
        END) AS rewritten,
       (SELECT AVG(q1.query_time_ms) FROM queries q1 WHERE q1.sql=q.original_sql) AS before_latency,
       q.query_time_ms AS after_latency,
       q.original_sql AS sql,
       (CASE WHEN s.query_id IS NOT NULL THEN 'YES' ELSE 'NO'
        END) AS suggestion,
       (CASE WHEN s.query_id IS NOT NULL THEN s.query_time_ms ELSE -1000
        END) AS suggested_latency,
       a.user_id AS user_id,
       a.name AS app_name
  FROM queries q 
        JOIN applications a ON q.appguid = a.guid
        LEFT OUTER JOIN suggestions s ON q.id = s.query_id
 ORDER BY q.timestamp DESC;