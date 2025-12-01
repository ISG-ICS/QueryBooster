import mo_sql_parsing as mosql
from core.ast.node import QueryNode
from core.ast.node import (
    QueryNode, SelectNode, FromNode, WhereNode, TableNode, ColumnNode, 
    LiteralNode, OperatorNode, FunctionNode, GroupByNode, HavingNode,
    OrderByNode, LimitNode, OffsetNode, SubqueryNode, VarNode, VarSetNode
)
from core.ast.enums import NodeType, JoinType, SortOrder
from core.ast.node import Node

class QueryFormatter:
    def format(self, query: QueryNode) -> str:
        # [1] AST (QueryNode) ->  JSON
        json_query = ast_to_json(query)

        # [2] Any (JSON) -> str
        sql = mosql.format(json_query)
        
        return sql

def ast_to_json(node: QueryNode) -> dict:
    """Convert QueryNode AST to JSON dictionary for mosql"""
    result = {}
    
    # process each clause in the query
    for child in node.children:
        if child.type == NodeType.SELECT:
            result['select'] = format_select(child)
        elif child.type == NodeType.FROM:
            result['from'] = format_from(child)
        elif child.type == NodeType.WHERE:
            result['where'] = format_where(child)
        elif child.type == NodeType.GROUP_BY:
            result['groupby'] = format_group_by(child)
        elif child.type == NodeType.HAVING:
            result['having'] = format_having(child)
        elif child.type == NodeType.ORDER_BY:
            result['orderby'] = format_order_by(child)
        elif child.type == NodeType.LIMIT:
            result['limit'] = child.limit
        elif child.type == NodeType.OFFSET:
            result['offset'] = child.offset
    
    return result


def format_select(select_node: SelectNode) -> list:
    """Format SELECT clause"""
    items = []
    
    for child in select_node.children:
        if child.type == NodeType.COLUMN:
            if child.alias:
                items.append({'name': child.alias, 'value': format_expression(child)})
            else:
                items.append({'value': format_expression(child)})
        elif child.type == NodeType.FUNCTION:
            func_expr = format_expression(child)
            if hasattr(child, 'alias') and child.alias:
                items.append({'name': child.alias, 'value': func_expr})
            else:
                items.append({'value': func_expr})
        else:
            items.append({'value': format_expression(child)})
    
    return items


def format_from(from_node: FromNode) -> list:
    """Format FROM clause"""
    sources = []
    tables = list(from_node.children)
    
    if tables:
        main_table = tables[0]
        sources.append(format_table(main_table))
        
        # additional tables become JOINs
        # TODO: add other join type support beyond implicit
        for table in tables[1:]:
            join_item = {
                'join': format_table(table),
                'on': infer_join_condition(tables[0], table)
            }
            sources.append(join_item)
    
    return sources


def format_table(table_node: TableNode) -> dict:
    """Format a table reference"""
    result = {'value': table_node.name}
    if table_node.alias:
        result['name'] = table_node.alias
    return result


def infer_join_condition(table1: TableNode, table2: TableNode) -> dict:
    """Infer JOIN condition between tables"""
    # assume foreign key pattern like table1.table2_id = table2.id
    alias1 = table1.alias or table1.name
    alias2 = table2.alias or table2.name
    
    return {'eq': [f'{alias1}.{table2.name[:-1]}_id', f'{alias2}.id']}


def format_where(where_node: WhereNode) -> dict:
    """Format WHERE clause"""
    predicates = list(where_node.children)
    if len(predicates) == 1:
        return format_expression(predicates[0])
    else:
        return {'and': [format_expression(p) for p in predicates]}


def format_group_by(group_by_node: GroupByNode) -> list:
    """Format GROUP BY clause"""
    return [{'value': format_expression(child)} 
            for child in group_by_node.children]


def format_having(having_node: HavingNode) -> dict:
    """Format HAVING clause"""
    predicates = list(having_node.children)
    if len(predicates) == 1:
        return format_expression(predicates[0])
    else:
        return {'and': [format_expression(p) for p in predicates]}


def format_order_by(order_by_node: OrderByNode) -> list:
    """Format ORDER BY clause items."""
    items = []
    
    # get all items and their sort orders
    sort_orders = []
    for child in order_by_node.children:
        if child.type == NodeType.ORDER_BY_ITEM:
            column = list(child.children)[0]
            item = {'value': format_expression(column)}
            sort_order = child.sort
            sort_orders.append(sort_order)
        else:
            item = {'value': format_expression(child)}
            sort_order = SortOrder.ASC
            sort_orders.append(sort_order)
        
        items.append((item, sort_order))
    
    # check if all sort orders are the same
    all_same = len(set(sort_orders)) == 1
    common_sort = sort_orders[0] if all_same else None
    
    # reformat into single sort operator if all items have same sort operator
    # ex. ORDER BY dept_name DESC, emp_count DESC -> ORDER BY dept_name, emp_count DESC
    result = []
    for i, (item, sort_order) in enumerate(items):
        if all_same and i == len(items) - 1:
            if common_sort != SortOrder.ASC:
                item['sort'] = common_sort.value.lower()
        elif not all_same:
            if sort_order != SortOrder.ASC:
                item['sort'] = sort_order.value.lower()
        
        result.append(item)
    
    return result


def format_expression(node: Node):
    """Format an expression node"""
    if node.type == NodeType.COLUMN:
        if node.parent_alias:
            return f"{node.parent_alias}.{node.name}"
        return node.name
    
    elif node.type == NodeType.LITERAL:
        return node.value
    
    elif node.type == NodeType.FUNCTION:
        # format: {'function_name': args}
        func_name = node.name.lower()
        args = [format_expression(arg) for arg in node.children]
        return {func_name: args[0] if len(args) == 1 else args}
    
    elif node.type == NodeType.OPERATOR:
        # format: {'operator': [left, right]}
        op_map = {
            '>': 'gt',
            '<': 'lt',
            '>=': 'gte',
            '<=': 'lte',
            '=': 'eq',
            '!=': 'ne',
            'AND': 'and',
            'OR': 'or',
        }
        
        op_name = op_map.get(node.name.upper(), node.name.lower())
        children = list(node.children)
        
        left = format_expression(children[0])
        
        if len(children) == 2:
            right = format_expression(children[1])
            return {op_name: [left, right]}
        else:
            # unary operator
            return {op_name: left}
    
    elif node.type == NodeType.TABLE:
        return format_table(node)
    
    else:
        raise ValueError(f"Unsupported node type in expression: {node.type}")