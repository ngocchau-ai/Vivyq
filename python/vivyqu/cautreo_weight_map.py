"""Cautreo Weight Map — Tree Index for hierarchical weight lookup (TD-3, TD-7).

Persistent weight registry with hierarchical tree structure for O(log n)
lookup. Maps model capabilities to weight slices across multiple model cores.

Structure:
    WeightMap
    ├── tree_index: dict[node_id -> WeightNode]
    │   ├── node_id, parent_id, children
    │   ├── model_alias, layer_range, capability_tags
    │   └── score: float (0-1 effectiveness)
    ├── insert(node) — add to tree
    ├── lookup(query) -> list[WeightNode] — hierarchical search
    └── by_capability(task) -> list[WeightNode] — capability → weights

Tree map = cấu trúc truy vấn (tốc độ). Session log = dữ liệu thời gian (audit).
Together they form the Cautreo memory layer.

Changelog:
    25/09/2026 (Claude Code — Wave 1A): Initial.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WeightNode:
    """One node in the weight map tree."""

    node_id: str
    model_alias: str
    layer_range: tuple[int, int] = (0, 0)
    capability_tags: tuple[str, ...] = ()
    score: float = 0.5
    parent_id: str = ""
    children: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "model_alias": self.model_alias,
            "layer_range": list(self.layer_range),
            "capability_tags": list(self.capability_tags),
            "score": self.score,
            "parent_id": self.parent_id,
            "children": list(self.children),
            "metadata": dict(self.metadata),
        }


class WeightMap:
    """Tree-indexed weight map for fast hierarchical lookup.

    Each node represents a weight slice (model + layer range) tagged with
    capabilities. The tree structure enables O(log n) lookup by capability
    or model alias.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, WeightNode] = {}
        self._capability_index: dict[str, list[str]] = {}

    @property
    def size(self) -> int:
        return len(self._nodes)

    def insert(self, node: WeightNode) -> None:
        """Insert a node. Auto-links to parent if parent_id is set."""
        self._nodes[node.node_id] = node
        if node.parent_id and node.parent_id in self._nodes:
            parent = self._nodes[node.parent_id]
            if node.node_id not in parent.children:
                parent.children.append(node.node_id)
        for tag in node.capability_tags:
            if tag not in self._capability_index:
                self._capability_index[tag] = []
            if node.node_id not in self._capability_index[tag]:
                self._capability_index[tag].append(node.node_id)

    def get(self, node_id: str) -> WeightNode | None:
        return self._nodes.get(node_id)

    def lookup(self, query: str) -> list[WeightNode]:
        """Search nodes by node_id prefix, model_alias, or capability tag."""
        results = []
        q = query.lower()
        for nid, node in self._nodes.items():
            if (
                nid.startswith(q)
                or node.model_alias.lower() == q
                or q in node.capability_tags
                or any(q in t for t in node.capability_tags)
            ):
                results.append(node)
        return results

    def by_capability(self, task: str) -> list[WeightNode]:
        """Return nodes matching a capability tag, sorted by score descending."""
        node_ids = self._capability_index.get(task, [])
        nodes = [self._nodes[nid] for nid in node_ids if nid in self._nodes]
        return sorted(nodes, key=lambda n: n.score, reverse=True)

    def by_model(self, model_alias: str) -> list[WeightNode]:
        """Return all nodes for a given model alias."""
        return [n for n in self._nodes.values() if n.model_alias == model_alias]

    def children_of(self, node_id: str) -> list[WeightNode]:
        """Return child nodes of a given node."""
        node = self._nodes.get(node_id)
        if node is None:
            return []
        return [self._nodes[cid] for cid in node.children if cid in self._nodes]

    def path_to_root(self, node_id: str) -> list[WeightNode]:
        """Walk from node up to root, returning the path."""
        path = []
        current = self._nodes.get(node_id)
        while current is not None:
            path.append(current)
            current = self._nodes.get(current.parent_id) if current.parent_id else None
        return path

    def update_score(self, node_id: str, new_score: float) -> None:
        """Update a node's effectiveness score (0-1)."""
        if node_id not in self._nodes:
            raise KeyError(f"node_id not found: {node_id}")
        clamped = max(0.0, min(1.0, new_score))
        self._nodes[node_id].score = clamped

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "capability_index": {k: list(v) for k, v in self._capability_index.items()},
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WeightMap:
        wm = cls()
        for nd in data.get("nodes", {}).values():
            node = WeightNode(
                node_id=nd["node_id"],
                model_alias=nd["model_alias"],
                layer_range=tuple(nd["layer_range"]),
                capability_tags=tuple(nd["capability_tags"]),
                score=nd["score"],
                parent_id=nd.get("parent_id", ""),
                children=list(nd.get("children", [])),
                metadata=dict(nd.get("metadata", {})),
            )
            wm._nodes[node.node_id] = node
        wm._capability_index = {
            k: list(v) for k, v in data.get("capability_index", {}).items()
        }
        return wm


def build_default_weight_map() -> WeightMap:
    """Build a starter weight map with known model capabilities."""
    wm = WeightMap()
    wm.insert(WeightNode(
        node_id="root",
        model_alias="*",
        capability_tags=("root",),
        score=1.0,
    ))
    wm.insert(WeightNode(
        node_id="gemma4-general",
        model_alias="gemma4-e4b",
        layer_range=(0, 32),
        capability_tags=("general", "reasoning", "chat"),
        score=0.8,
        parent_id="root",
    ))
    wm.insert(WeightNode(
        node_id="gemma4-memory",
        model_alias="gemma4-e4b",
        layer_range=(24, 32),
        capability_tags=("memory", "recall"),
        score=0.7,
        parent_id="gemma4-general",
    ))
    wm.insert(WeightNode(
        node_id="qwen-70b-specialized",
        model_alias="qwen2-70b",
        layer_range=(0, 80),
        capability_tags=("code", "math", "long-context"),
        score=0.9,
        parent_id="root",
        metadata={"status": "registered", "loaded": False},
    ))
    return wm
