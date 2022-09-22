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

-- rule 1
INSERT OR IGNORE INTO rules (
    id, 
    key, 
    name, 
    pattern, 
    constraints, 
    rewrite, 
    actions, 
    database) 
VALUES(
    1, 
    'remove_cast', 
    'Remove Cast', 
    'CAST(<x> AS DATE)', 
    'TYPE(x) = DATE',
    '<x>',
    '',
    'postgresql'
);
-- rule 2
INSERT OR IGNORE INTO rules (
    id, 
    key, 
    name, 
    pattern, 
    constraints, 
    rewrite, 
    actions, 
    database) 
VALUES(
    2, 
    'replace_strpos', 
    'Replace Strpos', 
    'STRPOS(LOWER(<x>), <y>) > 0',
    'IS(y) = CONSTANT and TYPE(y) = STRING',
    '<x> ILIKE ''%<y>%''',
    '', 
    'postgresql'
);
-- rule 101
INSERT OR IGNORE INTO rules (
    id, 
    key, 
    name, 
    pattern, 
    constraints, 
    rewrite, 
    actions, 
    database) 
VALUES(
    101, 
    'remove_adddate', 
    'Remove Adddate', 
    'ADDDATE(<x>, INTERVAL 0 SECOND)', 
    '',
    '<x>',
    '',
    'mysql');
-- rule 102
INSERT OR IGNORE INTO rules (
    id, 
    key, 
    name, 
    pattern, 
    constraints, 
    rewrite, 
    actions, 
    database) 
VALUES(
    102, 
    'remove_timestamp', 
    'Remove Timestamp', 
    '<x> = TIMESTAMP(<y>)', 
    'TYPE(x) = STRING',
    '<x> = <y>',
    '',
    'mysql');

CREATE TABLE IF NOT EXISTS disable_rules(
    rule_id INTEGER UNIQUE,
    disabled BOOLEAN
);