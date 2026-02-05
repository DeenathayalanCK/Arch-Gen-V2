from app.compiler.types import Graph


def render_mermaid(graph: Graph) -> str:
    lines = ["flowchart TD"]

    for node in graph.nodes:
        lines.append(
            f'{node.id}["{node.label}"]'
        )

    for edge in graph.edges:
        label = f"|{edge.label}|" if edge.label else ""
        lines.append(
            f"{edge.source} -->{label} {edge.target}"
        )

    return "\n".join(lines)
