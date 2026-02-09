from app.pipeline.stage import PipelineStage
from app.ir.validation import ValidationResult
from app.reference.resolver import resolve_reference_architecture
from app.ir.responsibility_ir import Responsibility, ServiceResponsibilities
from app.ir.data_ir import DataStore, canonical_datastore_name


class ReferenceInjectionStage(PipelineStage):
    name = "reference_injection"

    def run(self, context):
        if not context.service_ir:
            return ValidationResult.success()

        # Ensure responsibility map exists
        if not hasattr(context, "responsibility_map") or context.responsibility_map is None:
            context.responsibility_map = {}

        for service in context.service_ir.services:
            ref = resolve_reference_architecture(service.name)
            if not ref:
                continue

            # Inject responsibilities
            responsibilities = [
                Responsibility(
                    name=r["name"],
                    description=r.get("description"),
                    responsibility_type=r.get("type", "logic"),
                )
                for r in ref.get("responsibilities", [])
            ]

            context.responsibility_map[service.id] = ServiceResponsibilities(
                service_id=service.id,
                service_name=service.name,
                responsibilities=responsibilities,
            )

            # Inject data stores if Data IR exists
            if context.data_ir:
                existing = {d.name for d in context.data_ir.datastores}
                for d in ref.get("datastores", []):
                    canonical = canonical_datastore_name(d["name"])
                    if canonical and canonical not in existing:
                        context.data_ir.datastores.append(
                            DataStore(
                                name=d["name"],
                                store_type=d.get("store_type", "unknown"),
                            )
                        )

        return ValidationResult.success()
