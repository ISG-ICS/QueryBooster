CREATE TABLE IF NOT EXISTS rules(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(255) UNIQUE,
    name VARCHAR(2048) NOT NULL,
    formula TEXT,
    database VARCHAR(255) NOT NULL
);

INSERT OR IGNORE INTO rules (key, name, formula, database) VALUES('remove_cast', 'Remove Cast', 'CAST(<exp> AS <type>) => <exp>', 'postgresql');
INSERT OR IGNORE INTO rules (key, name, formula, database) VALUES('replace_strpos', 'Replace Strpos', 'STRPOS(LOWER(<exp>), ''<literal>'') > 0 => <exp> ILIKE ''%<literal>%''', 'postgresql');
INSERT OR IGNORE INTO rules (key, name, formula, database) VALUES('remove_adddate', 'Remove Adddate', 'ADDDATE(<exp>, INTERVAL 0 <unit>) => <exp>', 'mysql');
INSERT OR IGNORE INTO rules (key, name, formula, database) VALUES('remove_timestamp', 'Remove Timestamp', 'TIMESTAMP(<literal>) => <literal>', 'mysql');

CREATE TABLE IF NOT EXISTS disable_rules(
    rule_id INTEGER UNIQUE,
    disabled BOOLEAN
);