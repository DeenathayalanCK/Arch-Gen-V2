from app.compiler.types import Graph

LAYER_ORDER = ["business", "service", "data", "infra"]


def apply_layout(graph: Graph) -> Graph:
    graph.nodes.sort(
        key=lambda n: (LAYER_ORDER.index(n.layer), n.label.lower())
    )

    graph.edges.sort(
        key=lambda e: (e.source, e.target, e.label)
    )

    return graph
