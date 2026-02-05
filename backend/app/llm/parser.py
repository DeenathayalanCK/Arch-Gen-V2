import json
from app.ir.business_ir import BusinessIR, Actor, BusinessFlow, BusinessStep
from app.ir.service_ir import ServiceIR, Service, ServiceDependency
from app.ir.data_ir import DataIR, DataStore, DataAccess
from app.ir.infra_ir import InfraIR, ComputeNode, NetworkBoundary


def parse_business(json_text: str) -> BusinessIR:
    data = json.loads(json_text)

    # ---- ACTORS ----
    actors = []
    for a in data.get("actors", []):
        # CASE 1: actor is a string
        if isinstance(a, str):
            actors.append(
                Actor(
                    name=a,
                    role="unknown",
                )
            )

        # CASE 2: actor is a dict
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
            # CASE 1: step is a string
            if isinstance(s, str):
                steps.append(
                    BusinessStep(
                        name=s,
                        actor_id=actors[0].name if actors else "unknown",
                        order=len(steps) + 1,
                    )
                )

            # CASE 2: step is a dict
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



def parse_service(json_text: str) -> ServiceIR:
    data = json.loads(json_text)

    services = []
    for s in data.get("services", []):
        # CASE 1: service is a string
        if isinstance(s, str):
            name = s

        # CASE 2: service is a dict
        elif isinstance(s, dict):
            name = s.get("name", "unknown")

        else:
            continue

        if not name.endswith("Service"):
            name = f"{name}Service"

        services.append(
            Service(
                name=name
            )
        )

    return ServiceIR(
        name="Services",
        services=services,
    )



def parse_data(json_text: str) -> DataIR:
    data = json.loads(json_text)

    datastores = []
    for d in data.get("datastores", []):
        # CASE 1: d is a string (e.g. "database")
        if isinstance(d, str):
            datastores.append(
                DataStore(
                    name=d,
                    store_type="unknown",
                )
            )

        # CASE 2: d is a dict
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



def parse_infra(json_text: str) -> InfraIR:
    data = json.loads(json_text)

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

