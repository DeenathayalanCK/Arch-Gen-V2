from dataclasses import dataclass, field
from typing import List, Optional
import uuid


def uid() -> str:
    return str(uuid.uuid4())


@dataclass
class Responsibility:
    id: str = field(default_factory=uid)
    name: str = ""
    description: Optional[str] = None
    responsibility_type: str = "logic"  
    # logic | api | orchestration | persistence | integration


@dataclass
class ServiceResponsibilities:
    service_id: str
    service_name: str
    responsibilities: List[Responsibility] = field(default_factory=list)
