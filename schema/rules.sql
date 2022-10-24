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
    rule_id INTEGER,
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
    timestamp TEXT,
    latency REAL,
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
