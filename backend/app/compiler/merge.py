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

        # 🔑 service name → rendered svc_* node id
        for node in service_nodes:
            if node.id.startswith("svc_"):
                service_name = node.label.replace("Service:", "").strip()
                service_node_id_by_name[service_name] = node.id

        # Service → Service dependencies
        for dep in context.service_ir.dependencies:
            src = service_node_id_by_name.get(dep.from_service_id)
            tgt = service_node_id_by_name.get(dep.to_service_id)

            if not src or not tgt:
                continue

            graph.edges.append(
                Edge(
                    source=src,
                    target=tgt,
                    label=dep.interaction,
                )
            )


    # -------------------------
    # Service → Service Dependency Inference
    # -------------------------
    # service_name -> rendered svc_* id map
    svc_map = service_node_id_by_name

    if context.service_ir:
        for svc in context.service_ir.services:
            svc_id = svc_map.get(svc.name)
            if not svc_id:
                continue

            name_lower = svc.name.lower()

            # Web Application calls Order Management
            if "web application" in name_lower or "web" in name_lower:
                target = svc_map.get("Order Management Service")
                if target and target != svc_id:
                    graph.edges.append(
                        Edge(
                            source=svc_id,
                            target=target,
                            label="calls",
                        )
                    )

            # Order Management calls Payment & Identity
            if "order management" in name_lower:
                payment_target = svc_map.get("Payment Service")
                if payment_target:
                    graph.edges.append(
                        Edge(
                            source=svc_id,
                            target=payment_target,
                            label="calls",
                        )
                    )
                identity_target = svc_map.get("Customer Identity Service")
                if identity_target:
                    graph.edges.append(
                        Edge(
                            source=svc_id,
                            target=identity_target,
                            label="calls",
                        )
                    )

    # -------------------------
    # Data Layer + Wiring
    # -------------------------
    if context.data_ir:
        data_nodes = normalize_data(context.data_ir)
        graph.nodes.extend(data_nodes)

        datastore_ids = {ds.id for ds in context.data_ir.datastores}
        seen_edges = set()

        for access in context.data_ir.access_patterns:
            svc_id = service_node_id_by_name.get(access.service_id)
            ds_id = access.datastore_id

            if not svc_id or ds_id not in datastore_ids:
                continue

            key = (svc_id, ds_id, access.access_type)
            if key in seen_edges:
                continue
            seen_edges.add(key)

            graph.edges.append(
                Edge(
                    source=svc_id,
                    target=ds_id,
                    label=access.access_type,
                )
            )

    # -------------------------
    # Infrastructure Layer
    # -------------------------
    if context.infra_ir:
        infra_nodes = normalize_infra(context.infra_ir)
        graph.nodes.extend(infra_nodes)

    # -------------------------
    # Service → Infrastructure Wiring (FINAL)
    # -------------------------
    service_node_ids = [
        node.id for node in graph.nodes
        if node.id.startswith("svc_")
    ]
    compute_node_ids = [
        node.id for node in graph.nodes
        if node.id.startswith("infra_compute_")
    ]
    network_node_ids = [
        node.id for node in graph.nodes
        if node.id.startswith("infra_net_")
    ]

    seen_edges = set()

    # Service → Compute
    for svc_id in service_node_ids:
        for compute_id in compute_node_ids:
            key = (svc_id, compute_id, "runs on")
            if key in seen_edges:
                continue
            seen_edges.add(key)

            graph.edges.append(
                Edge(
                    source=svc_id,
                    target=compute_id,
                    label="runs on",
                )
            )

    # Service → Network
    for svc_id in service_node_ids:
        for net_id in network_node_ids:
            key = (svc_id, net_id, "inside")
            if key in seen_edges:
                continue
            seen_edges.add(key)

            graph.edges.append(
                Edge(
                    source=svc_id,
                    target=net_id,
                    label="inside",
                )
            )

    return graph
