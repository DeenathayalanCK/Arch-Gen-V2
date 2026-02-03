from app.ir.architecture import ArchitectureIR
import re


def _normalize_id(value: str) -> str:
    """
    Converts free text into safe snake_case ids.
    """
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def enrich_architecture_ir(ir: ArchitectureIR) -> ArchitectureIR:
    """
    Deterministically enriches Architecture IR without changing intent.
    """

    # ---- Normalize actor IDs ----
    for actor in ir.actors:
        actor.id = _normalize_id(actor.id)

    # ---- Normalize capability IDs & infer state ----
    for cap in ir.capabilities:
        cap.id = _normalize_id(cap.id)

        text = cap.purpose.lower()

        # Infer persistent state only if strongly implied
        if cap.state == "none":
            if any(word in text for word in ["store", "persist", "record", "manage", "history"]):
                cap.state = "persistent"

        # Infer regulatory constraints only if explicit
        if any(word in text for word in ["health", "financial", "personal", "consent"]):
            if "regulated" not in cap.constraints:
                cap.constraints.append("regulated")

    # ---- Normalize data entities & sensitivity ----
    for data in ir.data_entities:
        data.id = _normalize_id(data.id)

        text = data.description.lower()
        if "health" in text or "personal" in text:
            data.sensitivity = "restricted"

    # ---- Infer trust crossings (only if actor involved) ----
    actor_ids = {a.id for a in ir.actors}

    for interaction in ir.interactions:
        if interaction.source in actor_ids:
            interaction.trust_crossing = True

    # ---- Record enrichment assumptions (explicit!) ----
    ir.assumptions.append(
        "Some constraints and state types were inferred deterministically from wording."
    )

    return ir
