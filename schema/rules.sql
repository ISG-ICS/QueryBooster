CREATE TABLE IF NOT EXISTS rules(
    id INTEGER PRIMARY KEY,
    key VARCHAR(255) UNIQUE,
    name VARCHAR(2048) NOT NULL,
    formula TEXT,
    is_hint  BOOLEAN DEFAULT FALSE,
    database VARCHAR(255) NOT NULL
);

INSERT OR IGNORE INTO rules (id, key, name, formula, database) VALUES(1, 'remove_cast', 'Remove Cast', 'CAST(<exp> AS <type>) => <exp>', 'postgresql');
INSERT OR IGNORE INTO rules (id, key, name, formula, database) VALUES(2, 'replace_strpos', 'Replace Strpos', 'STRPOS(LOWER(<exp>), ''<literal>'') > 0 => <exp> ILIKE ''%<literal>%''', 'postgresql');
INSERT OR IGNORE INTO rules (id, key, name, formula, is_hint, database) VALUES(3, 'hint_monthly_idx', 'Hint Monthly Index', '<sql> => hint=BitmapScan(<idx_monthly_created_at>) ', 1, 'postgresql');
INSERT OR IGNORE INTO rules (id, key, name, formula, database) VALUES(4, 'remove_adddate', 'Remove Adddate', 'ADDDATE(<exp>, INTERVAL 0 <unit>) => <exp>', 'mysql');
INSERT OR IGNORE INTO rules (id, key, name, formula, database) VALUES(5, 'remove_timestamp', 'Remove Timestamp', 'TIMESTAMP(<literal>) => <literal>', 'mysql');

CREATE TABLE IF NOT EXISTS disable_rules(
    rule_id INTEGER UNIQUE,
    disabled BOOLEAN
);

INSERT OR IGNORE INTO disable_rules(rule_id, disabled) VALUES(3, 1);