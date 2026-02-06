from app.pipeline.stage import PipelineStage
from app.pipeline.context import PipelineContext
from app.ir.infra_ir import InfraIR, ComputeNode, NetworkBoundary
from app.ir.validation import ValidationResult


class InfraStage(PipelineStage):
    name = "infra"

    def run(self, context: PipelineContext) -> ValidationResult:
        if context.infra_ir and context.infra_ir.compute:
            return ValidationResult.success()

        compute = []
        network = []

        text = context.requirements_text.lower()

        # -------- REFERENCE ARCHITECTURE RULES --------

        if "cloud" in text:
            compute.append(
                ComputeNode(
                    name="Application Runtime",
                    compute_type="cloud",
                )
            )

            network.append(
                NetworkBoundary(
                    name="Private Network",
                    boundary_type="vpc",
                )
            )

        if not compute:
            return ValidationResult.success()

        context.infra_ir = InfraIR(
            name="Infrastructure",
            compute=compute,
            network=network,
        )

        return ValidationResult.success()
