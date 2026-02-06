from typing import Dict, List
import re

from app.pipeline.stage import PipelineStage
from app.ir.validation import ValidationResult
from app.ir.data_ir import DataIR, DataStore, DataAccess


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
# Responsibility → Data Rules
# -------------------------

def infer_datastore_access(responsibility_name: str) -> Dict[str, str]:
    """
    Infer datastore access from responsibility semantics.
    Returns: { datastore_name: access_type }
    """
    name = responsibility_name.lower()
    access = {}

    if "order" in name:
        access["Order"] = "read_write"

    if "payment" in name or "transaction" in name:
        access["Payment"] = "read_write"

    if any(k in name for k in ["user", "identity", "credential", "session"]):
        access["User"] = "read_write"

    if "validate" in name:
        # downgrade access to read if already inferred
        for k in access:
            access[k] = "read"

    return access


# -------------------------
# Data Stage (Step 3)
# -------------------------

class DataStage(PipelineStage):
    name = "data"

    def run(self, context) -> ValidationResult:
        if not context.service_ir:
            return ValidationResult.success()

        datastore_map: Dict[str, DataStore] = {}
        access_patterns: List[DataAccess] = []

        # -------------------------
        # Build Datastores
        # -------------------------

        for service in context.service_ir.services:
            for ds_name in self._infer_possible_datastores(
                service.name, context.requirements_text
            ):
                canonical = canonical_datastore_name(ds_name)
                if canonical not in datastore_map:
                    datastore_map[canonical] = DataStore(
                        name=canonical,
                        store_type="sql",
                    )

        # -------------------------
        # Responsibility-Aware Wiring
        # -------------------------

        for service in context.service_ir.services:
            responsibilities = context.responsibility_map.get(service.id)
            if not responsibilities:
                continue

            for resp in responsibilities.responsibilities:
                inferred = infer_datastore_access(resp.name)

                for datastore_name, access_type in inferred.items():
                    if datastore_name in datastore_map:
                        access_patterns.append(
                            DataAccess(
                                service_id=service.name,
                                datastore_id=datastore_map[datastore_name].id,
                                access_type=access_type,
                            )
                        )

        # -------------------------
        # Finalize Data IR
        # -------------------------

        context.data_ir = DataIR(
            datastores=list(datastore_map.values()),
            access_patterns=access_patterns,
        )

        return ValidationResult.success()

    # -------------------------
    # Baseline Datastore Inference
    # -------------------------

    def _infer_possible_datastores(self, service_name: str, text: str) -> List[str]:
        combined = f"{service_name} {text}".lower()
        stores = []

        if "order" in combined:
            stores.append("Order")

        if "payment" in combined:
            stores.append("Payment")

        if any(k in combined for k in ["user", "customer", "identity"]):
            stores.append("User")

        return stores
