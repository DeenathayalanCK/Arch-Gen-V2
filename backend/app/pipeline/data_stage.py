from app.pipeline.stage import PipelineStage
from app.pipeline.context import PipelineContext
from app.ir.data_ir import DataIR, DataStore, DataAccess
from app.ir.validation import ValidationResult


class DataStage(PipelineStage):
    name = "data"

    def run(self, context: PipelineContext) -> ValidationResult:
        if context.data_ir and context.data_ir.datastores:
            return ValidationResult.success()

        datastores = []
        access_patterns = []

        text = context.requirements_text.lower()

        # -------- DATASTORE INFERENCE --------

        if "order" in text:
            datastores.append(
                DataStore(
                    name="Orders",
                    store_type="sql",
                )
            )

        if "user" in text or "customer" in text:
            datastores.append(
                DataStore(
                    name="Users",
                    store_type="sql",
                )
            )

        # -------- ACCESS PATTERNS --------

        if context.service_ir:
            for service in context.service_ir.services:
                for store in datastores:
                    access_patterns.append(
                        DataAccess(
                            service_id=service.name,
                            datastore_id=store.name,
                            access_type="read_write",
                        )
                    )

        if not datastores:
            return ValidationResult.success()

        context.data_ir = DataIR(
            name="Data",
            datastores=datastores,
            access_patterns=access_patterns,
        )

        return ValidationResult.success()
