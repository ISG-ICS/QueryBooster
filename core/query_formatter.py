import re
import json
import mo_sql_parsing as mosql
from core.ast.node import (
    QueryNode,
    CompoundQueryNode,
    SelectNode,
    FromNode,
    WhereNode,
    TableNode,
    GroupByNode,
    HavingNode,
    OrderByNode,
    JoinNode,
    SubqueryNode,
)
from core.ast.enums import NodeType, JoinType, SortOrder
from core.ast.node import Node

class QueryFormatter:
    def format(self, query: Node) -> str:
        # [1] AST -> JSON
        json_query = ast_to_json(query)

        # [2] Any (JSON) -> str
        sql = mosql.format(json_query)

        # Fixes edge case where formatting json with INTERVAL '0' SECOND into SQL adds quotes
        sql = re.sub(r"INTERVAL '(\d+)'", r'INTERVAL \1', sql)  
              
        return sql

def _collect_union_branches(node: CompoundQueryNode, is_all: bool) -> list:
    """Flatten a left-chain of same-type CompoundQueryNodes into a list.

    mo_sql_parsing uses flat lists for chains of the same operator
    (e.g. A UNION B UNION C to {'union': [A, B, C]}).  Nesting is only
    used at type boundaries (e.g. (A UNION ALL B) UNION C).  This helper
    mirrors that convention so round-trips produce identical JSON.
    """
    result = []
    if isinstance(node.left, CompoundQueryNode) and node.left.is_all == is_all:
        result.extend(_collect_union_branches(node.left, is_all))
    else:
        result.append(node.left)
    if isinstance(node.right, CompoundQueryNode) and node.right.is_all == is_all:
        result.extend(_collect_union_branches(node.right, is_all))
    else:
        result.append(node.right)
    return result


def compound_to_mosql_json(node: CompoundQueryNode) -> dict:
    """Convert a CompoundQueryNode binary tree to mo_sql_parsing union/union_all JSON."""
    key = 'union_all' if node.is_all else 'union'
    branches = _collect_union_branches(node, node.is_all)
    return {key: [ast_to_json(b) for b in branches]}


def ast_to_json(node: Node) -> dict:
    """Convert AST to JSON dictionary for mosql."""
    if isinstance(node, CompoundQueryNode):
        return compound_to_mosql_json(node)
    if not isinstance(node, QueryNode):
        raise TypeError(
            f"ast_to_json: expected QueryNode or CompoundQueryNode, got {type(node).__name__}"
        )
    result = {}
    
    # process each clause in the query
    for child in node.children:
        if child.type == NodeType.SELECT:
            select_result = format_select(child)
            result.update(select_result)
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


def format_select(select_node: SelectNode) -> dict:
    """Format SELECT clause, returning dict with select/select_distinct and optional distinct_on keys"""
    result = {}
    
    children = list(select_node.children)
    if select_node.distinct_on is not None:
        children = children[:-1]
        distinct_on_items = [format_expression(item) for item in select_node.distinct_on.children]
        if len(distinct_on_items) == 1:
            result['distinct_on'] = {'value': distinct_on_items[0]}
        else:
            result['distinct_on'] = [{'value': item} for item in distinct_on_items]
    
    items = []
    for child in children:
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
    
    select_key = 'select_distinct' if select_node.distinct else 'select'
    result[select_key] = items
    return result


def format_from(from_node: FromNode):
    """Format the FROM clause for mo_sql_parsing.

    mo_sql_parsing quirk: a bare (unaliased) UNION/UNION ALL in FROM is
    represented as a plain dict at the FROM key, NOT as a one-element list
    wrapping a {'value': ...} dict.  For example:

        SELECT * FROM (SELECT 1 UNION SELECT 2)
        to {"select": ..., "from": {"union": [...]}}   ← dict, not list

    An aliased variant uses the normal list-of-sources form:
        SELECT * FROM (SELECT 1 UNION SELECT 2) t
        to {"select": ..., "from": [{"value": {"union": [...]}, "name": "t"}]}

    Everything else (tables, aliased subqueries, JOINs) returns a list.
    """
    children = list(from_node.children)

    # Special case: single unaliased UNION subquery must be a bare dict
    if (
        len(children) == 1
        and isinstance(children[0], SubqueryNode)
        and children[0].alias is None
    ):
        inner = list(children[0].children)[0]
        if isinstance(inner, CompoundQueryNode):
            return compound_to_mosql_json(inner)

    sources = []
    if not children:
        return sources
    
    # Process JoinNode structure
    for child in children:
        if child.type == NodeType.JOIN:
            join_sources = format_join(child)
            # format_join returns a list, extend sources with it
            if isinstance(join_sources, list):
                sources.extend(join_sources)
            else:
                sources.append(join_sources)
        else:
            sources.append(format_source(child))
    
    return sources


def format_join(join_node: JoinNode) -> list:
    """Format a JOIN node"""
    children = list(join_node.children)
    
    if len(children) < 2:
        raise ValueError("JoinNode must have at least 2 children (left and right tables)")
    
    left_node = children[0]
    right_node = children[1]
    join_condition = children[2] if len(children) > 2 else None
    
    result = []
    
    # Format left side (could be a table or nested join)
    if left_node.type == NodeType.JOIN:
        # Nested join - recursively format
        result.extend(format_join(left_node))
    else:
        # Simple table - this becomes the FROM table
        result.append(format_source(left_node))
    
    # Format the join itself
    join_dict = {}
    
    # Map join types to mosql format
    join_type_map = {
        JoinType.JOIN: 'join',
        JoinType.INNER: 'inner join',
        JoinType.LEFT: 'left join',
        JoinType.RIGHT: 'right join',
        JoinType.FULL: 'full join',
        JoinType.CROSS: 'cross join',
    }
    
    join_key = join_type_map.get(join_node.join_type, 'join')
    join_dict[join_key] = format_source(right_node)
    
    # Add join condition if it exists
    if join_condition:
        join_dict['on'] = format_expression(join_condition)
    
    result.append(join_dict)
    
    return result


def format_source(node: Node) -> dict:
    """Format a table or subquery reference for use in FROM/JOIN"""
    if node.type == NodeType.TABLE:
        return format_table(node)
    elif node.type == NodeType.SUBQUERY:
        subquery_child = list(node.children)[0]
        result = {'value': ast_to_json(subquery_child)}
        if node.alias:
            result['name'] = node.alias
        return result
    raise ValueError(f"Unsupported source type: {node.type}")


def format_table(table_node: TableNode) -> dict:
    """Format a table reference"""
    result = {'value': table_node.name}
    if table_node.alias:
        result['name'] = table_node.alias
    return result


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
    result = []
    
    for child in order_by_node.children:
        if child.type == NodeType.ORDER_BY_ITEM:
            column = list(child.children)[0]
            
            if hasattr(column, 'alias') and column.alias:
                item = {'value': column.alias}
            else:
                item = {'value': format_expression(column)}
            
            sort_order = child.sort
        else:
            if hasattr(child, 'alias') and child.alias:
                item = {'value': child.alias}
            else:
                item = {'value': format_expression(child)}
            
            sort_order = None
        
        if sort_order is not None:
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
        if node.value is None:
            return {'null': {}}
        if isinstance(node.value, str):
            return {'literal': node.value}
        return node.value
    
    elif node.type == NodeType.FUNCTION:
        # format: {'function_name': args}
        func_name = node.name.lower()
        children = list(node.children)
        
        if len(children) == 1 and children[0].type == NodeType.FUNCTION and children[0].name.upper() == 'DISTINCT':
            distinct_args = [format_expression(a) for a in children[0].children]
            return {'distinct': True, func_name: distinct_args[0] if len(distinct_args) == 1 else distinct_args}
        
        if func_name == 'extract':
            keyword = children[0].value.lower() if hasattr(children[0], 'value') else format_expression(children[0])
            from_expr = format_expression(children[1])
            return {'extract': [keyword, from_expr]}
        
        args = [format_expression(arg) for arg in children]
        return {func_name: args[0] if len(args) == 1 else args}
    
    elif node.type == NodeType.SUBQUERY:
        subquery_node = list(node.children)[0]
        return ast_to_json(subquery_node)
    
    elif node.type == NodeType.OPERATOR:
        # format: {'operator': [left, right]} or {'operator': operand} for unary ops
        def _flatten_logical(n: Node, op_upper: str) -> list:
            if (
                isinstance(n, Node)
                and n.type == NodeType.OPERATOR
                and getattr(n, "name", "").upper() == op_upper
                and len(list(n.children)) == 2
            ):
                ch = list(n.children)
                return _flatten_logical(ch[0], op_upper) + _flatten_logical(ch[1], op_upper)
            return [n]

        op_map = {
            '>': 'gt',
            '<': 'lt',
            '>=': 'gte',
            '<=': 'lte',
            '=': 'eq',
            '!=': 'neq',
            'AND': 'and',
            'OR': 'or',
            'IN': 'in',
            'LIKE': 'like',
            '+': 'add',
            '-': 'sub',
            '*': 'mul',
            '/': 'div',
        }
        
        children = list(node.children)

        if len(children) == 1:
            operand = format_expression(children[0])
            # Use mo_sql_parsing's unary-operator keys to avoid ambiguity with binary '-'
            # and to keep the JSON shape consistent with what `parse()` produces.
            unary_op_map = {
                'NEG': 'neg',
                '-': 'neg',
                '+': '+',
                'NOT': 'not',
            }
            op_name = unary_op_map.get(node.name.upper(), node.name.lower())
            return {op_name: operand}
        
        if node.name.upper() == 'IS' and len(children) == 2:
            right = children[1]
            if right.type == NodeType.LITERAL and right.value is None:
                return {'missing': format_expression(children[0])}
        
        op_name = op_map.get(node.name, op_map.get(node.name.upper(), node.name.lower()))
        
        if op_name == 'sub' and len(children) == 2 and children[0].type == NodeType.LITERAL and children[0].value == 0:
            return {'neg': format_expression(children[1])}

        # Canonicalize commutative logical operators so formatted SQL is stable
        # across equivalent ASTs (helps tests compare strings).
        if op_name in ("and", "or"):
            flat = _flatten_logical(node, node.name.upper())
            rendered = [format_expression(c) for c in flat]
            rendered.sort(key=lambda x: json.dumps(x, sort_keys=True, default=str))
            return {op_name: rendered}
        
        left = format_expression(children[0])
        
        if len(children) == 2:
            right = format_expression(children[1])
            return {op_name: [left, right]}

        raise ValueError(
            f"Unsupported operator arity for {node.name!r}: expected 1 or 2 operands, got {len(children)}"
        )
    
    elif node.type == NodeType.TABLE:
        return format_table(node)
    
    elif node.type == NodeType.DATA_TYPE:
        return {node.name.lower(): {}}
    
    elif node.type == NodeType.LIST:
        rendered = [format_expression(item) for item in node.children]
        # Canonicalize IN-list ordering when possible.
        try:
            rendered.sort(key=lambda x: json.dumps(x, sort_keys=True, default=str))
        except Exception:
            pass
        return rendered
    
    elif node.type == NodeType.CASE:
        case_list = []
        for wt in node.whens:
            case_list.append({'when': format_expression(wt.when), 'then': format_expression(wt.then)})
        if node.else_val is not None:
            case_list.append(format_expression(node.else_val))
        return {'case': case_list}
    
    elif node.type == NodeType.INTERVAL:
        value = format_expression(node.value) if isinstance(node.value, Node) else node.value
        unit = node.unit.name.lower()
        return {'interval': [value, unit]}
    
    else:
        raise ValueError(f"Unsupported node type in expression: {node.type}")