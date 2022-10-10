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
    FOREIGN KEY (rule_id) REFERENCES rules(id)
);

CREATE TABLE IF NOT EXISTS internal_rules(
    rule_id INTEGER,
    pattern_json TEXT,
    constraints_json TEXT,
    rewrite_json TEXT,
    actions_json TEXT,
    FOREIGN KEY (rule_id) REFERENCES rules(id)
);
