# backend/app/compiler/render_mermaid.py

from app.compiler.types import Graph
from collections import defaultdict


def render_mermaid(graph: Graph) -> str:
    lines = ["flowchart TD"]

    # -------------------------
    # Group service internals
    # -------------------------
    service_blocks = defaultdict(list)
    standalone_nodes = []

    for node in graph.nodes:
        if node.id.startswith("svc_"):
            parts = node.id.split("_")
            if len(parts) >= 3:
                # svc_<ServiceName>_<Thing>
                service_id = "_".join(parts[:3])
                service_blocks[service_id].append(node)
            else:
                standalone_nodes.append(node)
        else:
            standalone_nodes.append(node)

    # -------------------------
    # Render service subgraphs
    # -------------------------
    for service_id, nodes in service_blocks.items():
        service_label = nodes[0].label.split(":")[0] if ":" in nodes[0].label else nodes[0].label

        lines.append(
            f'subgraph {service_id}["Service: {service_label}"]'
        )

        # 🔑 Anchor node (REAL FIX)
        lines.append(
            f'  {service_id}_anchor["{service_label}"]'
        )

        for node in nodes:
            lines.append(
                f'  {node.id}["{node.label}"]'
            )

        lines.append("end")

    # -------------------------
    # Render non-service nodes
    # -------------------------
    for node in standalone_nodes:
        lines.append(
            f'{node.id}["{node.label}"]'
        )

    # -------------------------
    # Render edges (anchor-aware)
    # -------------------------
    for edge in graph.edges:
        label = f"|{edge.label}|" if edge.label else ""

        source = (
            f"{edge.source}_anchor"
            if edge.source in service_blocks
            else edge.source
        )

        target = (
            f"{edge.target}_anchor"
            if edge.target in service_blocks
            else edge.target
        )

        lines.append(
            f"{source} -->{label} {target}"
        )

    return "\n".join(lines)
