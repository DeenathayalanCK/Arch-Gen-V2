from app.pipeline.context import PipelineContext
from app.ir.responsibility_ir import ServiceResponsibilities, Responsibility
from app.llm.client import LLMClient
from app.llm.parser import safe_load_json


class ResponsibilityExpansionStage:
    """
    Expands services into C4-L3 responsibilities.

    This stage:
    - NEVER invents infrastructure
    - NEVER invents technologies
    - Expands only within an existing service boundary
    - Is safe against malformed LLM JSON
    """

    def __init__(self):
        self.client = LLMClient()

    def run(self, context: PipelineContext) -> PipelineContext:
        if not context.service_ir:
            return context

        for service in context.service_ir.services:
            responsibilities = self._expand_service(
                service_name=service.name,
                requirements=context.requirements_text,
            )

            context.responsibility_map[service.id] = ServiceResponsibilities(
                service_id=service.id,
                service_name=service.name,
                responsibilities=responsibilities,
            )

        return context

    def _expand_service(self, service_name: str, requirements: str):
        prompt = f"""
You are a software architect.

Expand the responsibilities of the service below.

Rules:
- Do NOT invent technologies
- Do NOT invent infrastructure
- Use high-level responsibilities only
- 3–6 responsibilities max
- Responsibilities must be abstract (C4 L3)
- Use nouns or short verb phrases

Service:
{service_name}

System requirements:
{requirements}

Return JSON ONLY as a list:
[
  {{
    "name": "...",
    "description": "...",
    "type": "logic | api | orchestration | persistence | integration"
  }}
]
"""

        raw = self.client.generate(prompt)

        # 🔒 HARDENED JSON PARSING (shared trust boundary)
        parsed = safe_load_json(raw)

        # We expect a LIST — anything else is invalid
        if not isinstance(parsed, list):
            return []

        responsibilities: list[Responsibility] = []

        for r in parsed:
            if not isinstance(r, dict):
                continue

            name = r.get("name")
            if not name or not isinstance(name, str):
                continue

            responsibilities.append(
                Responsibility(
                    name=name.strip(),
                    description=r.get("description"),
                    responsibility_type=r.get("type", "logic"),
                )
            )

        return responsibilities
