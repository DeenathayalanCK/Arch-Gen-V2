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

    if context.business_ir:
        graph.nodes.extend(normalize_business(context.business_ir))

    if context.service_ir:
        graph.nodes.extend(normalize_service(context.service_ir))

        for dep in context.service_ir.dependencies:
            graph.edges.append(
                Edge(
                    source=dep.from_service_id,
                    target=dep.to_service_id,
                    label=dep.interaction,
                )
            )

    if context.data_ir:
        graph.nodes.extend(normalize_data(context.data_ir))

        for access in context.data_ir.access_patterns:
            graph.edges.append(
                Edge(
                    source=access.service_id,
                    target=access.datastore_id,
                    label=access.access_type,
                )
            )

    if context.infra_ir:
        graph.nodes.extend(normalize_infra(context.infra_ir))

    return graph
