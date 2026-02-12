"""
Domain adapter module for domain-aware architecture generation.

Use lazy imports to avoid circular dependencies:
    from app.domain.detector import DomainDetector
    from app.domain.adapter_stage import DomainAdapterStage
"""

# Don't import anything at module level to avoid circular imports
# All imports should be done lazily when needed

__all__ = [
    "DomainDetector",
    "DomainDetectionResult", 
    "OntologyLoader",
    "DomainAdapterStage",
    "DomainContext",
    "DomainEnrichmentStage",
    "DomainValidationStage",
]
