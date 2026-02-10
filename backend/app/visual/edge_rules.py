"""
Phase 3B — Edge Suppression & Bundling Rules
"""

from __future__ import annotations

from typing import List, Set

from app.visual.visual_schema import VisualEdge


# ------------------------------------------------------------------ #
# Edge classification
# ------------------------------------------------------------------ #

# Keywords that signal a high-detail, semantically meaningful relation.
_SEMANTIC_KEYWORDS = {"→", "processing", "validation", "lifecycle", "retrieval"}

# Keywords for infrastructure layer edges.
_INFRA_KEYWORDS = {"runs on", "runs_on", "deployed", "hosted"}

# Keywords for data layer edges.
_DATA_KEYWORDS = {"read", "write", "read_write", "reads", "writes", "stores", "persists"}


def is_semantic_edge(edge: VisualEdge) -> bool:
    """Return True when the edge relation carries rich semantic meaning."""
    if not edge.relation:
        return False
    relation_lower = edge.relation.lower()
    return any(kw.lower() in relation_lower for kw in _SEMANTIC_KEYWORDS)


def is_infra_edge(edge: VisualEdge) -> bool:
    """Return True when the edge represents an infrastructure relationship."""
    if not edge.relation:
        return False
    relation_lower = edge.relation.lower()
    return any(kw in relation_lower for kw in _INFRA_KEYWORDS)


def is_data_edge(edge: VisualEdge) -> bool:
    """Return True when the edge represents a data access relationship."""
    if not edge.relation:
        return False
    relation_lower = edge.relation.lower()
    return any(kw in relation_lower for kw in _DATA_KEYWORDS)


def is_bundleable_edge(edge: VisualEdge) -> bool:
    """Return True if this edge is eligible for bundling.

    Bundleable edges include:
    - Semantic edges (responsibility-level)
    - Infrastructure edges (runs on)
    - Data edges (read/write)
    """
    return is_semantic_edge(edge) or is_infra_edge(edge) or is_data_edge(edge)


# ------------------------------------------------------------------ #
# Suppression logic
# ------------------------------------------------------------------ #

def should_suppress_edge(edge: VisualEdge, all_edges: List[VisualEdge]) -> bool:
    """Decide whether *edge* should be suppressed from the rendered diagram.

    Suppression rules:
    1. Generic "calls" edges are suppressed when a bundleable edge exists
       for the same (source, target) pair.
    2. After bundling, structural edges are implicitly suppressed via dedup.
    """
    if edge.relation != "calls":
        return False

    # Check whether a bundleable edge exists for the same source→target pair.
    for other in all_edges:
        if other is edge:
            continue
        if (
            other.source == edge.source
            and other.target == edge.target
            and is_bundleable_edge(other)
        ):
            return True

    return False


# ------------------------------------------------------------------ #
# Bundling logic
# ------------------------------------------------------------------ #

def _relation_prefix(relation: str) -> str:
    """Extract the leading semantic token used for grouping."""
    # Split on the arrow character first.
    if "→" in relation:
        return relation.split("→")[0].strip().lower()
    # Fallback: first word.
    return relation.split()[0].strip().lower() if relation.strip() else relation.lower()


def _extract_responsibility_target(relation: str) -> str:
    """Extract the target responsibility from an edge relation.

    For relations like "Order Validation → Payment Processing", returns
    "Payment Processing". For single-word relations, returns the relation.
    """
    if "→" in relation:
        return relation.split("→", 1)[1].strip()
    return relation.strip()


def bundle_edges(edges: List[VisualEdge]) -> List[VisualEdge]:
    """Group edges that share the same source and relation category.

    Bundled edges carry:
      - A combined list of targets
      - A rich label showing the semantic operation
      - Per-target labels stored in `_target_labels` for fan-out rendering
      - `_is_hub_bundle` flag for hub-based rendering

    Bundling applies to:
      - Semantic edges (grouped by relation prefix)
      - Infra edges (grouped by "runs on" pattern)
      - Data edges (grouped by access type)
    """
    bundleable: list[VisualEdge] = []
    passthrough: list[VisualEdge] = []

    for e in edges:
        if is_bundleable_edge(e):
            bundleable.append(e)
        else:
            passthrough.append(e)

    # Group bundleable edges by (source, category, relation_prefix).
    # Category ensures infra edges bundle together, data edges together, etc.
    groups: dict[tuple[str, str, str], list[VisualEdge]] = {}
    for e in bundleable:
        category = _get_edge_category(e)
        prefix = _relation_prefix(e.relation)
        key = (e.source, category, prefix)
        groups.setdefault(key, []).append(e)

    bundled: list[VisualEdge] = []
    for (_src, category, prefix), group in groups.items():
        if len(group) == 1:
            # No benefit from bundling a single edge — keep as-is.
            bundled.append(group[0])
        else:
            # Combine targets and build a rich, responsibility-derived label.
            combined_targets = [e.target for e in group]

            # Build per-target labels for fan-out rendering.
            target_labels = {
                e.target: _extract_responsibility_target(e.relation) for e in group
            }

            # Generate a combined relation based on category.
            combined_relation = _build_bundle_label(category, prefix, group)

            edge = VisualEdge(
                source=group[0].source,
                target=combined_targets,
                relation=combined_relation,
                style=group[0].style,
            )
            # Attach per-target labels and hub flag for the renderer.
            edge._target_labels = target_labels  # type: ignore[attr-defined]
            edge._is_hub_bundle = True  # type: ignore[attr-defined]
            edge._bundle_category = category  # type: ignore[attr-defined]
            bundled.append(edge)

    return passthrough + bundled


def _get_edge_category(edge: VisualEdge) -> str:
    """Classify edge into a category for grouping."""
    if is_infra_edge(edge):
        return "infra"
    if is_data_edge(edge):
        return "data"
    if is_semantic_edge(edge):
        return "semantic"
    return "other"


def _build_bundle_label(category: str, prefix: str, group: list[VisualEdge]) -> str:
    """Build a human-readable label for a bundled edge group."""
    if category == "infra":
        # For infra edges, use a simple "runs on" label.
        return "Runs On"

    if category == "data":
        # For data edges, summarize the access types.
        access_types: Set[str] = set()
        for e in group:
            rel = e.relation.lower()
            if "write" in rel and "read" in rel:
                access_types.add("read/write")
            elif "write" in rel:
                access_types.add("write")
            elif "read" in rel:
                access_types.add("read")
            else:
                access_types.add(e.relation)
        return "Data: " + ", ".join(sorted(access_types))

    # For semantic edges, extract responsibility names.
    responsibility_names = [
        _extract_responsibility_target(e.relation) for e in group
    ]
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique_responsibilities: list[str] = []
    for r in responsibility_names:
        r_lower = r.lower()
        if r_lower not in seen:
            seen.add(r_lower)
            unique_responsibilities.append(r)

    prefix_title = prefix.replace("_", " ").strip().title()
    if unique_responsibilities:
        return f"{prefix_title} → " + ", ".join(unique_responsibilities)
    return prefix_title
