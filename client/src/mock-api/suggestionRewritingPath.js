const defaultSuggestionRewritingPathData = 
{
    "original_sql": `SELECT "lineitem"."l_shipmode" AS "l_shipmode",
    SUM("lineitem"."l_quantity") AS "sum:l_quantity:ok:1"
FROM "public"."lineitem" AS "lineitem"
WHERE STRPOS(CAST(LOWER(CAST("lineitem"."l_comment" AS TEXT)) AS TEXT), CAST('late' AS TEXT)) > 0
GROUP BY 1`,
    "rewritings":
    [
        {
            "seq": 1,
            "rule": "Remove Cast Text",
            "rule_id": 11,
            "rule_user_id": 102153741508111367852,
            "rule_user_email": "alice.vldb@gmail.com",
            "rewritten_sql": `SELECT "lineitem"."l_shipmode" AS "l_shipmode",
            SUM("lineitem"."l_quantity") AS "sum:l_quantity:ok:1"
        FROM "public"."lineitem" AS "lineitem"
        WHERE STRPOS(LOWER(CAST("lineitem"."l_comment" AS TEXT)), CAST('late' AS TEXT)) > 0
        GROUP BY 1`
        },
        {
            "seq": 2,
            "rule": "Remove Cast Text",
            "rule_id": 11,
            "rule_user_id": 102153741508111367852,
            "rule_user_email": "alice.vldb@gmail.com",
            "rewritten_sql": `SELECT "lineitem"."l_shipmode" AS "l_shipmode",
            SUM("lineitem"."l_quantity") AS "sum:l_quantity:ok:1"
        FROM "public"."lineitem" AS "lineitem"
        WHERE STRPOS(LOWER("lineitem"."l_comment"), CAST('late' AS TEXT)) > 0
        GROUP BY 1`
        },
        {
            "seq": 3,
            "rule": "Remove Cast Text",
            "rule_id": 11,
            "rule_user_id": 102153741508111367852,
            "rule_user_email": "alice.vldb@gmail.com",
            "rewritten_sql": `SELECT "lineitem"."l_shipmode" AS "l_shipmode",
            SUM("lineitem"."l_quantity") AS "sum:l_quantity:ok:1"
        FROM "public"."lineitem" AS "lineitem"
        WHERE STRPOS(LOWER("lineitem"."l_comment"), 'late') > 0
        GROUP BY 1`
        },
        {
            "seq": 4,
            "rule": "Replace Strpos Lower",
            "rule_id": 21,
            "rule_user_id": 102153741508111367852,
            "rule_user_email": "alice.vldb@gmail.com",
            "rewritten_sql": `SELECT "lineitem"."l_shipmode" AS "l_shipmode",
            SUM("lineitem"."l_quantity") AS "sum:l_quantity:ok:1"
        FROM "public"."lineitem" AS "lineitem"
        WHERE "lineitem"."l_comment" ILIKE '%late%'
        GROUP BY 1`
        }
    ]
};

export default defaultSuggestionRewritingPathData;