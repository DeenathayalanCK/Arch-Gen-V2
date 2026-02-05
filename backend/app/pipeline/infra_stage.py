from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient, load_prompt
from app.llm.parser import parse_infra
from app.ir.validation import ValidationResult


class InfraStage(PipelineStage):
    name = "infra"

    def run(self, context):
        if not context.decomposed.infra:
            context.infra_ir = None
            return ValidationResult.success()

        prompt = load_prompt("infra.txt")
        full_prompt = prompt + "\n\n" + "\n".join(context.decomposed.infra)

        try:
            output = LLMClient().generate(full_prompt)
            context.infra_ir = parse_infra(output)
            return context.infra_ir.validate()
        except Exception as e:
            context.infra_ir = None
            return ValidationResult.failure([str(e)])
