import json
import re
from typing import Any, Dict

from app.ir.business_ir import BusinessIR, Actor, BusinessFlow, BusinessStep
from app.ir.service_ir import ServiceIR, Service, ServiceDependency
from app.ir.data_ir import DataIR, DataStore, DataAccess
from app.ir.infra_ir import InfraIR, ComputeNode, NetworkBoundary


# ============================================================
# SAFE JSON LOADER (LLM TRUST BOUNDARY)
# ============================================================

def safe_load_json(json_text: str) -> Dict[str, Any]:
    """
    Safely extract and parse JSON from LLM output.

    Strategy:
    1. Try direct json.loads (fast path)
    2. Fallback to extracting first JSON object
    3. Fail gracefully with empty dict

    NEVER throws.
    """

    if not json_text or not isinstance(json_text, str):
        return {}

    # Fast path
    try:
        return json.loads(json_text)
    except Exception:
        pass

    # Fallback: extract first JSON object
    match = re.search(r"\{.*\}", json_text, re.DOTALL)
    if not match:
        return {}

    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


# ============================================================
# BUSINESS PARSER
# ============================================================

def parse_business(json_text: str) -> BusinessIR:
    data = safe_load_json(json_text)

    # ---- ACTORS ----
    actors = []
    for a in data.get("actors", []):
        if isinstance(a, str):
            actors.append(
                Actor(
                    name=a,
                    role="unknown",
                )
            )
        elif isinstance(a, dict):
            actors.append(
                Actor(
                    name=a.get("name", "unknown"),
                    role=a.get("role", "unknown"),
                )
            )

    actor_ids = {a.name for a in actors}

    # ---- FLOWS ----
    flows = []
    for f in data.get("flows", []):
        if not isinstance(f, dict):
            continue

        steps = []
        for s in f.get("steps", []):
            if isinstance(s, str):
                steps.append(
                    BusinessStep(
                        name=s,
                        actor_id=actors[0].name if actors else "unknown",
                        order=len(steps) + 1,
                    )
                )
            elif isinstance(s, dict):
                actor = s.get("actor", "unknown")
                if actor not in actor_ids and actor_ids:
                    actor = actors[0].name

                steps.append(
                    BusinessStep(
                        name=s.get("name", "unknown"),
                        actor_id=actor,
                        order=s.get("order", len(steps) + 1),
                    )
                )

        flows.append(
            BusinessFlow(
                name=f.get("name", "Business Flow"),
                steps=steps,
            )
        )

    return BusinessIR(
        name="Business",
        actors=actors,
        flows=flows,
    )


# ============================================================
# SERVICE PARSER
# ============================================================

def parse_service(json_text: str) -> ServiceIR:
    data = safe_load_json(json_text)

    services = []
    for s in data.get("services", []):
        if isinstance(s, str):
            name = s
        elif isinstance(s, dict):
            name = s.get("name", "unknown")
        else:
            continue

        if not name.endswith("Service"):
            name = f"{name}Service"

        services.append(Service(name=name))

    return ServiceIR(
        name="Services",
        services=services,
    )


# ============================================================
# DATA PARSER
# ============================================================

def parse_data(json_text: str) -> DataIR:
    data = safe_load_json(json_text)

    datastores = []
    for d in data.get("datastores", []):
        if isinstance(d, str):
            datastores.append(
                DataStore(
                    name=d,
                    store_type="unknown",
                )
            )
        elif isinstance(d, dict):
            datastores.append(
                DataStore(
                    name=d.get("name", "unknown"),
                    store_type=d.get("store_type", "unknown"),
                )
            )

    access_patterns = []
    for a in data.get("access_patterns", []):
        if isinstance(a, dict):
            access_patterns.append(
                DataAccess(
                    service_id=a.get("service", "unknown"),
                    datastore_id=a.get("datastore", "unknown"),
                    access_type=a.get("access_type", "unknown"),
                )
            )

    return DataIR(
        name="Data",
        datastores=datastores,
        access_patterns=access_patterns,
    )


# ============================================================
# INFRA PARSER
# ============================================================

def parse_infra(json_text: str) -> InfraIR:
    data = safe_load_json(json_text)

    compute = []
    for c in data.get("compute", []):
        if isinstance(c, dict):
            compute.append(
                ComputeNode(
                    name=c.get("name", "unknown"),
                    compute_type=c.get("compute_type", "unknown"),
                )
            )
        elif isinstance(c, str):
            compute.append(
                ComputeNode(
                    name=c,
                    compute_type="unknown",
                )
            )

    network = []
    for n in data.get("network", []):
        if isinstance(n, dict):
            network.append(
                NetworkBoundary(
                    name=n.get("name", "unknown"),
                    boundary_type=n.get("boundary_type", "unknown"),
                )
            )
        elif isinstance(n, str):
            network.append(
                NetworkBoundary(
                    name=n,
                    boundary_type="unknown",
                )
            )

    return InfraIR(
        name="Infra",
        compute=compute,
        network=network,
    )
