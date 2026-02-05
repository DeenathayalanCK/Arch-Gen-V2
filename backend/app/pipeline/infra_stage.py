from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient
from app.llm.parser import parse_infra
from app.ir.validation import ValidationResult


class InfraStage(PipelineStage):
    name = "infra"

    def __init__(self):
        self.client = LLMClient()

    def run(self, context):
        if not context.decomposed or not context.decomposed.infra:
            context.infra_ir = None
            return ValidationResult.success()

        prompt = (
            "Extract infrastructure data from the following requirements:\n\n"
            + "\n".join(context.decomposed.infra)
        )

        try:
            raw = self.client.generate(prompt)
            ir = parse_infra(raw)
            context.infra_ir = ir
            return ValidationResult.success()
        except Exception as e:
            context.infra_ir = None
            return ValidationResult.failure([str(e)])
