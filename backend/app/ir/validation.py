from dataclasses import dataclass
from typing import List
from .errors import ValidationError


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError]

    @classmethod
    def success(cls):
        return cls(is_valid=True, errors=[])

    @classmethod
    def failure(cls, errors: List[ValidationError]):
        return cls(is_valid=False, errors=errors)
