const defaultRuleGraphData = { 
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
        }
    ],
    'relations': [
        {'parentRuleId': '1', 'childRuleId': '2'}
    ]
};

export default defaultRuleGraphData;