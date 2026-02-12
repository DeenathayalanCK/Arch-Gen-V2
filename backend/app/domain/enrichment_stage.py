from __future__ import annotations  # Enable postponed evaluation of annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
import json
import re

from app.domain.ontology_loader import OntologyLoader

# Only import for type checking to avoid circular imports
if TYPE_CHECKING:
    from app.domain.adapter_stage import DomainContext


@dataclass
class EnrichmentSuggestion:
    entity_id: str
    entity_name: str
    entity_type: str
    reason: str
    is_valid: bool = True
    rejection_reason: str = ""


@dataclass
class RelationshipSuggestion:
    from_id: str
    to_id: str
    relationship: str
    reason: str
    is_valid: bool = True
    rejection_reason: str = ""


@dataclass
class EnrichmentResult:
    suggested_entities: List[EnrichmentSuggestion] = field(default_factory=list)
    suggested_relationships: List[RelationshipSuggestion] = field(default_factory=list)
    compliance_additions: List[str] = field(default_factory=list)
    applied_entities: List[str] = field(default_factory=list)
    applied_relationships: List[Tuple[str, str]] = field(default_factory=list)
    rejected_entities: List[str] = field(default_factory=list)
    rejected_relationships: List[str] = field(default_factory=list)
    llm_raw_output: str = ""
    reasoning: str = ""
    
    def to_dict(self) -> dict:
        return {
            "suggested_entities": [
                {"id": e.entity_id, "name": e.entity_name, "type": e.entity_type, 
                 "reason": e.reason, "valid": e.is_valid}
                for e in self.suggested_entities
            ],
            "suggested_relationships": [
                {"from": r.from_id, "to": r.to_id, "relationship": r.relationship,
                 "reason": r.reason, "valid": r.is_valid}
                for r in self.suggested_relationships
            ],
            "compliance_additions": self.compliance_additions,
            "applied_entities": self.applied_entities,
            "applied_relationships": [f"{a}->{b}" for a, b in self.applied_relationships],
            "rejected_entities": self.rejected_entities,
            "rejected_relationships": self.rejected_relationships,
            "reasoning": self.reasoning,
        }


class DomainEnrichmentStage:
    """
    Domain Enrichment Stage - runs AFTER IR generation, BEFORE rendering.
    
    IMPORTANT: LLM enrichment operates on generated IR, NOT raw prompt.
    
    Pipeline position:
        Business Stage -> Service Stage -> Data Stage -> Infra Stage
        -> Pattern Injection -> [THIS STAGE] -> Validation -> Rendering
    
    Responsibilities:
    1. Take current generated IR (business, service, visual)
    2. Take domain ontology and rules
    3. Use LLM to suggest domain-specific additions
    4. Validate suggestions against ontology
    5. Apply valid enrichments to IR
    """
    
    def __init__(self):
        self.loader = OntologyLoader()
    
    def run(
        self,
        pipeline_context: Any,
        domain_context: DomainContext,
        use_llm: bool = True,
    ) -> EnrichmentResult:
        """
        Execute domain enrichment on generated IR.
        
        Args:
            pipeline_context: Contains generated IR (business_ir, service_ir, visual_ir)
            domain_context: Domain information from DomainAdapterStage
            use_llm: Whether to use LLM for suggestions
            
        Returns:
            EnrichmentResult with applied and rejected suggestions
        """
        print("\n" + "="*60)
        print("DOMAIN ENRICHMENT STAGE")
        print("="*60)
        
        result = EnrichmentResult()
        
        if not use_llm:
            print("[DomainEnrichment] LLM disabled, skipping enrichment")
            return result
        
        # ============================
        # 1. EXTRACT CURRENT IR STATE
        # ============================
        ir_json = self._extract_ir_state(pipeline_context)
        print(f"[DomainEnrichment] Extracted IR state: {len(ir_json)} chars")
        
        # ============================
        # 2. GET APPLIED PATTERNS
        # ============================
        applied_patterns = getattr(pipeline_context, 'applied_patterns', [])
        print(f"[DomainEnrichment] Applied patterns: {applied_patterns}")
        
        # ============================
        # 3. GENERATE LLM SUGGESTIONS
        # ============================
        llm_suggestions = self._get_llm_suggestions(
            ir_json=ir_json,
            domain_context=domain_context,
            applied_patterns=applied_patterns,
        )
        
        if not llm_suggestions:
            print("[DomainEnrichment] No LLM suggestions generated")
            return result
        
        result.llm_raw_output = llm_suggestions.get("raw", "")
        result.reasoning = llm_suggestions.get("reasoning", "")
        
        print(f"[DomainEnrichment] LLM raw output: {result.llm_raw_output[:500]}...")
        
        # ============================
        # 4. VALIDATE SUGGESTIONS AGAINST ONTOLOGY
        # ============================
        validated = self._validate_suggestions(
            suggestions=llm_suggestions,
            domain_context=domain_context,
            pipeline_context=pipeline_context,
        )
        
        result.suggested_entities = validated["entities"]
        result.suggested_relationships = validated["relationships"]
        result.compliance_additions = validated.get("compliance", [])
        
        # Log validation results
        valid_entities = [e for e in result.suggested_entities if e.is_valid]
        invalid_entities = [e for e in result.suggested_entities if not e.is_valid]
        
        print(f"[DomainEnrichment] Valid entities: {[e.entity_id for e in valid_entities]}")
        print(f"[DomainEnrichment] Rejected entities: {[e.entity_id for e in invalid_entities]}")
        
        valid_rels = [r for r in result.suggested_relationships if r.is_valid]
        print(f"[DomainEnrichment] Relationships validated: {len(valid_rels)}")
        
        # ============================
        # 5. APPLY VALID ENRICHMENTS TO IR
        # ============================
        self._apply_enrichments(
            pipeline_context=pipeline_context,
            valid_entities=valid_entities,
            valid_relationships=valid_rels,
            result=result,
        )
        
        result.rejected_entities = [e.entity_id for e in invalid_entities]
        result.rejected_relationships = [
            f"{r.from_id}->{r.to_id}" 
            for r in result.suggested_relationships if not r.is_valid
        ]
        
        print("="*60 + "\n")
        
        return result
    
    def _extract_ir_state(self, context: Any) -> str:
        """Extract current IR state as JSON for LLM prompt."""
        ir_state = {}
        
        # Business IR
        if hasattr(context, 'business_ir') and context.business_ir:
            ir_state["business"] = self._serialize_ir(context.business_ir)
        
        # Service IR
        if hasattr(context, 'service_ir') and context.service_ir:
            ir_state["services"] = self._serialize_ir(context.service_ir)
        
        # Visual IR (most important for enrichment)
        if hasattr(context, 'visual_ir') and context.visual_ir:
            ir_state["visual"] = {
                "nodes": [
                    {"id": n.id, "label": n.label, "type": n.node_type, "layer": n.layer}
                    for n in context.visual_ir.nodes
                ],
                "edges": [
                    {"source": e.source, "target": e.target, "label": getattr(e, 'label', '')}
                    for e in context.visual_ir.edges
                ],
            }
        
        return json.dumps(ir_state, indent=2)
    
    def _serialize_ir(self, ir: Any) -> dict:
        """Serialize an IR object to dict."""
        if hasattr(ir, 'to_dict'):
            return ir.to_dict()
        if hasattr(ir, '__dict__'):
            return {k: str(v) for k, v in ir.__dict__.items() if not k.startswith('_')}
        return {"raw": str(ir)}
    
    def _get_llm_suggestions(
        self,
        ir_json: str,
        domain_context: DomainContext,
        applied_patterns: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Generate enrichment suggestions using LLM."""
        try:
            from app.llm.client import LLMClient
            
            domain = domain_context.detection_result.primary_domain
            ontology_yaml = domain_context.ontology.to_yaml_str()
            
            prompt = f"""You are a domain architecture expert for {domain} systems.

Current Generated Architecture IR:
{ir_json}

Domain Ontology:
{ontology_yaml}

Already Applied Patterns:
{json.dumps(applied_patterns)}

Domain: {domain}

Analyze the current architecture and suggest:
1. Missing domain entities that should be present
2. Required compliance components for {domain}
3. Domain best practice integrations
4. Relationships that should exist

IMPORTANT: Only suggest entities/relationships that:
- Are defined in the domain ontology, OR
- Are generic system components (api_gateway, cache, queue, load_balancer, etc.)

Return ONLY valid JSON:
{{
    "suggested_entities": [
        {{"id": "entity_id", "name": "Entity Name", "type": "service|datastore|interface", "reason": "why needed"}}
    ],
    "suggested_relationships": [
        {{"from": "source_id", "to": "target_id", "relationship": "relationship_type", "reason": "why needed"}}
    ],
    "compliance_additions": ["compliance requirement 1", "compliance requirement 2"],
    "reasoning": "overall reasoning for suggestions"
}}
"""
            
            llm = LLMClient()
            response = llm.generate(prompt)
            
            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                parsed = json.loads(json_match.group())
                parsed["raw"] = response
                return parsed
            
            return {"raw": response, "suggested_entities": [], "suggested_relationships": []}
            
        except Exception as e:
            print(f"[DomainEnrichment] LLM error: {e}")
            return None
    
    def _validate_suggestions(
        self,
        suggestions: Dict[str, Any],
        domain_context: DomainContext,
        pipeline_context: Any,
    ) -> Dict[str, Any]:
        """Validate LLM suggestions against ontology and existing IR."""
        validated_entities = []
        validated_relationships = []
        
        domain = domain_context.detection_result.primary_domain
        
        # Get existing node IDs
        existing_ids = set()
        if hasattr(pipeline_context, 'visual_ir') and pipeline_context.visual_ir:
            existing_ids = {n.id for n in pipeline_context.visual_ir.nodes}
        
        # Validate entities
        for entity in suggestions.get("suggested_entities", []):
            entity_id = entity.get("id", "")
            entity_type = entity.get("type", "service")
            
            # Check if already exists
            if entity_id in existing_ids:
                validated_entities.append(EnrichmentSuggestion(
                    entity_id=entity_id,
                    entity_name=entity.get("name", ""),
                    entity_type=entity_type,
                    reason=entity.get("reason", ""),
                    is_valid=False,
                    rejection_reason="Entity already exists in diagram",
                ))
                continue
            
            # Validate against ontology
            if self.loader.is_valid_entity(entity_type, domain):
                validated_entities.append(EnrichmentSuggestion(
                    entity_id=entity_id,
                    entity_name=entity.get("name", ""),
                    entity_type=entity_type,
                    reason=entity.get("reason", ""),
                    is_valid=True,
                ))
            else:
                validated_entities.append(EnrichmentSuggestion(
                    entity_id=entity_id,
                    entity_name=entity.get("name", ""),
                    entity_type=entity_type,
                    reason=entity.get("reason", ""),
                    is_valid=False,
                    rejection_reason=f"Entity type '{entity_type}' not in domain ontology",
                ))
        
        # Validate relationships
        for rel in suggestions.get("suggested_relationships", []):
            from_id = rel.get("from", "")
            to_id = rel.get("to", "")
            
            # Source must exist (either in IR or in validated additions)
            valid_from = from_id in existing_ids or any(
                e.entity_id == from_id and e.is_valid for e in validated_entities
            )
            valid_to = to_id in existing_ids or any(
                e.entity_id == to_id and e.is_valid for e in validated_entities
            )
            
            if valid_from and valid_to:
                validated_relationships.append(RelationshipSuggestion(
                    from_id=from_id,
                    to_id=to_id,
                    relationship=rel.get("relationship", "connects_to"),
                    reason=rel.get("reason", ""),
                    is_valid=True,
                ))
            else:
                validated_relationships.append(RelationshipSuggestion(
                    from_id=from_id,
                    to_id=to_id,
                    relationship=rel.get("relationship", "connects_to"),
                    reason=rel.get("reason", ""),
                    is_valid=False,
                    rejection_reason=f"Source or target node does not exist",
                ))
        
        return {
            "entities": validated_entities,
            "relationships": validated_relationships,
            "compliance": suggestions.get("compliance_additions", []),
        }
    
    def _apply_enrichments(
        self,
        pipeline_context: Any,
        valid_entities: List[EnrichmentSuggestion],
        valid_relationships: List[RelationshipSuggestion],
        result: EnrichmentResult,
    ):
        """Apply validated enrichments to the visual IR."""
        if not hasattr(pipeline_context, 'visual_ir') or not pipeline_context.visual_ir:
            print("[DomainEnrichment] No visual_ir to enrich")
            return
        
        visual_ir = pipeline_context.visual_ir
        
        # Import VisualNode/VisualEdge
        try:
            from app.ir.visual_ir import VisualNode, VisualEdge
        except ImportError:
            print("[DomainEnrichment] Could not import visual IR types")
            return
        
        # Add valid entities as nodes
        for entity in valid_entities:
            # Map entity type to layer
            layer = self._type_to_layer(entity.entity_type)
            
            node = VisualNode(
                id=entity.entity_id,
                label=entity.entity_name,
                node_type=entity.entity_type,
                layer=layer,
                metadata={"enriched": True, "reason": entity.reason},
            )
            visual_ir.nodes.append(node)
            result.applied_entities.append(entity.entity_id)
            print(f"[DomainEnrichment] Added node: {entity.entity_id}")
        
        # Add valid relationships as edges
        for rel in valid_relationships:
            edge = VisualEdge(
                source=rel.from_id,
                target=rel.to_id,
                label=rel.relationship,
                metadata={"enriched": True, "reason": rel.reason},
            )
            visual_ir.edges.append(edge)
            result.applied_relationships.append((rel.from_id, rel.to_id))
            print(f"[DomainEnrichment] Added edge: {rel.from_id} -> {rel.to_id}")
    
    def _type_to_layer(self, entity_type: str) -> str:
        """Map entity type to visual layer."""
        type_lower = entity_type.lower()
        
        if type_lower in ["database", "datastore", "storage", "cache"]:
            return "data"
        if type_lower in ["queue", "message_broker", "event_bus", "messaging"]:
            return "messaging"
        if type_lower in ["api_gateway", "load_balancer", "cdn", "firewall"]:
            return "infrastructure"
        if type_lower in ["interface", "api", "client"]:
            return "interface"
        
        return "service"
