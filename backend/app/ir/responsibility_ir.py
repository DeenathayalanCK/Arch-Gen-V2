from dataclasses import dataclass, field
from typing import List, Optional, Literal
import uuid


def uid() -> str:
    return str(uuid.uuid4())


ResponsibilityType = Literal[
    "logic",
    "orchestration",
    "integration",
    "persistence",
    "api",
]


@dataclass(frozen=True)
class Responsibility:
    id: str = field(default_factory=uid)
    name: str = ""
    description: Optional[str] = None
    responsibility_type: ResponsibilityType = "logic"


@dataclass(frozen=True)
class ServiceResponsibilities:
    service_id: str
    service_name: str
    responsibilities: List[Responsibility]
    source: Literal["llm", "rule"] = "llm"
