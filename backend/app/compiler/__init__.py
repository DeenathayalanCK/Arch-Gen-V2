from app.compiler.merge import merge_context
from app.compiler.layout import apply_layout
from app.compiler.render_mermaid import render_mermaid
from app.pipeline.context import PipelineContext


def compile_to_mermaid(context: PipelineContext) -> str:
    graph = merge_context(context)
    graph = apply_layout(graph)
    return render_mermaid(graph)
