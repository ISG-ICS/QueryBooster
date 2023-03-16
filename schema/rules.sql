CREATE TABLE IF NOT EXISTS rules(
    id INTEGER PRIMARY KEY,
    key VARCHAR(255) UNIQUE,
    name VARCHAR(2048) NOT NULL,
    pattern TEXT,
    constraints TEXT,
    rewrite TEXT,
    actions TEXT,
    database VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS disable_rules(
    rule_id INTEGER UNIQUE,
    disabled BOOLEAN,
    CONSTRAINT fk_rules
        FOREIGN KEY (rule_id) 
        REFERENCES rules(id) 
        ON DELETE CASCADE
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

CREATE TABLE IF NOT EXISTS query_logs(
    id INTEGER PRIMARY KEY,
    appguid TEXT,
    guid TEXT,
    timestamp TEXT,
    query_time_ms REAL,
    original_sql TEXT,
    rewritten_sql TEXT
);

CREATE TABLE IF NOT EXISTS rewriting_paths(
    query_id INTEGER,
    seq INTEGER,
    rule_id INTEGER,
    rewritten_sql TEXT,
    PRIMARY KEY (query_id, seq),
    CONSTRAINT fk_queries 
        FOREIGN KEY (query_id) 
        REFERENCES query_logs(id) 
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
        REFERENCES query_logs(id) 
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

CREATE VIEW IF NOT EXISTS queries AS
SELECT ql.id AS id,
       ql.timestamp AS timestamp,
       (CASE WHEN ql.original_sql = ql.rewritten_sql THEN 'NO' 
             WHEN ql.original_sql != ql.rewritten_sql THEN 'YES'
        END) AS boosted,
       (SELECT AVG(ql1.query_time_ms) FROM query_logs ql1 WHERE ql1.rewritten_sql=ql.original_sql) AS before_latency,
       ql.query_time_ms AS after_latency,
       ql.original_sql AS sql,
       (CASE WHEN s.query_id IS NOT NULL THEN 'YES' ELSE 'NO'
        END) AS suggestion,
       (CASE WHEN s.query_id IS NOT NULL THEN s.query_time_ms ELSE -1000
        END) AS suggested_latency
  FROM query_logs ql LEFT OUTER JOIN suggestions s ON ql.id = s.query_id
 ORDER BY ql.timestamp DESC;