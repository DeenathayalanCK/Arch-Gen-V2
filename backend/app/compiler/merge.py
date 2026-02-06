from app.compiler.types import Graph, Edge
from app.compiler.normalize import (
    normalize_business,
    normalize_service,
    normalize_data,
    normalize_infra,
)
from app.pipeline.context import PipelineContext


def merge_context(context: PipelineContext) -> Graph:
    graph = Graph()

    # -------------------------
    # Business Layer
    # -------------------------
    if context.business_ir:
        graph.nodes.extend(normalize_business(context.business_ir))

    # -------------------------
    # Service Layer
    # -------------------------
    service_id_by_name = {}

    if context.service_ir:
        service_nodes = normalize_service(context.service_ir)
        graph.nodes.extend(service_nodes)

        # Build lookup: service name -> service id
        for svc in context.service_ir.services:
            service_id_by_name[svc.name] = svc.id

        # Service-to-service dependencies (unchanged)
        for dep in context.service_ir.dependencies:
            graph.edges.append(
                Edge(
                    source=dep.from_service_id,
                    target=dep.to_service_id,
                    label=dep.interaction,
                )
            )

    # -------------------------
    # Data Layer + Wiring
    # -------------------------
    datastore_ids = set()
    seen_edges = set()  # prevent visual duplicates

    if context.data_ir:
        data_nodes = normalize_data(context.data_ir)
        graph.nodes.extend(data_nodes)

        # Collect valid datastore IDs from IR
        for ds in context.data_ir.datastores:
            datastore_ids.add(ds.id)

        # Service -> Data edges (ID-correct, deduplicated)
        for access in context.data_ir.access_patterns:
            service_id = service_id_by_name.get(access.service_id)
            datastore_id = access.datastore_id

            # Safety checks (compiler correctness)
            if not service_id:
                continue
            if datastore_id not in datastore_ids:
                continue

            edge_key = (service_id, datastore_id, access.access_type)
            if edge_key in seen_edges:
                continue

            seen_edges.add(edge_key)

            graph.edges.append(
                Edge(
                    source=service_id,
                    target=datastore_id,
                    label=access.access_type,
                )
            )

    # -------------------------
    # Infrastructure Layer
    # -------------------------
    if context.infra_ir:
        graph.nodes.extend(normalize_infra(context.infra_ir))

    return graph
