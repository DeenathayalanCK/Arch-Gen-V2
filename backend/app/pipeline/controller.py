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

        # ============================
        # 0. DOMAIN ADAPTER STAGE (FIRST)
        # ============================
        domain_context = None
        if enable_domain_adapter:
            try:
                domain_adapter = self._get_domain_adapter()
                domain_context = domain_adapter.run(requirements, context)
                # domain_context is already attached by adapter, but ensure it's set
                context.domain_context = domain_context
                print(f"[Pipeline] Domain adapter completed: {domain_context.detection_result.primary_domain}")
            except Exception as e:
                print(f"[Pipeline] Domain adapter error: {e}")
                import traceback
                traceback.print_exc()
                context.errors.append(f"Domain adapter: {str(e)}")
        
        # ============================
        # 1-4. EXISTING STAGES (Business, Service, Data, Infra)
        # ============================
        # ...existing code for running business, service, data, infra stages...
        
        # ============================
        # 5. VISUAL IR GENERATION
        # ============================
        # ...existing code for visual IR...
        
        # ============================
        # 6. DOMAIN ENRICHMENT STAGE (AFTER IR GENERATION)
        # ============================
        if enable_domain_enrichment and domain_context is not None:
            try:
                domain_enrichment = self._get_domain_enrichment()
                enrichment_result = domain_enrichment.run(
                    pipeline_context=context,
                    domain_context=domain_context,
                    use_llm=True,
                )
                context.enrichment_result = enrichment_result
                print(f"[Pipeline] Domain enrichment completed")
            except Exception as e:
                print(f"[Pipeline] Domain enrichment error: {e}")
                import traceback
                traceback.print_exc()
                context.errors.append(f"Domain enrichment: {str(e)}")
        
        # ============================
        # 7. DOMAIN VALIDATION STAGE
        # ============================
        if domain_context is not None:
            try:
                domain_validation = self._get_domain_validation()
                validation_result = domain_validation.run(
                    pipeline_context=context,
                    domain_context=domain_context,
                )
                context.domain_validation = validation_result
                print(f"[Pipeline] Domain validation completed")
            except Exception as e:
                print(f"[Pipeline] Domain validation error: {e}")
                import traceback
                traceback.print_exc()
                context.errors.append(f"Domain validation: {str(e)}")
        
        # ============================
        # 8. EXISTING VALIDATION & RENDERING
        # ============================
        # ...existing code for remaining stages...
        
        # --------------------------------
        # Visual IR (AFTER all stages)
        # --------------------------------
        try:
            context.visual_ir = map_context_to_visual_ir(context)
        except Exception as e:
            print("[WARN] Visual IR generation failed:", e)
            context.visual_ir = None

        return context
