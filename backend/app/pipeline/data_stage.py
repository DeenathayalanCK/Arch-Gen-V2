from typing import Dict, List, Tuple

from app.pipeline.stage import PipelineStage
from app.ir.validation import ValidationResult
from app.ir.data_ir import (
    DataIR,
    DataStore,
    DataAccess,
    canonical_datastore_name,
    deduplicate_datastores,
)


# -------------------------
# Responsibility → Data Rules
# -------------------------

def infer_datastore_access(responsibility_name: str) -> Dict[str, str]:
    """
    Infer datastore access from responsibility semantics.
    Returns: { datastore_name: access_type }
    """
    name = (responsibility_name or "").lower()
    access: Dict[str, str] = {}

    if "order" in name:
        access["Order"] = "read_write"

    if "payment" in name or "transaction" in name:
        access["Payment"] = "read_write"

    if any(k in name for k in ["user", "identity", "credential", "session"]):
        access["User"] = "read_write"

    # Validation responsibilities are usually read-only
    if "validate" in name or "verification" in name:
        for k in list(access.keys()):
            access[k] = "read"

    return access


# -------------------------
# Data Stage (Hardened + Config Driven)
# -------------------------

class DataStage(PipelineStage):
    name = "data"

    def run(self, context) -> ValidationResult:

        if not context.service_ir:
            return ValidationResult.success()

        # canonical_name -> DataStore
        datastore_map: Dict[str, DataStore] = {}
        access_patterns: List[DataAccess] = []

        # =====================================================
        # 1️⃣ Discover Datastores (Service name + Requirements + Responsibilities)
        # =====================================================

        for service in context.service_ir.services:
            seeds: List[str] = []

            # Baseline inference from service name + requirements
            seeds.extend(
                self._infer_possible_datastores(
                    service.name,
                    context.requirements_text
                )
            )

            # Responsibility-based discovery
            responsibilities = context.responsibility_map.get(service.id)
            if responsibilities:
                for resp in responsibilities.responsibilities:
                    seeds.extend(
                        infer_datastore_access(resp.name).keys()
                    )

            # Create canonical datastore entries
            for raw_name in seeds:
                canonical = canonical_datastore_name(raw_name)
                if not canonical:
                    continue

                if canonical not in datastore_map:
                    datastore_map[canonical] = DataStore(
                        name=canonical,
                        store_type="database",  # ✅ FIXED (was sql)
                    )

        # =====================================================
        # 2️⃣ Build Deduplicated Access Map
        # =====================================================

        service_access: Dict[Tuple[str, str], str] = {}

        for service in context.service_ir.services:
            responsibilities = context.responsibility_map.get(service.id)
            if not responsibilities:
                continue

            for resp in responsibilities.responsibilities:
                inferred = infer_datastore_access(resp.name)

                for raw_name, access_type in inferred.items():
                    canonical = canonical_datastore_name(raw_name)
                    if not canonical:
                        continue

                    if canonical not in datastore_map:
                        continue

                    key = (service.name, canonical)
                    existing = service_access.get(key)

                    # Promote access
                    if existing == "read_write":
                        continue

                    if existing == "read" and access_type == "read_write":
                        service_access[key] = "read_write"
                    elif not existing:
                        service_access[key] = access_type

        # Materialize DataAccess
        for (service_name, datastore_name), access_type in service_access.items():
            access_patterns.append(
                DataAccess(
                    service_id=service_name,
                    datastore_id=datastore_map[datastore_name].id,
                    access_type=access_type,
                )
            )

        # =====================================================
        # 2.5️⃣ DOMAIN BASELINE DATASTORE INJECTION (CONFIG DRIVEN)
        # =====================================================

        domain_context = getattr(context, "domain_context", None)

        if domain_context and domain_context.domain_rules:
            baseline_datastores = domain_context.domain_rules.get(
                "baseline_datastores",
                []
            )

            for ds in baseline_datastores:
                ds_name = ds.get("name")
                if not ds_name:
                    continue

                canonical = canonical_datastore_name(ds_name)
                if not canonical:
                    continue

                if canonical not in datastore_map:
                    datastore_map[canonical] = DataStore(
                        name=canonical,
                        store_type=ds.get("type", "database"),
                    )

        # =====================================================
        # 3️⃣ Finalize Data IR (Dedup Safe)
        # =====================================================

        all_datastores = list(datastore_map.values())

        final_datastores, final_access_patterns = deduplicate_datastores(
            all_datastores,
            access_patterns,
        )

        # Deduplicate access edges
        seen_edges = set()
        unique_access_patterns: List[DataAccess] = []

        for a in final_access_patterns:
            key = (a.service_id, a.datastore_id)
            if key in seen_edges:
                continue

            seen_edges.add(key)
            unique_access_patterns.append(a)

        context.data_ir = DataIR(
            datastores=final_datastores,
            access_patterns=unique_access_patterns,
        )

        return ValidationResult.success()

    # =====================================================
    # Baseline Datastore Inference (Keyword Based)
    # =====================================================

    def _infer_possible_datastores(self, service_name: str, text: str) -> List[str]:
        combined = f"{service_name or ''} {text or ''}".lower()
        stores: List[str] = []

        if "order" in combined:
            stores.append("Order")

        if "payment" in combined:
            stores.append("Payment")

        if any(k in combined for k in ["user", "customer", "identity"]):
            stores.append("User")

        if "health" in combined or "medical" in combined:
            stores.append("Health Records")

        return stores
