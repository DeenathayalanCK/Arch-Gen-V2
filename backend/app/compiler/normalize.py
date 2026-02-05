from app.compiler.types import Node
from app.ir.business_ir import BusinessIR
from app.ir.service_ir import ServiceIR
from app.ir.data_ir import DataIR
from app.ir.infra_ir import InfraIR


def normalize_business(ir: BusinessIR) -> list[Node]:
    nodes = []
    for actor in ir.actors:
        nodes.append(Node(actor.id, actor.name, "business"))
    return nodes


def normalize_service(ir: ServiceIR) -> list[Node]:
    return [
        Node(service.id, service.name, "service")
        for service in ir.services
    ]


def normalize_data(ir: DataIR) -> list[Node]:
    return [
        Node(store.id, store.name, "data")
        for store in ir.datastores
    ]


def normalize_infra(ir: InfraIR) -> list[Node]:
    return [
        Node(node.id, node.name, "infra")
        for node in ir.compute
    ]
