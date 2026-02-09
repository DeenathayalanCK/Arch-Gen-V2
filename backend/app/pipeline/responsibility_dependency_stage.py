from dataclasses import dataclass
from typing import List

from app.pipeline.stage import PipelineStage
from app.ir.validation import ValidationResult
from app.ir.responsibility_ir import ResponsibilityDependency


# -------------------------------------------------
# Responsibility Dependency Stage
# -------------------------------------------------

class ResponsibilityDependencyStage(PipelineStage):
    """
    Infer responsibility-to-responsibility dependencies
    based on service dependencies + responsibility semantics.
    """

    name = "responsibility_dependency"

    def run(self, context) -> ValidationResult:
        if not context.service_ir or not context.responsibility_map:
            context.responsibility_dependencies = []
            return ValidationResult.success()

        dependencies: List[ResponsibilityDependency] = []

        # 🔑 FIX: build service lookup (repo-correct)
        service_by_id = {
            svc.id: svc for svc in context.service_ir.services
        }

        for dep in context.service_ir.dependencies:
            from_service = service_by_id.get(dep.from_service_id)
            to_service = service_by_id.get(dep.to_service_id)

            if not from_service or not to_service:
                continue

            from_bundle = context.responsibility_map.get(from_service.id)
            to_bundle = context.responsibility_map.get(to_service.id)

            if not from_bundle or not to_bundle:
                continue

            for from_resp in from_bundle.responsibilities:
                if not self._is_entry_responsibility(from_resp.name):
                    continue

                for to_resp in to_bundle.responsibilities:
                    if self._is_target_responsibility(
                        to_resp.name,
                        to_service.name,
                    ):
                        dependencies.append(
                            ResponsibilityDependency(
                                from_service=from_service.name,
                                from_responsibility=from_resp.name,
                                to_service=to_service.name,
                                to_responsibility=to_resp.name,
                            )
                        )

        # Attach derived IR
        context.responsibility_dependencies = dependencies
        return ValidationResult.success()

    # -------------------------------------------------
    # Deterministic heuristics
    # -------------------------------------------------

    def _is_entry_responsibility(self, name: str) -> bool:
        name = name.lower()
        return any(
            k in name
            for k in ["process", "handle", "orchestrate", "workflow"]
        )

    def _is_target_responsibility(self, resp_name: str, service_name: str) -> bool:
        r = resp_name.lower()
        s = service_name.lower()

        if "order" in s:
            return any(k in r for k in ["create", "validate", "update"])
        if "payment" in s:
            return any(k in r for k in ["process", "validate"])
        if "identity" in s or "user" in s:
            return any(k in r for k in ["validate", "verify", "authenticate"])

        return False
