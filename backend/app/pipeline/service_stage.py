from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient, load_prompt
from app.llm.parser import parse_service
from app.ir.validation import ValidationResult


class ServiceStage(PipelineStage):
    name = "service"

    def run(self, context):
        lines = []
        lines.extend(context.decomposed.service or [])
        lines.extend(context.decomposed.business or [])

        if not lines:
            context.service_ir = None
            return ValidationResult.success()

        prompt = load_prompt("service.txt")
        full_prompt = prompt + "\n\n" + "\n".join(lines)

        try:
            output = LLMClient().generate(full_prompt)
            context.service_ir = parse_service(output)
            return context.service_ir.validate()
        except Exception as e:
            context.service_ir = None
            return ValidationResult.failure([str(e)])
