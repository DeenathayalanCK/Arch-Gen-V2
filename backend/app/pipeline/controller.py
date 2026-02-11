from app.pipeline.context import PipelineContext
from app.pipeline.business_stage import BusinessStage
from app.pipeline.service_stage import ServiceStage
from app.pipeline.responsibility_stage import ResponsibilityExpansionStage
from app.pipeline.data_stage import DataStage
from app.pipeline.infra_stage import InfraStage
from app.pipeline.decomposition_stage import DecompositionStage
from app.pipeline.reference_injection_stage import ReferenceInjectionStage
from app.pipeline.service_inference_stage import ServiceInferenceStage
from app.pipeline.service_dependency_stage import ServiceDependencyStage
from app.pipeline.responsibility_dependency_stage import ResponsibilityDependencyStage
from app.pipeline.responsibility_dependency_inference_stage import (
    ResponsibilityDependencyInferenceStage,
)
from app.pipeline.system_context_stage import SystemContextStage
from app.visual.visual_mapper import map_context_to_visual_ir


class PipelineController:
    MAX_RETRIES = 2

    def __init__(self):
        # Core stages (always run)
        self.core_stages = [
            DecompositionStage(),
            BusinessStage(),
            ServiceInferenceStage(),
            ResponsibilityExpansionStage(),
            DataStage(),
            ServiceDependencyStage(),
            ResponsibilityDependencyStage(),
            ResponsibilityDependencyInferenceStage(),
            InfraStage(),
            ReferenceInjectionStage(),      
        ]
        
        # Optional stages
        self.system_context_stage = SystemContextStage()

    def run(
        self, 
        requirements_text: str,
        include_system_context: bool = False,
    ) -> PipelineContext:
        context = PipelineContext(requirements_text=requirements_text)

        # Determine which stages to run
        stages = list(self.core_stages)
        
        # Insert system context stage early if requested
        if include_system_context:
            # Run after decomposition but before business stage
            stages.insert(1, self.system_context_stage)

        for stage in stages:
            result = None

            for attempt in range(self.MAX_RETRIES + 1):
                result = stage.run(context)

                if result.is_valid:
                    break
                
                # 🔎 DEBUG: check decomposition output immediately
            if stage.__class__.__name__ == "DecompositionStage":
                print("\n===== DEBUG: DECOMPOSITION OUTPUT =====")
                print(context.decomposed)
                print("======================================\n")

            if not result or not result.is_valid:
                if result:
                    context.errors.extend(result.errors)
                break  # hard stop on failure

        # --------------------------------
        # Visual IR (AFTER all stages)
        # --------------------------------
        try:
            context.visual_ir = map_context_to_visual_ir(context)
        except Exception as e:
            print("[WARN] Visual IR generation failed:", e)
            context.visual_ir = None

        return context
