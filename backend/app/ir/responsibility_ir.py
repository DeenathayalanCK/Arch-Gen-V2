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


@dataclass
class ResponsibilityDependency:
    from_service: str
    from_responsibility: str
    to_service: str
    to_responsibility: str
    interaction: str = "calls"


@dataclass
class ResponsibilityDataAccess:
    """Represents a responsibility's access to a datastore."""
    service_name: str
    responsibility_name: str
    datastore_name: str
    access_type: Literal["read", "write", "read_write"] = "read_write"