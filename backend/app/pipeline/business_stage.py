from app.pipeline.stage import PipelineStage
from app.pipeline.context import PipelineContext
from app.ir.business_ir import (
    BusinessIR,
    Actor,
    BusinessFlow,
    BusinessStep,
)
from app.ir.validation import ValidationResult


class BusinessStage(PipelineStage):
    """
    Builds Business IR (C4 L2) from decomposed business sentences.
    """

    name = "business"

    def run(self, context: PipelineContext) -> ValidationResult:
        if not context.decomposed or not context.decomposed.business:
            # No business info is not a failure
            context.business_ir = BusinessIR(
                name="Business",
                actors=[],
                flows=[],
            )
            return ValidationResult.success()

        actors = {}
        flows = []

        step_counter = 1

        for sentence in context.decomposed.business:
            sentence = sentence.strip()
            if not sentence:
                continue

            # --- VERY SIMPLE NLP (intentional) ---
            # "Users place orders" → actor = Users
            words = sentence.split()
            actor_name = words[0].capitalize()

            if actor_name not in actors:
                actors[actor_name] = Actor(
                    name=actor_name,
                    role="business_actor",
                )

            step = BusinessStep(
                name=sentence,
                actor_id=actor_name,
                order=step_counter,
            )
            step_counter += 1

            flow = BusinessFlow(
                name=f"{actor_name} Flow",
                steps=[step],
            )

            flows.append(flow)

        context.business_ir = BusinessIR(
            name="Business",
            actors=list(actors.values()),
            flows=flows,
        )

        return ValidationResult.success()
