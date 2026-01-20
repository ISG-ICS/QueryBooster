from core.ast.node import (
    Node, QueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode, 
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, OrderByItemNode, LimitNode, OffsetNode, SubqueryNode, VarNode, VarSetNode, JoinNode
)
# TODO: implement SubqueryNode, VarNode, VarSetNode
from core.ast.enums import JoinType, SortOrder
import mo_sql_parsing as mosql
import json

class QueryParser:
    @staticmethod
    def normalize_to_list(value):
        """Normalize mo_sql_parsing output to a list format.
        
        mo_sql_parsing returns:
        - list when multiple items
        - dict when single item with structure
        - str when single simple value
        
        This normalizes all cases to a list.
        """
        if value is None:
            return []
        elif isinstance(value, list):
            return value
        elif isinstance(value, (dict, str)):
            return [value]
        else:
            raise TypeError(
                f"normalize_to_list: Unexpected type {type(value).__name__} for value {value!r}. "
                "Expected None, list, dict, or str."
            )

    def parse(self, query: str) -> QueryNode:
        # [1] Call mo_sql_parser
        # str ->  Any (JSON)
        mosql_ast = mosql.parse(query)

        # [2] Our new code
        # Any (JSON) -> AST (QueryNode)
        # Aliases dictionary
        aliases = {}

        select_clause = None
        from_clause = None
        where_clause = None
        group_by_clause = None
        having_clause = None
        order_by_clause = None
        limit_clause = None
        offset_clause = None
        
        if 'select' in mosql_ast:
            select_clause = self.parse_select(self.normalize_to_list(mosql_ast['select']), aliases)
        if 'from' in mosql_ast:
            from_clause = self.parse_from(self.normalize_to_list(mosql_ast['from']), aliases)
        if 'where' in mosql_ast:
            where_clause = self.parse_where(mosql_ast['where'], aliases)
        if 'groupby' in mosql_ast:
            group_by_clause = self.parse_group_by(self.normalize_to_list(mosql_ast['groupby']), aliases)
        if 'having' in mosql_ast:
            having_clause = self.parse_having(mosql_ast['having'], aliases)
        if 'orderby' in mosql_ast:
            order_by_clause = self.parse_order_by(self.normalize_to_list(mosql_ast['orderby']), aliases)
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
   
    def parse_select(self, select_list: list, aliases: dict) -> SelectNode:
        items = []
        for item in select_list:
            if isinstance(item, dict) and 'value' in item:
                expression = self.parse_expression(item['value'])
                # Handle alias - set for any node that has alias attribute
                if 'name' in item:
                    alias = item['name']
                    if hasattr(expression, 'alias'):
                        expression.alias = alias
                    aliases[alias] = expression
                
                items.append(expression)
            else:
                # Handle direct expression (string, int, etc.)
                expression = self.parse_expression(item)
                items.append(expression)
                
        return SelectNode(items)
    
    def parse_from(self, from_list: list, aliases: dict) -> FromNode:
        sources = []
        left_source = None  # Can be a table or the result of a previous join
        
        for item in from_list:
            # Check for JOIN first (before checking for 'value')
            if isinstance(item, dict):
                # Look for any join key
                join_key = next((k for k in item.keys() if 'join' in k.lower()), None)
                
                if join_key:
                    # This is a JOIN
                    if left_source is None:
                        raise ValueError(f"JOIN found without a left table. join_key={join_key}, item={item}")
                    
                    join_info = item[join_key]
                    # Handle both string and dict join_info
                    if isinstance(join_info, str):
                        table_name = join_info
                        alias = None
                    else:
                        table_name = join_info['value'] if isinstance(join_info, dict) else join_info
                        alias = join_info.get('name') if isinstance(join_info, dict) else None
                    
                    right_table = TableNode(table_name, alias)
                    # Track table alias
                    if alias:
                        aliases[alias] = right_table
                    
                    on_condition = None
                    if 'on' in item:
                        on_condition = self.parse_expression(item['on'])
                    
                    # Create join node - left_source might be a table or a previous join
                    join_type = self.parse_join_type(join_key)
                    join_node = JoinNode(left_source, right_table, join_type, on_condition)
                    # The result of this JOIN becomes the new left source for potential next JOIN
                    left_source = join_node
                elif 'value' in item:
                    # This is a table reference
                    table_name = item['value']
                    alias = item.get('name')
                    table_node = TableNode(table_name, alias)
                    # Track table alias
                    if alias:
                        aliases[alias] = table_node
                    
                    if left_source is None:
                        # First table becomes the left source
                        left_source = table_node
                    else:
                        # Multiple tables without explicit JOIN (cross join)
                        sources.append(table_node)
            elif isinstance(item, str):
                # Simple string table name
                table_node = TableNode(item)
                if left_source is None:
                    left_source = table_node
                else:
                    sources.append(table_node)
        
        # Add the final left source (which might be a single table or chain of joins)
        if left_source is not None:
            sources.append(left_source)
            
        return FromNode(sources)
    
    def parse_where(self, where_dict: dict, aliases: dict) -> WhereNode:
        predicates = []
        predicates.append(self.parse_expression(where_dict))
        return WhereNode(predicates)
    
    def parse_group_by(self, group_by_list: list, aliases: dict) -> GroupByNode:
        items = []
        for item in group_by_list:
            if isinstance(item, dict) and 'value' in item:
                expr = self.parse_expression(item['value'])
                # Resolve aliases
                expr = self.resolve_aliases(expr, aliases)
                items.append(expr)
            else:
                # Handle direct expression (string, int, etc.)
                expr = self.parse_expression(item)
                expr = self.resolve_aliases(expr, aliases)
                items.append(expr)

        return GroupByNode(items)
    
    def parse_having(self, having_dict: dict, aliases: dict) -> HavingNode:
        predicates = []
        expr = self.parse_expression(having_dict)
        # Check if this expression references an aliased function from SELECT
        expr = self.resolve_aliases(expr, aliases)
        
        predicates.append(expr)

        return HavingNode(predicates)
    
    def parse_order_by(self, order_by_list: list, aliases: dict) -> OrderByNode:
        items = []
        for item in order_by_list:
            if isinstance(item, dict) and 'value' in item:
                value = item['value']
                # Check if this is an alias reference
                if isinstance(value, str) and value in aliases:
                    column = aliases[value]
                else:
                    # Parse normally for other cases
                    column = self.parse_expression(value)
                
                # Get sort order (default is ASC)
                sort_order = SortOrder.ASC
                if 'sort' in item:
                    sort_str = item['sort'].upper()
                    if sort_str == 'DESC':
                        sort_order = SortOrder.DESC
                
                # Wrap in OrderByItemNode
                order_by_item = OrderByItemNode(column, sort_order)
                items.append(order_by_item)
            else:
                # Handle direct expression (string, int, etc.)
                column = self.parse_expression(item)
                order_by_item = OrderByItemNode(column, SortOrder.ASC)
                items.append(order_by_item)

        return OrderByNode(items)
    
    def resolve_aliases(self, expr: Node, aliases: dict) -> Node:
        if isinstance(expr, OperatorNode):
            # Recursively resolve aliases in operator operands
            if len(expr.children) >= 2:
                left = self.resolve_aliases(expr.children[0], aliases)
                right = self.resolve_aliases(expr.children[1], aliases)
                return OperatorNode(left, expr.name, right)
            elif len(expr.children) == 1:
                # Unary operator (e.g., NOT)
                operand = self.resolve_aliases(expr.children[0], aliases)
                return OperatorNode(operand, expr.name)
            else:
                raise ValueError(f"OperatorNode has {len(expr.children)} children, expected 2 for binary operators or 1 for unary operators")
        elif isinstance(expr, FunctionNode):
            # Check if this function matches an aliased function from SELECT
            if expr.alias is None:
                for alias, aliased_expr in aliases.items():
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
                for alias, aliased_expr in aliases.items():
                    if isinstance(aliased_expr, ColumnNode):
                        if (expr.name == aliased_expr.name and 
                            expr.parent_alias == aliased_expr.parent_alias):
                            # This column matches an aliased one, use the alias
                            expr.alias = alias
                            break
            return expr
        else:
            return expr
    
    def parse_expression(self, expr) -> Node:
        if isinstance(expr, str):
            # Column reference
            if '.' in expr:
                parts = expr.split('.', 1)
                return ColumnNode(parts[1], _parent_alias=parts[0])
            return ColumnNode(expr)
        
        if isinstance(expr, (int, float, bool)):
            return LiteralNode(expr)
        
        if isinstance(expr, list):
            # List literals (for IN clauses)
            parsed = [self.parse_expression(item) for item in expr]
            return parsed
        
        if isinstance(expr, dict):
            # Special cases first
            if 'all_columns' in expr:
                return ColumnNode('*')
            if 'literal' in expr:
                return LiteralNode(expr['literal'])
            
            # Skip metadata keys
            skip_keys = {'value', 'name', 'on', 'sort'}
            
            # Find the operator/function key
            for key in expr.keys():
                if key in skip_keys:
                    continue
                    
                value = expr[key]
                op_name = self.normalize_operator_name(key)
                
                # Pattern 1: Binary/N-ary operator with list of operands
                if isinstance(value, list):
                    if len(value) == 0:
                        return LiteralNode(None)
                    if len(value) == 1:
                        return self.parse_expression(value[0])
                    
                    # Parse all operands
                    operands = [self.parse_expression(v) for v in value]
                    
                    # Chain multiple operands with the same operator
                    result = operands[0]
                    for operand in operands[1:]:
                        result = OperatorNode(result, op_name, operand)
                    return result
                
                # Pattern 2: Unary operator
                if key == 'not':
                    return OperatorNode(self.parse_expression(value), 'NOT')
                
                # Pattern 3: Function call
                # Special case: COUNT(*), SUM(*), etc.
                if value == '*':
                    return FunctionNode(op_name, _args=[ColumnNode('*')])
                
                # Regular function
                args = [self.parse_expression(value)]
                return FunctionNode(op_name, _args=args)
            
            # No valid key found
            return LiteralNode(json.dumps(expr, sort_keys=True))
        
        # Other types
        return LiteralNode(expr)
    
    @staticmethod
    def normalize_operator_name(key: str) -> str:
        """Convert mo_sql_parsing operator keys to SQL operator names."""
        mapping = {
            'eq': '=', 'neq': '!=', 'ne': '!=',
            'gt': '>', 'gte': '>=', 
            'lt': '<', 'lte': '<=',
            'and': 'AND', 'or': 'OR',
        }
        return mapping.get(key.lower(), key.upper())
    
    @staticmethod
    def parse_join_type(join_key: str) -> JoinType:
        """Extract JoinType from mo_sql_parsing join key."""
        key_lower = join_key.lower().replace(' ', '_')
        
        if 'inner' in key_lower:
            return JoinType.INNER
        elif 'left' in key_lower:
            return JoinType.LEFT
        elif 'right' in key_lower:
            return JoinType.RIGHT
        elif 'full' in key_lower:
            return JoinType.FULL
        elif 'cross' in key_lower:
            return JoinType.CROSS
        
        return JoinType.INNER  # By default