from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient
from app.llm.parser import parse_service
from app.ir.validation import ValidationResult


class ServiceStage(PipelineStage):
    name = "service"

    def __init__(self):
        self.client = LLMClient()

    def run(self, context):
        if not context.decomposed or not context.decomposed.service and not context.decomposed.business:
            context.service_ir = None
            return ValidationResult.success()

        # build prompt on both decomposed.service and decomposed.business
        lines = []
        lines.extend(context.decomposed.service or [])
        lines.extend(context.decomposed.business or [])

        prompt = (
            "Extract structured services from the following requirements:\n\n"
            + "\n".join(lines)
        )

        try:
            raw = self.client.generate(prompt)
            ir = parse_service(raw)
            context.service_ir = ir
            return ValidationResult.success()
        except Exception as e:
            context.service_ir = None
            return ValidationResult.failure([str(e)])
