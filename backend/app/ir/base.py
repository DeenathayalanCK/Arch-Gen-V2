from dataclasses import dataclass, field
from typing import Optional
import uuid
from .validation import ValidationResult
from .errors import ValidationError


@dataclass
class TraceInfo:
    requirement_id: str
    source_text: str
    confidence: float  # 0.0 – 1.0


@dataclass
class BaseIR:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    trace: Optional[TraceInfo] = None

    

    def validate(self) -> ValidationResult:
        errors = []
        if not self.name:
            errors.append(
                ValidationError(
                    level="base",
                    message="name must not be empty",
                    object_id=self.id,
                )
            )

        if errors:
            return ValidationResult.failure(errors)

        return ValidationResult.success()
