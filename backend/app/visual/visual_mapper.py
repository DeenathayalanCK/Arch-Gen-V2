from app.visual.visual_schema import VisualNode, VisualEdge, VisualDiagram
from app.visual.visual_style import VISUAL_STYLE


def map_context_to_visual_ir(context) -> VisualDiagram:
    """
    Transform semantic architecture IRs into a unified Visual IR.
    Maps: business_ir, service_ir, responsibility_map, data_ir, infra_ir → VisualDiagram
    """
    nodes: list[VisualNode] = []
    edges: list[VisualEdge] = []
    node_index: dict[str, VisualNode] = {}

    # Build lookups for edge generation
    service_id_to_name: dict[str, str] = {}
    service_name_to_id: dict[str, str] = {}
    datastore_id_to_name: dict[str, str] = {}

    # -------------------------
    # ACTORS (from business_ir)
    # -------------------------
    if context.business_ir and context.business_ir.actors:
        for actor in context.business_ir.actors:
            style = VISUAL_STYLE["actor"]
            node = VisualNode(
                id=actor.id,
                label=actor.name,
                node_type="actor",
                layer=style["layer"],
                shape=style["shape"],
                color=style["color"],
            )
            nodes.append(node)
            node_index[actor.id] = node

    # -------------------------
    # SERVICES & APPLICATIONS
    # -------------------------
    if context.service_ir and context.service_ir.services:
        for service in context.service_ir.services:
            service_id_to_name[service.id] = service.name
            service_name_to_id[service.name] = service.id

            if service.service_type == "edge":
                style = VISUAL_STYLE.get("web_app", VISUAL_STYLE["service"])
                node_type = "web_app"
            else:
                style = VISUAL_STYLE["service"]
                node_type = "service"

            details: list[str] = []
            resp_block = context.responsibility_map.get(service.id)
            if resp_block:
                for r in resp_block.responsibilities:
                    details.append(f"• {r.name}")

            node = VisualNode(
                id=service.id,
                label=service.name,
                node_type=node_type,
                layer=style["layer"],
                shape=style["shape"],
                color=style["color"],
                details=details,
                group="services",
            )
            nodes.append(node)
            node_index[service.id] = node

    # -------------------------
    # DATA STORES
    # -------------------------
    if context.data_ir and context.data_ir.datastores:
        for store in context.data_ir.datastores:
            datastore_id_to_name[store.id] = store.name
            style = VISUAL_STYLE["database"]
            node = VisualNode(
                id=store.id,
                label=store.name,
                node_type="database",
                layer=style["layer"],
                shape=style["shape"],
                color=style["color"],
            )
            nodes.append(node)
            node_index[store.id] = node

    # -------------------------
    # INFRASTRUCTURE
    # -------------------------
    if context.infra_ir:
        infra_style = VISUAL_STYLE.get("infrastructure", VISUAL_STYLE["service"])
        for compute in getattr(context.infra_ir, "compute", []):
            node = VisualNode(
                id=compute.id,
                label=compute.name,
                node_type="infrastructure",
                layer="infra",
                shape=infra_style["shape"],
                color=infra_style["color"],
            )
            nodes.append(node)
            node_index[compute.id] = node

        for network in getattr(context.infra_ir, "network", []):
            node = VisualNode(
                id=network.id,
                label=network.name,
                node_type="infrastructure",
                layer="infra",
                shape=infra_style["shape"],
                color=infra_style["color"],
            )
            nodes.append(node)
            node_index[network.id] = node

    # =========================================================
    # EDGES
    # =========================================================

    # -------------------------
    # SERVICE → SERVICE DEPENDENCIES
    # -------------------------
    if context.service_ir and context.service_ir.dependencies:
        for dep in context.service_ir.dependencies:
            edges.append(
                VisualEdge(
                    source=dep.from_service_id,
                    target=dep.to_service_id,
                    relation=dep.interaction or "calls",
                    style="solid",
                )
            )

    # -------------------------
    # SERVICE → DATASTORE (data access patterns)
    # -------------------------
    if context.data_ir and context.data_ir.access_patterns:
        for access in context.data_ir.access_patterns:
            # access.service_id is the service NAME in this repo
            source_id = service_name_to_id.get(access.service_id, access.service_id)
            edges.append(
                VisualEdge(
                    source=source_id,
                    target=access.datastore_id,
                    relation=access.access_type,
                    style="dotted",
                )
            )

    # -------------------------
    # RESPONSIBILITY → RESPONSIBILITY DEPENDENCIES
    # -------------------------
    if context.responsibility_dependencies:
        for dep in context.responsibility_dependencies:
            # These use service names - map to IDs for consistency
            from_svc_id = service_name_to_id.get(dep.from_service, dep.from_service)
            to_svc_id = service_name_to_id.get(dep.to_service, dep.to_service)
            edges.append(
                VisualEdge(
                    source=from_svc_id,
                    target=to_svc_id,
                    relation=f"{dep.from_responsibility} → {dep.to_responsibility}",
                    style="dashed",
                )
            )

    # -------------------------
    # RESPONSIBILITY → DATASTORE ACCESS
    # -------------------------
    if context.responsibility_data_access:
        for access in context.responsibility_data_access:
            # Find service ID from name
            svc_id = service_name_to_id.get(access.service_name, access.service_name)
            # Find datastore ID from name
            ds_id = None
            for did, dname in datastore_id_to_name.items():
                if dname == access.datastore_name:
                    ds_id = did
                    break
            if ds_id:
                edges.append(
                    VisualEdge(
                        source=svc_id,
                        target=ds_id,
                        relation=access.access_type,
                        style="dotted",
                    )
                )

    # -------------------------
    # ACTOR → EDGE SERVICE (business flow)
    # -------------------------
    web_apps = [n for n in nodes if n.node_type == "web_app"]
    actors = [n for n in nodes if n.node_type == "actor"]

    if web_apps and actors:
        for actor in actors:
            edges.append(
                VisualEdge(
                    source=actor.id,
                    target=web_apps[0].id,
                    relation="uses",
                    style="dashed",
                )
            )

    # -------------------------
    # SERVICE → INFRASTRUCTURE
    # -------------------------
    if context.infra_ir and context.service_ir:
        compute_nodes = [n for n in nodes if n.node_type == "infrastructure" and "compute" in n.label.lower() or "runtime" in n.label.lower()]
        if not compute_nodes:
            # Fallback: use first infra node
            compute_nodes = [n for n in nodes if n.node_type == "infrastructure"]

        if compute_nodes:
            for svc_node in [n for n in nodes if n.node_type in ("service", "web_app")]:
                edges.append(
                    VisualEdge(
                        source=svc_node.id,
                        target=compute_nodes[0].id,
                        relation="runs on",
                        style="solid",
                    )
                )

    # -------------------------
    # WEB APP → BACKEND SERVICES (explicit edge for edge→logical)
    # -------------------------
    if context.service_ir:
        web_app_nodes = [n for n in nodes if n.node_type == "web_app"]
        backend_nodes = [n for n in nodes if n.node_type == "service"]
        
        # Create explicit edges from web apps to backend services
        for web_app in web_app_nodes:
            for backend in backend_nodes:
                # Only add if not already covered by service dependencies
                edge_exists = any(
                    e.source == web_app.id and e.target == backend.id 
                    for e in edges
                )
                if not edge_exists:
                    edges.append(
                        VisualEdge(
                            source=web_app.id,
                            target=backend.id,
                            relation="calls",
                            style="solid",
                        )
                    )

    return VisualDiagram(
        nodes=nodes,
        edges=edges,
        layout="top-down",
    )
