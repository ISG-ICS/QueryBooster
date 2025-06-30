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
        'constraints': 'TYPE(x)=DATE',
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
        'constraints': 'TYPE(x)=TEXT',
        'rewrite': '<x>',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 21,
        'key': 'replace_strpos_lower',
        'name': 'Replace Strpos Lower',
        'pattern': "STRPOS(LOWER(<x>),'<y>')>0",
        # 'pattern_json': '{"gt": [{"strpos": [{"lower": "V1"}, {"literal": "V2"}]}, 0]}',
        'constraints': 'IS(y)=CONSTANT and\n TYPE(y)=STRING',
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
        'actions': 'SUBSTITUTE(s1, t2, t1) and\n SUBSTITUTE(p1, t2, t1)',
        # 'actions_json': "[{\"function\": \"substitute\", \"variables\": [\"VL1\", \"V3\", \"V2\"]}, {\"function\": \"substitute\", \"variables\": [\"VL2\", \"V3\", \"V2\"]}]",
        # 'mapping': "{\"s1\": \"VL1\", \"p1\": \"VL2\", \"tb1\": \"V1\", \"t1\": \"V2\", \"t2\": \"V3\", \"a1\": \"V4\"}",
        'database': 'postgresql'
    },

    {
        'id': 31,
        'key': 'remove_self_join_advance',
        'name': 'Remove Self Join Advance',
        'pattern': '''
select <<s1>>
  from <t1>, 
       <t2>
 where <t1>.<a1>=<t2>.<a1>
   and <<p1>>
        ''',
        'constraints': 'UNIQUE(t1, a1) and t1 = t2',
        'rewrite': '''
select <<s1>> 
  from <t1>
 where 1=1 
   and <<p1>>
        ''',
        'actions': 'SUBSTITUTE(s1, t2, t1) and\n SUBSTITUTE(p1, t2, t1)',
        'database': 'postgresql'
    },

    {
        'id': 40,
        'key': 'subquery_to_join',
        'name': 'Subquery To Join',
        'pattern': '''
select <<s1>>
  from <tb1>
 where <a1> in (select <a2> from <tb2> where <<p2>>)
   and <<p1>>
        ''',
        'constraints': '',
        'rewrite': '''
select distinct <<s1>>
  from <tb1>, <tb2>
 where <tb1>.<a1> = <tb2>.<a2>
   and <<p1>>
   and <<p2>>
        ''',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 50,
        'key': 'join_to_filter',
        'name': 'Join To Filter',
        'pattern': '''
select <<s1>>
  from <tb1> <t1>
    inner join <tb2> <t2> on <t1>.<a1> = <t2>.<a2>
    inner join <tb3> <t3> on <t2>.<a3> = <t3>.<a4>
 where <t3>.<a4> = <c1>
   and <<p1>>
        ''',
        'constraints': '',
        'rewrite': '''
select <<s1>>
  from <tb1> <t1>
    inner join <tb2> <t2> on <t1>.<a1> = <t2>.<a2>
 where <t2>.<a3> = <c1>
   and <<p1>>
        ''',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 51,
        'key': 'join_to_filter_advance',
        'name': 'Join To Filter Advance',
        'pattern': '''
select <<s1>>
  from <tb1>
    inner join <tb2> on <tb1>.<a1> = <tb2>.<a2>
    inner join <tb3> on <tb2>.<a3> = <tb3>.<a4>
 where <tb3>.<a4> = <c1>
   and <<p1>>
        ''',
        'constraints': '',
        'rewrite': '''
select <<s1>>
  from <tb1>
    inner join <tb2> on <tb1>.<a1> = <tb2>.<a2>
 where <tb2>.<a3> = <c1>
   and <<p1>>
        ''',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 52,
        'key': 'join_to_filter_partial1',
        'name': 'Join To Filter Partial1',
        'pattern': '''
  FROM <x1>
    INNER JOIN <x2> ON <x9>
    INNER JOIN <x3> ON <x2>.<x5> = <x3>.<x5>
 WHERE <x3>.<x5> = <x7>
        ''',
        'constraints': '',
        'rewrite': '''
  FROM <x1>
    INNER JOIN <x2> ON <x9>
 WHERE <x2>.<x5> = <x7>
        ''',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 53,
        'key': 'join_to_filter_partial2',
        'name': 'Join To Filter Partial2',
        'pattern': '''
  FROM <x1>
    INNER JOIN <x2> ON <x9>
    INNER JOIN <x3> ON <x2>.<x5> = <x3>.<x5>
 WHERE <<y1>>
   AND <x3>.<x5> = <x7>
        ''',
        'constraints': '',
        'rewrite': '''
  FROM <x1>
    INNER JOIN <x2> ON <x9>
 WHERE <<y1>>
   AND <x2>.<x5> = <x7>
        ''',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 54,
        'key': 'join_to_filter_partial3',
        'name': 'Join To Filter Partial3',
        'pattern': '''
  FROM <x1>
    INNER JOIN <x2> ON <x9>
    INNER JOIN <x3> ON <x2>.<x5> = <x3>.<x5>
 WHERE <<y1>>
   AND <x3>.<x5> = <x7>
        ''',
        'constraints': '',
        'rewrite': '''
  FROM <x1>
    INNER JOIN <x2> ON <x9>
 WHERE <x2>.<x5> = <x7>
   AND <<y1>>
        ''',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 61,
        'key': 'remove_1useless_innerjoin',
        'name': 'Remove 1Useless InnerJoin',
        'pattern': '''
SELECT <x1>.<x2> 
  FROM <x1> 
    INNER JOIN <x3> ON <x1>.<x2> = <x3>.<x6> 
 WHERE <x5>
        ''',
        'constraints': '',
        'rewrite': '''
SELECT <x3>.<x6> 
  FROM <x3> 
 WHERE <x5>
        ''',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 8090,
        'key': 'test_rule_wetune_90',
        'name': 'Test Rule Wetune 90',
        'pattern': '''
SELECT <x1>.<x6> AS admin_pe1_4_, <x1>.<x5> AS descript2_4_, <x1>.<x4> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x8> AS permissi5_4_
  FROM <x1>
    INNER JOIN <x2> ON <x1>.<x6> = <x2>.<x6>
    INNER JOIN <x3> ON <x2>.<x7> = <x3>.<x7>
 WHERE <x1>.<x4> = <x10>
   AND <x3>.<x7> = <x10>
 ORDER BY <x1>.<x5> ASC
 LIMIT <x11>
        ''',
        'constraints': '',
        'rewrite': '''
SELECT <x1>.<x6> AS admin_pe1_4_, <x1>.<x5> AS descript2_4_, <x1>.<x4> AS is_frien3_4_, <x1>.<x9> AS name4_4_, <x1>.<x8> AS permissi5_4_
  FROM <x1>
    INNER JOIN <x2> ON <x1>.<x6> = <x2>.<x6>
 WHERE <x1>.<x4> = <x10>
   AND <x2>.<x7> = <x10>
 ORDER BY <x1>.<x5> ASC
 LIMIT <x11>
        ''',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 8190,
        'key': 'query_rule_wetune_90',
        'name': 'Query Rule Wetune 90',
        'pattern': '''
SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
       adminpermi0_.description AS descript2_4_,
       adminpermi0_.is_friendly AS is_frien3_4_,
       adminpermi0_.name AS name4_4_,
       adminpermi0_.permission_type AS permissi5_4_
  FROM blc_admin_permission adminpermi0_
    INNER JOIN blc_admin_role_permission_xref allroles1_ ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
    INNER JOIN blc_admin_role adminrolei2_ ON allroles1_.admin_role_id = adminrolei2_.admin_role_id
 WHERE adminpermi0_.is_friendly = 1
   AND adminrolei2_.admin_role_id = 1
 ORDER  BY adminpermi0_.description ASC
 LIMIT 50
        ''',
        'constraints': '',
        'rewrite': '''
SELECT adminpermi0_.admin_permission_id AS admin_pe1_4_,
       adminpermi0_.description AS descript2_4_,
       adminpermi0_.is_friendly AS is_frien3_4_,
       adminpermi0_.name AS name4_4_,
       adminpermi0_.permission_type AS permissi5_4_
  FROM blc_admin_permission adminpermi0_
    INNER JOIN blc_admin_role_permission_xref allroles1_ ON adminpermi0_.admin_permission_id = allroles1_.admin_permission_id
 WHERE adminpermi0_.is_friendly = 1
   AND allroles1_.admin_role_id = 1
 ORDER  BY adminpermi0_.description ASC
 LIMIT 50
        ''',
        'actions': '',
        'database': 'postgresql'
    },

    {
        'id': 10001,
        'key': 'test_rule_calcite_testPushMinThroughUnion',
        'name': 'Test Rule Calcite testPushMinThroughUnion',
        'pattern': '''
SELECT t.<x3>, MIN(t.<x4>)
  FROM(SELECT <x2>
         FROM <x1>
        UNION ALL
       SELECT <x2>
         FROM <x1>) AS t
 GROUP BY t.<x3>
        ''',
        'constraints': '',
        'rewrite': '''
SELECT t6.<x3>, MIN(MIN(<x1>.<x4>))
  FROM (SELECT <x1>.<x3>, MIN(<x1>.<x4>)
          FROM <x1>
         GROUP BY <x1>.<x3>
        UNION ALL SELECT <x1>.<x3>, MIN(<x1>.<x4>)
          FROM <x1>
         GROUP BY <x1>.<x3>) AS t6
 GROUP BY t6.<x3>
        ''',
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
        'constraints': 'TYPE(x)=STRING',
        # 'constraints_json': "[{\"operator\": \"=\", \"operands\": [{\"function\": \"type\", \"variables\": [\"V1\"]}, \" string\"]}]",
        'rewrite': '<x> = <y>',
        # 'rewrite_json': '{"eq": ["V1", "V2"]}',
        'actions': '',
        # 'actions_json': "[]",
        # 'mapping': "{\"x\": \"V1\", \"y\": \"V2\"}",
        'database': 'mysql'
    },

    {
        'id': 103,
        'key': 'stackoverflow_1',
        'name': 'Stackoverflow 1',
        'pattern': 'SELECT DISTINCT <<x2>> FROM <<x1>> WHERE <<y1>>',
        'constraints': '',
        'rewrite': 'SELECT <<x2>> FROM <<x1>> WHERE <<y1>> GROUP BY <<x2>>',
        'actions': '',
        'database': 'postgresql'
    },
    {
        'id': 2258,
        'key': 'combine_or_to_in',
        'name': 'combine multiple or to in',
        'pattern': '<x> = <y> OR <x> = <z>',
        'constraints': '',
        'rewrite': '<x> IN (<y>, <z>)',
        'actions': '',
        'database': 'mysql'
    },
    {
        'id': 2259,
        'key': 'merge_or_to_in',
        'name': 'merge or to in',
        'pattern': '<x> IN (<<y>>) OR <x> = <z>',
        'constraints': '',
        'rewrite': '<x> IN (<<y>>, <z>)',
        'actions': '',
        'database': 'mysql'
    },
    {
        'id': 2260,
        'key': 'merge_in_statements',
        'name': 'merge statements with in condition',
        'pattern': '<x> IN <<y>> OR <x> IN <<z>>',
        'constraints': '',
        'rewrite': '<x> IN (<<y>>, <<z>>)',
        'actions': '',
        'database': 'mysql'
    },
    {
      "id": 2261,
      'key': 'multiple_merge_in',
      'name': 'multiple merge in',
      "pattern": "<x> IN (<<y>>) OR <x> IN (<<z>>)",
      'constraints': '',
      "rewrite": "<x> IN (<<y>>, <<z>>)",
      'actions': '',
      'database': 'mysql'
    },
    {
      "id": 2262,
      'key': 'partial_subquery_to_join',
      'name': 'partial subquery to join',
      "pattern": "SELECT <x17>, <x16>, <x15>, <x14> FROM <x1> WHERE <x8> IN (SELECT <x4> FROM <x2> WHERE <<y2>>)",
      'constraints': '',
      "rewrite": "SELECT DISTINCT <x17>, <x16>, <x15>, <x14> FROM <x1>, <x2> WHERE <x1>.<x8> = <x2>.<x4> AND <<y2>>",
      'actions': '',
      'database': 'mysql'
    },
    {
      "id": 2263,
      'key': 'and_on_true',
      'name': 'where 1 and 1',
      "pattern": "FROM <x1> WHERE 1 AND 1",
      'constraints': '',
      "rewrite": "FROM <x1>",
      'actions': '',
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
    ans = []
    for rule in rules:
      # Only populate Tableau rules
      #
      if 0 <= rule['id'] < 30 or 100 <= rule['id'] < 130:
        rule['pattern_json'], rule['rewrite_json'], rule['mapping'] = RuleParser.parse(rule['pattern'], rule['rewrite'])
        rule['constraints_json'] = RuleParser.parse_constraints(rule['constraints'], rule['mapping'])
        rule['actions_json'] = RuleParser.parse_actions(rule['actions'], rule['mapping'])
        ans.append(rule)
    # For demo: populate no rules to the querybooster.db
    #
    ans = []
    return ans