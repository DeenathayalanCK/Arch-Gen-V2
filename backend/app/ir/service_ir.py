from dataclasses import dataclass, field
from typing import List, Literal
from .base import BaseIR
from .errors import ValidationError
from .validation import ValidationResult

@dataclass
class Service(BaseIR):
    service_type: Literal["api", "worker", "external"] = "api"
    protocol: Literal["http", "grpc", "event", "unknown"] = "unknown"


@dataclass
class ServiceDependency:
    from_service_id: str
    to_service_id: str
    interaction: Literal["sync", "async"]


@dataclass
class ServiceIR(BaseIR):
    services: List[Service] = field(default_factory=list)
    dependencies: List[ServiceDependency] = field(default_factory=list)

    def validate(self) -> ValidationResult:
        errors = []

        if not self.services:
            errors.append(
                ValidationError(
                    level="service",
                    message="at least one service must exist",
                    object_id=self.id,
                )
            )

        service_ids = {s.id for s in self.services}

        for dep in self.dependencies:
            if dep.from_service_id not in service_ids:
                errors.append(
                    ValidationError(
                        level="service",
                        message="dependency source service not found",
                        object_id=dep.from_service_id,
                    )
                )
            if dep.to_service_id not in service_ids:
                errors.append(
                    ValidationError(
                        level="service",
                        message="dependency target service not found",
                        object_id=dep.to_service_id,
                    )
                )

        if errors:
            return ValidationResult.failure(errors)

        return ValidationResult.success()