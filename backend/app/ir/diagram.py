from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class DiagramNode(BaseModel):
    id: str
    label: str
    kind: Literal["actor", "capability", "data"]  # REQUIRED
    emphasis: Literal["normal", "high"] = "normal"


class DiagramGroup(BaseModel):
    id: str
    label: str                     # REQUIRED
    rationale: Optional[str] = None
    nodes: List[str] = Field(default_factory=list)
    boundary: Literal["none", "trust", "domain"] = "none"


class DiagramEdge(BaseModel):
    source: str
    target: str
    label: str                     # REQUIRED (diagram label)
    style: Literal["solid", "dashed"] = "solid"


class DiagramIR(BaseModel):
    nodes: List[DiagramNode]
    groups: List[DiagramGroup] = []
    edges: List[DiagramEdge]
    notes: List[str] = []
