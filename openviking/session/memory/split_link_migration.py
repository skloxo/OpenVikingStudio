# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Link/backlink migration helpers for 1:1 chains and N-way split deletes (#5922)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from openviking.session.memory.dataclass import ResolvedOperations, StoredLink


def fan_out_stored_links(
    links: List[StoredLink], split_map: Dict[str, List[str]]
) -> List[StoredLink]:
    """Fan link endpoints out over N-way split replacements (1->N migration)."""
    if not links or not split_map:
        return list(links or [])
    fanned_links: List[StoredLink] = []
    for link in links:
        from_targets = split_map.get(link.from_uri) or [link.from_uri]
        to_targets = split_map.get(link.to_uri) or [link.to_uri]
        for from_uri in from_targets:
            for to_uri in to_targets:
                if from_uri == to_uri:
                    continue
                fanned_links.append(
                    link.model_copy(update={"from_uri": from_uri, "to_uri": to_uri})
                )
    return fanned_links


def detect_split_replacements(operations: ResolvedOperations) -> Dict[str, List[str]]:
    """Detect N-way splits among the batch's scheduled deletes."""
    delete_uris = {file.uri for file in (operations.delete_file_contents or []) if file.uri}
    if not delete_uris:
        return {}
    upsert_uris = {uri for op in (operations.upsert_operations or []) for uri in (op.uris or [])}
    if not upsert_uris:
        return {}
    explicit_replacements = dict(operations.delete_replacements or {})
    split_map: Dict[str, set] = {}
    for link in operations.resolved_links or []:
        if (link.link_type or "") != "derived_from":
            continue
        source_uri = link.to_uri
        derived_uri = link.from_uri
        if (
            source_uri in delete_uris
            and source_uri not in explicit_replacements
            and derived_uri in upsert_uris
            and derived_uri != source_uri
        ):
            split_map.setdefault(source_uri, set()).add(derived_uri)
    return {source_uri: sorted(targets) for source_uri, targets in split_map.items()}


def build_split_targets_by_source(
    uri_remap: Dict[str, str],
    split_map: Dict[str, List[str]],
    resolve_terminal: Callable[[str, Dict[str, str]], Optional[str]],
) -> Dict[str, List[str]]:
    """Resolve 1:1 chains to terminal targets and combine with N-way split targets."""
    targets_by_source: Dict[str, List[str]] = {
        source_uri: [target for target in targets if target and target != source_uri]
        for source_uri, targets in split_map.items()
    }
    for source_uri, replacement_uri in uri_remap.items():
        if (
            source_uri not in targets_by_source
            and replacement_uri
            and replacement_uri != source_uri
        ):
            terminal_uri = resolve_terminal(source_uri, uri_remap)
            if terminal_uri and terminal_uri != source_uri:
                targets_by_source[source_uri] = [terminal_uri]
    return targets_by_source


def fold_inherited_link(
    inherited_by_uri: Dict[str, Dict[str, List[Tuple[str, Dict[str, Any]]]]],
    remapped: Dict[str, Any],
    deleted_uri: str,
    targets: List[str],
    neighbor_uri: Optional[str],
    record_kind: str,
    stale_uris: Set[str],
) -> None:
    """Broadcast one inherited link/backlink record to every replacement target."""
    for target_uri in targets:
        record = dict(remapped)
        if record.get("from_uri") == deleted_uri:
            record["from_uri"] = target_uri
        if record.get("to_uri") == deleted_uri:
            record["to_uri"] = target_uri
        if record.get("from_uri") == record.get("to_uri"):
            continue
        inherited_by_uri.setdefault(target_uri, {"links": [], "backlinks": []})[
            record_kind
        ].append((deleted_uri, record))
        if neighbor_uri and neighbor_uri not in stale_uris:
            inherited_by_uri.setdefault(neighbor_uri, {"links": [], "backlinks": []})[
                "backlinks" if record_kind == "links" else "links"
            ].append((deleted_uri, record))


def collect_dangling_deleted_uris(
    resolved_links: List[StoredLink],
    deleted_uris: Set[str],
) -> List[str]:
    """Return sorted deleted URIs still referenced by in-batch links."""
    return sorted(
        {
            uri
            for link in (resolved_links or [])
            for uri in (link.from_uri, link.to_uri)
            if uri in deleted_uris
        }
    )
