"""
Diagram Validator - Validates the completeness and correctness of generated diagrams.

Catches issues like:
- Orphaned nodes (no connections)
- Missing node references in edges
- Duplicate IDs
- Empty labels
- Circular dependencies
- Layer integrity issues
- Missing required components
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional, Tuple
from enum import Enum
from collections import defaultdict

from app.visual.visual_schema import VisualDiagram, VisualNode, VisualEdge


class ValidationSeverity(Enum):
    ERROR = "error"      # Diagram will not render correctly
    WARNING = "warning"  # Diagram renders but has issues
    INFO = "info"        # Suggestions for improvement


@dataclass
class ValidationIssue:
    """A single validation issue found in the diagram"""
    severity: ValidationSeverity
    code: str           # Machine-readable issue code
    message: str        # Human-readable description
    node_id: Optional[str] = None
    edge_info: Optional[str] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "edge_info": self.edge_info,
            "suggestion": self.suggestion,
        }


@dataclass
class DiagramValidationResult:
    """Result of diagram validation"""
    is_valid: bool
    is_complete: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
    
    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "is_complete": self.is_complete,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        status = "✅ Valid" if self.is_valid else "❌ Invalid"
        completeness = "Complete" if self.is_complete else "Incomplete"
        return (
            f"{status} | {completeness} | "
            f"Errors: {self.error_count}, Warnings: {self.warning_count}, Info: {self.info_count}"
        )


class DiagramValidator:
    """
    Validates Visual IR diagrams for completeness and correctness.
    
    Usage:
        validator = DiagramValidator()
        result = validator.validate(visual_ir)
        
        if not result.is_valid:
            for issue in result.issues:
                print(f"[{issue.severity.value}] {issue.message}")
    """
    
    EXPECTED_LAYERS = {"business", "service", "data", "infra"}
    PRODUCER_TYPES = {"actor", "web_app", "gateway", "service"}
    CONSUMER_TYPES = {"database", "queue", "cache"}
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
    
    def validate(self, diagram: VisualDiagram) -> DiagramValidationResult:
        """Validate the entire diagram."""
        issues: List[ValidationIssue] = []
        
        if not diagram:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="EMPTY_DIAGRAM",
                message="Diagram is None or empty",
                suggestion="Ensure the pipeline generates a valid VisualDiagram"
            ))
            return DiagramValidationResult(
                is_valid=False,
                is_complete=False,
                issues=issues,
                stats={"nodes": 0, "edges": 0}
            )
        
        node_ids = {node.id for node in diagram.nodes}
        
        # Run all validation checks
        issues.extend(self._check_empty_diagram(diagram))
        issues.extend(self._check_duplicate_node_ids(diagram))
        issues.extend(self._check_empty_labels(diagram))
        issues.extend(self._check_orphaned_nodes(diagram, node_ids))
        issues.extend(self._check_missing_edge_references(diagram, node_ids))
        issues.extend(self._check_self_loops(diagram))
        issues.extend(self._check_duplicate_edges(diagram))
        issues.extend(self._check_layer_coverage(diagram))
        issues.extend(self._check_circular_dependencies(diagram))
        issues.extend(self._check_node_type_connections(diagram))
        
        stats = self._calculate_stats(diagram, node_ids)
        
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)
        has_warnings = any(i.severity == ValidationSeverity.WARNING for i in issues)
        
        is_valid = not has_errors
        if self.strict_mode:
            is_valid = not has_errors and not has_warnings
        
        is_complete = not has_errors and stats.get("orphaned_nodes", 0) == 0
        
        return DiagramValidationResult(
            is_valid=is_valid,
            is_complete=is_complete,
            issues=issues,
            stats=stats,
        )
    
    def _check_empty_diagram(self, diagram: VisualDiagram) -> List[ValidationIssue]:
        issues = []
        if not diagram.nodes:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="NO_NODES",
                message="Diagram has no nodes",
                suggestion="Ensure the pipeline extracts components from requirements"
            ))
        if not diagram.edges and len(diagram.nodes) > 1:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="NO_EDGES",
                message=f"Diagram has {len(diagram.nodes)} nodes but no edges",
                suggestion="Add connections between components"
            ))
        return issues
    
    def _check_duplicate_node_ids(self, diagram: VisualDiagram) -> List[ValidationIssue]:
        issues = []
        seen_ids: Dict[str, int] = defaultdict(int)
        for node in diagram.nodes:
            seen_ids[node.id] += 1
        for node_id, count in seen_ids.items():
            if count > 1:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DUPLICATE_NODE_ID",
                    message=f"Duplicate node ID '{node_id}' appears {count} times",
                    node_id=node_id,
                    suggestion="Ensure each node has a unique ID"
                ))
        return issues
    
    def _check_empty_labels(self, diagram: VisualDiagram) -> List[ValidationIssue]:
        issues = []
        for node in diagram.nodes:
            if not node.label or not node.label.strip():
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="EMPTY_LABEL",
                    message=f"Node '{node.id}' has empty label",
                    node_id=node.id,
                    suggestion="Add a descriptive label to the node"
                ))
        return issues
    
    def _check_orphaned_nodes(self, diagram: VisualDiagram, node_ids: Set[str]) -> List[ValidationIssue]:
        issues = []
        nodes_with_outgoing: Set[str] = set()
        nodes_with_incoming: Set[str] = set()
        
        for edge in diagram.edges:
            nodes_with_outgoing.add(edge.source)
            nodes_with_incoming.add(edge.target)
        
        connected_nodes = nodes_with_outgoing | nodes_with_incoming
        orphaned = node_ids - connected_nodes
        
        print(f"[VALIDATOR] Orphan check: {len(orphaned)} orphaned out of {len(node_ids)} nodes")
        print(f"[VALIDATOR] Connected nodes: {connected_nodes}")
        print(f"[VALIDATOR] Orphaned nodes: {orphaned}")
        
        for node_id in orphaned:
            node = next((n for n in diagram.nodes if n.id == node_id), None)
            node_type = node.node_type if node else "unknown"
            node_label = node.label if node else "?"
            node_group = node.group if node else None
            
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="ORPHANED_NODE",
                message=f"Node '{node_label}' ({node_id}, type={node_type}, group={node_group}) has no connections",
                node_id=node_id,
                suggestion=f"Connect this {node_type} to other components or remove if unused"
            ))
        return issues
    
    def _check_missing_edge_references(self, diagram: VisualDiagram, node_ids: Set[str]) -> List[ValidationIssue]:
        issues = []
        for edge in diagram.edges:
            if edge.source not in node_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_SOURCE_NODE",
                    message=f"Edge references non-existent source node '{edge.source}'",
                    edge_info=f"{edge.source} -> {edge.target}",
                    suggestion=f"Add node '{edge.source}' or fix the edge reference"
                ))
            if edge.target not in node_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_TARGET_NODE",
                    message=f"Edge references non-existent target node '{edge.target}'",
                    edge_info=f"{edge.source} -> {edge.target}",
                    suggestion=f"Add node '{edge.target}' or fix the edge reference"
                ))
        return issues
    
    def _check_self_loops(self, diagram: VisualDiagram) -> List[ValidationIssue]:
        issues = []
        for edge in diagram.edges:
            if edge.source == edge.target:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="SELF_LOOP",
                    message=f"Edge creates self-loop on node '{edge.source}'",
                    node_id=edge.source,
                    edge_info=f"{edge.source} -> {edge.target}",
                    suggestion="Remove self-referencing edge unless intentional"
                ))
        return issues
    
    def _check_duplicate_edges(self, diagram: VisualDiagram) -> List[ValidationIssue]:
        issues = []
        edge_counts: Dict[Tuple[str, str, str], int] = defaultdict(int)
        for edge in diagram.edges:
            key = (edge.source, edge.target, edge.relation or "")
            edge_counts[key] += 1
        for (source, target, relation), count in edge_counts.items():
            if count > 1:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="DUPLICATE_EDGE",
                    message=f"Duplicate edge '{source}' -> '{target}' ({relation}) appears {count} times",
                    edge_info=f"{source} -> {target}",
                    suggestion="Consider consolidating duplicate edges"
                ))
        return issues
    
    def _check_layer_coverage(self, diagram: VisualDiagram) -> List[ValidationIssue]:
        issues = []
        present_layers = {node.layer for node in diagram.nodes if node.layer}
        missing_layers = self.EXPECTED_LAYERS - present_layers
        for layer in missing_layers:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="MISSING_LAYER",
                message=f"Architecture layer '{layer}' has no components",
                suggestion=f"Consider adding {layer} layer components for completeness"
            ))
        return issues
    
    def _check_circular_dependencies(self, diagram: VisualDiagram) -> List[ValidationIssue]:
        issues = []
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for edge in diagram.edges:
            adjacency[edge.source].add(edge.target)
        
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles_found: List[List[str]] = []
        
        def dfs(node: str, path: List[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path + [neighbor]):
                        return True
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor) if neighbor in path else 0
                    cycle = path[cycle_start:] + [neighbor]
                    cycles_found.append(cycle)
                    return True
            rec_stack.remove(node)
            return False
        
        for node in [n.id for n in diagram.nodes]:
            if node not in visited:
                dfs(node, [node])
        
        for cycle in cycles_found[:3]:
            cycle_str = " -> ".join(cycle)
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="CIRCULAR_DEPENDENCY",
                message=f"Circular dependency detected: {cycle_str}",
                suggestion="Consider breaking the cycle with an intermediary or event-driven pattern"
            ))
        return issues
    
    def _check_node_type_connections(self, diagram: VisualDiagram) -> List[ValidationIssue]:
        issues = []
        outgoing: Dict[str, int] = defaultdict(int)
        incoming: Dict[str, int] = defaultdict(int)
        
        for edge in diagram.edges:
            outgoing[edge.source] += 1
            incoming[edge.target] += 1
        
        for node in diagram.nodes:
            if node.node_type == "actor" and outgoing[node.id] == 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="ACTOR_NO_OUTGOING",
                    message=f"Actor '{node.label}' has no outgoing connections",
                    node_id=node.id,
                    suggestion="Connect actor to services or entry points they interact with"
                ))
            if node.node_type == "database" and incoming[node.id] == 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="DATABASE_NO_INCOMING",
                    message=f"Database '{node.label}' has no incoming connections",
                    node_id=node.id,
                    suggestion="Connect services that read/write to this database"
                ))
            if node.node_type == "service":
                if outgoing[node.id] == 0 and incoming[node.id] == 0:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="ISOLATED_SERVICE",
                        message=f"Service '{node.label}' is completely isolated",
                        node_id=node.id,
                        suggestion="Connect service to its dependencies and consumers"
                    ))
        return issues
    
    def _calculate_stats(self, diagram: VisualDiagram, node_ids: Set[str]) -> Dict[str, int]:
        type_counts: Dict[str, int] = defaultdict(int)
        for node in diagram.nodes:
            type_counts[node.node_type] += 1
        
        connected = set()
        for edge in diagram.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        
        return {
            "nodes": len(diagram.nodes),
            "edges": len(diagram.edges),
            "orphaned_nodes": len(node_ids - connected),
            "actors": type_counts.get("actor", 0),
            "services": type_counts.get("service", 0) + type_counts.get("web_app", 0),
            "databases": type_counts.get("database", 0),
            "infrastructure": type_counts.get("infrastructure", 0),
        }


def validate_diagram(diagram: VisualDiagram, strict: bool = False) -> DiagramValidationResult:
    """Convenience function to validate a diagram."""
    validator = DiagramValidator(strict_mode=strict)
    return validator.validate(diagram)


def get_validation_summary(diagram: VisualDiagram) -> str:
    """Get a quick validation summary string."""
    result = validate_diagram(diagram)
    return result.get_summary()


def raise_on_errors(diagram: VisualDiagram) -> None:
    """Validate diagram and raise exception if errors found."""
    result = validate_diagram(diagram, strict=True)
    if not result.is_valid:
        error_messages = [
            f"[{i.code}] {i.message}"
            for i in result.issues
            if i.severity == ValidationSeverity.ERROR
        ]
        raise ValueError(
            f"Diagram validation failed with {result.error_count} errors:\n" +
            "\n".join(error_messages)
        )
