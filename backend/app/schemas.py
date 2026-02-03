from pydantic import BaseModel
from typing import List, Optional

class Actor(BaseModel):
    id: str
    description: str

class Capability(BaseModel):
    id: str
    responsibility: str
    state: Optional[str] = None
    constraints: List[str] = []

class Interaction(BaseModel):
    source: str
    target: str
    semantics: str

class ArchitectureIR(BaseModel):
    actors: List[Actor]
    capabilities: List[Capability]
    interactions: List[Interaction]
