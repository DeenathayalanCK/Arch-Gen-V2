from __future__ import annotations  # Enable postponed evaluation of annotations

from dataclasses import dataclass, field
from typing import List, Any, Optional, TYPE_CHECKING
from app.ir.validation import ValidationResult

from app.domain.ontology_loader import ValidationRule

# Only import for type checking to avoid circular imports
if TYPE_CHECKING:
    from app.domain.adapter_stage import DomainContext


@dataclass
class DomainValidationIssue:
    rule_id: str
    severity: str  # error, warning, info
    message: str
    affected_elements: List[str] = field(default_factory=list)


@dataclass
class DomainValidationResult:
    is_valid: bool
    is_compliant: bool
    issues: List[DomainValidationIssue] = field(default_factory=list)
    compliance_status: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "is_compliant": self.is_compliant,
            "issues": [
                {"rule_id": i.rule_id, "severity": i.severity, "message": i.message, "affected": i.affected_elements}
                for i in self.issues
            ],
            "compliance_status": self.compliance_status,
            "error_count": len([i for i in self.issues if i.severity == "error"]),
            "warning_count": len([i for i in self.issues if i.severity == "warning"]),
        }


class DomainValidationStage:
    """
    Domain-specific validation stage.
    
    Validates the generated architecture against:
    1. Domain ontology requirements
    2. Domain validation rules
    3. Compliance requirements
    """

    def run(self, context) -> ValidationResult:
        """
        Execute domain validation as a proper pipeline stage.
        """

        print("\n" + "="*60)
        print("DOMAIN VALIDATION STAGE")
        print("="*60)

        try:
            domain_context = getattr(context, "domain_context", None)

            result = DomainValidationResult(is_valid=True, is_compliant=True)

            if not domain_context:
                print("[DomainValidation] No domain context, skipping domain validation")
                context.domain_validation = result
                return ValidationResult.success()

            # ============================
            # 1. VALIDATE REQUIRED COMPONENTS
            # ============================
            self._validate_required_components(context, domain_context, result)

            # ============================
            # 2. APPLY VALIDATION RULES
            # ============================
            self._apply_validation_rules(context, domain_context, result)

            # ============================
            # 3. CHECK COMPLIANCE
            # ============================
            self._check_compliance(context, domain_context, result)

            # Determine overall validity
            has_errors = any(i.severity == "error" for i in result.issues)
            result.is_valid = not has_errors

            # Store result in pipeline context
            context.domain_validation = result

            print(f"[DomainValidation] Valid: {result.is_valid}, Compliant: {result.is_compliant}")
            print(f"[DomainValidation] Issues: {len(result.issues)}")
            print("="*60 + "\n")

            if has_errors:
                return ValidationResult.failure(
                    errors=[i.message for i in result.issues if i.severity == "error"]
                )

            return ValidationResult.success()

        except Exception as e:
            return ValidationResult.failure(
                errors=[f"DomainValidationStage failed: {str(e)}"]
            )

    
    def _validate_required_components(
        self,
        context: Any,
        domain_context: DomainContext,
        result: DomainValidationResult,
    ):
        """Check that required domain components are present."""
        required = domain_context.ontology.get_required_entities()
        
        if not required:
            return
        
        # Get existing node types
        existing_types = set()
        if hasattr(context, 'visual_ir') and context.visual_ir:
            existing_types = {n.node_type.lower() for n in context.visual_ir.nodes}
            existing_types.update(n.label.lower() for n in context.visual_ir.nodes)
        
        for entity in required:
            entity_found = (
                entity.type.lower() in existing_types or
                entity.name.lower() in existing_types or
                entity.id.lower() in existing_types
            )
            
            if not entity_found:
                result.issues.append(DomainValidationIssue(
                    rule_id="required_component",
                    severity="warning",
                    message=f"Required {domain_context.ontology.domain} component missing: {entity.name}",
                    affected_elements=[entity.id],
                ))
    
    def _apply_validation_rules(
        self,
        context: Any,
        domain_context: DomainContext,
        result: DomainValidationResult,
    ):
        """Apply domain-specific validation rules."""
        rules = domain_context.validation_rules
        
        if not rules:
            return
        
        for rule in rules:
            # Simple rule evaluation (can be extended)
            # Format: "has:component_type" or "connects:source->target"
            condition = rule.condition.strip()
            
            if condition.startswith("has:"):
                required_type = condition[4:].strip()
                if not self._has_component_type(context, required_type):
                    result.issues.append(DomainValidationIssue(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=rule.message or f"Missing required component: {required_type}",
                        affected_elements=[required_type],
                    ))
            
            elif condition.startswith("connects:"):
                # Format: connects:source_type->target_type
                parts = condition[9:].split("->")
                if len(parts) == 2:
                    if not self._has_connection(context, parts[0].strip(), parts[1].strip()):
                        result.issues.append(DomainValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=rule.message or f"Missing connection: {parts[0]} -> {parts[1]}",
                            affected_elements=parts,
                        ))
    
    def _check_compliance(
        self,
        context: Any,
        domain_context: DomainContext,
        result: DomainValidationResult,
    ):
        """Check compliance requirements."""
        compliance_reqs = domain_context.ontology.compliance_requirements
        
        result.compliance_status = {}
        
        for req in compliance_reqs:
            # Simple compliance check based on component presence
            req_lower = req.lower()
            
            # Check for compliance-related components
            has_compliance = False
            if hasattr(context, 'visual_ir') and context.visual_ir:
                for node in context.visual_ir.nodes:
                    label_lower = node.label.lower()
                    if any(kw in label_lower for kw in ["audit", "encryption", "auth", "compliance", req_lower]):
                        has_compliance = True
                        break
            
            result.compliance_status[req] = has_compliance
            
            if not has_compliance:
                result.is_compliant = False
                result.issues.append(DomainValidationIssue(
                    rule_id=f"compliance_{req.lower().replace(' ', '_')}",
                    severity="warning",
                    message=f"Compliance requirement may not be addressed: {req}",
                    affected_elements=[req],
                ))
    
    def _has_component_type(self, context: Any, component_type: str) -> bool:
        """Check if a component type exists in the diagram."""
        if not hasattr(context, 'visual_ir') or not context.visual_ir:
            return False
        
        type_lower = component_type.lower()
        for node in context.visual_ir.nodes:
            if type_lower in node.node_type.lower() or type_lower in node.label.lower():
                return True
        return False
    
    def _has_connection(self, context: Any, source_type: str, target_type: str) -> bool:
        """Check if a connection between types exists."""
        if not hasattr(context, 'visual_ir') or not context.visual_ir:
            return False
        
        # Build type lookup
        node_types = {n.id: n.node_type.lower() for n in context.visual_ir.nodes}
        node_labels = {n.id: n.label.lower() for n in context.visual_ir.nodes}
        
        source_lower = source_type.lower()
        target_lower = target_type.lower()
        
        for edge in context.visual_ir.edges:
            src_type = node_types.get(edge.source, "")
            src_label = node_labels.get(edge.source, "")
            tgt_type = node_types.get(edge.target, "")
            tgt_label = node_labels.get(edge.target, "")
            
            if (source_lower in src_type or source_lower in src_label) and \
               (target_lower in tgt_type or target_lower in tgt_label):
                return True
        
        return False
