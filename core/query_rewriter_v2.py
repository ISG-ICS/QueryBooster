"""
Rule dict expected by the public API (produced by data.rules.get_rule_v2):
  {
      'id': int,
      'key': str,
      'pattern_ast': Node,       # from RuleParserV2
      'rewrite_ast':  Node,      # from RuleParserV2
      'mapping':      dict,      # external_name -> internal_token (EV/SV prefix)
      'actions_json': list,      # same shape as v1: [{'function': str, 'variables': list}, ...]
  }

Memo dict produced by match():
  {
      var_name: Node | str | int | list,   # bindings for element/set variables
      '_rule_node': Node,                  # identity of the matched query subtree
      '_partial_op': str,                  # 'AND' | 'OR' when partial match
      '_partial_remaining': list[Node],    # unmatched siblings from partial match
      '_extra_clauses': list[Node],        # query clauses not in pattern (carry-through)
  }
"""

from __future__ import annotations

import copy
import logging
import re
from contextlib import contextmanager
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import sqlparse

from core.ast.enums import NodeType

logger = logging.getLogger(__name__)
from core.ast.node import (
    CaseNode,
    ColumnNode,
    CompoundQueryNode,
    DataTypeNode,
    ElementVariableNode,
    FromNode,
    FunctionNode,
    GroupByNode,
    HavingNode,
    IntervalNode,
    JoinNode,
    LimitNode,
    ListNode,
    LiteralNode,
    Node,
    OffsetNode,
    OperatorNode,
    OrderByItemNode,
    OrderByNode,
    QueryNode,
    SelectNode,
    SetVariableNode,
    SubqueryNode,
    TableNode,
    TimeUnitNode,
    UnaryOperatorNode,
    WhenThenNode,
    WhereNode,
)
from core.query_formatter import QueryFormatter
from core.query_parser import QueryParser


class MatchingMode(Enum):
    FULL_ONLY = "full_only"
    ALLOW_PARTIAL = "allow_partial"
    IN_PARTIAL = "in_partial"


# ============================================================================
# Logical-tree helpers
# ============================================================================

def _flatten_logical(node: Node, op_name: str) -> List[Node]:
    """Flatten a left-associative binary AND/OR tree into a flat list."""
    if isinstance(node, OperatorNode) and not isinstance(node, UnaryOperatorNode) \
            and node.name.upper() == op_name.upper():
        result: List[Node] = []
        for child in list(node.children):
            result.extend(_flatten_logical(child, op_name))
        return result
    return [node]


def _unflatten_logical(nodes: List[Node], op_name: str) -> Node:
    """Rebuild a left-associative binary AND/OR tree from a flat list."""
    if len(nodes) == 1:
        return nodes[0]
    left = _unflatten_logical(nodes[:-1], op_name)
    return OperatorNode(left, op_name, nodes[-1])


# ============================================================================
# QueryNode clause helpers
# ============================================================================

def _get_clause(query: QueryNode, clause_type: NodeType) -> Optional[Node]:
    for child in query.children:
        if child.type == clause_type:
            return child
    return None


_CLAUSE_TYPES = [
    NodeType.FROM, NodeType.SELECT, NodeType.WHERE,
    NodeType.GROUP_BY, NodeType.HAVING, NodeType.ORDER_BY,
    NodeType.LIMIT, NodeType.OFFSET,
]


# ============================================================================
# Variable binding
# ============================================================================

@contextmanager
def _memo_snapshot(memo: dict):
    """Context manager that rolls back memo mutations on failure.

    Usage:
        with _memo_snapshot(memo) as commit:
            if try_match():
                commit()
                return True
    """
    snap = dict(memo)
    committed = False

    def commit():
        nonlocal committed
        committed = True

    try:
        yield commit
    finally:
        if not committed:
            memo.clear()
            memo.update(snap)


def _bind(var_name: str, value: Any, memo: dict) -> bool:
    """Bind var_name -> value in memo; return False on inconsistency."""
    if var_name in memo:
        existing = memo[var_name]
        # Allow TableNode <-> string comparison via alias or name
        # (table vars bind to whole TableNode; ColumnNode.parent_alias binds to string)
        if isinstance(existing, TableNode) and isinstance(value, str):
            return (existing.alias or existing.name) == value
        if isinstance(value, TableNode) and isinstance(existing, str):
            return (value.alias or value.name) == existing
        if isinstance(existing, Node) and isinstance(value, Node):
            return existing == value
        return existing == value
    memo[var_name] = value
    return True


def _is_var_name(s: Any, mapping: dict) -> bool:
    """True if s is a string that is an external variable name in the rule mapping."""
    return isinstance(s, str) and s in mapping


# ============================================================================
# Core matching
# ============================================================================

def _match_node(
    q: Node, p: Node, memo: dict, mode: MatchingMode, mapping: dict
) -> bool:
    """Recursively match query node q against pattern node p."""

    # --- variable nodes in pattern ---
    if isinstance(p, ElementVariableNode):
        return _bind(p.name, q, memo)

    if isinstance(p, SetVariableNode):
        # Should only appear inside list matching; absorb as singleton list here.
        # When matching a ListNode (e.g. IN list contents), bind to its children
        # so <<y>> bound to IN ('s1','s2') gives memo['y']=[s1, s2] not [ListNode].
        if isinstance(q, ListNode):
            bind_value = list(q.children)
        else:
            bind_value = [q]
        val = memo.get(p.name)
        if val is None:
            memo[p.name] = bind_value
            return True
        if isinstance(val, list):
            return val == bind_value
        return False

    # --- type must be compatible ---
    if not isinstance(q, type(p)) and not isinstance(p, type(q)):
        # Allow OperatorNode / UnaryOperatorNode subclass relationship
        if not (isinstance(q, OperatorNode) and isinstance(p, OperatorNode)):
            return False

    # --- leaf nodes ---
    if isinstance(p, LiteralNode):
        if not isinstance(q, LiteralNode):
            return False
        qv, pv = q.value, p.value
        # RuleParserV2 may represent placeholders inside string literals like `'<s>'`
        # as LiteralNode("s") (where "s" is a declared rule variable). In that case,
        # treat it as a bindable placeholder rather than a concrete string.

        # TODO: We hope to further flatten variables in the literal, e.g.,
        # q: {like: [name, '%joe%']} -> Func(like, [Col('name'), LiteralNode('%joe%')]) 
        # p: {like: [x, '%y%']} -> Func(like, [EV(x),  LitrlComb([LiteralNode('%'), EV(y), LiteralNode('%')])])
        if isinstance(pv, str) and _is_var_name(pv, mapping):
            return _bind(pv, q, memo)
        if isinstance(qv, str) and isinstance(pv, str):
            return qv.lower() == pv.lower()
        return qv == pv

    if isinstance(p, DataTypeNode):
        return isinstance(q, DataTypeNode) and q.name.upper() == p.name.upper()

    if isinstance(p, TimeUnitNode):
        return isinstance(q, TimeUnitNode) and q.name.upper() == p.name.upper()

    # --- TableNode: name and alias may be variable names ---
    if isinstance(p, TableNode):
        if not isinstance(q, TableNode):
            return False
        if _is_var_name(p.name, mapping) and p.alias is None:
            # Variable stands for the entire table reference (name + alias).
            # Bind to the whole TableNode so the rewrite can reproduce it faithfully.
            return _bind(p.name, q, memo)
        if _is_var_name(p.name, mapping):
            if not _bind(p.name, q.name, memo):
                return False
        else:
            if not isinstance(q.name, str) or q.name.lower() != p.name.lower():
                return False
        if p.alias is not None:
            # Pattern requires an alias (even if it's a variable). Do not match
            # unaliased tables, otherwise the alias var would bind to None and
            # rewrites expecting a real alias/identifier become nonsensical.
            if q.alias is None:
                return False
            if _is_var_name(p.alias, mapping):
                if not _bind(p.alias, q.alias, memo):
                    return False
            else:
                qa = q.alias or ""
                if qa.lower() != p.alias.lower():
                    return False
        return True

    # --- ColumnNode: name and parent_alias may be variable names ---
    if isinstance(p, ColumnNode):
        if not isinstance(q, ColumnNode):
            return False
        if _is_var_name(p.name, mapping):
            if not _bind(p.name, q.name, memo):
                return False
        else:
            if not isinstance(q.name, str) or q.name.lower() != p.name.lower():
                return False
        if p.parent_alias is not None:
            # Pattern requires a qualifier (even if it's a variable). Do not match
            # unqualified columns, otherwise the qualifier var would bind to None.
            if q.parent_alias is None:
                return False
            if _is_var_name(p.parent_alias, mapping):
                if not _bind(p.parent_alias, q.parent_alias, memo):
                    return False
            else:
                qpa = q.parent_alias or ""
                if qpa.lower() != p.parent_alias.lower():
                    return False
        return True

    # --- OperatorNode ---
    if isinstance(p, OperatorNode):
        if not isinstance(q, OperatorNode):
            return False

        # Unary operator
        if isinstance(p, UnaryOperatorNode):
            if not isinstance(q, UnaryOperatorNode):
                return False
            if q.name.upper() != p.name.upper():
                return False
            return _match_node(list(q.children)[0], list(p.children)[0], memo, mode, mapping)

        p_op = p.name.upper()
        q_op = q.name.upper()

        # AND/OR: flatten and match with optional partial remaining
        if p_op in ("AND", "OR") or (q_op in ("AND", "OR") and mode == MatchingMode.ALLOW_PARTIAL):
            if p_op == q_op and q_op in ("AND", "OR"):
                return _match_and_or(q, p, q_op, memo, mode, mapping)
            elif q_op in ("AND", "OR") and mode == MatchingMode.ALLOW_PARTIAL:
                # Pattern is NOT the same AND/OR op; try to find p among q's flat elements
                return _partial_match_in_logical(q, p, q_op, memo, mode, mapping)
            else:
                # p_op == q_op but neither is AND/OR; or mismatch
                if p_op != q_op:
                    return False
                # fall through to structural match

        elif p_op != q_op:
            return False

        q_ch = list(q.children)
        p_ch = list(p.children)
        if len(q_ch) != len(p_ch):
            return False
        for qc, pc in zip(q_ch, p_ch):
            if not _match_node(qc, pc, memo, mode, mapping):
                return False
        return True

    # --- FunctionNode ---
    if isinstance(p, FunctionNode):
        if not isinstance(q, FunctionNode):
            return False
        if q.name.upper() != p.name.upper():
            return False
        return _match_children_list(list(q.children), list(p.children), memo, mode, mapping)

    # --- ListNode ---
    if isinstance(p, ListNode):
        if not isinstance(q, ListNode):
            return False
        return _match_children_list(list(q.children), list(p.children), memo, mode, mapping)

    # --- IntervalNode ---
    if isinstance(p, IntervalNode):
        if not isinstance(q, IntervalNode):
            return False
        if isinstance(p.value, Node):
            if not isinstance(q.value, Node):
                return False
            if not _match_node(q.value, p.value, memo, mode, mapping):
                return False
        else:
            if q.value != p.value:
                return False
        return _match_node(q.unit, p.unit, memo, mode, mapping)

    # --- SelectNode ---
    if isinstance(p, SelectNode):
        if not isinstance(q, SelectNode):
            return False
        q_items = [c for c in list(q.children)
                   if q.distinct_on is None or c is not q.distinct_on]
        p_items = [c for c in list(p.children)
                   if p.distinct_on is None or c is not p.distinct_on]
        return _match_children_list(q_items, p_items, memo, mode, mapping)

    # --- FromNode / WhereNode / GroupByNode / HavingNode / OrderByNode ---
    if isinstance(p, (FromNode, WhereNode, GroupByNode, HavingNode, OrderByNode)):
        if not isinstance(q, type(p)):
            return False
        return _match_children_list(list(q.children), list(p.children), memo, mode, mapping)

    # --- OrderByItemNode ---
    if isinstance(p, OrderByItemNode):
        if not isinstance(q, OrderByItemNode):
            return False
        if p.sort is not None and q.sort != p.sort:
            return False
        return _match_node(list(q.children)[0], list(p.children)[0], memo, mode, mapping)

    # --- LimitNode ---
    if isinstance(p, LimitNode):
        if not isinstance(q, LimitNode):
            return False
        if isinstance(p.limit, str) and _is_var_name(p.limit, mapping):
            return _bind(p.limit, q.limit, memo)
        return q.limit == p.limit

    # --- OffsetNode ---
    if isinstance(p, OffsetNode):
        if not isinstance(q, OffsetNode):
            return False
        if isinstance(p.offset, str) and _is_var_name(p.offset, mapping):
            return _bind(p.offset, q.offset, memo)
        return q.offset == p.offset

    # --- JoinNode ---
    if isinstance(p, JoinNode):
        if not isinstance(q, JoinNode):
            return False
        if q.join_type != p.join_type:
            return False
        q_ch = list(q.children)
        p_ch = list(p.children)
        if not _match_node(q_ch[0], p_ch[0], memo, mode, mapping):
            return False
        if not _match_node(q_ch[1], p_ch[1], memo, mode, mapping):
            return False
        if len(p_ch) > 2:
            if len(q_ch) < 3:
                return False
            if not _match_node(q_ch[2], p_ch[2], memo, mode, mapping):
                return False
        return True

    # --- SubqueryNode ---
    if isinstance(p, SubqueryNode):
        if not isinstance(q, SubqueryNode):
            return False
        return _match_node(list(q.children)[0], list(p.children)[0], memo, mode, mapping)

    # --- WhenThenNode ---
    if isinstance(p, WhenThenNode):
        if not isinstance(q, WhenThenNode):
            return False
        return (_match_node(q.when, p.when, memo, mode, mapping) and
                _match_node(q.then, p.then, memo, mode, mapping))

    # --- CaseNode ---
    if isinstance(p, CaseNode):
        if not isinstance(q, CaseNode):
            return False
        if len(q.whens) != len(p.whens):
            return False
        for qw, pw in zip(q.whens, p.whens):
            if not _match_node(qw, pw, memo, mode, mapping):
                return False
        if p.else_val is not None:
            if q.else_val is None:
                return False
            return _match_node(q.else_val, p.else_val, memo, mode, mapping)
        return True

    # --- QueryNode ---
    if isinstance(p, QueryNode):
        if not isinstance(q, QueryNode):
            return False
        return _match_query_node(q, p, memo, mode, mapping)

    # --- CompoundQueryNode ---
    if isinstance(p, CompoundQueryNode):
        if not isinstance(q, CompoundQueryNode):
            return False
        if q.is_all != p.is_all:
            return False
        return (_match_node(q.left, p.left, memo, mode, mapping) and
                _match_node(q.right, p.right, memo, mode, mapping))

    return False


def _match_and_or(
    q: OperatorNode, p: OperatorNode, op_name: str,
    memo: dict, mode: MatchingMode, mapping: dict
) -> bool:
    """Flatten both q and p into lists, do unordered matching, store remaining."""
    q_flat = _flatten_logical(q, op_name)
    p_flat = _flatten_logical(p, op_name)

    remaining = _match_logical_list_unordered(q_flat, p_flat, memo, mode, mapping)
    if remaining is None:
        return False

    if remaining:
        if mode == MatchingMode.FULL_ONLY:
            return False
        memo["_partial_op"] = op_name
        memo["_partial_remaining"] = remaining
    return True


def _partial_match_in_logical(
    q: OperatorNode, p: Node, op_name: str,
    memo: dict, mode: MatchingMode, mapping: dict
) -> bool:
    """When query is AND/OR and pattern is a different kind of node (ALLOW_PARTIAL).

    Try to match p against each flattened element of q; store the rest as remaining.
    Preserves the original position of the matched element so replace() can
    reconstruct the clause list in the same order.
    """
    q_flat = _flatten_logical(q, op_name)

    for i, qe in enumerate(q_flat):
        with _memo_snapshot(memo) as commit:
            if _match_node(qe, p, memo, MatchingMode.IN_PARTIAL, mapping):
                remaining = q_flat[:i] + q_flat[i + 1:]
                if remaining:
                    memo["_partial_op"] = op_name
                    memo["_partial_remaining"] = remaining
                    memo["_partial_matched_idx"] = i
                    memo["_partial_flat_list"] = q_flat
                commit()
                return True
    return False


def _match_logical_list_unordered(
    q_flat: List[Node], p_flat: List[Node],
    memo: dict, mode: MatchingMode, mapping: dict
) -> Optional[List[Node]]:
    """Match all pattern elements against query elements (unordered, like old match_list).

    Returns list of unmatched query elements on success, None on failure.
    SetVariableNode in pattern absorbs remaining after fixed elements are matched.
    """
    sv_in_p = [x for x in p_flat if isinstance(x, SetVariableNode)]
    fixed_in_p = [x for x in p_flat if not isinstance(x, SetVariableNode)]

    if sv_in_p:
        # Match fixed elements first (unordered)
        remaining_q = list(q_flat)
        for fp in fixed_in_p:
            found_idx = None
            for i, qe in enumerate(remaining_q):
                with _memo_snapshot(memo) as commit:
                    if _match_node(qe, fp, memo, MatchingMode.IN_PARTIAL, mapping):
                        found_idx = i
                        commit()
                        break
            if found_idx is None:
                return None
            remaining_q.pop(found_idx)
        # SVs absorb all remaining
        if len(sv_in_p) == 1:
            _bind(sv_in_p[0].name, remaining_q, memo)
        else:
            _bind(sv_in_p[0].name, remaining_q, memo)
            for sv in sv_in_p[1:]:
                _bind(sv.name, [], memo)
        return []  # SVs absorbed everything

    # No SVs: exact unordered match (combinatorial backtracking)
    def _try_match(remaining_q: List[Node], remaining_p: List[Node]) -> Optional[List[Node]]:
        if not remaining_p:
            return remaining_q  # unmatched q elements
        fp = remaining_p[0]
        rest_p = remaining_p[1:]
        for i, qe in enumerate(remaining_q):
            with _memo_snapshot(memo) as commit:
                if _match_node(qe, fp, memo, MatchingMode.IN_PARTIAL, mapping):
                    rest_q = remaining_q[:i] + remaining_q[i + 1:]
                    result = _try_match(rest_q, rest_p)
                    if result is not None:
                        commit()
                        return result
        return None

    return _try_match(list(q_flat), p_flat)


def _match_query_node(
    q: QueryNode, p: QueryNode, memo: dict, mode: MatchingMode, mapping: dict
) -> bool:
    """Match clause-by-clause; extra query clauses are stored in memo['_extra_clauses']."""
    extra_clauses: List[Node] = []
    for ct in _CLAUSE_TYPES:
        p_clause = _get_clause(p, ct)
        q_clause = _get_clause(q, ct)
        if p_clause is None:
            if q_clause is not None:
                extra_clauses.append(q_clause)
            continue
        if q_clause is None:
            return False
        if not _match_node(q_clause, p_clause, memo, mode, mapping):
            return False
    if extra_clauses:
        memo["_extra_clauses"] = extra_clauses
    return True


def _match_children_list(
    q_list: List[Node], p_list: List[Node],
    memo: dict, mode: MatchingMode, mapping: dict
) -> bool:
    """Match a query list against a pattern list; SetVariableNode absorbs sub-lists."""
    if not p_list and not q_list:
        return True
    if not p_list:
        return False

    sv_indices = [i for i, x in enumerate(p_list) if isinstance(x, SetVariableNode)]

    if not sv_indices:
        # Exact ordered match required
        if len(q_list) != len(p_list):
            return False
        for qi, pi in zip(q_list, p_list):
            if not _match_node(qi, pi, memo, mode, mapping):
                return False
        return True

    if len(sv_indices) == 1 and len(p_list) == 1:
        # Single SV absorbs the whole list
        return _bind(p_list[0].name, q_list, memo)

    # General case: SVs act as wildcards absorbing contiguous slices
    sv_idx = sv_indices[0]
    sv_node = p_list[sv_idx]
    before = p_list[:sv_idx]
    after = p_list[sv_idx + 1:]

    n_before = len(before)
    n_after = len(after)
    if len(q_list) < n_before + n_after:
        return False

    snap = {k: v for k, v in memo.items()}

    # Match prefix
    for i, pi in enumerate(before):
        if not _match_node(q_list[i], pi, memo, mode, mapping):
            for k in list(memo.keys()):
                if k not in snap:
                    del memo[k]
            memo.update(snap)
            return False

    # Match suffix from the end
    q_tail = q_list[n_before:]
    if after:
        for j, pi in enumerate(after):
            q_idx = len(q_tail) - n_after + j
            if q_idx < 0 or not _match_node(q_tail[q_idx], pi, memo, mode, mapping):
                for k in list(memo.keys()):
                    if k not in snap:
                        del memo[k]
                memo.update(snap)
                return False
        sv_absorbed = q_tail[:len(q_tail) - n_after]
    else:
        sv_absorbed = q_tail

    if not _bind(sv_node.name, sv_absorbed, memo):
        for k in list(memo.keys()):
            if k not in snap:
                del memo[k]
        memo.update(snap)
        return False

    return True


# ============================================================================
# Substitute variables into rewrite AST
# ============================================================================

def _subst(node: Node, memo: dict) -> Node:
    """Replace ElementVariableNode / SetVariableNode with memo bindings in a node."""

    def _materialize_element_binding(val: Any) -> Optional[Node]:
        """Convert an element-variable binding into a concrete AST node.

        Rules:
        - If bound to a Node, return it (but strip `.alias` to avoid leaking output aliases
          unless the rewrite explicitly carries them).
        - If bound to scalar identifiers, materialize as ColumnNode/LiteralNode so the
          formatter can emit SQL.
        """
        if isinstance(val, Node):
            if hasattr(val, "alias") and getattr(val, "alias") is not None:
                cloned = copy.deepcopy(val)
                setattr(cloned, "alias", None)
                return cloned
            return val
        if isinstance(val, str):
            return ColumnNode(val)
        if isinstance(val, (int, float, bool)) or val is None:
            return LiteralNode(val)
        # Fallback: caller will keep the variable node unchanged.
        return None

    if isinstance(node, ElementVariableNode):
        val = memo.get(node.name, node)
        materialized = _materialize_element_binding(val)
        if materialized is not None:
            return materialized
        return node

    if isinstance(node, SetVariableNode):
        # Should not appear at this level; caller handles list expansion
        return node

    if isinstance(node, (LiteralNode, DataTypeNode, TimeUnitNode)):
        # For string literals, substitute any variable names embedded in the value
        # (e.g. LiteralNode('%y%') with memo['y']=LiteralNode('iphone') to LiteralNode('%iphone%'))
        if isinstance(node, LiteralNode) and isinstance(node.value, str):
            new_val = node.value
            for var_name, bound in memo.items():
                if not isinstance(var_name, str) or var_name.startswith("_"):
                    continue
                if var_name not in new_val:
                    continue
                if isinstance(bound, LiteralNode) and isinstance(bound.value, (str, int, float)):
                    new_val = re.sub(r"\b" + re.escape(var_name) + r"\b", str(bound.value), new_val)
                elif isinstance(bound, str):
                    new_val = re.sub(r"\b" + re.escape(var_name) + r"\b", bound, new_val)
            if new_val != node.value:
                return LiteralNode(new_val)
        return node

    if isinstance(node, TableNode):
        # If the name variable is bound to a whole TableNode, return it directly
        if isinstance(node.name, str) and node.name in memo:
            val = memo[node.name]
            if isinstance(val, TableNode):
                return val
        new_name = _subst_str(node.name, memo)
        new_alias = _subst_str(node.alias, memo) if node.alias is not None else None
        return TableNode(new_name, new_alias)

    if isinstance(node, ColumnNode):
        new_name = _subst_str(node.name, memo)
        new_alias = _subst_str(node.alias, memo) if node.alias is not None else None
        new_pa = _subst_str(node.parent_alias, memo) if node.parent_alias is not None else None
        return ColumnNode(new_name, _alias=new_alias, _parent_alias=new_pa)

    if isinstance(node, FunctionNode):
        new_args = _subst_list(list(node.children), memo)
        new_alias = _subst_str(node.alias, memo) if node.alias is not None else None
        return FunctionNode(node.name, new_args, _alias=new_alias)

    if isinstance(node, UnaryOperatorNode):
        inner = list(node.children)[0]
        return UnaryOperatorNode(_subst(inner, memo), node.name)

    if isinstance(node, OperatorNode):
        ch = list(node.children)
        op = node.name.upper()
        if op in ("AND", "OR"):
            # Flatten, expand SVs, rebuild
            flat = _flatten_logical(node, op)
            expanded = _subst_list(flat, memo)
            return _unflatten_logical(expanded, op)
        left = _subst(ch[0], memo)
        right = _subst(ch[1], memo) if len(ch) > 1 else None
        if right is None:
            return OperatorNode(left, node.name)
        return OperatorNode(left, node.name, right)

    if isinstance(node, ListNode):
        return ListNode(_subst_list(list(node.children), memo))

    if isinstance(node, IntervalNode):
        if isinstance(node.value, Node):
            return IntervalNode(_subst(node.value, memo), node.unit)
        return IntervalNode(node.value, node.unit)

    if isinstance(node, SelectNode):
        items_raw = [c for c in list(node.children)
                     if node.distinct_on is None or c is not node.distinct_on]
        items = _subst_list(items_raw, memo)
        new_don = _subst(node.distinct_on, memo) if node.distinct_on is not None else None
        return SelectNode(items, _distinct=node.distinct, _distinct_on=new_don)

    if isinstance(node, (FromNode, WhereNode, GroupByNode, HavingNode, OrderByNode)):
        return type(node)(_subst_list(list(node.children), memo))

    if isinstance(node, OrderByItemNode):
        inner = list(node.children)[0]
        return OrderByItemNode(_subst(inner, memo), node.sort)

    if isinstance(node, LimitNode):
        val = node.limit
        if isinstance(val, str):
            val = memo.get(val, val)
        if isinstance(val, LiteralNode):
            val = val.value
        return LimitNode(val)

    if isinstance(node, OffsetNode):
        val = node.offset
        if isinstance(val, str):
            val = memo.get(val, val)
        if isinstance(val, LiteralNode):
            val = val.value
        return OffsetNode(val)

    if isinstance(node, JoinNode):
        ch = list(node.children)
        left = _subst(ch[0], memo)
        right = _subst(ch[1], memo)
        on = _subst(ch[2], memo) if len(ch) > 2 else None
        return JoinNode(left, right, node.join_type, on)

    if isinstance(node, SubqueryNode):
        inner = list(node.children)[0]
        new_alias = _subst_str(node.alias, memo) if node.alias is not None else None
        return SubqueryNode(_subst(inner, memo), new_alias)

    if isinstance(node, WhenThenNode):
        return WhenThenNode(_subst(node.when, memo), _subst(node.then, memo))

    if isinstance(node, CaseNode):
        new_whens = [WhenThenNode(_subst(wt.when, memo), _subst(wt.then, memo))
                     for wt in node.whens]
        new_else = _subst(node.else_val, memo) if node.else_val is not None else None
        return CaseNode(new_whens, new_else)

    if isinstance(node, QueryNode):
        return QueryNode(
            _select=_subst(_get_clause(node, NodeType.SELECT), memo) if _get_clause(node, NodeType.SELECT) else None,
            _from=_subst(_get_clause(node, NodeType.FROM), memo) if _get_clause(node, NodeType.FROM) else None,
            _where=_subst(_get_clause(node, NodeType.WHERE), memo) if _get_clause(node, NodeType.WHERE) else None,
            _group_by=_subst(_get_clause(node, NodeType.GROUP_BY), memo) if _get_clause(node, NodeType.GROUP_BY) else None,
            _having=_subst(_get_clause(node, NodeType.HAVING), memo) if _get_clause(node, NodeType.HAVING) else None,
            _order_by=_subst(_get_clause(node, NodeType.ORDER_BY), memo) if _get_clause(node, NodeType.ORDER_BY) else None,
            _limit=_subst(_get_clause(node, NodeType.LIMIT), memo) if _get_clause(node, NodeType.LIMIT) else None,
            _offset=_subst(_get_clause(node, NodeType.OFFSET), memo) if _get_clause(node, NodeType.OFFSET) else None,
        )

    if isinstance(node, CompoundQueryNode):
        return CompoundQueryNode(_subst(node.left, memo), _subst(node.right, memo), node.is_all)

    return node


def _subst_str(s: Any, memo: dict) -> Any:
    """Substitute a string field if it matches a variable name in memo.

    Extracts a canonical string from the bound value:
    - str  to return directly
    - TableNode to alias or name (used for parent_alias fields like 'tb1' to 'employee')
    - ColumnNode to name (used for name fields like 'a1' to 'workdept')
    """
    if isinstance(s, str) and s in memo:
        val = memo[s]
        if isinstance(val, str):
            return val
        if isinstance(val, TableNode):
            return val.alias if val.alias is not None else val.name
        if isinstance(val, ColumnNode):
            return val.name
        if isinstance(val, FunctionNode):
            ch = list(val.children)
            if len(ch) == 1 and isinstance(ch[0], ColumnNode):
                return ch[0].name
    return s


def _subst_list(items: List[Node], memo: dict) -> List[Node]:
    """Substitute a list of nodes, expanding SetVariableNode into their bound lists."""
    result: List[Node] = []
    for item in items:
        if isinstance(item, SetVariableNode):
            val = memo.get(item.name, [])
            if isinstance(val, list):
                result.extend(val)
            elif isinstance(val, Node):
                result.append(val)
        elif isinstance(item, ElementVariableNode):
            val = memo.get(item.name, item)
            if isinstance(val, list):
                result.extend(val)
            else:
                materialized = _subst(item, memo)
                # _subst(ElementVariableNode) returns either a Node or the original variable node
                if isinstance(materialized, ElementVariableNode):
                    result.append(materialized)
                else:
                    result.append(materialized)
        else:
            result.append(_subst(item, memo))
    return result


# ============================================================================
# Replace a specific node in the query tree (identity-based)
# ============================================================================

def _replace_in_tree(tree: Node, target_id: int, replacement: Node) -> Node:
    """Walk the tree; when id(node) == target_id return replacement; else rebuild."""
    if id(tree) == target_id:
        return replacement

    if isinstance(tree, (LiteralNode, DataTypeNode, TimeUnitNode, TableNode, ColumnNode,
                         ElementVariableNode, SetVariableNode)):
        return tree

    if isinstance(tree, FunctionNode):
        new_args = [_replace_in_tree(c, target_id, replacement) for c in list(tree.children)]
        return FunctionNode(tree.name, new_args, _alias=tree.alias)

    if isinstance(tree, UnaryOperatorNode):
        inner = list(tree.children)[0]
        return UnaryOperatorNode(_replace_in_tree(inner, target_id, replacement), tree.name)

    if isinstance(tree, OperatorNode):
        ch = list(tree.children)
        new_ch = [_replace_in_tree(c, target_id, replacement) for c in ch]
        if len(new_ch) == 1:
            return OperatorNode(new_ch[0], tree.name)
        return OperatorNode(new_ch[0], tree.name, new_ch[1])

    if isinstance(tree, ListNode):
        return ListNode([_replace_in_tree(c, target_id, replacement) for c in list(tree.children)])

    if isinstance(tree, IntervalNode):
        if isinstance(tree.value, Node):
            return IntervalNode(_replace_in_tree(tree.value, target_id, replacement), tree.unit)
        return IntervalNode(tree.value, tree.unit)

    if isinstance(tree, SelectNode):
        items = [c for c in list(tree.children)
                 if tree.distinct_on is None or c is not tree.distinct_on]
        new_items = [_replace_in_tree(c, target_id, replacement) for c in items]
        new_don = (_replace_in_tree(tree.distinct_on, target_id, replacement)
                   if tree.distinct_on is not None else None)
        return SelectNode(new_items, _distinct=tree.distinct, _distinct_on=new_don)

    if isinstance(tree, (FromNode, WhereNode, GroupByNode, HavingNode, OrderByNode)):
        return type(tree)([_replace_in_tree(c, target_id, replacement) for c in list(tree.children)])

    if isinstance(tree, OrderByItemNode):
        inner = list(tree.children)[0]
        return OrderByItemNode(_replace_in_tree(inner, target_id, replacement), tree.sort)

    if isinstance(tree, (LimitNode, OffsetNode)):
        return tree

    if isinstance(tree, JoinNode):
        ch = list(tree.children)
        new_left = _replace_in_tree(ch[0], target_id, replacement)
        new_right = _replace_in_tree(ch[1], target_id, replacement)
        new_on = _replace_in_tree(ch[2], target_id, replacement) if len(ch) > 2 else None
        return JoinNode(new_left, new_right, tree.join_type, new_on)

    if isinstance(tree, SubqueryNode):
        inner = list(tree.children)[0]
        return SubqueryNode(_replace_in_tree(inner, target_id, replacement), tree.alias)

    if isinstance(tree, WhenThenNode):
        return WhenThenNode(
            _replace_in_tree(tree.when, target_id, replacement),
            _replace_in_tree(tree.then, target_id, replacement),
        )

    if isinstance(tree, CaseNode):
        new_whens = [WhenThenNode(
            _replace_in_tree(wt.when, target_id, replacement),
            _replace_in_tree(wt.then, target_id, replacement),
        ) for wt in tree.whens]
        new_else = (_replace_in_tree(tree.else_val, target_id, replacement)
                    if tree.else_val is not None else None)
        return CaseNode(new_whens, new_else)

    if isinstance(tree, QueryNode):
        def _rc(ct: NodeType) -> Optional[Node]:
            c = _get_clause(tree, ct)
            return _replace_in_tree(c, target_id, replacement) if c is not None else None
        return QueryNode(
            _select=_rc(NodeType.SELECT),
            _from=_rc(NodeType.FROM),
            _where=_rc(NodeType.WHERE),
            _group_by=_rc(NodeType.GROUP_BY),
            _having=_rc(NodeType.HAVING),
            _order_by=_rc(NodeType.ORDER_BY),
            _limit=_rc(NodeType.LIMIT),
            _offset=_rc(NodeType.OFFSET),
        )

    if isinstance(tree, CompoundQueryNode):
        return CompoundQueryNode(
            _replace_in_tree(tree.left, target_id, replacement),
            _replace_in_tree(tree.right, target_id, replacement),
            tree.is_all,
        )

    return tree


# ============================================================================
# Node-level substitution for SUBSTITUTE actions
# ============================================================================

def _node_subst(tree: Any, src: Any, tgt: Any) -> Any:
    """Replace occurrences of src value with tgt value throughout tree.

    src / tgt are typically strings (table alias / column name) from the memo,
    but may also be Nodes when the variable was bound to a whole node.
    """
    if isinstance(tree, list):
        return [_node_subst(item, src, tgt) for item in tree]

    if not isinstance(tree, Node):
        return tree

    if isinstance(tree, ColumnNode):
        new_pa = _subst_val(tree.parent_alias, src, tgt)
        new_name = _subst_val(tree.name, src, tgt)
        return ColumnNode(new_name, _alias=tree.alias, _parent_alias=new_pa)

    if isinstance(tree, TableNode):
        return TableNode(_subst_val(tree.name, src, tgt), _subst_val(tree.alias, src, tgt))

    if isinstance(tree, (LiteralNode, DataTypeNode, TimeUnitNode)):
        return tree

    if isinstance(tree, FunctionNode):
        new_args = [_node_subst(c, src, tgt) for c in list(tree.children)]
        return FunctionNode(tree.name, new_args, _alias=tree.alias)

    if isinstance(tree, UnaryOperatorNode):
        inner = list(tree.children)[0]
        return UnaryOperatorNode(_node_subst(inner, src, tgt), tree.name)

    if isinstance(tree, OperatorNode):
        ch = list(tree.children)
        new_ch = [_node_subst(c, src, tgt) for c in ch]
        if len(new_ch) == 1:
            return OperatorNode(new_ch[0], tree.name)
        return OperatorNode(new_ch[0], tree.name, new_ch[1])

    if isinstance(tree, ListNode):
        return ListNode([_node_subst(c, src, tgt) for c in list(tree.children)])

    if isinstance(tree, SelectNode):
        items = [c for c in list(tree.children)
                 if tree.distinct_on is None or c is not tree.distinct_on]
        new_items = [_node_subst(c, src, tgt) for c in items]
        new_don = _node_subst(tree.distinct_on, src, tgt) if tree.distinct_on else None
        return SelectNode(new_items, _distinct=tree.distinct, _distinct_on=new_don)

    if isinstance(tree, (FromNode, WhereNode)):
        return type(tree)([_node_subst(c, src, tgt) for c in list(tree.children)])

    if isinstance(tree, JoinNode):
        ch = list(tree.children)
        new_left = _node_subst(ch[0], src, tgt)
        new_right = _node_subst(ch[1], src, tgt)
        new_on = _node_subst(ch[2], src, tgt) if len(ch) > 2 else None
        return JoinNode(new_left, new_right, tree.join_type, new_on)

    if isinstance(tree, SubqueryNode):
        inner = list(tree.children)[0]
        return SubqueryNode(_node_subst(inner, src, tgt), tree.alias)

    if isinstance(tree, QueryNode):
        def _rc(ct: NodeType) -> Optional[Node]:
            c = _get_clause(tree, ct)
            return _node_subst(c, src, tgt) if c is not None else None
        return QueryNode(
            _select=_rc(NodeType.SELECT),
            _from=_rc(NodeType.FROM),
            _where=_rc(NodeType.WHERE),
            _group_by=_rc(NodeType.GROUP_BY),
            _having=_rc(NodeType.HAVING),
            _order_by=_rc(NodeType.ORDER_BY),
            _limit=_rc(NodeType.LIMIT),
            _offset=_rc(NodeType.OFFSET),
        )

    return tree


def _subst_val(field: Any, src: Any, tgt: Any) -> Any:
    if field is None:
        return field
    # String alias substitution (both src and tgt are plain strings)
    if isinstance(field, str) and isinstance(src, str) and field == src:
        return tgt if isinstance(tgt, str) else field
    # TableNode src: compare field string against table alias (or name)
    if isinstance(field, str) and isinstance(src, TableNode):
        src_id = src.alias if src.alias is not None else src.name
        if field == src_id:
            if isinstance(tgt, TableNode):
                return tgt.alias if tgt.alias is not None else tgt.name
            return tgt if isinstance(tgt, str) else field
    # Node equality substitution
    if isinstance(field, Node) and isinstance(src, Node) and field == src:
        return tgt
    return field


def _rule_key(rule: dict) -> Any:
    """Stable id for skipping a rule within one rewrite round."""
    k = rule.get("key")
    if k is not None:
        return k
    return rule.get("id")


def _pick_applicable_rule(
    query_ast: Node, rules: list, excluded: set,
) -> Tuple[Optional[dict], dict]:
    """First full root match, else first partial match; skip guardrailed rules.

    Rules listed in ``excluded`` (by :func:`_rule_key`) are not returned. When
    :func:`_should_skip_partial_and_application` applies, the rule key is added to
    ``excluded`` and the search continues.
    """
    for rule in rules:
        rk = _rule_key(rule)
        if rk in excluded:
            continue
        memo: dict = {}
        if (QueryRewriterV2.match(query_ast, rule, memo, MatchingMode.FULL_ONLY)
                and memo.get("_rule_node") is query_ast):
            if _should_skip_partial_and_application(rule, memo):
                excluded.add(rk)
                continue
            return rule, memo

    for rule in rules:
        rk = _rule_key(rule)
        if rk in excluded:
            continue
        memo = {}
        if QueryRewriterV2.match(query_ast, rule, memo, MatchingMode.ALLOW_PARTIAL):
            if _should_skip_partial_and_application(rule, memo):
                excluded.add(rk)
                continue
            return rule, memo

    return None, {}


# ============================================================================
# Public QueryRewriterV2 class
# ============================================================================

class QueryRewriterV2:

    @staticmethod
    def reformat(query: str) -> str:
        """Round-trip through parser + formatter for canonical form."""
        return QueryFormatter().format(QueryParser().parse(query))

    @staticmethod
    def beautify(query: str) -> str:
        return sqlparse.format(query, reindent=True)

    @staticmethod
    def rewrite(query: str, rules: list, iterate: bool = True) -> Tuple[str, list]:
        """Rewrite query using rules iteratively.

        Each rule dict must be produced by data.rules.get_rule_v2().
        Returns (final_sql, rewriting_path) where rewriting_path is a list of
        [rule_id, formatted_sql] pairs.
        """
        formatter = QueryFormatter()
        parser = QueryParser()

        query_ast = parser.parse(query)
        rewriting_path: list = []

        # Cycle detection: track canonical SQL strings seen so far
        query_trace: set[str] = set()
        cycle_found = False

        new_query = True
        while new_query:
            new_query = False

            formatted = formatter.format(query_ast)
            if formatted in query_trace:
                cycle_found = True
            else:
                query_trace.add(formatted)

            # Pick and apply at most one rule per outer iteration. Skip guardrailed
            # partial-AND matches and retry with the next rule; on apply failure, exclude
            # that rule and try another (same query_ast) instead of ending the round.
            excluded: set = set()
            while True:
                rule_applied, memo_applied = _pick_applicable_rule(query_ast, rules, excluded)
                if rule_applied is None:
                    break
                try:
                    query_ast = QueryRewriterV2.take_actions(
                        query_ast, rule_applied, memo_applied
                    )
                    query_ast = QueryRewriterV2.replace(
                        query_ast, rule_applied, memo_applied
                    )
                    new_formatted = formatter.format(query_ast)
                    rewriting_path.append([rule_applied["id"], new_formatted])
                    # Re-parse to normalise (mirrors old parse(format(...)))
                    query_ast = parser.parse(new_formatted)
                    if not cycle_found and iterate:
                        new_query = True
                    break
                except Exception as exc:
                    logger.warning(
                        "Failed to rewrite with rule %s: %s",
                        rule_applied.get("key", rule_applied.get("id")),
                        exc,
                        exc_info=True,
                    )
                    excluded.add(_rule_key(rule_applied))

        return formatter.format(query_ast), rewriting_path

    @staticmethod
    def match(
        query_ast: Node, rule: dict, memo: dict,
        matching_mode: MatchingMode = MatchingMode.FULL_ONLY,
    ) -> bool:
        """BFS over query_ast; try match_node at each position against rule pattern.

        On success sets memo['_rule_node'] = matched node and returns True.
        """
        pattern = rule["pattern_ast"]
        mapping = rule["mapping"]

        queue: deque[Node] = deque([query_ast])
        while queue:
            curr = queue.popleft()
            attempt_memo: dict = {}
            if _match_node(curr, pattern, attempt_memo, matching_mode, mapping):
                if "_rule_node" not in attempt_memo:
                    attempt_memo["_rule_node"] = curr
                memo.clear()
                memo.update(attempt_memo)
                return True

            # Add children to BFS queue
            if isinstance(curr, CompoundQueryNode):
                queue.append(curr.left)
                queue.append(curr.right)
            elif hasattr(curr, "children"):
                for child in list(curr.children):
                    if isinstance(child, Node):
                        queue.append(child)

        return False

    @staticmethod
    def match_node(
        query_node: Node, pattern_node: Node, rule: dict, memo: dict,
        matching_mode: MatchingMode = MatchingMode.FULL_ONLY,
    ) -> bool:
        """Public wrapper around _match_node."""
        return _match_node(query_node, pattern_node, memo, matching_mode, rule["mapping"])

    @staticmethod
    def replace(query_ast: Node, rule: dict, memo: dict) -> Node:
        """Build the rewritten AST: substitute vars into rewrite_ast, then graft
        in place of the matched node.  Partial-match remaining elements are
        wrapped back into the appropriate AND/OR tree.
        """
        # Build the replacement by substituting memo bindings into rewrite AST
        rewrite = _subst(rule["rewrite_ast"], memo)

        # Carry extra query clauses (present in query but not in pattern) into rewrite
        if "_extra_clauses" in memo and isinstance(rewrite, QueryNode):
            rewrite = _merge_extra_clauses(rewrite, memo["_extra_clauses"])

        # Wrap with partial remaining if needed, preserving original clause order
        if "_partial_remaining" in memo and memo["_partial_remaining"]:
            op = memo["_partial_op"]
            remaining = memo["_partial_remaining"]

            if isinstance(rewrite, QueryNode):
                # When rewrite is a full QueryNode, merge remaining predicates into its WHERE
                # clause rather than wrapping the QueryNode in an AND/OR operator.
                where_node = _get_clause(rewrite, NodeType.WHERE)
                if where_node is not None:
                    where_items = list(where_node.children)
                    # Flatten the existing WHERE if it's already the same logical op
                    if (len(where_items) == 1 and isinstance(where_items[0], OperatorNode)
                            and where_items[0].name == op):
                        existing_flat = _flatten_logical(where_items[0], op)
                    else:
                        existing_flat = where_items
                    all_conditions = existing_flat + remaining
                    new_where = WhereNode([_unflatten_logical(all_conditions, op)])
                else:
                    new_where = WhereNode([_unflatten_logical(remaining, op)])
                rewrite = QueryNode(
                    _select=_get_clause(rewrite, NodeType.SELECT),
                    _from=_get_clause(rewrite, NodeType.FROM),
                    _where=new_where,
                    _group_by=_get_clause(rewrite, NodeType.GROUP_BY),
                    _having=_get_clause(rewrite, NodeType.HAVING),
                    _order_by=_get_clause(rewrite, NodeType.ORDER_BY),
                    _limit=_get_clause(rewrite, NodeType.LIMIT),
                    _offset=_get_clause(rewrite, NodeType.OFFSET),
                )
            else:
                flat_list = memo.get("_partial_flat_list")
                matched_idx = memo.get("_partial_matched_idx")
                if flat_list is not None and matched_idx is not None:
                    # Reconstruct flat list with the rewrite substituted in-place
                    new_flat = list(flat_list)
                    new_flat[matched_idx] = rewrite
                    rewrite = _unflatten_logical(new_flat, op)
                else:
                    rewrite = _unflatten_logical([rewrite] + remaining, op)

        # Graft rewrite in place of the matched node
        rule_node = memo.get("_rule_node")
        if rule_node is None:
            return rewrite

        if id(rule_node) == id(query_ast):
            return rewrite

        return _replace_in_tree(query_ast, id(rule_node), rewrite)

    @staticmethod
    def take_actions(query_ast: Node, rule: dict, memo: dict) -> Node:
        """Execute rule actions against memo bindings.

        Currently supports 'substitute' only:
            SUBSTITUTE(scope, source, target)  =>
                memo[scope] = node_subst(memo[scope], memo[source], memo[target])
        """
        def _resolve_action_var(name: Any) -> Any:
            """Resolve action variable names to memo keys.

            v2 rule AST uses internal variable tokens (EV###/SV###) as node names,
            so match() binds those internal names in memo.
            Actions are parsed from the original rule text and may refer to
            external variable names (x1/y1/etc).  Use rule['mapping'] to map
            external -> internal when needed.
            """
            if not isinstance(name, str):
                return name
            if name in memo:
                return name
            mapping = rule.get("mapping") or {}
            internal = mapping.get(name)
            if isinstance(internal, str) and internal in memo:
                return internal
            return name

        for action in rule.get("actions_json", []):
            func = action.get("function", "").strip().lower()
            if func == "substitute":
                variables = action.get("variables", [])
                if len(variables) == 3:
                    scope_name, src_name, tgt_name = variables
                    scope_key = _resolve_action_var(scope_name)
                    src_key = _resolve_action_var(src_name)
                    tgt_key = _resolve_action_var(tgt_name)
                    if scope_key in memo and src_key in memo and tgt_key in memo:
                        src_val = memo[src_key]
                        tgt_val = memo[tgt_key]
                        memo[scope_key] = _node_subst(memo[scope_key], src_val, tgt_val)
        return query_ast

    @staticmethod
    def substitute(tree: Any, source: Any, target: Any) -> Any:
        """Public wrapper for structural substitution (used by tests)."""
        return _node_subst(tree, source, target)


# ============================================================================
# Helper: merge extra query clauses into a rewritten QueryNode
# ============================================================================

def _merge_extra_clauses(rewrite: QueryNode, extra: List[Node]) -> QueryNode:
    """Add clauses from 'extra' to the rewrite QueryNode if not already present."""
    existing_types = {c.type for c in rewrite.children}
    kwargs: Dict[str, Optional[Node]] = {}
    for ct in _CLAUSE_TYPES:
        c = _get_clause(rewrite, ct)
        kwargs[ct.name.lower()] = c
    for extra_clause in extra:
        key = extra_clause.type.name.lower()
        if extra_clause.type not in existing_types:
            kwargs[key] = extra_clause
    return QueryNode(
        _select=kwargs.get("select"),
        _from=kwargs.get("from"),
        _where=kwargs.get("where"),
        _group_by=kwargs.get("group_by"),
        _having=kwargs.get("having"),
        _order_by=kwargs.get("order_by"),
        _limit=kwargs.get("limit"),
        _offset=kwargs.get("offset"),
    )


def _should_skip_partial_and_application(rule: dict, memo: dict) -> bool:
    """Heuristic guardrail for partial AND matches.

    If we matched only one element inside an AND (memo['_partial_op'] == 'AND') and
    the rule's rewrite expands the FROM clause with JOINs, applying it as a partial
    match is often order-dependent and can disrupt subsequent, more structurally
    suitable rules.
    """
    if memo.get("_partial_op") != "AND":
        return False

    pattern_ast = rule.get("pattern_ast")
    rewrite_ast = rule.get("rewrite_ast")
    if not isinstance(pattern_ast, QueryNode) or not isinstance(rewrite_ast, QueryNode):
        return False

    # Only guard rules that introduce JOIN structure.
    from_clause = _get_clause(rewrite_ast, NodeType.FROM)
    if not isinstance(from_clause, FromNode):
        return False
    introduces_join = any(isinstance(c, JoinNode) for c in list(from_clause.children))
    if not introduces_join:
        return False

    # If the pattern's WHERE is not explicitly an AND/OR shape, it likely represents
    # a single predicate intended to be rewritten as a whole clause or OR-branch.
    where_clause = _get_clause(pattern_ast, NodeType.WHERE)
    if not isinstance(where_clause, WhereNode) or len(list(where_clause.children)) != 1:
        return False
    only_pred = list(where_clause.children)[0]
    if isinstance(only_pred, OperatorNode) and only_pred.name.upper() in ("AND", "OR"):
        return False

    return True
