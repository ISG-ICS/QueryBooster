
class QueryParser:

    def parse(self, query: str) -> QueryNode:
        # Implement parsing logic using self.rules
        pass

        # [1] Call mo_sql_parser
        # str ->  Any (JSON)

        # [2] Our new code
        # Any (JSON) -> AST (QueryNode)

    def format(self, query: QueryNode) -> str:
        # Implement formatting logic to convert AST back to SQL string
        pass

        # [1] Our new code
        # AST (QueryNode) ->  JSON

        # [2] Call mo_sql_format
        # Any (JSON) -> str