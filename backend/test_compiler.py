from dotenv import load_dotenv
load_dotenv()

import os
import json
from app.pipeline.reasoner import run_architecture_reasoner
from app.pipeline.enricher import enrich_architecture_ir
from app.pipeline.planner import run_diagram_planner
from app.pipeline.compiler import compile_to_mermaid
from app.inference.chat_completions_client import ChatCompletionsClient

reasoner = ChatCompletionsClient(
    base_url=os.environ["REASONER_BASE_URL"],
    model=os.environ["REASONER_MODEL"],
)

planner = ChatCompletionsClient(
    base_url=os.environ["PLANNER_BASE_URL"],
    model=os.environ["PLANNER_MODEL"],
)

prompt = """
A consent-based health data sharing platform
where citizens approve researchers to access datasets.
"""

arch_ir = run_architecture_reasoner(prompt, reasoner)
arch_ir = enrich_architecture_ir(arch_ir)
diagram_ir = run_diagram_planner(arch_ir, planner)

mermaid = compile_to_mermaid(diagram_ir)

print("✅ Mermaid Output")
print(mermaid)
