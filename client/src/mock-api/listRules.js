const defaultRulesData = [
    {
        "id": 0,
        "key": "remove_max_distinct",
        "name": "Remove Max Distinct",
        "pattern": "MAX(DISTINCT <x>)",
        "constraints": "",
        "rewrite": "MAX(<x>)",
        "actions": "",
        "enabled": true
    },
    {
        "id": 10,
        "key": "remove_cast_date",
        "name": "Remove Cast Date",
        "pattern": "CAST(<x> AS DATE)",
        "constraints": "TYPE(x)=DATE",
        "rewrite": "<x>",
        "actions": "",
        "enabled": false
    },
    {
        "id": 11,
        "key": "remove_cast_text",
        "name": "Remove Cast Text",
        "pattern": "CAST(<x> AS TEXT)",
        "constraints": "TYPE(x)=TEXT",
        "rewrite": "<x>",
        "actions": "",
        "enabled": false
    },
    {
        "id": 21,
        "key": "replace_strpos_lower",
        "name": "Replace Strpos Lower",
        "pattern": "STRPOS(LOWER(<x>),'<y>')>0",
        "constraints": "IS(y)=CONSTANT and\nTYPE(y)=STRING",
        "rewrite": "<x> ILIKE '%<y>%'",
        "actions": "",
        "enabled": false
    },
    {
        "id": 30,
        "key": "remove_self_join",
        "name": "Remove Self Join",
        "pattern": "select <<s1>> \nfrom <tb1> <t1>,\n     <tb1> <t2>\nwhere <t1>.<a1>=<t2>.<a1>\nand <<p1>>\n",
        "constraints": "UNIQUE(tb1, a1)",
        "rewrite": "select <<s1>> \nfrom <tb1> <t1>\nwhere 1=1 \nand <<p1>>\n",
        "actions": "SUBSTITUTE(s1, t2, t1) and\nSUBSTITUTE(p1, t2, t1)",
        "enabled": true
    },
    {
        "id": 101,
        "key": "remove_adddate",
        "name": "Remove Adddate",
        "pattern": "ADDDATE(<x>, INTERVAL 0 SECOND)",
        "constraints": "",
        "rewrite": "<x>",
        "actions": "",
        "enabled": true
    },
    {
        "id": 102,
        "key": "remove_timestamp",
        "name": "Remove Timestamp",
        "pattern": "<x> = TIMESTAMP(<y>)",
        "constraints": "TYPE(x)=STRING",
        "rewrite": "<x> = <y>",
        "actions": "",
        "enabled": true
    }
];

export default defaultRulesData