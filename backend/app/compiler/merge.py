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
    
    service_node_id_by_name = {}

    if context.service_ir:
        service_nodes = normalize_service(context.service_ir)
        graph.nodes.extend(service_nodes)

        # 🔑 Build lookup: service name -> rendered node id (svc_*)
        for node in service_nodes:
            if node.id.startswith("svc_"):
                service_name = node.label.replace("Service:", "").strip()
                service_node_id_by_name[service_name] = node.id

        # Service-to-service dependencies (unchanged)
        for dep in context.service_ir.dependencies:
            graph.edges.append(
                Edge(
                    source=service_node_id_by_name.get(dep.from_service_id),
                    target=service_node_id_by_name.get(dep.to_service_id),
                    label=dep.interaction,
                )
            )

    # -------------------------
    # Data Layer + Wiring
    # -------------------------
    datastore_ids = set()
    seen_edges = set()

    if context.data_ir:
        data_nodes = normalize_data(context.data_ir)
        graph.nodes.extend(data_nodes)

        for ds in context.data_ir.datastores:
            datastore_ids.add(ds.id)

        for access in context.data_ir.access_patterns:
            service_node_id = service_node_id_by_name.get(access.service_id)
            datastore_id = access.datastore_id

            if not service_node_id or datastore_id not in datastore_ids:
                continue

            edge_key = (service_node_id, datastore_id, access.access_type)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            graph.edges.append(
                Edge(
                    source=service_node_id,     # 🔥 svc_* ID
                    target=datastore_id,
                    label=access.access_type,
                )
            )


    # -------------------------
    # Infrastructure Layer
    # -------------------------
    # -------------------------
    # Service → Infrastructure Wiring
    # -------------------------
    if context.infra_ir and context.service_ir:
        # Collect compute & network nodes
        compute_nodes = [c.id for c in context.infra_ir.compute]
        network_nodes = [n.id for n in context.infra_ir.network]

        # Collect rendered service node IDs (svc_*)
        service_node_ids = [
            node.id for node in graph.nodes
            if node.type == "service"
        ]

        seen_edges = set()

        # Service → Compute (runs on)
        for svc_id in service_node_ids:
            for compute_id in compute_nodes:
                edge_key = (svc_id, compute_id, "runs_on")
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)

                graph.edges.append(
                    Edge(
                        source=svc_id,
                        target=compute_id,
                        label="runs on",
                    )
                )

        # Service → Network (inside)
        for svc_id in service_node_ids:
            for net_id in network_nodes:
                edge_key = (svc_id, net_id, "inside")
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)

                graph.edges.append(
                    Edge(
                        source=svc_id,
                        target=net_id,
                        label="inside",
                    )
                )


    return graph
