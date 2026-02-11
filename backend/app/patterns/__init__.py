# backend/app/patterns/__init__.py
"""
Architecture Pattern Library

Provides pre-built architectural patterns that can be:
- Suggested based on requirements analysis
- Injected into generated architectures
- Used as templates for common scenarios
"""

from app.patterns.registry import (
    Pattern,
    PatternCategory,
    PatternComponent,
    PatternConnection,
    PatternRegistry,
    get_pattern_registry,
    get_registry,
)
from app.patterns.catalog import (
    PATTERN_CATALOG,
    register_all_patterns,
    test_pattern_catalog,
)

__all__ = [
    "Pattern",
    "PatternCategory", 
    "PatternComponent",
    "PatternConnection",
    "PatternRegistry",
    "get_pattern_registry",
    "get_registry",
    "PATTERN_CATALOG",
    "register_all_patterns",
    "test_pattern_catalog",
]

# Print debug info on import
print(f"[PATTERNS MODULE] Loaded with {len(PATTERN_CATALOG)} patterns in catalog")
