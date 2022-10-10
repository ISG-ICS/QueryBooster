import json

from core.rule_parser import RuleParser

rules = [
    # PostgresSQL Rules
    # 
    {
        'id': 0,
        'key': 'remove_max_distinct',
        'name': 'Remove Max Distinct',
        'pattern': 'MAX(DISTINCT <x>)',
        # 'pattern_json': '{"max": {"distinct": "V1"}}',
        'constraints': '',
        # 'constraints_json': '[]',
        'rewrite': 'MAX(<x>)',
        # 'rewrite_json': '{"max": "V1"}',
        'actions': '',
        # 'actions_json': '[]',
        # 'mapping': '{"x": "V1"}',
        'database': 'postgresql'
    },

    {
        'id': 10,
        'key': 'remove_cast_date',
        'name': 'Remove Cast Date',
        'pattern': 'CAST(<x> AS DATE)',
        # 'pattern_json': '{"cast": ["V1", {"date": {}}]}',
        'constraints': 'TYPE(x) = DATE',
        # 'constraints_json': "[{\"operator\": \"=\", \"operands\": [{\"function\": \"type\", \"variables\": [\"V1\"]}, \" date\"]}]",
        'rewrite': '<x>',
        # 'rewrite_json': '"V1"',
        'actions': '',
        # 'actions_json': "[]",
        # 'mapping': "{\"x\": \"V1\"}",
        'database': 'postgresql'
    },

    {
        'id': 11,
        'key': 'remove_cast_text',
        'name': 'Remove Cast Text',
        'pattern': 'CAST(<x> AS TEXT)',
        'constraints': 'TYPE(x) = TEXT',
        'rewrite': '<x>',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 21,
        'key': 'replace_strpos_lower',
        'name': 'Replace Strpos Lower',
        'pattern': "STRPOS(LOWER(<x>), '<y>') > 0",
        # 'pattern_json': '{"gt": [{"strpos": [{"lower": "V1"}, {"literal": "V2"}]}, 0]}',
        'constraints': 'IS(y) = CONSTANT and TYPE(y) = STRING',
        # 'constraints_json': "[{\"operator\": \"=\", \"operands\": [{\"function\": \"is\", \"variables\": [\"V2\"]}, \" constant \"]}, {\"operator\": \"=\", \"operands\": [{\"function\": \" type\", \"variables\": [\"V2\"]}, \" string\"]}]",
        'rewrite': "<x> ILIKE '%<y>%'",
        # 'rewrite_json': '{"ilike": ["V1", {"literal": "%V2%"}]}',
        'actions': '',
        # 'actions_json': "[]",
        # 'mapping': "{\"x\": \"V1\", \"y\": \"V2\"}",
        'database': 'postgresql'
    },

    {
        'id': 30,
        'key': 'remove_self_join',
        'name': 'Remove Self Join',
        'pattern': '''
            select <<s1>>
            from <tb1> <t1>, 
                 <tb1> <t2>
            where <t1>.<a1>=<t2>.<a1>
            and <<p1>>
        ''',
        # 'pattern_json': "{\"select\": {\"value\": \"VL1\"}, \"from\": [{\"value\": \"V1\", \"name\": \"V2\"}, {\"value\": \"V1\", \"name\": \"V3\"}], \"where\": {\"and\": [{\"eq\": [\"V2.V4\", \"V3.V4\"]}, \"VL2\"]}}",
        'constraints': 'UNIQUE(tb1, a1)',
        # 'constraints_json': "[{\"operator\": \"=\", \"operands\": [{\"function\": \"unique\", \"variables\": [\"V1\", \"V4\"]}, \"true\"]}]",
        'rewrite': '''
            select <<s1>> 
            from <tb1> <t1>
            where 1=1 
            and <<p1>>
        ''',
        # 'rewrite_json': "{\"select\": {\"value\": \"VL1\"}, \"from\": {\"value\": \"V1\", \"name\": \"V2\"}, \"where\": {\"and\": [{\"eq\": [1, 1]}, \"VL2\"]}}",
        'actions': 'SUBSTITUTE(s1, t2, t1) AND SUBSTITUTE(p1, t2, t1)',
        # 'actions_json': "[{\"function\": \"substitute\", \"variables\": [\"VL1\", \"V3\", \"V2\"]}, {\"function\": \"substitute\", \"variables\": [\"VL2\", \"V3\", \"V2\"]}]",
        # 'mapping': "{\"s1\": \"VL1\", \"p1\": \"VL2\", \"tb1\": \"V1\", \"t1\": \"V2\", \"t2\": \"V3\", \"a1\": \"V4\"}",
        'database': 'postgresql'
    },

    # MySQL Rules
    # 
    {
        'id': 101,
        'key': 'remove_adddate',
        'name': 'Remove Adddate', 
        'pattern': "ADDDATE(<x>, INTERVAL 0 SECOND)", 
        # 'pattern_json': '{"adddate": ["V1", {"interval": [0, "second"]}]}',
        'constraints': '',
        # 'constraints_json': "[]",
        'rewrite': '<x>',
        # 'rewrite_json': '"V1"',
        'actions': '',
        # 'actions_json': "[]",
        # 'mapping': "{\"x\": \"V1\"}",
        'database': 'mysql'
    },

    {
        'id': 102,
        'key': 'remove_timestamp', 
        'name': 'Remove Timestamp', 
        'pattern': '<x> = TIMESTAMP(<y>)', 
        # 'pattern_json': '{"eq": ["V1", {"timestamp": "V2"}]}',
        'constraints': 'TYPE(x) = STRING',
        # 'constraints_json': "[{\"operator\": \"=\", \"operands\": [{\"function\": \"type\", \"variables\": [\"V1\"]}, \" string\"]}]",
        'rewrite': '<x> = <y>',
        # 'rewrite_json': '{"eq": ["V1", "V2"]}',
        'actions': '',
        # 'actions_json': "[]",
        # 'mapping': "{\"x\": \"V1\", \"y\": \"V2\"}",
        'database': 'mysql'
    },
]

# fetch one rule by key (json attributes are in json)
# 
def get_rule(key: str) -> dict:
    rule = next(filter(lambda x: x['key'] == key, rules), None)
    rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
    rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
    rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
    return {
        'id': rule['id'],
        'key': rule['key'], 
        'name': rule['name'], 
        'pattern': rule['pattern'], 
        'pattern_json': json.loads(rule['pattern_json']),
        'constraints': rule['constraints'],
        'constraints_json': json.loads(rule['constraints_json']),
        'rewrite': rule['rewrite'],
        'rewrite_json': json.loads(rule['rewrite_json']),
        'actions': rule['actions'],
        'actions_json': json.loads(rule['actions_json']),
        'mapping': json.loads(rule['mapping']),
        'database': rule['database']
    }

# return a list of rules (json attributes are in str)
# 
def get_rules() -> list:
    for rule in rules:
        rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
        rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
        rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
    return rules