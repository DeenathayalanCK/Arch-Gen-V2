#backend\app\compiler\compiler.py

from typing import List, Optional
import re

from app.pipeline.context import PipelineContext
from app.ir.business_ir import BusinessIR
from app.ir.service_ir import ServiceIR
from app.ir.data_ir import DataIR
from app.ir.infra_ir import InfraIR
from app.ir.responsibility_ir import ServiceResponsibilities


# ============================================================
# Mermaid ID helper (CRITICAL FIX)
# ============================================================

def mermaid_id(text: str) -> str:
    """
    Convert any human-readable string into a Mermaid-safe ID.
    Deterministic and collision-safe.
    """
    return re.sub(r"[^a-zA-Z0-9_]", "_", text)


# ============================================================
# Mermaid Diagram Builder
# ============================================================

class MermaidDiagram:
    """
    Deterministic Mermaid diagram builder.
    No inference. No LLM usage.
    """

    def __init__(self):
        self.lines: List[str] = ["flowchart TD"]
        self._nodes: set[str] = set()
        self._edges: set[tuple[str, str, Optional[str]]] = set()

    # ---------- helpers ----------

    def _add_node(self, node_id: str, label: str):
        if node_id not in self._nodes:
            self.lines.append(f'  {node_id}["{label}"]')
            self._nodes.add(node_id)

    def _add_edge(self, src: str, dst: str, label: Optional[str] = None):
        edge_key = (src, dst, label)
        if edge_key in self._edges:
            return
        self._edges.add(edge_key)

        if label:
            self.lines.append(f"  {src} -->|{label}| {dst}")
        else:
            self.lines.append(f"  {src} --> {dst}")

    # ---------- business ----------

    def add_business(self, ir: BusinessIR):
        self.lines.append("  %% Business Layer")

        for actor in sorted(ir.actors, key=lambda a: a.name):
            actor_id = f"actor_{mermaid_id(actor.name)}"
            self._add_node(actor_id, f"Actor: {actor.name}")

        for flow in sorted(ir.flows, key=lambda f: f.name):
            prev_step = None
            for step in sorted(flow.steps, key=lambda s: s.order):
                step_node = f"biz_step_{mermaid_id(step.id)}"
                self._add_node(step_node, step.name)

                actor_node = f"actor_{mermaid_id(step.actor_id)}"
                self._add_edge(actor_node, step_node)

                if prev_step:
                    self._add_edge(prev_step, step_node)

                prev_step = step_node

    # ---------- services ----------

    def add_services_with_responsibilities(
        self,
        service_ir: ServiceIR,
        responsibility_map: dict[str, ServiceResponsibilities],
    ):
        self.lines.append("  %% Service Layer")

        for service in sorted(service_ir.services, key=lambda s: s.name):
            svc_id = f"svc_{mermaid_id(service.name)}"

            # 🔒 Explicit service node
            self._add_node(svc_id, f"Service: {service.name}")

            self.lines.append(f"  subgraph {svc_id}")

            resp_bundle = responsibility_map.get(service.id)
            if resp_bundle:
                for resp in sorted(resp_bundle.responsibilities, key=lambda r: r.name):
                    resp_id = f"{svc_id}_{mermaid_id(resp.name)}"
                    self._add_node(resp_id, resp.name)

            self.lines.append("  end")

    # ---------- data ----------

    def add_data(self, ir: DataIR):
        self.lines.append("  %% Data Layer")

        for store in sorted(ir.datastores, key=lambda d: d.name):
            self._add_node(
                f"data_{mermaid_id(store.name)}",
                f"Data: {store.name}",
            )

    # ---------- data access edges ----------

    def add_data_access_edges(self, data_ir: DataIR, service_ir: ServiceIR):
        # Map service ID → service name
        service_id_to_name = {
            svc.id: svc.name for svc in service_ir.services
        }

        # Map datastore ID → datastore name
        datastore_id_to_name = {
            ds.id: ds.name for ds in data_ir.datastores
        }

        for access in data_ir.access_patterns:
            service_name = service_id_to_name.get(access.service_id)
            datastore_name = datastore_id_to_name.get(access.datastore_id)

            if not service_name or not datastore_name:
                continue  # Safety

            svc_node = f"svc_{mermaid_id(service_name)}"
            data_node = f"data_{mermaid_id(datastore_name)}"

            self._add_edge(svc_node, data_node, access.access_type)


    # ---------- infra ----------

    def add_infra(self, ir: InfraIR):
        self.lines.append("  %% Infrastructure Layer")

        for compute in sorted(ir.compute, key=lambda c: c.name):
            self._add_node(
                f"infra_compute_{mermaid_id(compute.name)}",
                f"Compute: {compute.name}",
            )

        for network in sorted(ir.network, key=lambda n: n.name):
            self._add_node(
                f"infra_net_{mermaid_id(network.name)}",
                f"Network: {network.name}",
            )

    # ---------- business to service ----------

    def add_business_to_service_edges(self, business_ir: BusinessIR, service_ir: ServiceIR):
        edge_services = [
            svc for svc in service_ir.services
            if svc.service_type == "edge"
            or svc.protocol in ("http", "https", "grpc")
        ]

        for flow in business_ir.flows:
            if not flow.steps:
                continue

            last_step = sorted(flow.steps, key=lambda s: s.order)[-1]
            step_node = f"biz_step_{mermaid_id(last_step.id)}"

            for svc in edge_services:
                self._add_edge(
                    step_node,
                    f"svc_{mermaid_id(svc.name)}",
                    "uses",
                )

    # ---------- service to service ----------
    def add_service_dependencies(self, service_ir: ServiceIR):
        if not service_ir.dependencies:
            return

        # Build UUID → name map
        service_id_to_name = {
            svc.id: svc.name for svc in service_ir.services
        }

        for dep in service_ir.dependencies:
            from_name = service_id_to_name.get(dep.from_service_id)
            to_name = service_id_to_name.get(dep.to_service_id)

            if not from_name or not to_name:
                continue  # safety

            src = f"svc_{mermaid_id(from_name)}"
            dst = f"svc_{mermaid_id(to_name)}"

            self._add_edge(src, dst, dep.interaction)

    # ---------- responsibility dependencies ----------
    def add_responsibility_dependency_edges(self, deps):
        if not deps:
            return

        self.lines.append("  %% Responsibility Dependencies")

        for dep in deps:
            from_node = f"svc_{mermaid_id(dep.from_service)}_{mermaid_id(dep.from_responsibility)}"
            to_node = f"svc_{mermaid_id(dep.to_service)}_{mermaid_id(dep.to_responsibility)}"

            self._add_edge(from_node, to_node, dep.interaction)

    # ---------- responsibility data access ----------
    def add_responsibility_data_access_edges(self, access_list):
        """Render responsibility → datastore edges."""
        if not access_list:
            return

        self.lines.append("  %% Responsibility Data Access")

        for access in access_list:
            resp_node = f"svc_{mermaid_id(access.service_name)}_{mermaid_id(access.responsibility_name)}"
            data_node = f"data_{mermaid_id(access.datastore_name)}"

            self._add_edge(resp_node, data_node, access.access_type)


    # ---------- service to infra ----------

    def add_service_to_infra_edges(self, service_ir: ServiceIR, infra_ir: InfraIR):
        if infra_ir.compute:
            compute = sorted(infra_ir.compute, key=lambda c: c.name)[0]
            compute_node = f"infra_compute_{mermaid_id(compute.name)}"

            for svc in service_ir.services:
                self._add_edge(
                    f"svc_{mermaid_id(svc.name)}",
                    compute_node,
                    "runs on",
                )

        if infra_ir.network:
            network = sorted(infra_ir.network, key=lambda n: n.name)[0]
            network_node = f"infra_net_{mermaid_id(network.name)}"

            for svc in service_ir.services:
                if svc.service_type == "edge":
                    self._add_edge(
                        f"svc_{mermaid_id(svc.name)}",
                        network_node,
                        "exposed via",
                    )

    # ---------- output ----------

    def render(self) -> str:
        return "\n".join(self.lines)


# ============================================================
# PUBLIC COMPILER ENTRY POINT
# ============================================================

def compile_diagram(context: PipelineContext) -> str:
    diagram = MermaidDiagram()

    if context.business_ir:
        diagram.add_business(context.business_ir)

    if context.service_ir:
        diagram.add_services_with_responsibilities(
            context.service_ir,
            context.responsibility_map,
        )

    if context.data_ir:
        diagram.add_data(context.data_ir)

    if context.data_ir and context.service_ir:
        diagram.add_data_access_edges(context.data_ir, context.service_ir)

    if context.infra_ir:
        diagram.add_infra(context.infra_ir)

    if context.business_ir and context.service_ir:
        diagram.add_business_to_service_edges(
            context.business_ir,
            context.service_ir,
        )

    # 🔑 Service → Service FIRST
    if context.service_ir:
        diagram.add_service_dependencies(context.service_ir)

    # 🔑 Responsibility → Responsibility AFTER services exist
    if context.responsibility_dependencies:
        diagram.add_responsibility_dependency_edges(
            context.responsibility_dependencies
        )

    # 🔑 Responsibility → Data access
    if context.responsibility_data_access:
        diagram.add_responsibility_data_access_edges(
            context.responsibility_data_access
        )

    if context.service_ir and context.infra_ir:
        diagram.add_service_to_infra_edges(
            context.service_ir,
            context.infra_ir,
        )

    return diagram.render()
