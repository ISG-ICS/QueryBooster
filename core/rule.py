from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from core.ast.node import Node


@dataclass
class RuleV2:
    pattern: str
    rewrite: str
    pattern_ast: Node
    rewrite_ast: Node
    mapping: Dict[str, str]
    source_pattern_ast: Optional[Node] = None
    source_rewrite_ast: Optional[Node] = None
    source_pattern_sql: str = ""
    source_rewrite_sql: str = ""
    constraints: str = ""
    actions: str = ""
    id: Optional[Any] = None
    key: Optional[str] = None
    children: Optional[List[RuleV2]] = field(default=None)

    @classmethod
    def from_dict(cls, d: dict) -> RuleV2:
        return cls(
            pattern=d.get("pattern", ""),
            rewrite=d.get("rewrite", ""),
            pattern_ast=d["pattern_ast"],
            rewrite_ast=d["rewrite_ast"],
            mapping=d.get("mapping", {}),
            source_pattern_ast=d.get("source_pattern_ast"),
            source_rewrite_ast=d.get("source_rewrite_ast"),
            source_pattern_sql=d.get("source_pattern_sql", ""),
            source_rewrite_sql=d.get("source_rewrite_sql", ""),
            constraints=d.get("constraints", ""),
            actions=d.get("actions", ""),
            id=d.get("id"),
            key=d.get("key"),
            children=d.get("children"),
        )

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)
