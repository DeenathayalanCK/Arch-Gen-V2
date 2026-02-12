from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from app.domain.detector import DomainDetector, DomainDetectionResult
from app.domain.ontology_loader import OntologyLoader, DomainOntology, DomainPatternConfig, ValidationRule
from app.patterns.registry import get_pattern_registry


# Define PatternCategory locally to avoid import issues
class PatternCategory(Enum):
    STRUCTURAL = "structural"
    RESILIENCE = "resilience"
    SECURITY = "security"
    DATA = "data"
    MESSAGING = "messaging"
    INTEGRATION = "integration"
    DEPLOYMENT = "deployment"


@dataclass
class PatternComponent:
    id: str
    name: str
    node_type: str = "service"
    description: str = ""
    is_variable: bool = False


@dataclass
class PatternConnection:
    from_id: str
    to_id: str
    relationship: str = "connects_to"
    label: str = ""
    protocol: Optional[str] = None  # <- added to match injector expectation


@dataclass
class DomainContext:
    """Context object carrying domain information through pipeline."""
    detection_result: DomainDetectionResult
    ontology: DomainOntology
    patterns: List[DomainPatternConfig] = field(default_factory=list)
    validation_rules: List[ValidationRule] = field(default_factory=list)
    injected_pattern_ids: List[str] = field(default_factory=list)
    
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
    
    def run(self, requirements: str, pipeline_context: Any) -> DomainContext:
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
            global_count = len(registry._patterns) - len(injected_ids)
            print(f"\n[PatternInjection] Global patterns loaded: {global_count}")
            print(f"[PatternInjection] Domain patterns loaded: {len(domain_patterns)}")
            print(f"[PatternInjection] Total merged patterns: {len(registry._patterns)}")
            print(f"[PatternInjection] Applied patterns: {injected_ids}")
        except Exception as e:
            print(f"[DomainAdapter] Warning: Could not log pattern counts: {e}")
        
        # ============================
        # 6. BUILD DOMAIN CONTEXT
        # ============================
        domain_context = DomainContext(
            detection_result=detection_result,
            ontology=ontology,
            patterns=domain_patterns,
            validation_rules=validation_rules,
            injected_pattern_ids=injected_ids,
        )
        
        # Attach to pipeline context - set attribute directly
        pipeline_context.domain_context = domain_context
        
        print("="*60 + "\n")
        
        return domain_context
    
    def _inject_patterns_to_registry(self, domain_patterns: List[DomainPatternConfig], domain: str) -> List[str]:
        """
        Convert domain patterns to ArchitecturePattern and inject into global registry.
        
        This uses the EXISTING PatternRegistry - no separate system.
        """
        registry = get_pattern_registry()
        injected_ids = []
        
        for dp in domain_patterns:
            try:
                # Convert to ArchitecturePattern (existing model)
                pattern_id = f"domain_{domain}_{dp.pattern_id}"
                
                # Convert components
                components = []
                for i, c in enumerate(dp.components):
                    comp = PatternComponent(
                        id=c.get("id", f"comp_{i}"),
                        name=c.get("name", "Component"),
                        node_type=c.get("type", "service"),
                        description=c.get("description", ""),
                        is_variable=c.get("is_variable", False),
                    )
                    components.append(comp)
                
                # Convert connections
                connections = []
                for c in dp.connections:
                    conn = PatternConnection(
                        from_id=c.get("from", ""),
                        to_id=c.get("to", ""),
                        relationship=c.get("relationship", "connects_to"),
                        label=c.get("label", ""),
                        protocol=c.get("protocol", None),  # <- include protocol if provided
                    )
                    connections.append(conn)
                
                # Determine category - use string value
                category_str = self._determine_category_str(dp.tags)
                
                # Build pattern dict for registry
                pattern_data = {
                    "id": pattern_id,
                    "name": dp.name,
                    "description": dp.description,
                    "category": category_str,
                    "components": components,
                    "connections": connections,
                    "tags": dp.tags + [domain, "domain_pattern"],
                    "applicable_when": dp.applicable_when,
                    "trade_offs": getattr(dp, "trade_offs", {}),  # <- ensure trade_offs exists
                }
                
                # Try to register using registry's method
                if hasattr(registry, 'register_dict'):
                    registry.register_dict(pattern_data)
                elif hasattr(registry, 'register'):
                    # Create a simple object that registry can accept
                    from types import SimpleNamespace
                    pattern_obj = SimpleNamespace(**pattern_data)
                    pattern_obj.category = SimpleNamespace(value=category_str)
                    registry.register(pattern_obj)
                
                injected_ids.append(pattern_id)
                print(f"[DomainAdapter] ✅ Registered pattern: {pattern_id}")
                
            except Exception as e:
                print(f"[DomainAdapter] ⚠️ Failed to inject pattern {dp.pattern_id}: {e}")
                continue
        
        return injected_ids
    
    def _determine_category_str(self, tags: List[str]) -> str:
        """Map tags to category string."""
        tag_set = set(t.lower() for t in tags)
        
        if "resilience" in tag_set or "reliability" in tag_set:
            return "resilience"
        if "security" in tag_set or "auth" in tag_set:
            return "security"
        if "data" in tag_set or "storage" in tag_set:
            return "data"
        if "messaging" in tag_set or "event" in tag_set:
            return "messaging"
        if "integration" in tag_set:
            return "integration"
        if "deployment" in tag_set or "infra" in tag_set:
            return "deployment"
        
        return "structural"
