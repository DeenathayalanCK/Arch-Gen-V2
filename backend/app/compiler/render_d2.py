# backend/app/compiler/render_d2.py
"""
D2 Diagram Renderer

D2 is a modern diagram language with:
- Better auto-layout algorithms
- Built-in icons and shapes
- Multiple layout engines (dagre, elk, tala)
- Native theming support

Docs: https://d2lang.com/
"""

from typing import Optional
from app.compiler.types import Graph, Node, Edge
from app.visual.visual_schema import VisualDiagram, VisualNode, VisualEdge


# D2 shape mappings from Visual IR node types
D2_SHAPE_MAP = {
    "actor": "person",
    "service": "rectangle",
    "web_app": "rectangle",
    "database": "cylinder",
    "queue": "queue",
    "infrastructure": "cloud",
    "external": "rectangle",
    "gateway": "hexagon",
    "cache": "oval",
}

# D2 style mappings
D2_STYLE_MAP = {
    "actor": "fill: '#E3F2FD'; stroke: '#1565C0'",
    "service": "fill: '#E8F5E9'; stroke: '#2E7D32'",
    "web_app": "fill: '#FFF3E0'; stroke: '#EF6C00'",
    "database": "fill: '#FCE4EC'; stroke: '#C2185B'",
    "queue": "fill: '#F3E5F5'; stroke: '#7B1FA2'",
    "infrastructure": "fill: '#ECEFF1'; stroke: '#546E7A'",
    "external": "fill: '#FAFAFA'; stroke: '#9E9E9E'",
    "gateway": "fill: '#FFF8E1'; stroke: '#FF8F00'",
    "cache": "fill: '#E0F7FA'; stroke: '#00838F'",
}


def render_d2(graph: Graph, theme: str = "default") -> str:
    """
    Render a Graph to D2 format.
    
    Args:
        graph: The compiled graph
        theme: D2 theme (default, dark, terminal, etc.)
    
    Returns:
        D2 diagram source code
    """
    lines = []
    
    # Direction
    lines.append("direction: down")
    lines.append("")
    
    # Theme configuration
    if theme != "default":
        lines.append(f"# Theme: {theme}")
        lines.append("")
    
    # Group nodes by layer/group for subgraph creation
    groups: dict[str, list[Node]] = {}
    standalone: list[Node] = []
    
    for node in graph.nodes:
        # Extract group from node metadata if available
        group = getattr(node, 'group', None) or getattr(node, 'layer', None)
        if group:
            if group not in groups:
                groups[group] = []
            groups[group].append(node)
        else:
            standalone.append(node)
    
    # Render grouped nodes as containers
    for group_name, nodes in groups.items():
        lines.append(f"{_sanitize_id(group_name)}: {group_name.replace('_', ' ').title()} {{")
        for node in nodes:
            node_def = _render_node(node)
            lines.append(f"  {node_def}")
        lines.append("}")
        lines.append("")
    
    # Render standalone nodes
    for node in standalone:
        lines.append(_render_node(node))
    
    lines.append("")
    
    # Render edges
    for edge in graph.edges:
        edge_line = _render_edge(edge)
        lines.append(edge_line)
    
    return "\n".join(lines)


def render_d2_from_visual_ir(visual_ir: VisualDiagram) -> str:
    """
    Render a VisualDiagram directly to D2 format.
    
    This provides richer output using visual metadata.
    """
    lines = []
    
    # Header
    lines.append("direction: down")
    lines.append("")
    
    # Group nodes by their group attribute
    groups: dict[str, list[VisualNode]] = {}
    standalone: list[VisualNode] = []
    
    for node in visual_ir.nodes:
        if node.group:
            if node.group not in groups:
                groups[node.group] = []
            groups[node.group].append(node)
        else:
            standalone.append(node)
    
    # Render grouped nodes
    for group_name, nodes in groups.items():
        lines.append(f"{_sanitize_id(group_name)}: {group_name.replace('_', ' ').title()} {{")
        for node in nodes:
            lines.append(f"  {_render_visual_node(node)}")
        lines.append("}")
        lines.append("")
    
    # Render standalone nodes
    for node in standalone:
        lines.append(_render_visual_node(node))
    
    lines.append("")
    
    # Render edges
    for edge in visual_ir.edges:
        lines.append(_render_visual_edge(edge))
    
    return "\n".join(lines)


def _sanitize_id(id_str: str) -> str:
    """Make ID safe for D2"""
    # D2 IDs can contain alphanumeric, underscore, hyphen
    return id_str.replace(" ", "_").replace("-", "_")


def _render_node(node: Node) -> str:
    """Render a single node to D2 format"""
    node_id = _sanitize_id(node.id)
    label = node.label
    shape = D2_SHAPE_MAP.get(getattr(node, 'node_type', 'service'), 'rectangle')
    
    # Basic node definition
    if shape == "person":
        return f'{node_id}: "{label}" {{ shape: person }}'
    elif shape == "cylinder":
        return f'{node_id}: "{label}" {{ shape: cylinder }}'
    else:
        return f'{node_id}: "{label}"'


def _render_visual_node(node: VisualNode) -> str:
    """Render a VisualNode to D2 format with full styling"""
    node_id = _sanitize_id(node.id)
    shape = D2_SHAPE_MAP.get(node.node_type, 'rectangle')
    style = D2_STYLE_MAP.get(node.node_type, "")
    
    # Build label with details if present
    if node.details:
        # D2 supports markdown in labels
        details_text = "\\n".join(node.details[:3])  # Limit to 3 details
        label = f"{node.label}\\n---\\n{details_text}"
    else:
        label = node.label
    
    # Build node with shape and style
    parts = [f'{node_id}: "{label}"']
    
    style_parts = []
    if shape != "rectangle":
        style_parts.append(f"shape: {shape}")
    if style:
        style_parts.append(f"style: {{ {style} }}")
    if node.icon:
        style_parts.append(f"icon: {node.icon}")
    
    if style_parts:
        return f'{parts[0]} {{ {"; ".join(style_parts)} }}'
    else:
        return parts[0]


def _render_edge(edge: Edge) -> str:
    """Render an edge to D2 format"""
    source = _sanitize_id(edge.source)
    target = _sanitize_id(edge.target)
    
    if edge.label:
        return f'{source} -> {target}: "{edge.label}"'
    else:
        return f'{source} -> {target}'


def _render_visual_edge(edge: VisualEdge) -> str:
    """Render a VisualEdge to D2 format"""
    source = _sanitize_id(edge.source)
    target = _sanitize_id(edge.target)
    
    # D2 supports different arrow styles
    arrow = "->"
    if edge.style == "dotted":
        arrow = "-->"  # D2 uses -- for dotted
    
    if edge.relation:
        return f'{source} {arrow} {target}: "{edge.relation}"'
    else:
        return f'{source} {arrow} {target}'


# Convenience function for CLI/testing
def render_d2_from_context(context) -> str:
    """Render D2 from a PipelineContext (uses visual_ir if available)"""
    if hasattr(context, 'visual_ir') and context.visual_ir:
        return render_d2_from_visual_ir(context.visual_ir)
    else:
        # Fallback: would need to compile graph first
        from app.compiler.compiler import compile_graph
        graph = compile_graph(context)
        return render_d2(graph)
