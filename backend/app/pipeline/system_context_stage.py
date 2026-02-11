# backend/app/pipeline/system_context_stage.py
"""
C4 Model Level 1: System Context Stage

Generates a high-level view showing:
- The system under design (central)
- External users/actors
- External systems it integrates with
- Key relationships between them
"""

from dataclasses import dataclass, field
from typing import List, Optional

from app.pipeline.stage import PipelineStage
from app.pipeline.context import PipelineContext
from app.ir.validation import ValidationResult
from app.llm.client import LLMClient
from app.llm.parser import safe_load_json


@dataclass
class ExternalSystem:
    """An external system that the architecture integrates with"""
    id: str
    name: str
    description: str
    system_type: str  # "saas", "legacy", "partner", "government", "payment", etc.
    integration_type: str  # "api", "file", "queue", "manual"


@dataclass
class SystemBoundary:
    """The main system being designed"""
    id: str
    name: str
    description: str
    key_capabilities: List[str] = field(default_factory=list)


@dataclass
class ContextRelationship:
    """Relationship between actors/systems and the main system"""
    source_id: str
    target_id: str
    description: str
    protocol: Optional[str] = None  # "REST", "GraphQL", "SFTP", "SMTP", etc.


@dataclass
class SystemContextIR:
    """C4 Level 1 - System Context Diagram IR"""
    system_boundary: Optional[SystemBoundary] = None
    external_systems: List[ExternalSystem] = field(default_factory=list)
    relationships: List[ContextRelationship] = field(default_factory=list)

    def validate(self) -> ValidationResult:
        errors = []
        if not self.system_boundary:
            errors.append("System boundary must be defined")
        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()


SYSTEM_CONTEXT_PROMPT = """You are an expert software architect. Analyze the requirements and extract the C4 Level 1 (System Context) view.

Identify:
1. The main system being built (the boundary)
2. All external users/actors who interact with it
3. All external systems it must integrate with
4. The relationships between them

Return a JSON object with this structure:
{
    "system_boundary": {
        "id": "system_main",
        "name": "System Name",
        "description": "What the system does",
        "key_capabilities": ["capability1", "capability2"]
    },
    "external_systems": [
        {
            "id": "ext_1",
            "name": "External System Name",
            "description": "What it does",
            "system_type": "saas|legacy|partner|payment|government|analytics",
            "integration_type": "api|file|queue|manual"
        }
    ],
    "relationships": [
        {
            "source_id": "actor_customer",
            "target_id": "system_main",
            "description": "Places orders via",
            "protocol": "HTTPS"
        },
        {
            "source_id": "system_main",
            "target_id": "ext_payment",
            "description": "Processes payments through",
            "protocol": "REST API"
        }
    ]
}

Requirements:
"""


class SystemContextStage(PipelineStage):
    """
    C4 Level 1: System Context Stage
    
    Extracts the high-level system context showing:
    - The system boundary
    - External actors (from business_ir if available)
    - External systems and integrations
    """
    name = "system_context"

    def run(self, context: PipelineContext) -> ValidationResult:
        # Build context-aware prompt
        full_prompt = SYSTEM_CONTEXT_PROMPT + context.requirements_text

        # Add existing actor info if available
        if context.business_ir and context.business_ir.actors:
            actor_info = "\n\nAlready identified actors:\n"
            for actor in context.business_ir.actors:
                actor_info += f"- {actor.name} (role: {actor.role})\n"
            full_prompt += actor_info

        try:
            raw = LLMClient().generate(full_prompt)
            parsed = safe_load_json(raw)

            if not isinstance(parsed, dict):
                return ValidationResult.failure(
                    ["Invalid system context JSON (expected object)"]
                )

            # Parse system boundary
            boundary_data = parsed.get("system_boundary", {})
            system_boundary = SystemBoundary(
                id=boundary_data.get("id", "system_main"),
                name=boundary_data.get("name", "Main System"),
                description=boundary_data.get("description", ""),
                key_capabilities=boundary_data.get("key_capabilities", []),
            )

            # Parse external systems
            external_systems = []
            for ext in parsed.get("external_systems", []):
                external_systems.append(ExternalSystem(
                    id=ext.get("id", f"ext_{len(external_systems)}"),
                    name=ext.get("name", "Unknown System"),
                    description=ext.get("description", ""),
                    system_type=ext.get("system_type", "external"),
                    integration_type=ext.get("integration_type", "api"),
                ))

            # Parse relationships
            relationships = []
            for rel in parsed.get("relationships", []):
                relationships.append(ContextRelationship(
                    source_id=rel.get("source_id", ""),
                    target_id=rel.get("target_id", ""),
                    description=rel.get("description", ""),
                    protocol=rel.get("protocol"),
                ))

            # Store in context
            context.system_context_ir = SystemContextIR(
                system_boundary=system_boundary,
                external_systems=external_systems,
                relationships=relationships,
            )

            return ValidationResult.success()

        except Exception as e:
            return ValidationResult.failure([f"System context extraction failed: {str(e)}"])
