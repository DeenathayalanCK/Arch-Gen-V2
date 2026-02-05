from dataclasses import dataclass, field
from typing import List
from .base import BaseIR
from .errors import ValidationError
from .validation import ValidationResult

@dataclass
class Actor(BaseIR):
    role: str = ""  # user, system, external, admin


@dataclass
class BusinessStep(BaseIR):
    actor_id: str = ""
    order: int = 0


@dataclass
class BusinessFlow(BaseIR):
    steps: List[BusinessStep] = field(default_factory=list)

    def validate(self) -> list[ValidationError]:
        errors = []
        if not self.steps:
            errors.append(
                ValidationError(
                    level="business",
                    message="business flow must contain at least one step",
                    object_id=self.id,
                )
            )
        return errors


@dataclass
class BusinessIR(BaseIR):
    actors: List[Actor] = field(default_factory=list)
    flows: List[BusinessFlow] = field(default_factory=list)

    

    def validate(self) -> ValidationResult:
        errors = []

        if not self.actors:
            errors.append(
                ValidationError(
                    level="business",
                    message="at least one actor is required",
                    object_id=self.id,
                )
            )

        for flow in self.flows:
            if not flow.steps:
                errors.append(
                    ValidationError(
                        level="business",
                        message="business flow must have steps",
                        object_id=flow.id,
                    )
                )

        if errors:
            return ValidationResult.failure(errors)

        return ValidationResult.success()

