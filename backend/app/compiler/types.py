from dataclasses import dataclass, field
from typing import List


@dataclass
class Node:
    id: str
    label: str
    layer: str  # business | service | data | infra


@dataclass
class Edge:
    source: str
    target: str
    label: str = ""


@dataclass
class Graph:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
