import re


class QueryPatcher:

    # Patch the SQL query based on specific database
    #
    @staticmethod
    def patch(sql: str, database: str) -> str:
        if database == 'postgresql':
            sql = QueryPatcher.patch_ilike(sql)
            sql = QueryPatcher.patch_timestamp(sql)
        return sql

    # Patch the SQL query with a trasnformation for ILIKE
    #   Note: This is needed only because the SQL Parser (mo_sql_parsing) 
    #         we use treats ILIKE as a normal function instead of a predicate,
    #         e.g., ILIKE("tweets"."text",\'%microsoft%\').
    #         We need to use regex to transform it back to 
    #           "tweets"."text" ILIKE \'%microsoft%\'.
    #   Demo: https://regex101.com/r/gkUZb4/3
    #         
    @staticmethod
    def patch_ilike(sql: str) -> str:
        return re.sub(r"ILIKE\((.[^\,]*)\s*,\s*(.[^\)]*)\)", r"\1 ILIKE \2", sql)
    
    # Patch the SQL query with a transformation for TIMESTAMP (postgresql)
    #   Note: PostgreSQL syntax for TIMESTAMP constant is the following:
    #           TIMESTAMP '2017-04-01 00:00:00.000'
    #         while the SQL Parser (mo_sql_parsing) serializes it as:
    #           TIMESTAMP('2017-04-01 00:00:00.000')
    #   Demo: https://regex101.com/r/ywmIUn/4
    # 
    @staticmethod
    def patch_timestamp(sql: str) -> str:
        return re.sub(r"TIMESTAMP\(\s*(.[^\)]*)\s*\)", r"(TIMESTAMP \1)", sql)
