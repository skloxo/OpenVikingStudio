# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
HG-RAG Hierarchical Compass Topology & Breadcrumb Lineage Navigator.
(Card-Knowledge-HG-RAG-HierarchicalCompass / v1.5.19)
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CompassDirection(str, Enum):
    """Compass directions for roaming the hierarchical knowledge graph."""
    NORTH = "north"  # Parent / Category level summary (Upwards)
    SOUTH = "south"  # Children / Granular implementations (Downwards)
    EAST = "east"    # Next sibling in same category (Lateral)
    WEST = "west"    # Previous sibling in same category (Lateral)


class CompassNode(BaseModel):
    """A node in the hierarchical knowledge graph with compass pointers."""
    node_id: str
    title: str
    content_snippet: str
    depth: int = Field(default=0, ge=0, description="Depth level: 0=Root, 1=Chapter, 2=Section, 3=Leaf")
    breadcrumbs: List[str] = Field(default_factory=list, description="Full ancestor hierarchy path")
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)
    sibling_prev_id: Optional[str] = None
    sibling_next_id: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class NavigationResult(BaseModel):
    """Result of traversing in a compass direction from an anchor node."""
    anchor_id: str
    direction: CompassDirection
    target_node: Optional[CompassNode] = None
    available_directions: List[CompassDirection] = Field(default_factory=list)
    lineage_path: str = ""
    status: str = "ok"


class HierarchicalCompassNavigator:
    """
    Navigator for traversing the hierarchical knowledge graph along compass directions.
    Provides deterministic parent-child roaming without losing high-level category context.
    """

    def __init__(self, nodes: Optional[Dict[str, CompassNode]] = None):
        self._nodes: Dict[str, CompassNode] = nodes or {}

    def add_node(self, node: CompassNode) -> None:
        """Register a node into the topology graph."""
        self._nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[CompassNode]:
        """Fetch node by unique ID."""
        return self._nodes.get(node_id)

    def get_available_directions(self, node_id: str) -> List[CompassDirection]:
        """Inspect which compass directions are navigable from this node."""
        node = self._nodes.get(node_id)
        if not node:
            return []

        available: List[CompassDirection] = []
        if node.parent_id and node.parent_id in self._nodes:
            available.append(CompassDirection.NORTH)
        if node.children_ids and any(cid in self._nodes for cid in node.children_ids):
            available.append(CompassDirection.SOUTH)
        if node.sibling_next_id and node.sibling_next_id in self._nodes:
            available.append(CompassDirection.EAST)
        if node.sibling_prev_id and node.sibling_prev_id in self._nodes:
            available.append(CompassDirection.WEST)
        return available

    def navigate(
        self, anchor_id: str, direction: CompassDirection, child_index: int = 0
    ) -> NavigationResult:
        """Traverse one step in the specified compass direction."""
        anchor = self._nodes.get(anchor_id)
        if not anchor:
            return NavigationResult(
                anchor_id=anchor_id,
                direction=direction,
                target_node=None,
                status="ANCHOR_NOT_FOUND",
            )

        target_id: Optional[str] = None
        if direction == CompassDirection.NORTH:
            target_id = anchor.parent_id
        elif direction == CompassDirection.SOUTH:
            if anchor.children_ids:
                idx = max(0, min(child_index, len(anchor.children_ids) - 1))
                target_id = anchor.children_ids[idx]
        elif direction == CompassDirection.EAST:
            target_id = anchor.sibling_next_id
        elif direction == CompassDirection.WEST:
            target_id = anchor.sibling_prev_id

        target_node = self._nodes.get(target_id) if target_id else None
        lineage = " > ".join(target_node.breadcrumbs) if target_node else " > ".join(anchor.breadcrumbs)
        available = self.get_available_directions(target_id) if target_id else self.get_available_directions(anchor_id)

        return NavigationResult(
            anchor_id=anchor_id,
            direction=direction,
            target_node=target_node,
            available_directions=available,
            lineage_path=lineage,
            status="SUCCESS" if target_node else "NO_TARGET_IN_DIRECTION",
        )

    def get_full_lineage(self, node_id: str) -> List[CompassNode]:
        """Retrieve full chain from root down to this node."""
        chain: List[CompassNode] = []
        curr_id: Optional[str] = node_id
        visited: set[str] = set()

        while curr_id and curr_id in self._nodes and curr_id not in visited:
            visited.add(curr_id)
            node = self._nodes[curr_id]
            chain.insert(0, node)
            curr_id = node.parent_id
        return chain

    @property
    def total_nodes(self) -> int:
        return len(self._nodes)
