from fastapi import APIRouter
from pydantic import BaseModel
import os

from app.inference.chat_completions_client import ChatCompletionsClient
from app.pipeline.reasoner import run_architecture_reasoner
from app.pipeline.enricher import enrich_architecture_ir
from app.pipeline.planner import run_diagram_planner
from app.pipeline.compiler import compile_to_mermaid

router = APIRouter(
    prefix="",
    tags=["generator"],
)


class GenerateRequest(BaseModel):
    prompt: str


@router.post("/generate")
def generate(req: GenerateRequest):
    reasoner = ChatCompletionsClient(
        base_url=os.environ["REASONER_BASE_URL"],
        model=os.environ["REASONER_MODEL"],
        temperature=0.2,
    )

    planner = ChatCompletionsClient(
        base_url=os.environ["PLANNER_BASE_URL"],
        model=os.environ["PLANNER_MODEL"],
        temperature=0.25,
    )

    arch_ir = run_architecture_reasoner(req.prompt, reasoner)
    arch_ir = enrich_architecture_ir(arch_ir)
    diagram_ir = run_diagram_planner(arch_ir, planner)
    mermaid = compile_to_mermaid(diagram_ir)

    return {"mermaid": mermaid}
