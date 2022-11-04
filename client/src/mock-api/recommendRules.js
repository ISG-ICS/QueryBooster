const defaultRecommendRulesData = [
    {
        "pattern": "CAST(<x1> AS DATE)",
        "rewrite": "<x1>"
    },
    {
        "pattern": "STRPOS(UPPER(<x>),'<y>')>0",
        "rewrite": "<x> ILIKE '%<y>%'"
    }
];

export default defaultRecommendRulesData;