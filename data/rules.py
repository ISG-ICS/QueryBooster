import json

rules = [
    # PostgresSQL Rules
    # 
    {
        'id': 0,
        'key': 'remove_distinct',
        'name': 'Remove Distinct',
        'pattern': 'MAX(DISTINCT <x>)',
        'pattern_json': json.loads('{"max": {"distinct": "V1"}}'),
        'constraints': '',
        'rewrite': 'MAX(<x>)',
        'rewrite_json': json.loads('{"max": "V1"}'),
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 1,
        'key': 'remove_cast',
        'name': 'Remove Cast',
        'pattern': 'CAST(<x> AS DATE)',
        'pattern_json': json.loads('{"cast": ["V1", {"date": {}}]}'),
        'constraints': 'TYPE(x) = DATE',
        'rewrite': '<x>',
        'rewrite_json': json.loads('"V1"'),
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 2,
        'key': 'replace_strpos',
        'name': 'Replace Strpos',
        'pattern': "STRPOS(LOWER(<x>), '<y>') > 0",
        'pattern_json': json.loads('{"gt": [{"strpos": [{"lower": "V1"}, {"literal": "V2"}]}, 0]}'),
        'constraints': 'IS(y) = CONSTANT and TYPE(y) = STRING',
        'rewrite': "<x> ILIKE '%<y>%'",
        'rewrite_json': json.loads('{"ilike": ["V1", {"literal": "%V2%"}]}'),
        'actions': '',
        'database': 'postgresql'
    },

    # MySQL Rules
    # 
    {
        'id': 101,
        'key': 'remove_adddate',
        'name': 'Remove Adddate', 
        'pattern': "ADDDATE(<x>, INTERVAL 0 SECOND)", 
        'pattern_json': json.loads('{"adddate": ["V1", {"interval": [0, "second"]}]}'),
        'constraints': '',
        'rewrite': '<x>',
        'rewrite_json': json.loads('"V1"'),
        'actions': '',
        'database': 'mysql'
    },

    {
        'id': 102,
        'key': 'remove_timestamp', 
        'name': 'Remove Timestamp', 
        'pattern': '<x> = TIMESTAMP(<y>)', 
        'pattern_json': json.loads('{"eq": ["V1", {"timestamp": "V2"}]}'),
        'constraints': 'TYPE(x) = STRING',
        'rewrite': '<x> = <y>',
        'rewrite_json': json.loads('{"eq": ["V1", "V2"]}'),
        'actions': '',
        'database': 'mysql'
    },
]

def get_rule(id: int):
    return next(filter(lambda x: x['id'] == id, rules), None)