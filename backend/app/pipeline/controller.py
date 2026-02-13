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
        # Domain stages - lazy loaded
        self._domain_adapter = None
        self._domain_enrichment = None
        self._domain_validation = None

        # Optional stages
        self.system_context_stage = SystemContextStage()

        # Core stages (always run)
        self.core_stages = [
            DecompositionStage(),
            self._get_domain_adapter(),          # Domain must run early
            BusinessStage(),
            ServiceInferenceStage(),
            ResponsibilityExpansionStage(),
            DataStage(),
            ServiceDependencyStage(),
            ResponsibilityDependencyStage(),
            ResponsibilityDependencyInferenceStage(),
            InfraStage(),
            ReferenceInjectionStage(),
            #self._get_domain_enrichment(),       # After IR generation
            self._get_domain_validation(),       # Final validation
        ]



        
        # Optional stages
        self.system_context_stage = SystemContextStage()

        # Domain stages - lazy loaded
        self._domain_adapter = None
        self._domain_enrichment = None
        self._domain_validation = None
    
    def _get_domain_adapter(self):
        """Lazy load domain adapter to avoid circular imports."""
        if self._domain_adapter is None:
            from app.domain.adapter_stage import DomainAdapterStage
            self._domain_adapter = DomainAdapterStage()
        return self._domain_adapter
    
    def _get_domain_enrichment(self):
        """Lazy load domain enrichment to avoid circular imports."""
        if self._domain_enrichment is None:
            from app.domain.enrichment_stage import DomainEnrichmentStage
            self._domain_enrichment = DomainEnrichmentStage()
        return self._domain_enrichment
    
    def _get_domain_validation(self):
        """Lazy load domain validation to avoid circular imports."""
        if self._domain_validation is None:
            from app.domain.validation_stage import DomainValidationStage
            self._domain_validation = DomainValidationStage()
        return self._domain_validation
    
    def run(
        self, 
        requirements: str, 
        include_system_context: bool = False,
        enable_domain_adapter: bool = True,
        enable_domain_enrichment: bool = True,        
    ) -> PipelineContext:
        # Import context here to ensure it has latest definition
        from app.pipeline.context import PipelineContext
        
        # Create context with requirements_text
        context = PipelineContext(requirements_text=requirements)
        
        # Determine which stages to run
        stages = list(self.core_stages)

        # Insert system context stage early if requested
        if include_system_context:
            # Run after decomposition but before business stage
            stages.insert(1, self.system_context_stage)

        for stage in stages:
            result = None

            stage_name = stage.__class__.__name__

            # -------------------------------------------------
            # Non-retry stages (deterministic / evaluation)
            # -------------------------------------------------
            if stage_name in {
                "DomainValidationStage",
                "DomainEnrichmentStage",
                "DomainAdapterStage",
            }:
                result = stage.run(context)

            # -------------------------------------------------
            # Retry-enabled stages (LLM / inference / unstable)
            # -------------------------------------------------
            else:
                for attempt in range(self.MAX_RETRIES + 1):
                    result = stage.run(context)

                    if result.is_valid:
                        break

            # 🔎 DEBUG: check decomposition output immediately
            if stage_name == "DecompositionStage":
                print("\n===== DEBUG: DECOMPOSITION OUTPUT =====")
                print(context.decomposed)
                print("======================================\n")

            # -------------------------------------------------
            # Hard stop on failure
            # -------------------------------------------------
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
