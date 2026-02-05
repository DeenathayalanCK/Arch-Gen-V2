from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient
from app.llm.parser import parse_data
from app.ir.validation import ValidationResult


class DataStage(PipelineStage):
    name = "data"

    def __init__(self):
        self.client = LLMClient()

    def run(self, context):
        if not context.decomposed or not context.decomposed.data:
            context.data_ir = None
            return ValidationResult.success()

        prompt = (
            "Extract data store and access information from the following requirements:\n\n"
            + "\n".join(context.decomposed.data)
        )

        try:
            raw = self.client.generate(prompt)
            ir = parse_data(raw)
            context.data_ir = ir
            return ValidationResult.success()
        except Exception as e:
            context.data_ir = None
            return ValidationResult.failure([str(e)])
