from app.pipeline.stage import PipelineStage
from app.llm.client import LLMClient, load_prompt
from app.ir.validation import ValidationResult
from app.pipeline.context import DecomposedRequirements
from app.llm.parser import safe_load_json


class DecompositionStage(PipelineStage):
    name = "decomposition"

    def run(self, context):
        prompt = load_prompt("decompose.txt")
        full_prompt = prompt + "\n\n" + context.requirements_text

        try:
            raw = LLMClient().generate(full_prompt)
            parsed = safe_load_json(raw)

            if not isinstance(parsed, dict):
                context.decomposed = None
                return ValidationResult.failure(
                    ["Invalid decomposition JSON (expected object)"]
                )

            # 🧼 Defensive normalization
            context.decomposed = DecomposedRequirements(
                business=parsed.get("business", []) or [],
                service=parsed.get("service", []) or [],
                data=parsed.get("data", []) or [],
                infra=parsed.get("infra", []) or [],
            )

            return ValidationResult.success()

        except Exception as e:
            context.decomposed = None
            return ValidationResult.failure([str(e)])
