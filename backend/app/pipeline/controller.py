from app.pipeline.context import PipelineContext
from app.pipeline.business_stage import BusinessStage
from app.pipeline.service_stage import ServiceStage
from app.pipeline.data_stage import DataStage
from app.pipeline.infra_stage import InfraStage
from app.pipeline.decomposition_stage import DecompositionStage

class PipelineController:
    MAX_RETRIES = 2

    def __init__(self):
        self.stages = [
            DecompositionStage(),
            BusinessStage(),
            ServiceStage(),
            DataStage(),
            InfraStage(),
        ]

    def run(self, requirements_text: str) -> PipelineContext:
        context = PipelineContext(requirements_text=requirements_text)

        for stage in self.stages:
            result = None

            for attempt in range(self.MAX_RETRIES + 1):
                result = stage.run(context)

                if result.is_valid:
                    break

            if not result or not result.is_valid:
                if result:
                    context.errors.extend(result.errors)
                break  # hard stop on failure

        return context
