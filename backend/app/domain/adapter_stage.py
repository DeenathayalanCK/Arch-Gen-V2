from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from app.domain.detector import DomainDetector, DomainDetectionResult
from app.domain.ontology_loader import OntologyLoader, DomainOntology, DomainPatternConfig, ValidationRule
from app.patterns.registry import get_pattern_registry
from app.ir.validation import ValidationResult



from app.patterns.registry import (
    get_pattern_registry,
    Pattern,
    PatternCategory,
    PatternComponent,
    PatternConnection,
)



@dataclass
class DomainContext:
    """Context object carrying domain information through pipeline."""
    detection_result: DomainDetectionResult
    ontology: DomainOntology
    patterns: List[DomainPatternConfig] = field(default_factory=list)
    validation_rules: List[ValidationRule] = field(default_factory=list)
    injected_pattern_ids: List[str] = field(default_factory=list)
    domain_rules: Dict[str, Any] = field(default_factory=dict)   # ← ADD THIS

    
    def to_dict(self) -> dict:
        return {
            "domain": self.detection_result.primary_domain,
            "confidence": self.detection_result.confidence,
            "detection_method": self.detection_result.detection_method.value,
            "sub_domains": self.detection_result.sub_domains,
            "ontology": self.ontology.to_dict(),
            "patterns_loaded": len(self.patterns),
            "validation_rules_loaded": len(self.validation_rules),
            "injected_pattern_ids": self.injected_pattern_ids,
            "domain_rules_loaded": list(self.domain_rules.keys()),  # ← ADD THIS
        }



class DomainAdapterStage:
    """
    Domain Adapter Stage - runs FIRST in pipeline.
    
    Responsibilities:
    1. Detect domain from requirements
    2. Load domain ontology
    3. Load domain patterns and INJECT into PatternRegistry
    4. Load validation rules
    5. Attach DomainContext to PipelineContext
    
    Does NOT do enrichment - that happens in DomainEnrichmentStage.
    """
    
    def __init__(self):
        self.detector = DomainDetector()
        self.loader = OntologyLoader()
    
    def run(self, context) -> ValidationResult:
        """
        Execute domain adaptation stage.
        
        Args:
            requirements: Raw user requirements text
            pipeline_context: The pipeline context to attach domain info to
            
        Returns:
            DomainContext with all loaded domain information
        """
        print("\n" + "="*60)
        print("DOMAIN ADAPTER STAGE")
        print("="*60)
        
        # ============================
        # 1. DETECT DOMAIN
        # ============================
        requirements = context.requirements_text
        detection_result = self.detector.detect(requirements, use_llm_fallback=True)

        
        print(f"[DomainAdapter] Detected domain: {detection_result.primary_domain}")
        print(f"[DomainAdapter] Confidence: {detection_result.confidence:.2f}")
        print(f"[DomainAdapter] Method: {detection_result.detection_method.value}")
        print(f"[DomainAdapter] Sub-domains: {detection_result.sub_domains}")
        
        # ============================
        # 2. LOAD ONTOLOGY
        # ============================
        ontology = self.loader.load_ontology(detection_result.primary_domain)
        print(f"[DomainAdapter] Loaded ontology: {len(ontology.entities)} entities")
        
        # ============================
        # 3. LOAD DOMAIN PATTERNS
        # ============================
        domain_patterns = self.loader.load_patterns(detection_result.primary_domain)
        
        # Also load sub-domain patterns
        for sub_domain in detection_result.sub_domains:
            sub_patterns = self.loader.load_patterns(sub_domain)
            domain_patterns.extend(sub_patterns)
        
        print(f"[DomainAdapter] Loaded domain patterns: {len(domain_patterns)}")
        
        # ============================
        # 4. INJECT INTO PATTERN REGISTRY (UNIFIED)
        # ============================
        injected_ids = []
        try:
            injected_ids = self._inject_patterns_to_registry(domain_patterns, detection_result.primary_domain)
            print(f"[DomainAdapter] Injected patterns into registry: {injected_ids}")
        except Exception as e:
            print(f"[DomainAdapter] Warning: Pattern injection failed: {e}")
            import traceback
            traceback.print_exc()
        
        # ============================
        # 5. LOAD VALIDATION RULES
        # ============================
        validation_rules = self.loader.load_validation_rules(detection_result.primary_domain)
        print(f"[DomainAdapter] Loaded validation rules: {len(validation_rules)}")
        
        # Log pattern counts
        try:
            registry = get_pattern_registry()

            total_patterns = len(registry.patterns)
            global_patterns = total_patterns - len(injected_ids)

            print(f"\n[PatternInjection] Global patterns loaded: {global_patterns}")
            print(f"[PatternInjection] Domain patterns loaded: {len(injected_ids)}")
            print(f"[PatternInjection] Total merged patterns: {total_patterns}")
            print(f"[PatternInjection] Applied patterns: {injected_ids}")

        except Exception as e:
            print(f"[DomainAdapter] Warning: Could not log pattern counts: {e}")

        
        # ============================
        # 6. BUILD DOMAIN CONTEXT
        # ============================
        domain_rules = self.loader.load_domain_rules(detection_result.primary_domain)
        print(f"[DomainAdapter] Loaded domain rules: {list(domain_rules.keys())}")
        domain_context = DomainContext(
                detection_result=detection_result,
                ontology=ontology,
                patterns=domain_patterns,
                validation_rules=validation_rules,
                injected_pattern_ids=injected_ids,
                domain_rules=domain_rules,   # ← ADD THIS
            )

        # Attach to pipeline context - set attribute directly
        context.domain_context = domain_context

        
        print("="*60 + "\n")
        
        return ValidationResult.success()
    
    def _inject_patterns_to_registry(
        self,
        domain_patterns: List[DomainPatternConfig],
        domain: str,
    ) -> List[str]:

        registry = get_pattern_registry()
        injected_ids = []

        for dp in domain_patterns:
            try:
                pattern_id = f"domain_{domain}_{dp.pattern_id}"

                # Convert components
                components = [
                    PatternComponent(
                        id=c.get("id", f"{pattern_id}_comp_{i}"),
                        name=c.get("name", "Component"),
                        node_type=c.get("type", "service"),
                        description=c.get("description", ""),
                        config=c.get("config", {}),
                    )
                    for i, c in enumerate(dp.components)
                ]

                # Convert connections
                connections = [
                    PatternConnection(
                        from_id=c.get("from", ""),
                        to_id=c.get("to", ""),
                        relationship=c.get("relationship", "connects_to"),
                        protocol=c.get("protocol"),
                    )
                    for c in dp.connections
                ]

                # Convert category string → Enum
                category_enum = self._map_category(dp.tags)

                pattern = Pattern(
                    id=pattern_id,
                    name=dp.name,
                    description=dp.description,
                    category=category_enum,
                    components=components,
                    connections=connections,
                    injection_points=[],
                    tags=dp.tags + [domain, "domain_pattern"],
                    applicable_when=dp.applicable_when,
                    trade_offs=getattr(dp, "trade_offs", {}),
                    variables={},
                )

                registry.register(pattern)

                injected_ids.append(pattern_id)
                print(f"[DomainAdapter] ✅ Registered pattern: {pattern_id}")

            except Exception as e:
                print(f"[DomainAdapter] ❌ Failed to inject pattern {dp.pattern_id}: {e}")

        return injected_ids

    
    def _map_category(self, tags: List[str]) -> PatternCategory:
        tag_set = set(t.lower() for t in tags)

        if "resilience" in tag_set or "reliability" in tag_set:
            return PatternCategory.RESILIENCE
        if "security" in tag_set or "auth" in tag_set:
            return PatternCategory.SECURITY
        if "data" in tag_set or "storage" in tag_set:
            return PatternCategory.DATA
        if "messaging" in tag_set or "event" in tag_set:
            return PatternCategory.MESSAGING
        if "integration" in tag_set:
            return PatternCategory.INTEGRATION
        if "deployment" in tag_set or "infra" in tag_set:
            return PatternCategory.DEPLOYMENT

        return PatternCategory.INTEGRATION
