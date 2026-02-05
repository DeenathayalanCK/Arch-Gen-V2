from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient, load_prompt
from app.llm.parser import parse_data
from app.ir.validation import ValidationResult


class DataStage(PipelineStage):
    name = "data"

    def run(self, context):
        if not context.decomposed.data:
            context.data_ir = None
            return ValidationResult.success()

        prompt = load_prompt("data.txt")
        full_prompt = prompt + "\n\n" + "\n".join(context.decomposed.data)

        try:
            output = LLMClient().generate(full_prompt)
            context.data_ir = parse_data(output)
            return context.data_ir.validate()
        except Exception as e:
            context.data_ir = None
            return ValidationResult.failure([str(e)])
