from app.pipeline.stage import PipelineStage
from app.ir.validation import ValidationResult
from app.ir.responsibility_ir import ServiceResponsibilities, Responsibility
from app.llm.client import LLMClient
from app.llm.parser import safe_load_json


class ResponsibilityExpansionStage(PipelineStage):
    name = "responsibility_expansion"

    def __init__(self):
        self.client = LLMClient()

    def run(self, context):
        if not context.service_ir:
            return ValidationResult.success()

        if not hasattr(context, "responsibility_map") or context.responsibility_map is None:
            context.responsibility_map = {}

        for service in context.service_ir.services:
            prompt = f"""
You are a software architect.

Expand high-level responsibilities for the following service.

Rules:
- Do NOT invent infrastructure
- Do NOT invent technologies
- Responsibilities must be C4 Level 3
- 3 to 6 items max
- Use abstract responsibilities

Service:
{service.name}

System requirements:
{context.requirements_text}

Return JSON ONLY:
[
  {{
    "name": "...",
    "description": "...",
    "type": "logic | api | orchestration | persistence | integration"
  }}
]
"""

            raw = self.client.generate(prompt)
            parsed = safe_load_json(raw)

            if not isinstance(parsed, list):
                continue

            responsibilities = []
            for r in parsed:
                if not isinstance(r, dict):
                    continue
                if not r.get("name"):
                    continue

                responsibilities.append(
                    Responsibility(
                        name=r["name"],
                        description=r.get("description"),
                        responsibility_type=r.get("type", "logic"),
                    )
                )

            context.responsibility_map[service.id] = ServiceResponsibilities(
                service_id=service.id,
                service_name=service.name,
                responsibilities=responsibilities,
            )

        return ValidationResult.success()
