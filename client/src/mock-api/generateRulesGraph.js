const defaultRulesGraphData = { 
    'rules': [
        {
            'id': '1', 
            'pattern': 'CAST(created_at AS DATE)', 
            'rewrite': 'created_at', 
            'constraints': '', 
            'actions': '',
            'level': 1
        },
        {
            'id': '2', 
            'pattern': 'CAST(<x1> AS DATE)', 
            'rewrite': '<x1>', 
            'constraints': '', 
            'actions': '', 
            'level': 2,
            'recommended': true
        },
        {
            'id': '3', 
            'pattern': 'CAST(timestamp AS DATE)', 
            'rewrite': 'timestamp', 
            'constraints': '', 
            'actions': '',
            'level': 1
        }
    ],
    'relations': [
        {'parentRuleId': '1', 'childRuleId': '2'},
        {'parentRuleId': '3', 'childRuleId': '2'}
    ]
};

export default defaultRulesGraphData;