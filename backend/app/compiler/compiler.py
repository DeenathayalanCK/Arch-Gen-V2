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
    Rules:
    - No spaces
    - No special characters
    - Deterministic
    """
    return re.sub(r"[^a-zA-Z0-9_]", "_", text)


# ============================================================
# Mermaid Diagram Builder
# ============================================================

class MermaidDiagram:
    """
    Deterministic Mermaid diagram builder.
    No LLM usage.
    Same IR => same output.
    """

    def __init__(self):
        self.lines: List[str] = ["flowchart TD"]
        self._nodes: set[str] = set()

    # ---------- helpers ----------

    def _add_node(self, node_id: str, label: str):
        if node_id not in self._nodes:
            self.lines.append(f'  {node_id}["{label}"]')
            self._nodes.add(node_id)

    def _add_edge(self, src: str, dst: str, label: Optional[str] = None):
        if label:
            self.lines.append(f"  {src} -->|{label}| {dst}")
        else:
            self.lines.append(f"  {src} --> {dst}")

    # ---------- business ----------

    def add_business(self, ir: BusinessIR):
        self.lines.append("  %% Business Layer")

        # Actors (sorted for determinism)
        actors = sorted(ir.actors, key=lambda a: a.name)
        for actor in actors:
            actor_id = mermaid_id(actor.name)
            self._add_node(
                node_id=f"actor_{actor_id}",
                label=f"Actor: {actor.name}",
            )

        # Flows and steps
        flows = sorted(ir.flows, key=lambda f: f.name)
        for flow in flows:
            prev_step_node = None

            steps = sorted(flow.steps, key=lambda s: s.order)
            for step in steps:
                step_node = f"biz_step_{mermaid_id(step.id)}"

                self._add_node(
                    node_id=step_node,
                    label=step.name,
                )

                actor_node = f"actor_{mermaid_id(step.actor_id)}"
                self._add_edge(actor_node, step_node)

                if prev_step_node:
                    self._add_edge(prev_step_node, step_node)

                prev_step_node = step_node

    # ---------- services ----------

    def add_services_with_responsibilities(
        self,
        service_ir: ServiceIR,
        responsibility_map: dict[str, ServiceResponsibilities],
    ):
        self.lines.append("  %% Service Layer")

        for service in sorted(service_ir.services, key=lambda s: s.name):
            svc_safe = mermaid_id(service.name)
            subgraph_id = f"svc_{svc_safe}"

            self.lines.append(
                f'  subgraph {subgraph_id}["Service: {service.name}"]'
            )

            resp_bundle = responsibility_map.get(service.id)

            if resp_bundle:
                for resp in resp_bundle.responsibilities:
                    resp_id = f"{subgraph_id}_{mermaid_id(resp.name)}"
                    self._add_node(
                        resp_id,
                        resp.name,
                    )

            self.lines.append("  end")

    # ---------- data ----------

    def add_data(self, ir: DataIR):
        self.lines.append("  %% Data Layer")

        datastores = sorted(ir.datastores, key=lambda d: d.name)
        for store in datastores:
            store_id = mermaid_id(store.name)
            self._add_node(
                node_id=f"data_{store_id}",
                label=f"Data: {store.name}",
            )

    # ---------- data access edges ----------

    def add_data_access_edges(
        self,
        data_ir: DataIR,
        service_ir: ServiceIR,
    ):
        """Render service -> datastore edges based on access_patterns."""
        if not data_ir or not service_ir:
            return

        # Build lookup: datastore_id (UUID) -> canonical datastore name
        datastore_id_to_name = {ds.id: ds.name for ds in data_ir.datastores}

        # Build lookup: service_name -> service exists
        service_names = {svc.name for svc in service_ir.services}

        for access in data_ir.access_patterns:
            # access.service_id is the service NAME (not UUID)
            service_name = access.service_id
            if service_name not in service_names:
                continue

            # access.datastore_id is the datastore UUID
            datastore_name = datastore_id_to_name.get(access.datastore_id)
            if not datastore_name:
                continue

            # Generate mermaid-safe IDs
            svc_node = f"svc_{mermaid_id(service_name)}"
            data_node = f"data_{mermaid_id(datastore_name)}"

            self._add_edge(svc_node, data_node, access.access_type)

    # ---------- infra ----------

    def add_infra(self, ir: InfraIR):
        self.lines.append("  %% Infrastructure Layer")

        compute_nodes = sorted(ir.compute, key=lambda c: c.name)
        for node in compute_nodes:
            node_id = mermaid_id(node.name)
            self._add_node(
                node_id=f"infra_compute_{node_id}",
                label=f"Compute: {node.name}",
            )

        network_nodes = sorted(ir.network, key=lambda n: n.name)
        for net in network_nodes:
            net_id = mermaid_id(net.name)
            self._add_node(
                node_id=f"infra_net_{net_id}",
                label=f"Network: {net.name}",
            )

    # ---------- output ----------

    def render(self) -> str:
        return "\n".join(self.lines)


# ============================================================
# PUBLIC COMPILER ENTRY POINT
# ============================================================

def compile_diagram(context: PipelineContext) -> str:
    """
    Canonical deterministic compiler.

    RULES:
    - Rendering order is fixed
    - Sorting is enforced
    - No inference
    - No side effects
    """

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

    # Add edges between services and datastores
    if context.data_ir and context.service_ir:
        diagram.add_data_access_edges(context.data_ir, context.service_ir)

    if context.infra_ir:
        diagram.add_infra(context.infra_ir)

    return diagram.render()
