from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient, load_prompt
from app.llm.parser import parse_business
from app.ir.validation import ValidationResult


class BusinessStage(PipelineStage):
    name = "business"

    def run(self, context):
        if not context.decomposed.business:
            context.business_ir = None
            return ValidationResult.success()

        prompt = load_prompt("business.txt")
        full_prompt = prompt + "\n\n" + "\n".join(context.decomposed.business)

        try:
            output = LLMClient().generate(full_prompt)
            context.business_ir = parse_business(output)
            return context.business_ir.validate()
        except Exception as e:
            context.business_ir = None
            return ValidationResult.failure([str(e)])
