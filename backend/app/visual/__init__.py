# Visual IR module
# Provides a clean separation between semantic architecture logic and visual rendering

from app.visual.visual_schema import VisualNode, VisualEdge, VisualDiagram
from app.visual.visual_style import VISUAL_STYLE
from app.visual.visual_mapper import map_context_to_visual_ir

__all__ = [
    "VisualNode",
    "VisualEdge",
    "VisualDiagram",
    "VISUAL_STYLE",
    "map_context_to_visual_ir",
]
