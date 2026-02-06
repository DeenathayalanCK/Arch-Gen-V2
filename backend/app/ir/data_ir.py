from dataclasses import dataclass, field
from typing import List, Literal
import re

from .base import BaseIR
from .errors import ValidationError
from .validation import ValidationResult


# -------------------------
# Canonicalization Helper
# -------------------------

def canonical_datastore_name(name: str) -> str:
   
    base = name.strip().lower()

    if base.endswith("s"):
        base = base[:-1]

    base = re.sub(r"[^a-z0-9]", "", base)

    return base.capitalize()


# -------------------------
# IR Models
# -------------------------

@dataclass
class DataStore(BaseIR):
    store_type: Literal["sql", "nosql", "object", "cache"] = "sql"

    def __post_init__(self):
        # Ensure ALL datastores are canonicalized,
        # regardless of which stage created them
        self.name = canonical_datastore_name(self.name)


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

        # -------------------------
        # Deduplicate Datastores
        # -------------------------
        unique_by_name = {}
        for ds in self.datastores:
            unique_by_name[ds.name] = ds

        self.datastores = list(unique_by_name.values())

        datastore_ids = {d.id for d in self.datastores}

        # -------------------------
        # Validate Access Patterns
        # -------------------------
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
