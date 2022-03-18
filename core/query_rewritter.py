from typing import Any, Dict, List
import sqlparse
from sqlparse.sql import Where, Parenthesis, Function, TokenList, Identifier, Token, Comparison
from sqlparse.tokens import Token as T
from mo_sql_parsing import parse
from mo_sql_parsing import format

from core.data_manager import DataManager

class QueryRewritter:

    @staticmethod
    def rewrite(query: str, dm: DataManager, database: str) -> str:
        
        # fetch enabled rules order by id ascending
        enabled_rules = QueryRewritter.fetch_enabled_rules(dm, database)
        
        # TODO - use different paths for PostgreSQL and MySQL rules,
        #        combine them when re-implement PostgreSQL rules using mo-sql-parsing
        # 
        # - PostgreSQL rules
        # 
        if database == 'postgresql':
            # parse query
            parsed = sqlparse.parse(query)[0]
            # rewrite query by firing enabled rules in order
            for rule in enabled_rules:
                QueryRewritter.fire_rule_pg(parsed, rule)
            return str(parsed)
        elif database == 'mysql':
            # parse query
            parsed = parse(query)
            # rewrite query by firing enabled rules in order
            for rule in enabled_rules:
                parsed = QueryRewritter.fire_rule_mysql(parsed, rule)
            return format(parsed)
    
    @staticmethod
    def fetch_enabled_rules(dm: DataManager, database: str) -> List:
        enabled_rules = dm.enabled_rules(database)
        res = []
        for enabled_rule in enabled_rules:
            res.append({
                'id': enabled_rule[0],
                'key': enabled_rule[1],
                'name': enabled_rule[2],
                'formula': enabled_rule[3]
            })
        return res
    
    @staticmethod
    def fire_rule_pg(parsed, rule) -> None:
        if rule['key'] == 'remove_cast':
            QueryRewritter.remove_cast(parsed)
        if rule['key'] == 'replace_strpos':
            QueryRewritter.replace_strpos(parsed)
        return

    @staticmethod
    def fire_rule_mysql(parsed, rule) -> Any:
        if rule['key'] == 'remove_adddate':
            return QueryRewritter.remove_adddate(parsed)
        if rule['key'] == 'remove_timestamp':
            return QueryRewritter.remove_timestamp(parsed)
        return parsed
    
    @staticmethod
    def format(query):
        return sqlparse.format(query, reindent=True)
    
    @staticmethod
    def remove_adddate(parsed: Any) -> Any:
        if isinstance(parsed, Dict):
            for key, value in parsed.items():
                # function name is 'adddate'
                if key == 'adddate':
                    # adddate function is a list with two elements
                    if isinstance(value, List) and len(value) == 2:
                        # the second element is the literal to add
                        added_literal = value[1]
                        # the literal is a dict with key 'interval'
                        if isinstance(added_literal, Dict) and 'interval' in added_literal.keys():
                            interval = added_literal['interval']
                            # interval is a list with two elements:
                            if isinstance(interval, List) and len(interval) == 2:
                                # the first element of interval is the length of interval
                                # if the added interval has length 0,
                                # then it is safe to remove adddate function
                                if interval[0] == 0:
                                    # upgrade the operand of 'adddate' function as result,
                                    # which is the parent of 'adddate' function
                                    return value[0]
                else:
                    parsed[key] = QueryRewritter.remove_adddate(value)
            return parsed
        elif isinstance(parsed, List):
            for index, element in enumerate(parsed):
                parsed[index] = QueryRewritter.remove_adddate(element)
            return parsed
        else:
            return parsed
    
    @staticmethod
    def remove_timestamp(parsed: Any) -> Any:
        if isinstance(parsed, Dict):
            for key, value in parsed.items():
                # function name is 'timestamp'
                if key == 'timestamp':
                    # timestamp() has only one paramter
                    if isinstance(value, Dict):
                        return value
                    else:
                        return parsed
                else:
                    parsed[key] = QueryRewritter.remove_timestamp(value)
            return parsed
        elif isinstance(parsed, List):
            for index, element in enumerate(parsed):
                parsed[index] = QueryRewritter.remove_timestamp(element)
            return parsed
        else:
            return parsed
                        
    
    @staticmethod
    def get_column(parsed):
        column = None
        find = False
        for item in parsed.tokens:
            # column is identifier
            if isinstance(item, Identifier):
                # pattern is [Symbol, Punctuation, Symbol]
                if len(item.tokens) == 3:
                    if item.tokens[0].ttype is T.Literal.String.Symbol:
                        if item.tokens[1].ttype is T.Punctuation:
                            if item.tokens[2].ttype is T.Literal.String.Symbol:
                                column = item
                                find = True
            if not find and isinstance(item, TokenList):
                column = QueryRewritter.get_column(item)
        return column
    
    @staticmethod
    def get_literal(parsed):
        literal = None
        find = False
        for item in parsed.tokens:
            if item.ttype is T.Literal.String.Single:
                literal = item
                find = True
            if not find and isinstance(item, TokenList):
                literal = QueryRewritter.get_literal(item)
        return literal
    
    # Pattern of STRPOS() > 0
    # |- 1 Comparison 'STRPOS...'
    # |  |  |  |  |- 0 Function 'STRPOS...'
    # |  |  |  |  |  |- 0 Identifier 'STRPOS'
    # |  |  |  |  |  |  `- 0 Name 'STRPOS'
    # |  |  |  |  |  `- 1 Parenthesis '(LOWER...'
    # |  |  |  |  |     |- 0 Punctuation '('
    # |  |  |  |  |     |- 1 IdentifierList 'LOWER(...'
    # |  |  |  |  |     |  |- 0 Function 'LOWER(...'
    # |  |  |  |  |     |  |  `- 0 Parenthesis 'LOWER(...'
    # |  |  |  |  |     |  |     `- 0 Identifier 'LOWER(...'
    # |  |  |  |  |     |  |        `- 0 Function 'LOWER(...'
    # |  |  |  |  |     |  |           |- 0 Identifier 'LOWER'
    # |  |  |  |  |     |  |           |  `- 0 Name 'LOWER'
    # |  |  |  |  |     |  |           `- 1 Parenthesis '("twee...'
    # |  |  |  |  |     |  |              |- 0 Punctuation '('
    # |  |  |  |  |     |  |              |- 1 Function '"tweet...'
    # |  |  |  |  |     |  |              |  `- 0 Parenthesis '"tweet...'
    # |  |  |  |  |     |  |              |     `- 0 Identifier '"tweet...'
    # |  |  |  |  |     |  |              |        `- 0 Function '"tweet...'
    # |  |  |  |  |     |  |              |           `- 0 Parenthesis '"tweet...'
    # |  |  |  |  |     |  |              |              `- 0 Identifier '"tweet...'
    # |  |  |  |  |     |  |              |                 |- 0 Symbol '"tweet...'
    # |  |  |  |  |     |  |              |                 |- 1 Punctuation '.'
    # |  |  |  |  |     |  |              |                 `- 2 Symbol '"text"'
    # |  |  |  |  |     |  |              `- 2 Punctuation ')'
    # |  |  |  |  |     |  |- 1 Punctuation ','
    # |  |  |  |  |     |  `- 2 Function ''micro...'
    # |  |  |  |  |     |     `- 0 Parenthesis ''micro...'
    # |  |  |  |  |     |        `- 0 Identifier ''micro...'
    # |  |  |  |  |     |           `- 0 Single ''micro...'
    # |  |  |  |  |     `- 2 Punctuation ')'
    # |  |  |  |  |- 1 Whitespace ' '
    # |  |  |  |  |- 2 Comparison '>'
    # |  |  |  |  |- 3 Whitespace ' '
    # |  |  |  |  `- 4 Integer '0'
    @staticmethod
    def replace_strpos(parsed):
        for item in parsed.tokens:
            if isinstance(item, Comparison):
                # right of Comparison is 0
                if str(item.right) == '0':
                    # last third token is '>'
                    if str(item.tokens[-3]) == '>':
                        # left of Comparison is Function
                        if isinstance(item.left, Function):
                            function = item.left
                            # first token of Function is function name identifier
                            t_function_name = function.tokens[0]
                            if isinstance(t_function_name, Identifier):
                                function_name = t_function_name.get_name()
                                # function name is 'STRPOS'
                                if function_name.upper() == 'STRPOS':
                                    parameters = list(function.get_parameters())
                                    # decide whether case sensitive or not
                                    case_sensitive = True
                                    if 'lower(' in str(parameters[0]).lower():
                                        case_sensitive = False
                                    # get column identifier from the left parameter
                                    column = QueryRewritter.get_column(parameters[0])
                                    # get string literal from the right parameter
                                    literal = QueryRewritter.get_literal(parameters[1])
                                    # insert % to both sides of the literal
                                    literal.value = '\'%' + str(literal.value)[1:-1] + '%\''
                                    # replace the current Comparison token with the new token of LIKE/ILIKE predicate
                                    # template of "tweets"."text" ILIKE 'microsoft':
                                    # `- 0 Comparison '"tweet...'
                                    # |- 0 Identifier '"tweet...'
                                    # |  |- 0 Symbol '"tweet...'
                                    # |  |- 1 Punctuation '.'
                                    # |  `- 2 Symbol '"text"'
                                    # |- 1 Whitespace ' '
                                    # |- 2 Comparison 'ILIKE'
                                    # |- 3 Whitespace ' '
                                    # `- 4 Single ''micro...'
                                    item.tokens[0] = column
                                    column.parent = item
                                    item.tokens[-1] = literal
                                    literal.parent = item
                                    if case_sensitive:
                                        item.tokens[-3] = Token(T.Comparison, 'LIKE')
                                    else:
                                        item.tokens[-3] = Token(T.Comparison, 'ILIKE')

            if isinstance(item, TokenList):
                QueryRewritter.replace_strpos(item)


    @staticmethod
    def remove_cast(parsed):
        for item in parsed.tokens:
            if isinstance(item, Function):
                # first token of Function is function name identifier
                t_function_name = item.tokens[0]
                if isinstance(t_function_name, Identifier):
                    function_name = t_function_name.get_name()
                    # function name is 'CAST'
                    if function_name.upper() == 'CAST':
                        # remove 'CAST' identifier
                        item.tokens = item.tokens[1:]
                        # second token of CAST Function is (... AS [TYPE])
                        cast_content = item.tokens[0]
                        # remove the following parenthesis of CAST
                        if isinstance(cast_content, Parenthesis):
                            cast_content.tokens = cast_content.tokens[1:-1]
                            # remove the pattern of suffix: Whitespace, AS, Whitespace, [TYPE] (e.g., TEXT)
                            # but this pattern is 1-level under the cast_content.tokens
                            # e.g.,
                            # |- 0 Identifier 'CAST'
                            # |  `- 0 Name 'CAST'
                            # `- 1 Parenthesis '('micr...'  <---- cast_content
                            # |- 0 Punctuation '('
                            # |- 1 Identifier ''micro...'
                            # |  |- 0 Single ''micro...'
                            # |  |- 1 Whitespace ' '
                            # |  |- 2 Keyword 'AS'
                            # |  |- 3 Whitespace ' '
                            # |  `- 4 Builtin 'TEXT'
                            # `- 2 Punctuation ')'
                            identifier = cast_content.tokens[0]
                            # remove the last 4 tokens under identifier
                            identifier.tokens = identifier.tokens[:-4]
            if isinstance(item, TokenList):
                QueryRewritter.remove_cast(item)

    @staticmethod
    def get_where(parsed):
        for item in parsed.tokens:
            if isinstance(item, Where):
                return item


if __name__ == '__main__':
    
    # PostgreSQL Query
    # 
    sql = '''SELECT "tweets"."latitude" AS "latitude",
                    "tweets"."longitude" AS "longitude"
               FROM "public"."tweets" "tweets"
              WHERE (("tweets"."latitude" >= -90) AND ("tweets"."latitude" <= 80) 
                AND ((("tweets"."longitude" >= -173.80000000000001) AND ("tweets"."longitude" <= 180)) OR ("tweets"."longitude" IS NULL)) 
                AND (CAST((DATE_TRUNC( \'day\', CAST("tweets"."created_at" AS DATE) ) + (-EXTRACT(DOW FROM "tweets"."created_at") * INTERVAL \'1 DAY\')) AS DATE) 
                    = (TIMESTAMP \'2018-04-22 00:00:00.000\')) 
                AND (STRPOS(CAST(LOWER(CAST(CAST("tweets"."text" AS TEXT) AS TEXT)) AS TEXT),CAST(\'microsoft\' AS TEXT)) > 0))
              GROUP BY 1, 2'''
    
    print("======================================")
    print("    PostgreSQL Original Query")
    print("--------------------------------------")
    print(sqlparse.format(sql, reindent=True))
    parsed = sqlparse.parse(sql)[0]

    # test QueryRewritter.remove_cast()
    #
    print("======================================")
    print("    After remove_cast()")
    print("--------------------------------------")
    QueryRewritter.remove_cast(parsed)
    sql1 = str(parsed)
    print(sqlparse.format(sql1, reindent=True))

    # test QueryRewritter.replace_strpos()
    #
    print("======================================")
    print("    After replace_strpos()")
    print("--------------------------------------")
    QueryRewritter.replace_strpos(parsed)
    sql2 = str(parsed)
    print(sqlparse.format(sql2, reindent=True))


    # MySQL Query
    # 
    sql = '''SELECT `tweets`.`latitude` AS `latitude`,
                    `tweets`.`longitude` AS `longitude`
               FROM `tweets`
              WHERE ((ADDDATE(DATE_FORMAT(`tweets`.`created_at`, '%Y-%m-01 00:00:00'), INTERVAL 0 SECOND) = TIMESTAMP('2017-03-01 00:00:00'))
                AND (LOCATE('iphone', LOWER(`tweets`.`text`)) > 0))
              GROUP BY 1, 2'''
    
    print("======================================")
    print("    MySQL Original Query")
    print("--------------------------------------")
    print(sqlparse.format(sql, reindent=True))
    
    # test QueryRewritter.remove_adddate()
    #
    print("======================================")
    print("    After remove_adddate()")
    print("--------------------------------------")
    parsed = parse(sql)
    parsed = QueryRewritter.remove_adddate(parsed)
    sql1 = format(parsed)
    print(sqlparse.format(sql1, reindent=True))

    # test QueryRewritter.remove_timestamp()
    #
    print("======================================")
    print("    After remove_timestamp()")
    print("--------------------------------------")
    parsed = parse(sql1)
    parsed = QueryRewritter.remove_timestamp(parsed)
    sql2 = format(parsed)
    print(sqlparse.format(sql2, reindent=True))