from dataclasses import dataclass, field
from typing import List


@dataclass
class DecomposedRequirements:
    business: List[str] = field(default_factory=list)
    service: List[str] = field(default_factory=list)
    data: List[str] = field(default_factory=list)
    infra: List[str] = field(default_factory=list)

    def validate(self) -> bool:
        # At least one level must be non-empty
        return any([self.business, self.service, self.data, self.infra])
