from dataclasses import dataclass
from enum import Enum
import json
import mo_sql_parsing as mosql
import re
from typing import Any, Dict, List, Optional, Tuple

from core.ast.enums import NodeType
from core.ast.node import (
    CaseNode,
    ColumnNode,
    FromNode,
    FunctionNode,
    GroupByNode,
    HavingNode,
    JoinNode,
    LimitNode,
    ListNode,
    Node,
    OffsetNode,
    OperatorNode,
    OrderByItemNode,
    OrderByNode,
    QueryNode,
    SelectNode,
    SubqueryNode,
    TableNode,
    UnaryOperatorNode,
    VarNode,
    VarSetNode,
    WhenThenNode,
    WhereNode,
    IntervalNode,
)
from core.query_parser import QueryParser


# Variable Type
# 
class VarType(Enum):
    Var = 1
    VarList = 2

# Variable Types' infro
VarTypesInfo = {
    VarType.Var: {
        'markerStart': '<',
        'markerEnd': '>',
        'internalBase': 'V',
        'externalBase': 'x',
    },
    VarType.VarList: {
        'markerStart': '<<',
        'markerEnd': '>>',
        'internalBase': 'VL',
        'externalBase': 'y'
    }
}

# Scope of pattern/rewrite describes
class Scope(Enum):
    SELECT = 1
    FROM = 2
    WHERE = 3
    CONDITION = 4

# Partial SQL statement for extension
ScopeExtension = {
    Scope.CONDITION: 'SELECT * FROM t WHERE ',
    Scope.WHERE: 'SELECT * FROM t ',
    Scope.FROM: 'SELECT * ',
    Scope.SELECT: ''
}


@dataclass(frozen=True)
class RuleParseResult:
    """Structured result from RuleParser.parse_v2 (project AST instead of mo-sql JSON)."""

    pattern_ast: Node
    rewrite_ast: Node
    mapping: Dict[str, str]
    pattern_scope: Scope
    rewrite_scope: Scope


class RuleParser:
    
    # parse a rule (pattern, rewrite) into a SQL AST json str
    # 
    @staticmethod
    def parse(pattern: str, rewrite: str) -> Tuple[str, str, str]:
        # 1. Replace user-faced variables and variable lists 
        #    with internal representations 
        # 
        pattern, rewrite, mapping = RuleParser.replaceVars(pattern, rewrite)

        # 2. Extend partial SQL statement to full SQL statement
        #    for the sake of sql parser
        # 
        pattern, patternScope = RuleParser.extendToFullSQL(pattern)
        rewrite, rewriteScope = RuleParser.extendToFullSQL(rewrite)

        # 3. Parse extended full SQL statement into AST json
        patternASTJson = mosql.parse(pattern)
        rewriteASTJson = mosql.parse(rewrite)

        # 4. Extract subtree from AST json based on scope
        patternASTJson = RuleParser.extractASTSubtree(patternASTJson, patternScope)
        rewriteASTJson = RuleParser.extractASTSubtree(rewriteASTJson, rewriteScope)

        # 5. Return the AST subtree as json string
        return json.dumps(patternASTJson), json.dumps(rewriteASTJson), json.dumps(mapping)

    @staticmethod
    def parse_v2(pattern: str, rewrite: str) -> RuleParseResult:
        """Parse a rule into project AST nodes with external rule variable names.

        Uses the same extension and placeholder replacement as parse(), then
        QueryParser plus substitution of internal tokens (V001 / VL001) to
        VarNode / VarSetNode or decoded ColumnNode / TableNode names.
        """
        pattern_sql, rewrite_sql, mapping = RuleParser.replaceVars(pattern, rewrite)
        pattern_full, pattern_scope = RuleParser.extendToFullSQL(pattern_sql)
        rewrite_full, rewrite_scope = RuleParser.extendToFullSQL(rewrite_sql)
        qparser = QueryParser()
        pattern_query = qparser.parse(pattern_full)
        rewrite_query = qparser.parse(rewrite_full)
        internal_to_external = {internal: external for external, internal in mapping.items()}
        pattern_ast = RuleParser._extract_rule_ast(pattern_query, pattern_scope, internal_to_external)
        rewrite_ast = RuleParser._extract_rule_ast(rewrite_query, rewrite_scope, internal_to_external)
        return RuleParseResult(
            pattern_ast=pattern_ast,
            rewrite_ast=rewrite_ast,
            mapping=mapping,
            pattern_scope=pattern_scope,
            rewrite_scope=rewrite_scope,
        )

    @staticmethod
    def _get_clause(query: QueryNode, clause_type: NodeType) -> Optional[Node]:
        for child in query.children:
            if child.type == clause_type:
                return child
        return None

    @staticmethod
    def _extract_rule_ast(
        query: QueryNode, scope: Scope, internal_to_external: Dict[str, str]
    ) -> Node:
        sel = RuleParser._get_clause(query, NodeType.SELECT)
        frm = RuleParser._get_clause(query, NodeType.FROM)
        wh = RuleParser._get_clause(query, NodeType.WHERE)
        gb = RuleParser._get_clause(query, NodeType.GROUP_BY)
        hav = RuleParser._get_clause(query, NodeType.HAVING)
        ob = RuleParser._get_clause(query, NodeType.ORDER_BY)
        lim = RuleParser._get_clause(query, NodeType.LIMIT)
        off = RuleParser._get_clause(query, NodeType.OFFSET)

        if scope == Scope.CONDITION:
            if wh is None or not list(wh.children):
                raise ValueError("CONDITION scope requires a WHERE predicate")
            pred = list(wh.children)[0]
            return RuleParser._as_rule_ast(pred, internal_to_external)

        if scope == Scope.WHERE:
            return RuleParser._as_rule_ast(
                QueryNode(
                    _select=None,
                    _from=None,
                    _where=RuleParser._as_rule_ast(wh, internal_to_external) if wh else None,
                    _group_by=RuleParser._as_rule_ast(gb, internal_to_external) if gb else None,
                    _having=RuleParser._as_rule_ast(hav, internal_to_external) if hav else None,
                    _order_by=RuleParser._as_rule_ast(ob, internal_to_external) if ob else None,
                    _limit=RuleParser._as_rule_ast(lim, internal_to_external) if lim else None,
                    _offset=RuleParser._as_rule_ast(off, internal_to_external) if off else None,
                ),
                internal_to_external,
            )

        if scope == Scope.FROM:
            return RuleParser._as_rule_ast(
                QueryNode(
                    _select=None,
                    _from=RuleParser._as_rule_ast(frm, internal_to_external) if frm else None,
                    _where=RuleParser._as_rule_ast(wh, internal_to_external) if wh else None,
                    _group_by=RuleParser._as_rule_ast(gb, internal_to_external) if gb else None,
                    _having=RuleParser._as_rule_ast(hav, internal_to_external) if hav else None,
                    _order_by=RuleParser._as_rule_ast(ob, internal_to_external) if ob else None,
                    _limit=RuleParser._as_rule_ast(lim, internal_to_external) if lim else None,
                    _offset=RuleParser._as_rule_ast(off, internal_to_external) if off else None,
                ),
                internal_to_external,
            )

        return RuleParser._as_rule_ast(query, internal_to_external)

    @staticmethod
    def _as_rule_ast(node: Optional[Node], internal_to_external: Dict[str, str]) -> Optional[Node]:
        if node is None:
            return None
        return RuleParser._substitute_placeholders(node, internal_to_external)

    @staticmethod
    def _placeholder_varnode(internal_token: str, external_name: str) -> Node:
        if internal_token.startswith(VarTypesInfo[VarType.VarList]["internalBase"]):
            return VarSetNode(external_name)
        return VarNode(external_name)

    @staticmethod
    def _substitute_placeholders(node: Node, rev: Dict[str, str]) -> Node:
        if node.type == NodeType.COLUMN:
            col = node
            if not isinstance(col, ColumnNode):
                return node
            pa = col.parent_alias
            nm = col.name
            if pa is None and nm in rev:
                return RuleParser._placeholder_varnode(nm, rev[nm])
            if pa is not None and pa in rev and nm in rev:
                return ColumnNode(rev[nm], _alias=col.alias, _parent_alias=rev[pa])
            if pa is not None and pa in rev:
                return ColumnNode(nm, _alias=col.alias, _parent_alias=rev[pa])
            return ColumnNode(nm, _alias=col.alias, _parent_alias=pa)

        if node.type == NodeType.TABLE:
            t = node
            if not isinstance(t, TableNode):
                return node
            new_name = rev.get(t.name, t.name)
            new_alias = rev[t.alias] if t.alias and t.alias in rev else t.alias
            return TableNode(new_name, new_alias)

        if node.type == NodeType.QUERY:
            q = node
            if not isinstance(q, QueryNode):
                return node
            return QueryNode(
                _select=RuleParser._as_rule_ast(RuleParser._get_clause(q, NodeType.SELECT), rev),
                _from=RuleParser._as_rule_ast(RuleParser._get_clause(q, NodeType.FROM), rev),
                _where=RuleParser._as_rule_ast(RuleParser._get_clause(q, NodeType.WHERE), rev),
                _group_by=RuleParser._as_rule_ast(RuleParser._get_clause(q, NodeType.GROUP_BY), rev),
                _having=RuleParser._as_rule_ast(RuleParser._get_clause(q, NodeType.HAVING), rev),
                _order_by=RuleParser._as_rule_ast(RuleParser._get_clause(q, NodeType.ORDER_BY), rev),
                _limit=RuleParser._as_rule_ast(RuleParser._get_clause(q, NodeType.LIMIT), rev),
                _offset=RuleParser._as_rule_ast(RuleParser._get_clause(q, NodeType.OFFSET), rev),
            )

        if node.type == NodeType.SELECT:
            sn = node
            if not isinstance(sn, SelectNode):
                return node
            items: List[Node] = []
            don = sn.distinct_on
            for ch in sn.children:
                if don is not None and ch is don:
                    continue
                items.append(RuleParser._substitute_placeholders(ch, rev))
            new_don = (
                RuleParser._substitute_placeholders(don, rev) if don is not None else None
            )
            return SelectNode(items, _distinct=sn.distinct, _distinct_on=new_don)

        if node.type == NodeType.FROM:
            fn = node
            if not isinstance(fn, FromNode):
                return node
            return FromNode([RuleParser._substitute_placeholders(c, rev) for c in fn.children])

        if node.type == NodeType.WHERE:
            wn = node
            if not isinstance(wn, WhereNode):
                return node
            return WhereNode([RuleParser._substitute_placeholders(c, rev) for c in wn.children])

        if node.type == NodeType.GROUP_BY:
            g = node
            if not isinstance(g, GroupByNode):
                return node
            return GroupByNode([RuleParser._substitute_placeholders(c, rev) for c in g.children])

        if node.type == NodeType.HAVING:
            h = node
            if not isinstance(h, HavingNode):
                return node
            return HavingNode([RuleParser._substitute_placeholders(c, rev) for c in h.children])

        if node.type == NodeType.ORDER_BY:
            o = node
            if not isinstance(o, OrderByNode):
                return node
            return OrderByNode([RuleParser._substitute_placeholders(c, rev) for c in o.children])

        if node.type == NodeType.ORDER_BY_ITEM:
            oi = node
            if not isinstance(oi, OrderByItemNode):
                return node
            inner = list(oi.children)[0]
            return OrderByItemNode(RuleParser._substitute_placeholders(inner, rev), oi.sort)

        if node.type == NodeType.JOIN:
            j = node
            if not isinstance(j, JoinNode):
                return node
            ch = list(j.children)
            left = RuleParser._substitute_placeholders(ch[0], rev)
            right = RuleParser._substitute_placeholders(ch[1], rev)
            on_expr = (
                RuleParser._substitute_placeholders(ch[2], rev) if len(ch) > 2 else None
            )
            return JoinNode(left, right, j.join_type, on_expr)

        if node.type == NodeType.SUBQUERY:
            sq = node
            if not isinstance(sq, SubqueryNode):
                return node
            inner = list(sq.children)[0]
            return SubqueryNode(RuleParser._substitute_placeholders(inner, rev), sq.alias)

        if node.type == NodeType.FUNCTION:
            f = node
            if not isinstance(f, FunctionNode):
                return node
            new_args = [RuleParser._substitute_placeholders(a, rev) for a in f.children]
            return FunctionNode(f.name, _args=new_args, _alias=f.alias)

        if node.type == NodeType.LIST:
            ln = node
            if not isinstance(ln, ListNode):
                return node
            return ListNode([RuleParser._substitute_placeholders(c, rev) for c in ln.children])

        if node.type == NodeType.INTERVAL:
            inv = node
            if not isinstance(inv, IntervalNode):
                return node
            if isinstance(inv.value, Node):
                return IntervalNode(
                    RuleParser._substitute_placeholders(inv.value, rev),
                    inv.unit,  # type: ignore[arg-type]
                )
            return IntervalNode(inv.value, inv.unit)  # type: ignore[arg-type]

        if node.type == NodeType.CASE:
            cn = node
            if not isinstance(cn, CaseNode):
                return node
            new_whens: List[WhenThenNode] = []
            for wt in cn.whens:
                new_whens.append(
                    WhenThenNode(
                        RuleParser._substitute_placeholders(wt.when, rev),
                        RuleParser._substitute_placeholders(wt.then, rev),
                    )
                )
            new_else = (
                RuleParser._substitute_placeholders(cn.else_val, rev) if cn.else_val else None
            )
            return CaseNode(new_whens, new_else)

        if node.type == NodeType.OPERATOR:
            if isinstance(node, UnaryOperatorNode):
                op = node
                inner = list(op.children)[0] if op.children else op.operand
                return UnaryOperatorNode(RuleParser._substitute_placeholders(inner, rev), op.name)
            op = node
            ch = list(op.children)
            if len(ch) == 1:
                return OperatorNode(RuleParser._substitute_placeholders(ch[0], rev), op.name)
            return OperatorNode(
                RuleParser._substitute_placeholders(ch[0], rev),
                op.name,
                RuleParser._substitute_placeholders(ch[1], rev),
            )

        return node

    #  Extend pattern/rewrite to full SQL statement
    # 
    @staticmethod
    def extendToFullSQL(partialSQL: str) -> Tuple[str, Scope]:

        # Special case: condition on subquery 
        #   e.g., group_users.group_id IN (SELECT groups.id FROM groups WHERE groups.id > 0 ORDER BY NAME ASC)
        # Remove subquery in (*) before check existence of SELECT, FROM, and WHERE keywords
        #
        sanitisedPartialSQL = re.sub(r'\(.*\)', '(x)', partialSQL)

        # case-1: no SELECT and no FROM and no WHERE
        if not 'SELECT' in sanitisedPartialSQL.upper() and \
            not 'FROM' in sanitisedPartialSQL.upper() and \
                not 'WHERE' in sanitisedPartialSQL.upper():
            scope = Scope.CONDITION
        # case-2: no SELECT and no FROM but has WHERE
        elif not 'SELECT' in sanitisedPartialSQL.upper() and \
            not 'FROM' in sanitisedPartialSQL.upper():
            scope = Scope.WHERE
        # case-3: no SELECT but has FROM
        elif not 'SELECT' in sanitisedPartialSQL.upper():
            scope = Scope.FROM
        # case-4: has SELECT and has FROM
        else:
            scope = Scope.SELECT
        
        partialSQL = ScopeExtension[scope] + partialSQL
        return partialSQL, scope
    
    # Extract the AST subtree of pattern/rewrite based on scope
    # 
    @staticmethod
    def extractASTSubtree(aSTJson: Any, scope: Scope) -> Any:
        if scope == Scope.CONDITION:
            aSTJson = aSTJson['where']
        elif scope == Scope.WHERE:
            aSTJson.pop('select', None)
            aSTJson.pop('from', None)
        elif scope == Scope.FROM:
            aSTJson.pop('select', None)
        return aSTJson

    # Replace user-faced variables and variable lists with internal representations
    #   e.g., <x> ==> V1, <<y>> ==> VL1
    # 
    @staticmethod
    def replaceVars(pattern: str, rewrite: str) -> Tuple[str, str, dict]:
        
        # common function to replace one VarType
        # 
        def replaceVars(pattern: str, rewrite: str, varType: VarType, mapping: dict) -> Tuple[str, str]:
            regexPattern = VarTypesInfo[varType]['markerStart'] + r'(\w+)' + VarTypesInfo[varType]['markerEnd']
            vars = re.findall(regexPattern, pattern)
            varInternalBase = VarTypesInfo[varType]['internalBase']
            varInternalCount = 1
            for var in vars:
                if var not in mapping:
                    # var -> varInternal map
                    #   e.g., <x> ==> V1, <<y>> ==> VL1
                    specificRegexPattern = VarTypesInfo[varType]['markerStart'] + var + VarTypesInfo[varType]['markerEnd']
                    varInternal = varInternalBase + str(varInternalCount).zfill(3)
                    varInternalCount += 1
                    # replace var with varInternal in both pattern and rewrite
                    pattern = re.sub(specificRegexPattern, varInternal, pattern)
                    rewrite = re.sub(specificRegexPattern, varInternal, rewrite)
                    # take down the mapping x -> V1
                    mapping[var] = varInternal
            return pattern, rewrite
        
        # replace VarList first, then Var
        mapping = {}
        pattern, rewrite = replaceVars(pattern, rewrite, VarType.VarList, mapping)
        pattern, rewrite = replaceVars(pattern, rewrite, VarType.Var, mapping)
        return pattern, rewrite, mapping
        
    # parse a rule constraints into a list of conditions
    #
    @staticmethod
    def parse_constraints(constraints: str, mapping: str) -> str:
        mapping = json.loads(mapping)
        _conditions = constraints.lower().split('and')
        conditions = []
        for _condition in _conditions:
            condition = {}
            # TODO - we only support = conditions now
            # 
            if '=' in _condition:
                condition['operator'] = '='
                condition['operands'] = []
                _operands = _condition.split('=')
                for _operand in _operands:
                    if '(' in _operand and ')' in _operand:
                        operand = {}
                        func = RuleParser.extractFunc(_operand)
                        vars = RuleParser.extractVars(_operand)
                        operand['function'] = func
                        operand['variables'] = [mapping[var] if var in mapping else var for var in vars]
                    else:
                        operand = mapping[_operand] if _operand in mapping else _operand
                    condition['operands'].append(operand)
                conditions.append(condition)
            # or a boolean function, e.g., UNIQUE(t1, a1)
            #    we treat it as UNIQUE(t1, a1) = TRUE automatically
            # 
            else:
                condition['operator'] = '='
                condition['operands'] = []
                _operand = _condition
                if '(' in _operand and ')' in _operand:
                    operand = {}
                    func = RuleParser.extractFunc(_operand)
                    vars = RuleParser.extractVars(_operand)
                    operand['function'] = func
                    operand['variables'] = [mapping[var] if var in mapping else var for var in vars]
                else:
                    operand = mapping[_operand] if _operand in mapping else _operand
                condition['operands'].append(operand)
                condition['operands'].append('true')
                conditions.append(condition)

        return json.dumps(conditions)
    
    # extract function name from an operand in a condition in constraints
    # 
    @staticmethod
    def extractFunc(operand: str) -> str:
        parts = operand.split('(')
        return parts[0].strip()
    
    # extract variables inside a function of an operand in a condition in constraints
    # 
    @staticmethod
    def extractVars(operand: str) -> list:
        parts = operand.split(')')
        parts = parts[0].split('(')
        vars = parts[1].split(',')
        return [var.strip() for var in vars]
    
    # parse a rule actions into a list of actions
    # 
    @staticmethod
    def parse_actions(actions: str, mapping: str) -> list:
        mapping = json.loads(mapping)
        _actions = actions.lower().split('and')
        actions = []
        for _action in _actions:
            # TODO - we only support function in actions now
            # 
            if '(' in _action and ')' in _action:
                action = {}
                func = RuleParser.extractFunc(_action)
                vars = RuleParser.extractVars(_action)
                action['function'] = func
                action['variables'] = [mapping[var] if var in mapping else var for var in vars]
                actions.append(action)
        return json.dumps(actions)

            
    # mosql parsing will find the the index after a mismatching bracket so the index could
    #    be slightly off and confusing so there is a function to find mismatched variables
    #    with wrong brackets
    @staticmethod     
    def find_malformed_brackets(pattern: str) -> int:
        CommonMistakeVarTypesInfo = {
            'markerStart': [r'\(', r'\{', r'\['],
            'markerEnd': [r'\)', r'\}', r'\]'],
        }

        for i in range(len(CommonMistakeVarTypesInfo['markerStart'])):
            regexPatternVarStart = CommonMistakeVarTypesInfo['markerStart'][i] + r'(\w+)' + VarTypesInfo[VarType.Var]['markerEnd']
            regexPatternVarEnd = VarTypesInfo[VarType.Var]['markerStart'] + r'(\w+)' + CommonMistakeVarTypesInfo['markerEnd'][i]
        
            varStart = re.search(regexPatternVarStart, pattern)
            varEnd = re.search(regexPatternVarEnd, pattern)

            if varStart:
                return varStart.start()
            elif varEnd:
                return varEnd.start()
        
        return -1
    
if __name__ == '__main__':

    def print_rule(_title, _pattern, _rewrite, _constraints="", _actions=""):
        _patternASTJson, _rewriteASTJson, _mapping = RuleParser.parse(_pattern, _rewrite)
        _constraintsJson = RuleParser.parse_constraints(_constraints, _mapping)
        _actionsJson = RuleParser.parse_actions(_actions, _mapping)
        print()
        print("==================================================")
        print("    " + _title)
        print("--------------------------------------------------")
        print("pattern     |  " + _pattern)
        print("constraints |  " + _constraints)
        print("rewrite     |  " + _rewrite)
        print("actions     |  " + _actions)
        print("--------------------------------------------------")
        print("pattern AST Json |  " + _patternASTJson)
        print("constraints Json |  " + _constraintsJson)
        print("rewrite AST Json |  " + _rewriteASTJson)
        print("actions Json     |  " + _actionsJson)
        print("vars mapping     |  " + _mapping)

    # rule 1
    pattern = 'CAST(<x> AS DATE)'
    rewrite = '<x>'
    constraints = "TYPE(x) = DATE"
    print_rule('Rule 1', pattern, rewrite, constraints)
    
    # rule 2
    pattern = 'STRPOS(LOWER(<x>), <y>) > 0'
    rewrite = "<x> ILIKE '%<y>%'"
    print_rule('Rule 2', pattern, rewrite)

    # rule 3
    pattern = '''
            select <<s1>>
            from <tb1> <t1>, 
                 <tb1> <t2>
            where <t1>.<a1>=<t2>.<a1>
            and <<p1>>
        '''
    rewrite = '''
            select <<s1>> 
            from <tb1> <t1>
            where 1=1 
            and <<p1>>
        '''
    print_rule('Rule 3', pattern, rewrite)

    # rule 101
    pattern = 'ADDDATE(<x>, INTERVAL 0 SECOND)'
    rewrite = '<x>'
    print_rule('Rule 101', pattern, rewrite)

    # rule 102
    pattern = '<x> = TIMESTAMP(<y>)'
    rewrite = '<x> = <y>'
    print_rule('Rule 102', pattern, rewrite)