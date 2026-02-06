from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient
from app.llm.parser import parse_service
from app.ir.validation import ValidationResult


class ServiceStage(PipelineStage):
    name = "service"

    def __init__(self):
        self.client = LLMClient()

    def run(self, context):
        # Check if decomposed exists and has any service or business content
        service_lines = getattr(context.decomposed, 'service', None) or [] if context.decomposed else []
        business_lines = getattr(context.decomposed, 'business', None) or [] if context.decomposed else []

        if not service_lines and not business_lines:
            context.service_ir = None
            return ValidationResult.success()

        # build prompt on both decomposed.service and decomposed.business
        lines = []
        lines.extend(service_lines)
        lines.extend(business_lines)

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
