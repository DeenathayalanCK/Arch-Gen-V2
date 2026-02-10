from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class VisualNode:
    id: str
    label: str
    node_type: str                          # actor, service, database, infra
    layer: str                              # business, service, data, infra
    shape: str
    color: str
    icon: Optional[str] = None
    group: Optional[str] = None             # service cluster
    details: List[str] = field(default_factory=list)  # responsibilities, notes


@dataclass
class VisualEdge:
    source: str
    target: str
    relation: str
    style: str = "solid"


@dataclass
class VisualDiagram:
    nodes: List[VisualNode] = field(default_factory=list)
    edges: List[VisualEdge] = field(default_factory=list)
    layout: str = "top-down"
