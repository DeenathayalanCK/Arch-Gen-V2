from dataclasses import dataclass, field, asdict
from typing import List, Literal, Dict
import re

from .base import BaseIR
from .errors import ValidationError
from .validation import ValidationResult


# -------------------------
# Canonicalization Helper
# -------------------------

def canonical_datastore_name(name: str) -> str:
    base = (name or "").strip().lower()
    # Only strip 's' for known plural patterns, not words like "order"
    known_singular = {"order", "payment", "user", "customer", "session", "transaction", "cache"}
    if base not in known_singular and base.endswith("s") and len(base) > 1:
        singular = base[:-1]
        if singular in known_singular:
            base = singular
    base = re.sub(r"[^a-z0-9]", "", base)
    return base.capitalize() if base else ""


# -------------------------
# IR Models
# -------------------------

@dataclass
class DataStore(BaseIR):
    store_type: Literal["sql", "nosql", "object", "cache"] = "sql"

    def __post_init__(self):
        # Ensure ALL datastores are canonicalized
        self.name = canonical_datastore_name(self.name)


@dataclass
class DataAccess:
    service_id: str
    datastore_id: str
    access_type: Literal["read", "write", "read_write"]


def deduplicate_datastores(
    datastores: List[DataStore], 
    access_patterns: List[DataAccess]
) -> tuple[List[DataStore], List[DataAccess]]:
    """Deduplicate datastores by name and fix access pattern references."""
    print(f"[DEBUG] deduplicate_datastores called with {len(datastores)} datastores")
    for ds in datastores:
        print(f"[DEBUG]   - id={ds.id}, name={ds.name}")
    
    if not datastores:
        return datastores, access_patterns
    
    # Build map: name -> first DataStore with that name
    unique_by_name: Dict[str, DataStore] = {}
    # Build map: old_id -> new_id (for fixing access patterns)
    id_remap: Dict[str, str] = {}
    
    for ds in datastores:
        name = ds.name  # Already canonicalized by DataStore.__post_init__
        if not name:
            continue
        if name in unique_by_name:
            # This is a duplicate - map its ID to the first one's ID
            print(f"[DEBUG] Found duplicate: {name} (id={ds.id} -> {unique_by_name[name].id})")
            id_remap[ds.id] = unique_by_name[name].id
        else:
            unique_by_name[name] = ds
            id_remap[ds.id] = ds.id  # Maps to itself
    
    deduped_datastores = list(unique_by_name.values())
    
    print(f"[DEBUG] After dedup: {len(deduped_datastores)} datastores")
    for ds in deduped_datastores:
        print(f"[DEBUG]   - id={ds.id}, name={ds.name}")
    
    # Fix access patterns to point to deduplicated datastore IDs
    fixed_access_patterns: List[DataAccess] = []
    for access in access_patterns:
        new_datastore_id = id_remap.get(access.datastore_id, access.datastore_id)
        fixed_access_patterns.append(DataAccess(
            service_id=access.service_id,
            datastore_id=new_datastore_id,
            access_type=access.access_type,
        ))
    
    return deduped_datastores, fixed_access_patterns


@dataclass
class DataIR(BaseIR):
    datastores: List[DataStore] = field(default_factory=list)
    access_patterns: List[DataAccess] = field(default_factory=list)

    def __post_init__(self):
        # Deduplicate immediately on creation
        self.datastores, self.access_patterns = deduplicate_datastores(
            self.datastores, self.access_patterns
        )

    def to_dict(self) -> dict:
        """Custom serialization that ensures deduplication."""
        # Deduplicate one more time before serialization
        unique_datastores: Dict[str, DataStore] = {}
        for ds in self.datastores:
            if ds.name not in unique_datastores:
                unique_datastores[ds.name] = ds
        
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trace": asdict(self.trace) if self.trace else None,
            "datastores": [asdict(ds) for ds in unique_datastores.values()],
            "access_patterns": [asdict(ap) for ap in self.access_patterns],
        }

    def validate(self) -> ValidationResult:
        errors = []

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
