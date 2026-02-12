#backend\app\pipeline\responsibility_stage.py

from app.pipeline.stage import PipelineStage
from app.ir.validation import ValidationResult
from app.ir.responsibility_ir import ServiceResponsibilities, Responsibility
from app.llm.client import LLMClient
from app.llm.parser import safe_load_json


FORBIDDEN_TERMS = {
    "api", "database", "db", "queue", "kafka",
    "aws", "azure", "gcp", "ui", "frontend",
    "backend", "lambda", "s3", "redis"
}

ALLOWED_RESPONSIBILITY_TYPES = {
    "logic",
    "orchestration",
    "integration",
    "persistence",
}


class ResponsibilityExpansionStage(PipelineStage):
    name = "responsibility_expansion"

    def __init__(self):
        self.client = LLMClient()

    def run(self, context):
        # --------------------------------
        # Guard: nothing to expand
        # --------------------------------
        if not context.service_ir or not context.service_ir.services:
            return ValidationResult.success()

        if not hasattr(context, "responsibility_map") or context.responsibility_map is None:
            context.responsibility_map = {}

        # --------------------------------
        # Expand responsibilities per service
        # --------------------------------
        for service in context.service_ir.services:
            responsibilities = self._expand_with_llm(service.name, context)
            responsibilities = self._inject_domain_baseline(service.name, responsibilities, context)


            if not responsibilities:
                responsibilities = self._fallback(service.name)
                source = "rule"
            else:
                source = "llm"

            context.responsibility_map[service.id] = ServiceResponsibilities(
                service_id=service.id,
                service_name=service.name,
                responsibilities=responsibilities,
                source=source,
            )


        return ValidationResult.success()

    def _inject_domain_baseline(self, service_name, responsibilities, context):
        domain = self._get_domain(context)

        if not responsibilities:
            return responsibilities

        existing_names = {r.name.lower() for r in responsibilities}

        # Healthcare audit enforcement
        if domain == "healthcare" and "audit" not in service_name.lower():
            if "audit logging" not in existing_names:
                responsibilities.append(
                    Responsibility(
                        name="Audit logging",
                        description="Records domain events for compliance tracking",
                        responsibility_type="integration",
                    )
                )

        # Fintech fraud enforcement
        if domain == "fintech" and "payment" in service_name.lower():
            if "fraud validation" not in existing_names:
                responsibilities.append(
                    Responsibility(
                        name="Fraud validation",
                        description="Validates transactions against fraud rules",
                        responsibility_type="logic",
                    )
                )

        return responsibilities


    # ------------------------
    # LLM Expansion (Safe Zone)
    # ------------------------

    def _expand_with_llm(self, service_name: str, context):
        service_role = self._infer_service_role(service_name)

        prompt = f"""
You are a senior software architect.

Your task is to define INTERNAL RESPONSIBILITIES (C4 Level 3)
for the given service.

Service Role:
{service_role}

Domain:
{self._get_domain(context)}

Domain-specific guidance:
{self._get_domain_guidance(context)}


Rules (STRICT):
- Responsibilities must be ABSTRACT
- No infrastructure
- No databases
- No APIs
- No technologies
- No UI components
- 3 to 6 responsibilities only
- Verb + noun phrasing
- Business semantics only

Service Name:
{service_name}

System Requirements:
{context.requirements_text}

Return JSON ONLY in this format:
[
  {{
    "name": "...",
    "description": "...",
    "type": "logic | orchestration | integration | persistence"
  }}
]
"""

        raw = self.client.generate(prompt)
        parsed = safe_load_json(raw)

        if not isinstance(parsed, list):
            return None

        responsibilities = []
        seen = set()

        for item in parsed:
            if not isinstance(item, dict):
                return None

            name = str(item.get("name", "")).strip()
            if not name or len(name.split()) > 5:
                return None

            lower_name = name.lower()

            # Word-level forbidden term check (safe)
            for term in FORBIDDEN_TERMS:
                if f" {term} " in f" {lower_name} ":
                    return None

            if lower_name in seen:
                continue

            seen.add(lower_name)

            resp_type = str(item.get("type", "logic")).lower()
            if resp_type not in ALLOWED_RESPONSIBILITY_TYPES:
                resp_type = "logic"

            description = item.get("description")
            if not description:
                description = f"Handles {name.lower()} responsibilities"

            responsibilities.append(
                Responsibility(
                    name=name,
                    description=description,
                    responsibility_type=resp_type,
                )
            )

        if not (3 <= len(responsibilities) <= 6):
            return None

        return responsibilities

    # ------------------------
    # Rule-Based Fallback
    # ------------------------

    def _fallback(self, service_name: str):
        base = service_name.replace("Service", "").strip()

        return [
            Responsibility(
                name=f"{base} validation",
                description=f"Validates {base.lower()} related inputs and rules",
                responsibility_type="logic",
            ),
            Responsibility(
                name=f"{base} processing",
                description=f"Processes core {base.lower()} business logic",
                responsibility_type="logic",
            ),
            Responsibility(
                name=f"{base} lifecycle management",
                description=f"Manages {base.lower()} state transitions",
                responsibility_type="orchestration",
            ),
            Responsibility(
                name=f"{base} retrieval",
                description=f"Retrieves {base.lower()} information",
                responsibility_type="persistence",
            ),
        ]

    def _infer_service_role(self, service_name: str) -> str:
        name = service_name.lower()

        if "web" in name or "ui" in name:
            return "Edge service handling user interaction and request routing"

        if "identity" in name or "auth" in name:
            return "Supporting service responsible for identity and access logic"

        if "payment" in name or "billing" in name:
            return "Supporting service handling financial transaction logic"

        return "Core domain service handling business logic"
    
    
    def _get_domain(self, context):
        domain_context = getattr(context, "domain_context", None)
        if not domain_context:
            return "generic"
        return domain_context.detection_result.primary_domain

    def _get_domain_guidance(self, context):
        domain = self._get_domain(context)

        if domain == "healthcare":
            return (
                "- Ensure patient data handling responsibilities\n"
                "- Include compliance or audit-related logic if applicable\n"
                "- Consider consent validation and clinical data integrity"
            )

        if domain == "fintech":
            return (
                "- Include fraud detection or risk assessment if applicable\n"
                "- Ensure transaction validation logic\n"
                "- Consider audit or regulatory compliance checks"
            )

        if domain == "ecommerce":
            return (
                "- Include inventory coordination if relevant\n"
                "- Consider order lifecycle orchestration\n"
                "- Handle payment or refund processing semantics"
            )

        return "Follow general business logic responsibilities."
