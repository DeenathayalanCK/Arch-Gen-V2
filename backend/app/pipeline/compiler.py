from app.ir.diagram import DiagramIR


def compile_to_mermaid(diagram: DiagramIR) -> str:
    """
    Guarantees:
    - Planner group ordering respected
    - Layered enterprise layout
    - Request → response only when valid
    - Data read/write only when relevant
    - No edge explosion
    """

    lines: list[str] = ["flowchart TD"]
    emitted: set[tuple[str, str, str]] = set()

    # ==================================================
    # GROUPS (planner order is law)
    # ==================================================
    grouped_nodes: set[str] = set()

    for group in diagram.groups:
        lines.append(f'subgraph {group.id}["{_escape(group.label)}"]')

        for node_id in group.nodes:
            node = _find_node(diagram, node_id)
            if not node:
                continue

            grouped_nodes.add(node.id)
            lines.append(
                _node_template(node.kind).format(
                    id=node.id,
                    label=_escape(node.label),
                )
            )

        lines.append("end")

    # ==================================================
    # ACTORS (always outside)
    # ==================================================
    for node in diagram.nodes:
        if node.kind == "actor":
            lines.append(
                _node_template(node.kind).format(
                    id=node.id,
                    label=_escape(node.label),
                )
            )

    # ==================================================
    # EXPLICIT EDGES (planner truth only)
    # ==================================================
    for edge in diagram.edges:
        arrow = "-->" if edge.style == "solid" else "-.->"
        key = (edge.source, edge.target, edge.label)

        if key in emitted:
            continue

        emitted.add(key)
        lines.append(
            f"{edge.source} {arrow}|{_escape(edge.label)}| {edge.target}"
        )

    # ==================================================
    # STEP 15A — REQUEST / RESPONSE (guarded)
    # ==================================================
    for edge in diagram.edges:
        src = _find_node(diagram, edge.source)
        tgt = _find_node(diagram, edge.target)

        if not src or not tgt:
            continue

        if src.kind == "actor" and tgt.kind == "capability":
            response = (tgt.id, src.id, "response")
            if response not in emitted:
                emitted.add(response)
                lines.append(f"{tgt.id} -->|response| {src.id}")

    # ==================================================
    # STEP 15B — CAPABILITY ↔ DATA (controlled)
    # ==================================================
    for cap in diagram.nodes:
        if cap.kind != "capability":
            continue

        cap_name = cap.id.lower()

        for data in diagram.nodes:
            if data.kind != "data":
                continue

            data_name = data.id.lower()

            # --- Ownership heuristics ---
            related = False

            if "auth" in cap_name or "session" in cap_name:
                related = "session" in data_name or "auth" in data_name

            elif "data" in cap_name or "retrieve" in cap_name or "store" in cap_name:
                related = "user" in data_name or "data" in data_name

            if not related:
                continue

            read = (cap.id, data.id, "read")
            write = (data.id, cap.id, "write")

            if read not in emitted:
                emitted.add(read)
                lines.append(f"{cap.id} -->|read| {data.id}")

            if write not in emitted:
                emitted.add(write)
                lines.append(f"{data.id} -->|write| {cap.id}")

    # ==================================================
    # NOTES
    # ==================================================
    for note in diagram.notes:
        lines.append(f"%% {_escape(note)}")

    return "\n".join(lines)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _find_node(diagram: DiagramIR, node_id: str):
    for n in diagram.nodes:
        if n.id == node_id:
            return n
    return None


def _node_template(kind: str) -> str:
    return {
        "actor": '{id}(["{label}"])',
        "capability": '{id}["{label}"]',
        "data": '{id}[("{label}")]',
    }.get(kind, '{id}["{label}"]')


def _escape(text: str) -> str:
    return text.replace('"', "'")
