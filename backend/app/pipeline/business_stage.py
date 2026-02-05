from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient
from app.llm.parser import parse_business
from app.ir.validation import ValidationResult


class BusinessStage(PipelineStage):
    name = "business"

    def __init__(self):
        self.client = LLMClient()

    def run(self, context):
        if not context.decomposed or not context.decomposed.business:
            context.business_ir = None
            return ValidationResult.success()

        prompt = (
            "Extract structured business information from the following requirements:\n\n"
            + "\n".join(context.decomposed.business)
        )

        try:
            raw = self.client.generate(prompt)
            ir = parse_business(raw)
            context.business_ir = ir
            return ValidationResult.success()
        except Exception as e:
            context.business_ir = None
            return ValidationResult.failure([str(e)])
