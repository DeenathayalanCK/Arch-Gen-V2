import json
from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient, load_prompt
from app.ir.validation import ValidationResult
from app.pipeline.context import DecomposedRequirements


class DecompositionStage(PipelineStage):
    name = "decomposition"

    def run(self, context):
        prompt = load_prompt("decompose.txt")
        full_prompt = prompt + "\n\n" + context.requirements

        try:
            output = LLMClient().generate(full_prompt)
            data = json.loads(output)
            context.decomposed = DecomposedRequirements(**data)
            return ValidationResult.success()
        except Exception as e:
            context.decomposed = DecomposedRequirements()
            return ValidationResult.failure([str(e)])
