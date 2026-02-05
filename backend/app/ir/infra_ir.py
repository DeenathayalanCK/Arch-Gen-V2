from dataclasses import dataclass, field
from typing import List, Literal
from .base import BaseIR
from .errors import ValidationError
from .validation import ValidationResult

@dataclass
class ComputeNode(BaseIR):
    compute_type: Literal["vm", "container", "serverless"] = "container"


@dataclass
class NetworkBoundary(BaseIR):
    boundary_type: Literal["public", "private", "internal"] = "private"


@dataclass
class InfraIR(BaseIR):
    compute: List[ComputeNode] = field(default_factory=list)
    network: List[NetworkBoundary] = field(default_factory=list)

    

    def validate(self) -> ValidationResult:
        errors = []

        if not self.compute:
            errors.append(
                ValidationError(
                    level="infra",
                    message="at least one compute node required",
                    object_id=self.id,
                )
            )

        if errors:
            return ValidationResult.failure(errors)

        return ValidationResult.success()
