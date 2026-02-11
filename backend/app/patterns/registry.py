# backend/app/patterns/registry.py
"""
Pattern Registry - Central store for architecture patterns
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
from typing import Any, Optional


class PatternCategory(Enum):
    """Categories of architectural patterns"""
    INTEGRATION = "integration"
    SCALABILITY = "scalability"
    SECURITY = "security"
    DATA = "data"
    MESSAGING = "messaging"
    RESILIENCE = "resilience"
    DEPLOYMENT = "deployment"


@dataclass
class PatternComponent:
    """A component within a pattern"""
    id: str
    name: str
    node_type: str  # service, database, queue, cache, gateway, etc.
    description: str
    config: Dict = field(default_factory=dict)


@dataclass
class PatternConnection:
    """Connection between pattern components"""
    from_id: str
    to_id: str
    relationship: str
    protocol: Optional[str] = None


@dataclass
class Pattern:
    """
    An architectural pattern template
    
    Patterns can be applied to an existing architecture to add
    capabilities like caching, security layers, or message queues.
    """
    id: str
    name: str
    description: str
    category: PatternCategory
    
    # Pattern structure
    components: List[PatternComponent] = field(default_factory=list)
    connections: List[PatternConnection] = field(default_factory=list)
    
    # Integration points
    injection_points: List[str] = field(default_factory=list)  # Where pattern attaches
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    applicable_when: List[str] = field(default_factory=list)  # Trigger conditions
    trade_offs: Dict[str, str] = field(default_factory=dict)  # pros/cons
    
    # Template variables for customization
    variables: Dict[str, str] = field(default_factory=dict)


class PatternRegistry:
    """
    Central registry for architecture patterns
    
    Provides pattern lookup, filtering, and matching capabilities.
    """
    
    def __init__(self):
        self.patterns: Dict[str, Pattern] = {}
        self._category_index: Dict[PatternCategory, List[str]] = {cat: [] for cat in PatternCategory}
        self._tag_index: Dict[str, List[str]] = {}
        print("[REGISTRY DEBUG] PatternRegistry initialized")
    
    def register(self, pattern: Pattern) -> None:
        """Register a pattern in the registry"""
        self.patterns[pattern.id] = pattern
        
        # Update category index
        self._category_index[pattern.category].append(pattern.id)
        
        # Update tag index
        for tag in pattern.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(pattern.id)
    
    def get(self, pattern_id: str) -> Optional[Pattern]:
        """Get a pattern by ID"""
        pattern = self.patterns.get(pattern_id)
        print(f"[REGISTRY DEBUG] get('{pattern_id}') -> {'Found' if pattern else 'Not found'}")
        return pattern
    
    def find_applicable(self, context: str, max_results: int = 5) -> list[Pattern]:
        """Find patterns applicable to a given context"""
        context_lower = context.lower()
        scored_patterns = []
        
        print(f"[REGISTRY DEBUG] find_applicable called with context: '{context[:50]}...'")
        print(f"[REGISTRY DEBUG] Searching through {len(self.patterns)} patterns")
        
        for pattern in self.patterns.values():
            score = 0
            
            # Check applicable_when keywords
            for keyword in pattern.applicable_when:
                if keyword.lower() in context_lower:
                    score += 2
                    print(f"[REGISTRY DEBUG]   Pattern '{pattern.id}' matched keyword '{keyword}' (+2)")
            
            # Check tags
            for tag in pattern.tags:
                if tag.lower() in context_lower:
                    score += 1
                    print(f"[REGISTRY DEBUG]   Pattern '{pattern.id}' matched tag '{tag}' (+1)")
            
            # Check name and description
            if pattern.name.lower() in context_lower:
                score += 3
            if any(word in context_lower for word in pattern.description.lower().split()[:10]):
                score += 1
            
            if score > 0:
                scored_patterns.append((score, pattern))
        
        # Sort by score descending
        scored_patterns.sort(key=lambda x: x[0], reverse=True)
        results = [p for _, p in scored_patterns[:max_results]]
        
        print(f"[REGISTRY DEBUG] Found {len(results)} applicable patterns: {[p.id for p in results]}")
        return results
    
    def suggest_patterns(self, context: str, max_results: int = 5) -> list[Pattern]:
        """Suggest patterns based on context - alias for find_applicable"""
        return self.find_applicable(context, max_results)
    
    def get_by_category(self, category: PatternCategory) -> list[Pattern]:
        """Get all patterns in a category"""
        pattern_ids = self._category_index.get(category, [])
        return [self.patterns[pid] for pid in pattern_ids if pid in self.patterns]
    
    def get_by_tag(self, tag: str) -> list[Pattern]:
        """Get all patterns with a specific tag"""
        pattern_ids = self._tag_index.get(tag, [])
        return [self.patterns[pid] for pid in pattern_ids if pid in self.patterns]
    
    def list_all(self) -> list[Pattern]:
        """List all registered patterns"""
        return list(self.patterns.values())


# Global registry instance
_global_registry: Optional[PatternRegistry] = None


def get_pattern_registry() -> PatternRegistry:
    """Get or create the global pattern registry"""
    global _global_registry
    if _global_registry is None:
        print("[REGISTRY DEBUG] Creating global PatternRegistry")
        _global_registry = PatternRegistry()
        # Import and register patterns
        from app.patterns.catalog import register_all_patterns
        register_all_patterns(_global_registry)
    return _global_registry


# Alias for backwards compatibility
get_registry = get_pattern_registry
