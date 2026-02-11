import re

from app.visual.edge_rules import should_suppress_edge, bundle_edges


class _IdMapper:
    """Maps raw IDs (UUIDs etc.) to short Mermaid-safe sequential IDs."""

    def __init__(self, prefix: str = "nd"):
        self._prefix = prefix
        self._counter = 0
        self._map: dict[str, str] = {}

    def get(self, raw_id: str) -> str:
        if raw_id not in self._map:
            self._counter += 1
            self._map[raw_id] = f"{self._prefix}{self._counter}"
        return self._map[raw_id]


def _truncate_label(label: str, max_len: int = 20) -> str:
    """Truncate label for hub nodes to prevent oversized shapes."""
    if len(label) <= max_len:
        return label
    return label[:max_len - 3] + "..."


def render_mermaid_from_visual_ir(visual_ir):
    """
    Converts VisualDiagram → Mermaid flowchart.
    Uses short sequential IDs to avoid Mermaid parser issues with UUIDs.
    """
    ids = _IdMapper()
    lines = ["flowchart TD"]

    # -------------------------
    # Subgraphs by layer
    # -------------------------
    layers: dict[str, list] = {}
    for node in visual_ir.nodes:
        layers.setdefault(node.layer, []).append(node)

    layer_counter = 0
    for layer, nodes in layers.items():
        layer_counter += 1
        layer_id = f"layer{layer_counter}"
        lines.append(f'  subgraph {layer_id}["{layer.capitalize()} Layer"]')

        for node in nodes:
            node_id = ids.get(node.id)

            label = node.label
            if node.details:
                # Use \n for Mermaid-native line breaks (SVG-safe, no <br/> tags)
                detail_text = " | ".join(d.lstrip("• ").strip() for d in node.details)
                label += " | " + detail_text

            # Escape quotes in label
            label = label.replace('"', "'")

            # Shape mapping
            if node.shape == "circle":
                lines.append(f'    {node_id}(("{label}"))')
            elif node.shape == "cylinder":
                lines.append(f'    {node_id}[("{label}")]')
            elif node.shape == "rounded_rect":
                lines.append(f'    {node_id}["{label}"]')
            else:
                lines.append(f'    {node_id}["{label}"]')

            # Style
            lines.append(
                f'    style {node_id} fill:{node.color},stroke:#333,stroke-width:1px'
            )

        lines.append("  end")

    # -------------------------
    # Edges (with labels)
    # -------------------------
    # FIX 2: Deduplicate edges by (source, target, relation)
    unique_edges: dict[tuple[str, str, str], object] = {}
    for e in visual_ir.edges:
        key = (e.source, e.target, e.relation)
        unique_edges[key] = e
    edges = list(unique_edges.values())

    # ------------------------------------------------------------------
    # Phase 3B — Edge Suppression & Bundling
    # ------------------------------------------------------------------
    edges = [e for e in edges if not should_suppress_edge(e, edges)]
    edges = bundle_edges(edges)

    seen_pairs: set[tuple[str, str]] = set()
    hub_counter = 0

    for edge in edges:
        # Check if this is a hub-based bundle.
        is_hub_bundle = getattr(edge, "_is_hub_bundle", False)
        targets = edge.target if isinstance(edge.target, list) else [edge.target]
        is_bundle = isinstance(edge.target, list) and len(targets) > 1

        src = ids.get(edge.source)
        target_labels = getattr(edge, "_target_labels", None)
        bundle_category = getattr(edge, "_bundle_category", "semantic")

        # Build a default sanitized label from the edge relation.
        default_label = ""
        if edge.relation:
            sanitized = edge.relation
            sanitized = re.sub(r'[|"#;]', "", sanitized)
            sanitized = re.sub(r"\s+", " ", sanitized).strip()
            default_label = sanitized

        # ---------------------------------------------------------
        # Hub-based rendering for bundled edges
        # ---------------------------------------------------------
        if is_hub_bundle and is_bundle:
            hub_counter += 1
            hub_id = f"hub{hub_counter}"

            # Create the hub node (small circle with TRUNCATED bundle label).
            hub_label = default_label if default_label else bundle_category.title()
            # TRUNCATE for consistent sizing
            hub_label = _truncate_label(hub_label, max_len=15)
            # Escape quotes in hub label.
            hub_label = hub_label.replace('"', "'")

            # Use smaller diamond shape for hubs instead of large circle
            lines.append(f'  {hub_id}{{{hub_label}}}')
            lines.append(f"  style {hub_id} fill:#E0E0E0,stroke:#666,stroke-width:1px")

            # Connect source to hub (the spine).
            if edge.style == "dashed":
                lines.append(f"  {src} -.-> {hub_id}")
            elif edge.style == "dotted":
                lines.append(f"  {src} -.-> {hub_id}")
            else:
                lines.append(f"  {src} --> {hub_id}")

            # Connect hub to each target (the fan-out stubs).
            for target_id in targets:
                tgt = ids.get(target_id)

                if src == tgt:
                    continue

                pair = (hub_id, tgt)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                if edge.style == "dashed":
                    lines.append(f"  {hub_id} -.-> {tgt}")
                elif edge.style == "dotted":
                    lines.append(f"  {hub_id} -.-> {tgt}")
                else:
                    lines.append(f"  {hub_id} --> {tgt}")

            # Mark the source-hub pair as seen to avoid duplicates.
            seen_pairs.add((src, hub_id))
        else:
            # ---------------------------------------------------------
            # Standard rendering for single edges or non-bundled edges.
            # ---------------------------------------------------------
            for target_id in targets:
                tgt = ids.get(target_id)

                if src == tgt:
                    continue

                pair = (src, tgt)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                if target_labels and target_id in target_labels:
                    use_label = target_labels[target_id]
                    use_label = re.sub(r'[|"#;]', "", use_label)
                    use_label = re.sub(r"\s+", " ", use_label).strip()
                else:
                    use_label = default_label

                if edge.style == "dashed":
                    if use_label:
                        lines.append(f"  {src} -.-|{use_label}| {tgt}")
                    else:
                        lines.append(f"  {src} -.-> {tgt}")
                elif edge.style == "dotted":
                    if use_label:
                        lines.append(f"  {src} -.-|{use_label}| {tgt}")
                    else:
                        lines.append(f"  {src} -.-> {tgt}")
                else:
                    if use_label:
                        lines.append(f"  {src} --|{use_label}|--> {tgt}")
                    else:
                        lines.append(f"  {src} --> {tgt}")

    return "\n".join(lines)
