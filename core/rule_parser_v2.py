# Rule parser v2: self-contained rule preprocessing (duplicated from v1 on purpose), then
#   QueryParser and ElementVariableNode / SetVariableNode rule AST via parse().

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.ast.enums import NodeType
from core.ast.node import (
    CaseNode,
    ColumnNode,
    CompoundQueryNode,
    FromNode,
    FunctionNode,
    GroupByNode,
    HavingNode,
    IntervalNode,
    JoinNode,
    LiteralNode,
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
    ElementVariableNode,
    SetVariableNode,
    WhenThenNode,
    WhereNode,
)
from core.query_parser import QueryParser


# Variable types (v2 naming; same placeholder syntax as v1).
# AST: ``<name>`` to ElementVariableNode, ``<<name>>`` to SetVariableNode.
#
class VarType(Enum):
    ElementVariable = 1  # <x>  to ElementVariableNode in rule AST
    SetVariable = 2  # <<y>> to SetVariableNode in rule AST


# Placeholder markers and internal token prefixes for rule variables.
#
VarTypesInfo = {
    VarType.ElementVariable: {
        "markerStart": "<",
        "markerEnd": ">",
        "internalBase": "EV",
        "externalBase": "x",
    },
    VarType.SetVariable: {
        "markerStart": "<<",
        "markerEnd": ">>",
        "internalBase": "SV",
        "externalBase": "y",
    },
}


# Scope of pattern/rewrite fragment (same as v1).
#
class Scope(Enum):
    SELECT = 1
    FROM = 2
    WHERE = 3
    CONDITION = 4


# Partial-SQL prefix for extendToFullSQL (same as v1).
#
ScopeExtension = {
    Scope.CONDITION: "SELECT * FROM t WHERE ",
    Scope.WHERE: "SELECT * FROM t ",
    Scope.FROM: "SELECT * ",
    Scope.SELECT: "",
}


# Result of RuleParserV2.parse: rule AST with external variable names restored.
#
@dataclass(frozen=True)
class RuleParseResult:
    pattern_ast: Node
    rewrite_ast: Node
    mapping: Dict[str, str]


class RuleParserV2:

    # mosql parsing can report mismatching brackets at a confusing index; detect common
    #   wrong delimiters around rule variables (same logic as v1 RuleParser.find_malformed_brackets).
    #
    @staticmethod
    def find_malformed_brackets(pattern: str) -> int:
        CommonMistakeVarTypesInfo = {
            "markerStart": [r"\(", r"\{", r"\["],
            "markerEnd": [r"\)", r"\}", r"\]"],
        }

        for i in range(len(CommonMistakeVarTypesInfo["markerStart"])):
            regexPatternVarStart = (
                CommonMistakeVarTypesInfo["markerStart"][i]
                + r"(\w+)"
                + VarTypesInfo[VarType.ElementVariable]["markerEnd"]
            )
            regexPatternVarEnd = (
                VarTypesInfo[VarType.ElementVariable]["markerStart"]
                + r"(\w+)"
                + CommonMistakeVarTypesInfo["markerEnd"][i]
            )

            varStart = re.search(regexPatternVarStart, pattern)
            varEnd = re.search(regexPatternVarEnd, pattern)

            if varStart:
                return varStart.start()
            if varEnd:
                return varEnd.start()

        return -1

    # Extend pattern/rewrite fragment to full SQL (same as v1 RuleParser.extendToFullSQL).
    #
    @staticmethod
    def extendToFullSQL(partialSQL: str) -> Tuple[str, Scope]:
        # Special case: condition on subquery
        #   e.g., group_users.group_id IN (SELECT ... )
        # Remove subquery in (*) before checking SELECT / FROM / WHERE.
        #
        sanitisedPartialSQL = re.sub(r"\(.*\)", "(x)", partialSQL)

        # case-1: no SELECT and no FROM and no WHERE
        if (
            "SELECT" not in sanitisedPartialSQL.upper()
            and "FROM" not in sanitisedPartialSQL.upper()
            and "WHERE" not in sanitisedPartialSQL.upper()
        ):
            scope = Scope.CONDITION
        # case-2: no SELECT and no FROM but has WHERE
        elif (
            "SELECT" not in sanitisedPartialSQL.upper()
            and "FROM" not in sanitisedPartialSQL.upper()
        ):
            scope = Scope.WHERE
        # case-3: no SELECT but has FROM
        elif "SELECT" not in sanitisedPartialSQL.upper():
            scope = Scope.FROM
        # case-4: has SELECT (and typically FROM)
        else:
            scope = Scope.SELECT

        partialSQL = ScopeExtension[scope] + partialSQL
        return partialSQL, scope

    # Replace user-facing rule variables with internal tokens.
    #   e.g., <x> ==> EV001, <<y>> ==> SV001
    #
    @staticmethod
    def replaceVars(pattern: str, rewrite: str) -> Tuple[str, str, Dict[str, str]]:

        def _replace_one_var_type(
            pattern: str, rewrite: str, varType: VarType, mapping: Dict[str, str]
        ) -> Tuple[str, str]:
            regexPattern = (
                VarTypesInfo[varType]["markerStart"]
                + r"(\w+)"
                + VarTypesInfo[varType]["markerEnd"]
            )
            found = re.findall(regexPattern, pattern)
            varInternalBase = VarTypesInfo[varType]["internalBase"]
            varInternalCount = 1
            for var in found:
                if var not in mapping:
                    specificRegexPattern = (
                        VarTypesInfo[varType]["markerStart"]
                        + var
                        + VarTypesInfo[varType]["markerEnd"]
                    )
                    varInternal = varInternalBase + str(varInternalCount).zfill(3)
                    varInternalCount += 1
                    pattern = re.sub(specificRegexPattern, varInternal, pattern)
                    rewrite = re.sub(specificRegexPattern, varInternal, rewrite)
                    mapping[var] = varInternal
            return pattern, rewrite

        mapping: Dict[str, str] = {}
        pattern, rewrite = _replace_one_var_type(pattern, rewrite, VarType.SetVariable, mapping)
        pattern, rewrite = _replace_one_var_type(pattern, rewrite, VarType.ElementVariable, mapping)
        return pattern, rewrite, mapping

    # parse a rule into project AST nodes (ElementVariableNode / SetVariableNode for rule variables)
    #
    @staticmethod
    def parse(pattern: str, rewrite: str) -> RuleParseResult:

        # 1. Replace user-faced variables and variable lists
        #    with internal representations
        #
        pattern_sql, rewrite_sql, mapping = RuleParserV2.replaceVars(pattern, rewrite)

        # 2. Extend partial SQL statement to full SQL statement
        #    for the sake of sql parser
        #
        pattern_full, pattern_scope = RuleParserV2.extendToFullSQL(pattern_sql)
        rewrite_full, rewrite_scope = RuleParserV2.extendToFullSQL(rewrite_sql)

        # 3. Parse extended full SQL statement into AST (QueryParser)
        #
        qparser = QueryParser()
        pattern_query = qparser.parse(pattern_full)
        rewrite_query = qparser.parse(rewrite_full)

        # 4. Map internal tokens (EV00x / SV00x) to ElementVariableNode / SetVariableNode across the full query AST
        #
        internal_to_external = {internal: external for external, internal in mapping.items()}
        pattern_after_vars = RuleParserV2._substitute_rule_vars(pattern_query, internal_to_external)
        rewrite_after_vars = RuleParserV2._substitute_rule_vars(rewrite_query, internal_to_external)

        # 5. Reduce to the rule fragment for the inferred scope (CONDITION / WHERE / FROM / SELECT)
        #
        pattern_ast = RuleParserV2._extract_rule_fragment(pattern_after_vars, pattern_scope)
        rewrite_ast = RuleParserV2._extract_rule_fragment(rewrite_after_vars, rewrite_scope)

        # 6. Return AST result + mapping
        #
        return RuleParseResult(
            pattern_ast=pattern_ast,
            rewrite_ast=rewrite_ast,
            mapping=mapping,
        )

    # Find first child of query with given clause type (SELECT, FROM, WHERE, ...).
    #
    @staticmethod
    def _get_clause(query: QueryNode, clause_type: NodeType) -> Optional[Node]:
        for child in query.children:
            if child.type == clause_type:
                return child
        return None

    # Apply internal_to_external across an entire parsed query (EV00x / SV00x -> ElementVariableNode, etc.).
    #
    @staticmethod
    def _substitute_rule_vars(
        query: QueryNode, internal_to_external: Dict[str, str]
    ) -> QueryNode:
        out = RuleParserV2._as_rule_ast(query, internal_to_external)
        if not isinstance(out, (QueryNode, CompoundQueryNode)):
            raise TypeError("expected QueryNode after substituting rule variables on full query")
        return out

    # Slice a fully substituted query to the rule fragment for this scope (no variable-node pass).
    #
    @staticmethod
    def _extract_rule_fragment(query: QueryNode, scope: Scope) -> Node:
        # CompoundQueryNode (e.g. UNION) is always a full-query scope — return as-is
        if isinstance(query, CompoundQueryNode):
            return query
        frm = RuleParserV2._get_clause(query, NodeType.FROM)
        wh = RuleParserV2._get_clause(query, NodeType.WHERE)
        gb = RuleParserV2._get_clause(query, NodeType.GROUP_BY)
        hav = RuleParserV2._get_clause(query, NodeType.HAVING)
        ob = RuleParserV2._get_clause(query, NodeType.ORDER_BY)
        lim = RuleParserV2._get_clause(query, NodeType.LIMIT)
        off = RuleParserV2._get_clause(query, NodeType.OFFSET)

        # case CONDITION: predicate only
        #
        if scope == Scope.CONDITION:
            if wh is None or not list(wh.children):
                raise ValueError("CONDITION scope requires a WHERE predicate")
            return list(wh.children)[0]

        # case WHERE: query without select/from lists
        #
        if scope == Scope.WHERE:
            return QueryNode(
                _select=None,
                _from=None,
                _where=wh,
                _group_by=gb,
                _having=hav,
                _order_by=ob,
                _limit=lim,
                _offset=off,
            )

        # case FROM: from + following clauses, no select list
        #
        if scope == Scope.FROM:
            return QueryNode(
                _select=None,
                _from=frm,
                _where=wh,
                _group_by=gb,
                _having=hav,
                _order_by=ob,
                _limit=lim,
                _offset=off,
            )

        # case SELECT: full query
        #
        return query

    # Run ElementVariableNode / SetVariableNode substitution on one subtree (None stays None).
    #
    @staticmethod
    def _as_rule_ast(node: Optional[Node], internal_to_external: Dict[str, str]) -> Optional[Node]:
        if node is None:
            return None
        return RuleParserV2._substitute_placeholders(node, internal_to_external)

    # Build ElementVariableNode or SetVariableNode from internal token prefix (EV... vs SV...).
    #
    @staticmethod
    def _placeholder_varnode(internal_token: str, external_name: str) -> Node:
        if internal_token.startswith(VarTypesInfo[VarType.SetVariable]["internalBase"]):
            return SetVariableNode(external_name)
        return ElementVariableNode(external_name)

    # Structural recursion: replace internal identifiers with ElementVariableNode / SetVariableNode where appropriate.
    #
    @staticmethod
    def _substitute_placeholders(node: Node, rev: Dict[str, str]) -> Node:
        def _replace_internal_in_string(s: str) -> str:
            # Replace EV00x / SV00x occurrences inside strings (e.g., '%EV001%').
            out = s
            for internal, external in rev.items():
                out = out.replace(internal, external)
            return out

        if node.type == NodeType.COLUMN:
            col = node
            if not isinstance(col, ColumnNode):
                return node
            pa = col.parent_alias
            nm = col.name
            new_alias = _replace_internal_in_string(col.alias) if isinstance(col.alias, str) else col.alias
            new_pa = _replace_internal_in_string(pa) if isinstance(pa, str) else pa
            if pa is None and nm in rev:
                return RuleParserV2._placeholder_varnode(nm, rev[nm])
            if pa is not None and pa in rev and nm in rev:
                return ColumnNode(rev[nm], _alias=new_alias, _parent_alias=rev[pa])
            if pa is not None and pa in rev:
                return ColumnNode(nm, _alias=new_alias, _parent_alias=rev[pa])
            if pa is not None and nm in rev:
                return ColumnNode(rev[nm], _alias=new_alias, _parent_alias=new_pa)
            return ColumnNode(nm, _alias=new_alias, _parent_alias=new_pa)

        if node.type == NodeType.TABLE:
            t = node
            if not isinstance(t, TableNode):
                return node
            # If table name is a SET variable placeholder (<<name>>), promote to SetVariableNode
            # so it matches any table or list of tables in the FROM clause.
            # Element variable tokens (EV...) stay as TableNode so _match_node handles them.
            sv_base = VarTypesInfo[VarType.SetVariable]["internalBase"]
            if isinstance(t.name, str) and t.name in rev and t.name.startswith(sv_base):
                return SetVariableNode(rev[t.name])
            new_name = rev.get(t.name, t.name) if isinstance(t.name, str) else t.name
            if t.alias is not None and isinstance(t.alias, str) and t.alias in rev:
                new_alias = rev[t.alias]
            else:
                new_alias = t.alias
            return TableNode(new_name, new_alias)

        if node.type == NodeType.LITERAL:
            lit = node
            if not isinstance(lit, LiteralNode):
                return node
            if isinstance(lit.value, str):
                # If the entire literal value is an internal placeholder token, keep it as a
                # string literal (rules like `'<s>'` should parse as LiteralNode('s'), not a
                # variable node in expression position).
                if lit.value in rev:
                    return LiteralNode(rev[lit.value])
                # Otherwise substitute any embedded tokens (e.g. '%EV001%' to '%x%')
                return LiteralNode(_replace_internal_in_string(lit.value))
            return LiteralNode(lit.value)

        if node.type == NodeType.QUERY:
            q = node
            if not isinstance(q, QueryNode):
                return node
            return QueryNode(
                _select=RuleParserV2._as_rule_ast(RuleParserV2._get_clause(q, NodeType.SELECT), rev),
                _from=RuleParserV2._as_rule_ast(RuleParserV2._get_clause(q, NodeType.FROM), rev),
                _where=RuleParserV2._as_rule_ast(RuleParserV2._get_clause(q, NodeType.WHERE), rev),
                _group_by=RuleParserV2._as_rule_ast(RuleParserV2._get_clause(q, NodeType.GROUP_BY), rev),
                _having=RuleParserV2._as_rule_ast(RuleParserV2._get_clause(q, NodeType.HAVING), rev),
                _order_by=RuleParserV2._as_rule_ast(RuleParserV2._get_clause(q, NodeType.ORDER_BY), rev),
                _limit=RuleParserV2._as_rule_ast(RuleParserV2._get_clause(q, NodeType.LIMIT), rev),
                _offset=RuleParserV2._as_rule_ast(RuleParserV2._get_clause(q, NodeType.OFFSET), rev),
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
                items.append(RuleParserV2._substitute_placeholders(ch, rev))
            new_don = (
                RuleParserV2._substitute_placeholders(don, rev) if don is not None else None
            )
            return SelectNode(items, _distinct=sn.distinct, _distinct_on=new_don)

        if node.type == NodeType.FROM:
            fn = node
            if not isinstance(fn, FromNode):
                return node
            return FromNode([RuleParserV2._substitute_placeholders(c, rev) for c in fn.children])

        if node.type == NodeType.WHERE:
            wn = node
            if not isinstance(wn, WhereNode):
                return node
            return WhereNode([RuleParserV2._substitute_placeholders(c, rev) for c in wn.children])

        if node.type == NodeType.GROUP_BY:
            g = node
            if not isinstance(g, GroupByNode):
                return node
            return GroupByNode([RuleParserV2._substitute_placeholders(c, rev) for c in g.children])

        if node.type == NodeType.HAVING:
            h = node
            if not isinstance(h, HavingNode):
                return node
            return HavingNode([RuleParserV2._substitute_placeholders(c, rev) for c in h.children])

        if node.type == NodeType.ORDER_BY:
            o = node
            if not isinstance(o, OrderByNode):
                return node
            return OrderByNode([RuleParserV2._substitute_placeholders(c, rev) for c in o.children])

        if node.type == NodeType.LIMIT:
            lim = node
            if not isinstance(lim, LimitNode):
                return node
            if isinstance(lim.limit, str):
                return LimitNode(_replace_internal_in_string(lim.limit))
            return LimitNode(lim.limit)

        if node.type == NodeType.OFFSET:
            off = node
            if not isinstance(off, OffsetNode):
                return node
            if isinstance(off.offset, str):
                return OffsetNode(_replace_internal_in_string(off.offset))
            return OffsetNode(off.offset)

        if node.type == NodeType.ORDER_BY_ITEM:
            oi = node
            if not isinstance(oi, OrderByItemNode):
                return node
            inner = list(oi.children)[0]
            return OrderByItemNode(RuleParserV2._substitute_placeholders(inner, rev), oi.sort)

        if node.type == NodeType.JOIN:
            j = node
            if not isinstance(j, JoinNode):
                return node
            ch = list(j.children)
            left = RuleParserV2._substitute_placeholders(ch[0], rev)
            right = RuleParserV2._substitute_placeholders(ch[1], rev)
            on_expr = (
                RuleParserV2._substitute_placeholders(ch[2], rev) if len(ch) > 2 else None
            )
            return JoinNode(left, right, j.join_type, on_expr)

        if node.type == NodeType.SUBQUERY:
            sq = node
            if not isinstance(sq, SubqueryNode):
                return node
            inner = list(sq.children)[0]
            alias = _replace_internal_in_string(sq.alias) if isinstance(sq.alias, str) else sq.alias
            return SubqueryNode(RuleParserV2._substitute_placeholders(inner, rev), alias)

        if node.type == NodeType.FUNCTION:
            f = node
            if not isinstance(f, FunctionNode):
                return node
            new_args = [RuleParserV2._substitute_placeholders(a, rev) for a in f.children]
            alias = _replace_internal_in_string(f.alias) if isinstance(f.alias, str) else f.alias
            return FunctionNode(f.name, _args=new_args, _alias=alias)

        if node.type == NodeType.LIST:
            ln = node
            if not isinstance(ln, ListNode):
                return node
            return ListNode([RuleParserV2._substitute_placeholders(c, rev) for c in ln.children])

        if node.type == NodeType.INTERVAL:
            inv = node
            if not isinstance(inv, IntervalNode):
                return node
            if isinstance(inv.value, Node):
                return IntervalNode(
                    RuleParserV2._substitute_placeholders(inv.value, rev),
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
                        RuleParserV2._substitute_placeholders(wt.when, rev),
                        RuleParserV2._substitute_placeholders(wt.then, rev),
                    )
                )
            new_else = (
                RuleParserV2._substitute_placeholders(cn.else_val, rev) if cn.else_val else None
            )
            return CaseNode(new_whens, new_else)

        if node.type == NodeType.OPERATOR:
            if isinstance(node, UnaryOperatorNode):
                op = node
                inner = list(op.children)[0] if op.children else op.operand
                return UnaryOperatorNode(RuleParserV2._substitute_placeholders(inner, rev), op.name)
            op = node
            ch = list(op.children)
            if len(ch) == 1:
                return OperatorNode(RuleParserV2._substitute_placeholders(ch[0], rev), op.name)
            return OperatorNode(
                RuleParserV2._substitute_placeholders(ch[0], rev),
                op.name,
                RuleParserV2._substitute_placeholders(ch[1], rev),
            )

        if node.type == NodeType.COMPOUND_QUERY:
            cq = node
            if not isinstance(cq, CompoundQueryNode):
                return node
            return CompoundQueryNode(
                RuleParserV2._substitute_placeholders(cq.left, rev),
                RuleParserV2._substitute_placeholders(cq.right, rev),
                cq.is_all,
            )

        return node
