# backend/app/patterns/injector.py
"""
Pattern Injector - Applies patterns to existing architecture IRs

Takes a pattern and injects its components and connections
into the current pipeline context.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import re

from app.pipeline.context import PipelineContext
from app.patterns.registry import Pattern, PatternComponent, PatternConnection
from app.visual.visual_schema import VisualNode, VisualEdge, VisualDiagram
from app.visual.visual_style import VISUAL_STYLE


@dataclass
class InjectionResult:
    """Result of pattern injection"""
    success: bool
    nodes_added: List[str] = field(default_factory=list)
    edges_added: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass 
class InjectionMapping:
    """Maps pattern variables to actual IDs in the architecture"""
    variable: str  # e.g., "{{service}}"
    target_id: str  # e.g., "svc_order_service"


class PatternInjector:
    """
    Injects architectural patterns into existing Visual IR
    
    Example usage:
        injector = PatternInjector()
        result = injector.inject(
            context.visual_ir,
            pattern=CACHING_PATTERN,
            mappings=[
                InjectionMapping("{{service}}", "svc_order_service"),
                InjectionMapping("{{database}}", "db_orders"),
            ]
        )
    """
    
    # Node type to visual style mapping
    NODE_STYLE_MAP = {
        "cache": "cache",
        "queue": "queue",
        "gateway": "gateway",
        "service": "service",
        "database": "database",
        "infrastructure": "infrastructure",
        "external": "external",
    }
    
    def inject(
        self,
        visual_ir: VisualDiagram,
        pattern: Pattern,
        mappings: List[InjectionMapping],
        prefix: str = "",
    ) -> InjectionResult:
        """
        Inject a pattern into the visual IR
        
        Args:
            visual_ir: The existing VisualDiagram to modify
            pattern: The pattern to inject
            mappings: Variable mappings (pattern vars -> actual node IDs)
            prefix: Optional prefix for generated node IDs
            
        Returns:
            InjectionResult with status and details
        """
        result = InjectionResult(success=True)
        
        # Build mapping dictionary
        var_map = {m.variable: m.target_id for m in mappings}
        
        # Validate required mappings
        required_vars = self._extract_variables(pattern)
        missing = required_vars - set(var_map.keys())
        if missing:
            result.warnings.append(
                f"Missing mappings for: {', '.join(missing)}. Pattern may be incomplete."
            )
        
        # Track existing node IDs for collision detection
        existing_ids = {node.id for node in visual_ir.nodes}
        
        # Inject pattern components as nodes
        id_remap: Dict[str, str] = {}  # pattern_id -> actual_id
        
        for component in pattern.components:
            new_id = self._generate_id(component.id, prefix, existing_ids)
            id_remap[component.id] = new_id
            
            # Get style for node type
            style_key = self.NODE_STYLE_MAP.get(component.node_type, "service")
            style = VISUAL_STYLE.get(style_key, VISUAL_STYLE["service"])
            
            node = VisualNode(
                id=new_id,
                label=component.name,
                node_type=component.node_type,
                layer=style.get("layer", "service"),
                shape=style.get("shape", "rectangle"),
                color=style.get("color", "#4CAF50"),
                details=[component.description] if component.description else [],
                group=f"pattern_{pattern.id}",
            )
            
            visual_ir.nodes.append(node)
            result.nodes_added.append(new_id)
            existing_ids.add(new_id)
        
        # Inject pattern connections as edges
        for connection in pattern.connections:
            source = self._resolve_id(connection.from_id, var_map, id_remap)
            target = self._resolve_id(connection.to_id, var_map, id_remap)
            
            if not source or not target:
                result.warnings.append(
                    f"Could not resolve edge: {connection.from_id} -> {connection.to_id}"
                )
                continue
            
            # Check if source/target exist
            if source not in existing_ids and not source.startswith("{{"):
                result.warnings.append(f"Source node not found: {source}")
            if target not in existing_ids and not target.startswith("{{"):
                result.warnings.append(f"Target node not found: {target}")
            
            edge = VisualEdge(
                source=source,
                target=target,
                relation=connection.relationship,
                style="solid" if connection.protocol else "dotted",
            )
            
            visual_ir.edges.append(edge)
            result.edges_added += 1
        
        return result
    
    def suggest_mappings(
        self,
        visual_ir: VisualDiagram,
        pattern: Pattern,
    ) -> List[Tuple[str, List[str]]]:
        """
        Suggest possible mappings for pattern variables based on existing nodes
        
        Returns list of (variable, [candidate_node_ids])
        """
        suggestions = []
        
        for var in self._extract_variables(pattern):
            # Extract expected type from variable name
            var_type = var.strip("{}").lower()
            
            candidates = []
            for node in visual_ir.nodes:
                # Match by node type or partial name match
                if self._is_compatible(node, var_type):
                    candidates.append(node.id)
            
            suggestions.append((var, candidates))
        
        return suggestions
    
    def _extract_variables(self, pattern: Pattern) -> set:
        """Extract all template variables from pattern"""
        variables = set()
        pattern_re = re.compile(r"\{\{[^}]+\}\}")
        
        for conn in pattern.connections:
            for match in pattern_re.findall(conn.from_id):
                variables.add(match)
            for match in pattern_re.findall(conn.to_id):
                variables.add(match)
        
        return variables
    
    def _generate_id(self, base_id: str, prefix: str, existing: set) -> str:
        """Generate unique ID avoiding collisions"""
        candidate = f"{prefix}_{base_id}" if prefix else base_id
        
        if candidate not in existing:
            return candidate
        
        # Add suffix for uniqueness
        counter = 1
        while f"{candidate}_{counter}" in existing:
            counter += 1
        return f"{candidate}_{counter}"
    
    def _resolve_id(
        self,
        pattern_id: str,
        var_map: Dict[str, str],
        id_remap: Dict[str, str],
    ) -> Optional[str]:
        """Resolve a pattern ID to actual ID"""
        # Check if it's a template variable
        if pattern_id.startswith("{{") and pattern_id.endswith("}}"):
            return var_map.get(pattern_id, pattern_id)
        
        # Check if it's a pattern component ID
        if pattern_id in id_remap:
            return id_remap[pattern_id]
        
        # Return as-is (existing node reference)
        return pattern_id
    
    def _is_compatible(self, node: VisualNode, var_type: str) -> bool:
        """Check if node is compatible with variable type"""
        type_mappings = {
            "service": ["service", "web_app"],
            "database": ["database"],
            "cache": ["cache"],
            "queue": ["queue"],
            "client": ["actor", "web_app"],
            "producer": ["service", "web_app"],
            "consumer": ["service"],
            "caller": ["service", "web_app", "gateway"],
            "callee": ["service", "database", "external"],
        }
        
        compatible_types = type_mappings.get(var_type, [var_type])
        return node.node_type in compatible_types


def inject_pattern_into_context(
    context: PipelineContext,
    pattern: Pattern,
    mappings: List[InjectionMapping],
) -> InjectionResult:
    """
    Convenience function to inject pattern into a pipeline context
    
    Creates visual_ir if it doesn't exist.
    """
    if not context.visual_ir:
        # Create empty visual diagram
        from app.visual.visual_mapper import map_context_to_visual_ir
        context.visual_ir = map_context_to_visual_ir(context)
    
    injector = PatternInjector()
    return injector.inject(context.visual_ir, pattern, mappings)
