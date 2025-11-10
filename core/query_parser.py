from core.ast.node import (
    Node, QueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode, 
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, LimitNode, OffsetNode, SubqueryNode, VarNode, VarSetNode, JoinNode
)
import mo_sql_parsing as mosql

class QueryParser:

    def parse(self, query: str) -> QueryNode:
        # [1] Call mo_sql_parser
        # str ->  Any (JSON)
        mosql_ast = mosql.parse(query)

        # [2] Our new code
        # Any (JSON) -> AST (QueryNode)
        self.aliases = {}

        select_clause = None
        from_clause = None
        where_clause = None
        group_by_clause = None
        having_clause = None
        order_by_clause = None
        limit_clause = None
        offset_clause = None
        
        if 'select' in mosql_ast:
            select_clause = self._parse_select(mosql_ast['select'])
        if 'from' in mosql_ast:
            from_clause = self._parse_from(mosql_ast['from'])
        if 'where' in mosql_ast:
            where_clause = self._parse_where(mosql_ast['where'])
        if 'groupby' in mosql_ast:
            group_by_clause = self._parse_group_by(mosql_ast['groupby'])
        if 'having' in mosql_ast:
            having_clause = self._parse_having(mosql_ast['having'])
        if 'orderby' in mosql_ast:
            order_by_clause = self._parse_order_by(mosql_ast['orderby'])
        if 'limit' in mosql_ast:
            limit_clause = LimitNode(mosql_ast['limit'])
        if 'offset' in mosql_ast:
            offset_clause = OffsetNode(mosql_ast['offset'])
            
        return QueryNode(
            _select=select_clause,
            _from=from_clause,
            _where=where_clause,
            _group_by=group_by_clause,
            _having=having_clause,
            _order_by=order_by_clause,
            _limit=limit_clause,
            _offset=offset_clause
        )
   
    def _parse_select(self, select_list: list) -> SelectNode:
        items = set()
        for item in select_list:
            if 'value' in item:
                expression = self._parse_expression(item['value'])
                # Handle alias
                if 'name' in item:
                    alias = item['name']
                    if isinstance(expression, ColumnNode):
                        expression.alias = alias
                    elif isinstance(expression, FunctionNode):
                        expression.alias = alias
                    # Add other types if needed
                    
                    self.aliases[alias] = expression
                
                items.add(expression)
                
        return SelectNode(items)
    
    def _parse_from(self, from_list: list) -> FromNode:
        sources = set()
        left_table = None
        
        for item in from_list:
            if 'value' in item:
                table_name = item['value']
                alias = item.get('name')
                table_node = TableNode(table_name, alias)
                # Track table alias
                if alias:
                    self.aliases[alias] = table_node
                
                if left_table is None:
                    # First table becomes the left table
                    left_table = table_node
                else:
                    # This shouldn't happen in normal SQL, but handle it
                    sources.add(table_node)
                    
            elif 'join' in item:
                if left_table is None:
                    raise ValueError("JOIN found without a left table")
                
                join_info = item['join']
                table_name = join_info['value']
                alias = join_info.get('name')
                right_table = TableNode(table_name, alias)
                # Track table alias
                if alias:
                    self.aliases[alias] = right_table
                
                on_condition = None
                if 'on' in item:
                    on_condition = self._parse_expression(item['on'])
                
                join_node = JoinNode(left_table, right_table, "INNER", on_condition)
                sources.add(join_node)
                # Reset for potential chained JOINs
                left_table = None
        
        # Add any remaining left table
        if left_table is not None:
            sources.add(left_table)
            
        return FromNode(sources)
    
    def _parse_where(self, where_dict: dict) -> WhereNode:
        predicates = set()
        predicates.add(self._parse_expression(where_dict))
        return WhereNode(predicates)
    
    def _parse_group_by(self, group_by_list: list) -> GroupByNode:
        items = []
        for item in group_by_list:
            if 'value' in item:
                expr = self._parse_expression(item['value'])
                # Resolve aliases
                expr = self._resolve_aliases(expr)
                items.append(expr)
        return GroupByNode(items)
    
    def _parse_having(self, having_dict: dict) -> HavingNode:
        predicates = set()
        expr = self._parse_expression(having_dict)
        # Check if this expression references an aliased function from SELECT
        expr = self._resolve_aliases(expr)
        
        predicates.add(expr)
        return HavingNode(predicates)
    
    def _parse_order_by(self, order_by_list: list) -> OrderByNode:
        items = []
        for item in order_by_list:
            if 'value' in item:
                value = item['value']
                # Check if this is an alias reference
                if value in self.aliases:
                    column = self.aliases[value]
                else:
                    # Parse normally for other cases
                    column = self._parse_expression(value)
                items.append(column)
        return OrderByNode(items)
    
    def _resolve_aliases(self, expr: Node) -> Node:
        if isinstance(expr, OperatorNode):
            # Recursively resolve aliases in operator operands
            left = self._resolve_aliases(expr.children[0])
            right = self._resolve_aliases(expr.children[1])
            return OperatorNode(left, expr.name, right)
        elif isinstance(expr, FunctionNode):
            # Check if this function matches an aliased function from SELECT
            if expr.alias is None:
                for alias, aliased_expr in self.aliases.items():
                    if isinstance(aliased_expr, FunctionNode):
                        if (expr.name == aliased_expr.name and 
                            len(expr.children) == len(aliased_expr.children) and
                            all(expr.children[i] == aliased_expr.children[i] 
                                for i in range(len(expr.children)))):
                            # This function matches an aliased one, use the alias
                            expr.alias = alias
                            break
            return expr
        elif isinstance(expr, ColumnNode):
            # Check if this column matches an aliased column from SELECT
            if expr.alias is None:
                for alias, aliased_expr in self.aliases.items():
                    if isinstance(aliased_expr, ColumnNode):
                        if (expr.name == aliased_expr.name and 
                            expr.parent_alias == aliased_expr.parent_alias):
                            # This column matches an aliased one, use the alias
                            expr.alias = alias
                            break
            return expr
        else:
            return expr
    
    def _parse_expression(self, expr) -> Node:
        if isinstance(expr, str):
            # Column reference
            if '.' in expr:
                parts = expr.split('.')
                if len(parts) == 2:
                    return ColumnNode(parts[1], _parent_alias=parts[0])
                else:
                    return ColumnNode(expr)
            else:
                return ColumnNode(expr)
        elif isinstance(expr, (int, float, bool)):
            # Literal value
            return LiteralNode(expr)
        elif isinstance(expr, dict):
            # Complex expression
            if 'count' in expr:
                # COUNT function
                if expr['count'] == '*':
                    return FunctionNode("COUNT", [ColumnNode("*")])
                else:
                    return FunctionNode("COUNT", [self._parse_expression(expr['count'])])
            elif 'eq' in expr:
                # Equality operator
                left = self._parse_expression(expr['eq'][0])
                right = self._parse_expression(expr['eq'][1])
                return OperatorNode(left, "=", right)
            elif 'gt' in expr:
                # Greater than operator
                left = self._parse_expression(expr['gt'][0])
                right = self._parse_expression(expr['gt'][1])
                return OperatorNode(left, ">", right)
            elif 'lt' in expr:
                # Less than operator
                left = self._parse_expression(expr['lt'][0])
                right = self._parse_expression(expr['lt'][1])
                return OperatorNode(left, "<", right)
            elif 'and' in expr:
                # AND operator
                conditions = expr['and']
                if len(conditions) == 2:
                    left = self._parse_expression(conditions[0])
                    right = self._parse_expression(conditions[1])
                    return OperatorNode(left, "AND", right)
                else:
                    # Handle multiple AND conditions
                    result = self._parse_expression(conditions[0])
                    for condition in conditions[1:]:
                        result = OperatorNode(result, "AND", self._parse_expression(condition))
                    return result
            else:
                # Unknown expression type
                return LiteralNode(str(expr))
        else:
            return LiteralNode(str(expr))


    def format(self, query: QueryNode) -> str:
        # Implement formatting logic to convert AST back to SQL string
        pass

        # [1] Our new code
        # AST (QueryNode) ->  JSON

        # [2] Call mo_sql_format
        # Any (JSON) -> str