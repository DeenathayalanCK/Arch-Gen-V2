from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import os

# Safe yaml import
try:
    import yaml
except ImportError:
    yaml = None
    print("[OntologyLoader] Warning: PyYAML not installed")


@dataclass
class DomainEntity:
    id: str
    name: str
    type: str
    description: str = ""
    required: bool = False
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainRelationship:
    from_type: str
    to_type: str
    relationship: str
    required: bool = False
    description: str = ""


@dataclass
class ValidationRule:
    rule_id: str
    description: str
    condition: str
    severity: str = "error"  # error, warning, info
    message: str = ""


@dataclass
class DomainOntology:
    domain: str
    version: str = "1.0"
    description: str = ""
    entities: List[DomainEntity] = field(default_factory=list)
    relationships: List[DomainRelationship] = field(default_factory=list)
    required_components: List[str] = field(default_factory=list)
    compliance_requirements: List[str] = field(default_factory=list)
    
    def get_entity_types(self) -> List[str]:
        return [e.type for e in self.entities]
    
    def get_required_entities(self) -> List[DomainEntity]:
        return [e for e in self.entities if e.required]
    
    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "version": self.version,
            "description": self.description,
            "entities": [
                {"id": e.id, "name": e.name, "type": e.type, "description": e.description, "required": e.required}
                for e in self.entities
            ],
            "relationships": [
                {"from": r.from_type, "to": r.to_type, "relationship": r.relationship, "required": r.required}
                for r in self.relationships
            ],
            "required_components": self.required_components,
            "compliance_requirements": self.compliance_requirements,
        }
    
    def to_yaml_str(self) -> str:
        return yaml.dump(self.to_dict(), default_flow_style=False)


@dataclass 
class DomainPatternConfig:
    pattern_id: str
    name: str
    description: str
    applicable_when: List[str] = field(default_factory=list)
    components: List[Dict[str, Any]] = field(default_factory=list)
    connections: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

@dataclass
class DomainRules:
    baseline_services: List[Dict[str, Any]] = field(default_factory=list)
    mandatory_dependencies: List[Dict[str, Any]] = field(default_factory=list)
    baseline_responsibilities: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

class OntologyLoader:
    """
    Loads domain ontologies, patterns, and validation rules from config files.
    
    Directory structure:
    domains/
        healthcare/
            ontology.yaml
            patterns.yaml
            validation_rules.yaml
            keywords.yaml
        fintech/
            ...
    """
    
    # Generic system entities allowed in any domain
    GENERIC_ENTITIES = [
        "api_gateway", "load_balancer", "cache", "queue", "message_broker",
        "database", "cdn", "firewall", "auth_service", "monitoring",
        "logging", "service_mesh", "container", "kubernetes", "storage",
    ]
    
    def __init__(self, domains_path: Optional[str] = None):
        self.domains_path = domains_path or self._get_default_domains_path()
        self._cache: Dict[str, DomainOntology] = {}
        self._patterns_cache: Dict[str, List[DomainPatternConfig]] = {}
        self._rules_cache: Dict[str, List[ValidationRule]] = {}
        self._rules_config_cache: Dict[str, DomainRules] = {}

    def load_domain_rules(self, domain: str) -> dict:
        if yaml is None:
            return {}

        rules_path = os.path.join(self.domains_path, domain, "domain_rules.yaml")

        if not os.path.exists(rules_path):
            print(f"[OntologyLoader] No domain rules found for {domain}")
            return {}

        try:
            with open(rules_path, "r") as f:
                data = yaml.safe_load(f)
            print(f"[OntologyLoader] Loaded domain rules for {domain}")
            return data or {}
        except Exception as e:
            print(f"[OntologyLoader] Error loading domain rules for {domain}: {e}")
            return {}



    def _get_default_domains_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), "domains")
    
    def load_ontology(self, domain: str) -> DomainOntology:
        """Load ontology for a domain."""
        if domain in self._cache:
            return self._cache[domain]
        
        if yaml is None:
            print(f"[OntologyLoader] YAML not available, using generic ontology for {domain}")
            return self._get_generic_ontology(domain)
        
        ontology_path = os.path.join(self.domains_path, domain, "ontology.yaml")
        
        if not os.path.exists(ontology_path):
            print(f"[OntologyLoader] No ontology found for {domain}, using generic")
            return self._get_generic_ontology(domain)
        
        try:
            with open(ontology_path, "r") as f:
                data = yaml.safe_load(f)
            
            entities = [
                DomainEntity(
                    id=e.get("id", e.get("name", "").lower().replace(" ", "_")),
                    name=e.get("name", ""),
                    type=e.get("type", "service"),
                    description=e.get("description", ""),
                    required=e.get("required", False),
                    attributes=e.get("attributes", {}),
                )
                for e in data.get("entities", [])
            ]
            
            relationships = [
                DomainRelationship(
                    from_type=r.get("from", ""),
                    to_type=r.get("to", ""),
                    relationship=r.get("relationship", "connects_to"),
                    required=r.get("required", False),
                    description=r.get("description", ""),
                )
                for r in data.get("relationships", [])
            ]
            
            ontology = DomainOntology(
                domain=domain,
                version=data.get("version", "1.0"),
                description=data.get("description", ""),
                entities=entities,
                relationships=relationships,
                required_components=data.get("required_components", []),
                compliance_requirements=data.get("compliance_requirements", []),
            )
            
            self._cache[domain] = ontology
            print(f"[OntologyLoader] Loaded ontology for {domain}: {len(entities)} entities, {len(relationships)} relationships")
            return ontology
            
        except Exception as e:
            print(f"[OntologyLoader] Error loading ontology for {domain}: {e}")
            return self._get_generic_ontology(domain)
    
    def load_patterns(self, domain: str) -> List[DomainPatternConfig]:
        """Load domain-specific patterns."""
        if domain in self._patterns_cache:
            return self._patterns_cache[domain]
        
        if yaml is None:
            return []
        
        patterns_path = os.path.join(self.domains_path, domain, "patterns.yaml")
        
        if not os.path.exists(patterns_path):
            print(f"[OntologyLoader] No patterns found for {domain}")
            return []
        
        try:
            with open(patterns_path, "r") as f:
                data = yaml.safe_load(f)
            
            patterns = [
                DomainPatternConfig(
                    pattern_id=p.get("id", f"{domain}_{i}"),
                    name=p.get("name", ""),
                    description=p.get("description", ""),
                    applicable_when=p.get("applicable_when", []),
                    components=p.get("components", []),
                    connections=p.get("connections", []),
                    tags=p.get("tags", []) + [domain],
                )
                for i, p in enumerate(data.get("patterns", []))
            ]
            
            self._patterns_cache[domain] = patterns
            print(f"[OntologyLoader] Loaded {len(patterns)} patterns for {domain}")
            return patterns
            
        except Exception as e:
            print(f"[OntologyLoader] Error loading patterns for {domain}: {e}")
            return []
    
    def load_validation_rules(self, domain: str) -> List[ValidationRule]:
        """Load domain-specific validation rules."""
        if domain in self._rules_cache:
            return self._rules_cache[domain]
        
        if yaml is None:
            return []
        
        rules_path = os.path.join(self.domains_path, domain, "validation_rules.yaml")
        
        if not os.path.exists(rules_path):
            print(f"[OntologyLoader] No validation rules found for {domain}")
            return []
        
        try:
            with open(rules_path, "r") as f:
                data = yaml.safe_load(f)
            
            rules = [
                ValidationRule(
                    rule_id=r.get("id", f"rule_{i}"),
                    description=r.get("description", ""),
                    condition=r.get("condition", ""),
                    severity=r.get("severity", "warning"),
                    message=r.get("message", ""),
                )
                for i, r in enumerate(data.get("rules", []))
            ]
            
            self._rules_cache[domain] = rules
            print(f"[OntologyLoader] Loaded {len(rules)} validation rules for {domain}")
            return rules
            
        except Exception as e:
            print(f"[OntologyLoader] Error loading validation rules for {domain}: {e}")
            return []
    
    def _get_generic_ontology(self, domain: str) -> DomainOntology:
        """Return a generic ontology as fallback."""
        return DomainOntology(
            domain=domain,
            version="1.0",
            description="Generic domain ontology",
            entities=[
                DomainEntity(id="service", name="Service", type="service"),
                DomainEntity(id="database", name="Database", type="datastore"),
                DomainEntity(id="api", name="API", type="interface"),
                DomainEntity(id="queue", name="Message Queue", type="messaging"),
            ],
            relationships=[
                DomainRelationship(from_type="service", to_type="database", relationship="reads_writes"),
                DomainRelationship(from_type="service", to_type="queue", relationship="publishes_subscribes"),
            ],
        )
    
    def is_valid_entity(self, entity_type: str, domain: str) -> bool:
        """Check if entity type is valid for domain."""
        # Generic entities are always valid
        if entity_type.lower() in self.GENERIC_ENTITIES:
            return True
        
        ontology = self.load_ontology(domain)
        valid_types = [e.type.lower() for e in ontology.entities]
        valid_ids = [e.id.lower() for e in ontology.entities]
        
        return entity_type.lower() in valid_types or entity_type.lower() in valid_ids
    
    def get_available_domains(self) -> List[str]:
        """List available domain configurations."""
        if not os.path.exists(self.domains_path):
            return ["generic"]
        
        domains = []
        for name in os.listdir(self.domains_path):
            domain_dir = os.path.join(self.domains_path, name)
            if os.path.isdir(domain_dir):
                domains.append(name)
        
        return domains if domains else ["generic"]
