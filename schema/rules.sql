CREATE TABLE IF NOT EXISTS rules(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(255) UNIQUE,
    name VARCHAR(2048) NOT NULL,
    formula TEXT
);

INSERT OR IGNORE INTO rules (key, name, formula) VALUES('remove_cast', 'Remove Cast', 'CAST(<exp> AS <type>) => <exp>');
INSERT OR IGNORE INTO rules (key, name, formula) VALUES('replace_strpos', 'Replace Strpos', 'STRPOS(LOWER(<exp>), ''<literal>'') > 0 => <exp> ILIKE ''%<literal>%''');

CREATE TABLE IF NOT EXISTS disable_rules(
    rule_id INTEGER UNIQUE,
    disabled BOOLEAN
);