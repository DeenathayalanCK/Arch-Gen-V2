from app.compiler.types import Node
from app.ir.business_ir import BusinessIR
from app.ir.service_ir import ServiceIR
from app.ir.data_ir import DataIR
from app.ir.infra_ir import InfraIR


# -------------------------
# Business Layer
# -------------------------

def normalize_business(ir: BusinessIR) -> list[Node]:
    nodes = []
    for actor in ir.actors:
        nodes.append(
            Node(
                actor.id,
                actor.name,
                "business",
            )
        )
    return nodes


# -------------------------
# Service Layer
# -------------------------

def normalize_service(ir: ServiceIR) -> list[Node]:
    return [
        Node(
            service.id,
            service.name,
            "service",
        )
        for service in ir.services
    ]


# -------------------------
# Data Layer (CRITICAL FIX)
# -------------------------

def normalize_data(ir: DataIR) -> list[Node]:
    

    nodes: list[Node] = []
    seen: dict[str, str] = {}  # datastore_name -> datastore_id

    for store in ir.datastores:
        # Deduplicate by canonical datastore name
        if store.name in seen:
            continue

        seen[store.name] = store.id

        nodes.append(
            Node(
                store.id,
                f"Data: {store.name}",
                "data",
            )
        )

    return nodes


# -------------------------
# Infrastructure Layer
# -------------------------

def normalize_infra(ir: InfraIR) -> list[Node]:
    return [
        Node(
            node.id,
            node.name,
            "infra",
        )
        for node in ir.compute
    ]
