from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# ---- Core Concepts ----

class Actor(BaseModel):
    id: str
    role: str
    description: Optional[str] = None
    channels: List[str] = []  # browser, api, batch, internal, etc.


class Capability(BaseModel):
    id: str
    purpose: str  # what responsibility this capability owns
    state: Optional[Literal["none", "local", "shared", "persistent"]] = "none"
    constraints: List[str] = []  # e.g. regulated, pii, high-availability
    audience: List[str] = []     # actor ids that use it


class DataEntity(BaseModel):
    id: str
    description: str
    sensitivity: Optional[Literal["public", "internal", "restricted"]] = "internal"


class Interaction(BaseModel):
    source: str   # actor or capability id
    target: str   # capability or data id
    semantics: str  # request, command, query, event, sync, async
    trust_crossing: bool = False


# ---- Root IR ----

class ArchitectureIR(BaseModel):
    actors: List[Actor] = Field(default_factory=list)
    capabilities: List[Capability] = Field(default_factory=list)
    data_entities: List[DataEntity] = Field(default_factory=list)
    interactions: List[Interaction] = Field(default_factory=list)

    assumptions: List[str] = []   # explicit inferred assumptions
    constraints: List[str] = []   # global constraints (regulatory, scale)
