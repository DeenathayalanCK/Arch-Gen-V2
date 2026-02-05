from dataclasses import dataclass, field
from typing import List, Literal
from .base import BaseIR
from .errors import ValidationError
from .validation import ValidationResult

@dataclass
class DataStore(BaseIR):
    store_type: Literal["sql", "nosql", "object", "cache"] = "sql"


@dataclass
class DataAccess:
    service_id: str
    datastore_id: str
    access_type: Literal["read", "write", "read_write"]


@dataclass
class DataIR(BaseIR):
    datastores: List[DataStore] = field(default_factory=list)
    access_patterns: List[DataAccess] = field(default_factory=list)

    

    def validate(self) -> ValidationResult:
        errors = []

        datastore_ids = {d.id for d in self.datastores}

        for access in self.access_patterns:
            if access.datastore_id not in datastore_ids:
                errors.append(
                    ValidationError(
                        level="data",
                        message="access references unknown datastore",
                        object_id=access.datastore_id,
                    )
                )

        if errors:
            return ValidationResult.failure(errors)

        return ValidationResult.success()
