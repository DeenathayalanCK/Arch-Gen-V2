"""
Diagram Auto-Fixer - Hybrid approach for fixing diagram issues.

Simple fixes (duplicates, invalid refs) -> Auto-fix (rule-based, no LLM)
Complex fixes (orphans, patterns) -> LLM fallback
Fallback if LLM fails -> Remove problematic elements or apply heuristics
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
import copy

from app.visual.visual_schema import VisualDiagram, VisualNode, VisualEdge
from app.validation.diagram_validator import (
    DiagramValidator,
    DiagramValidationResult,
    ValidationIssue,
    ValidationSeverity,
)


@dataclass
class FixResult:
    """Result of a fix operation"""
    success: bool
    fix_type: str  # "auto" | "llm" | "fallback"
    issues_fixed: List[str] = field(default_factory=list)
    issues_remaining: List[str] = field(default_factory=list)
    changes_made: List[str] = field(default_factory=list)
    llm_used: bool = False
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "fix_type": self.fix_type,
            "issues_fixed": self.issues_fixed,
            "issues_remaining": self.issues_remaining,
            "changes_made": self.changes_made,
            "llm_used": self.llm_used,
        }


class DiagramAutoFixer:
    """
    Hybrid auto-fixer for diagram issues.
    
    Fix priority:
    1. Rule-based auto-fixes (fast, deterministic)
    2. LLM-based fixes for complex issues
    3. Fallback fixes if LLM fails
    
    Usage:
        fixer = DiagramAutoFixer()
        fixed_diagram, result = fixer.fix(diagram, validation_result)
    """
    
    # Issue codes that can be auto-fixed without LLM
    AUTO_FIXABLE = {
        "DUPLICATE_NODE_ID",
        "DUPLICATE_EDGE",
        "MISSING_SOURCE_NODE",
        "MISSING_TARGET_NODE",
        "SELF_LOOP",
        "EMPTY_LABEL",
    }
    
    # Issue codes that need LLM assistance
    LLM_FIXABLE = {
        "ORPHANED_NODE",
        "NO_EDGES",
        "ACTOR_NO_OUTGOING",
        "DATABASE_NO_INCOMING",
        "ISOLATED_SERVICE",
        "CIRCULAR_DEPENDENCY",
    }
    
    def __init__(self, max_iterations: int = 3, use_llm: bool = True):
        """
        Initialize the fixer.
        
        Args:
            max_iterations: Maximum fix iterations to prevent infinite loops
            use_llm: Whether to use LLM for complex fixes
        """
        self.max_iterations = max_iterations
        self.use_llm = use_llm
        self.validator = DiagramValidator()
        self._llm_client = None
    
    @property
    def llm_client(self):
        """Lazy load LLM client"""
        if self._llm_client is None and self.use_llm:
            try:
                from app.llm.client import LLMClient
                self._llm_client = LLMClient()
            except Exception as e:
                print(f"[FIXER] Failed to initialize LLM client: {e}")
                self._llm_client = False  # Mark as unavailable
        return self._llm_client if self._llm_client else None
    
    def fix(
        self,
        diagram: VisualDiagram,
        validation_result: Optional[DiagramValidationResult] = None,
    ) -> Tuple[VisualDiagram, FixResult]:
        """
        Fix diagram issues using hybrid approach.
        
        Returns:
            Tuple of (fixed_diagram, fix_result)
        """
        # Work on a copy to preserve original
        fixed_diagram = self._deep_copy_diagram(diagram)
        
        all_changes = []
        all_fixed = []
        llm_used = False
        
        for iteration in range(self.max_iterations):
            print(f"\n[FIXER] === Iteration {iteration + 1}/{self.max_iterations} ===")
            
            # Validate current state
            if validation_result is None or iteration > 0:
                validation_result = self.validator.validate(fixed_diagram)
            
            if validation_result.is_valid and validation_result.is_complete:
                print("[FIXER] ✅ Diagram is valid and complete!")
                break
            
            # Collect issues by fixability
            auto_issues = []
            llm_issues = []
            
            for issue in validation_result.issues:
                if issue.code in self.AUTO_FIXABLE:
                    auto_issues.append(issue)
                elif issue.code in self.LLM_FIXABLE:
                    llm_issues.append(issue)
            
            # Phase 1: Auto-fix simple issues
            if auto_issues:
                print(f"[FIXER] Applying {len(auto_issues)} auto-fixes...")
                changes, fixed = self._apply_auto_fixes(fixed_diagram, auto_issues)
                all_changes.extend(changes)
                all_fixed.extend(fixed)
            
            # Phase 2: LLM fixes for complex issues
            if llm_issues and self.use_llm and self.llm_client:
                print(f"[FIXER] Attempting LLM fixes for {len(llm_issues)} issues...")
                try:
                    changes, fixed = self._apply_llm_fixes(fixed_diagram, llm_issues)
                    all_changes.extend(changes)
                    all_fixed.extend(fixed)
                    llm_used = True
                except Exception as e:
                    print(f"[FIXER] ⚠️ LLM fix failed: {e}")
                    # Apply fallback fixes
                    changes, fixed = self._apply_fallback_fixes(fixed_diagram, llm_issues)
                    all_changes.extend(changes)
                    all_fixed.extend(fixed)
            
            # Phase 3: Fallback if no LLM available
            elif llm_issues and (not self.use_llm or not self.llm_client):
                print(f"[FIXER] Applying fallback fixes for {len(llm_issues)} issues...")
                changes, fixed = self._apply_fallback_fixes(fixed_diagram, llm_issues)
                all_changes.extend(changes)
                all_fixed.extend(fixed)
            
            # Reset for next iteration
            validation_result = None
        
        # Final validation
        final_validation = self.validator.validate(fixed_diagram)
        remaining_issues = [i.code for i in final_validation.issues if i.severity == ValidationSeverity.ERROR]
        
        result = FixResult(
            success=final_validation.is_valid,
            fix_type="llm" if llm_used else "auto",
            issues_fixed=list(set(all_fixed)),
            issues_remaining=remaining_issues,
            changes_made=all_changes,
            llm_used=llm_used,
        )
        
        print(f"\n[FIXER] Fix complete: {result.to_dict()}")
        return fixed_diagram, result
    
    # ============================================================
    # AUTO-FIX METHODS (Rule-based, no LLM)
    # ============================================================
    
    def _apply_auto_fixes(
        self,
        diagram: VisualDiagram,
        issues: List[ValidationIssue],
    ) -> Tuple[List[str], List[str]]:
        """Apply deterministic auto-fixes"""
        changes = []
        fixed = []
        
        for issue in issues:
            if issue.code == "DUPLICATE_NODE_ID":
                if self._fix_duplicate_node_id(diagram, issue):
                    changes.append(f"Renamed duplicate node: {issue.node_id}")
                    fixed.append(issue.code)
            
            elif issue.code == "DUPLICATE_EDGE":
                if self._fix_duplicate_edge(diagram, issue):
                    changes.append(f"Removed duplicate edge: {issue.edge_info}")
                    fixed.append(issue.code)
            
            elif issue.code == "MISSING_SOURCE_NODE":
                if self._fix_missing_node_reference(diagram, issue, is_source=True):
                    changes.append(f"Removed edge with missing source: {issue.edge_info}")
                    fixed.append(issue.code)
            
            elif issue.code == "MISSING_TARGET_NODE":
                if self._fix_missing_node_reference(diagram, issue, is_source=False):
                    changes.append(f"Removed edge with missing target: {issue.edge_info}")
                    fixed.append(issue.code)
            
            elif issue.code == "SELF_LOOP":
                if self._fix_self_loop(diagram, issue):
                    changes.append(f"Removed self-loop on: {issue.node_id}")
                    fixed.append(issue.code)
            
            elif issue.code == "EMPTY_LABEL":
                if self._fix_empty_label(diagram, issue):
                    changes.append(f"Set default label for: {issue.node_id}")
                    fixed.append(issue.code)
        
        return changes, fixed
    
    def _fix_duplicate_node_id(self, diagram: VisualDiagram, issue: ValidationIssue) -> bool:
        """Rename duplicate node IDs by adding suffix"""
        node_id = issue.node_id
        if not node_id:
            return False
        
        seen = set()
        counter = 1
        
        for node in diagram.nodes:
            if node.id == node_id:
                if node.id in seen:
                    # Rename this duplicate
                    new_id = f"{node.id}_{counter}"
                    while new_id in seen:
                        counter += 1
                        new_id = f"{node.id}_{counter}"
                    
                    # Update edges referencing old ID
                    for edge in diagram.edges:
                        if edge.source == node.id:
                            edge.source = new_id
                        if edge.target == node.id:
                            edge.target = new_id
                    
                    node.id = new_id
                    counter += 1
                seen.add(node.id)
        
        return True
    
    def _fix_duplicate_edge(self, diagram: VisualDiagram, issue: ValidationIssue) -> bool:
        """Remove duplicate edges, keep first occurrence"""
        seen: Set[Tuple[str, str, str]] = set()
        edges_to_keep = []
        
        for edge in diagram.edges:
            key = (edge.source, edge.target, edge.relation or "")
            if key not in seen:
                edges_to_keep.append(edge)
                seen.add(key)
        
        diagram.edges = edges_to_keep
        return True
    
    def _fix_missing_node_reference(
        self,
        diagram: VisualDiagram,
        issue: ValidationIssue,
        is_source: bool,
    ) -> bool:
        """Remove edges that reference non-existent nodes"""
        if not issue.edge_info:
            return False
        
        # Parse edge info "source -> target"
        parts = issue.edge_info.split(" -> ")
        if len(parts) != 2:
            return False
        
        source, target = parts
        
        # Remove the problematic edge
        diagram.edges = [
            e for e in diagram.edges
            if not (e.source == source and e.target == target)
        ]
        return True
    
    def _fix_self_loop(self, diagram: VisualDiagram, issue: ValidationIssue) -> bool:
        """Remove self-referencing edges"""
        if not issue.node_id:
            return False
        
        diagram.edges = [
            e for e in diagram.edges
            if not (e.source == issue.node_id and e.target == issue.node_id)
        ]
        return True
    
    def _fix_empty_label(self, diagram: VisualDiagram, issue: ValidationIssue) -> bool:
        """Set default label based on node ID"""
        if not issue.node_id:
            return False
        
        for node in diagram.nodes:
            if node.id == issue.node_id:
                # Generate label from ID
                label = issue.node_id.replace("_", " ").replace("-", " ").title()
                node.label = label
                return True
        return False
    
    # ============================================================
    # LLM-BASED FIXES (Complex issues)
    # ============================================================
    
    def _apply_llm_fixes(
        self,
        diagram: VisualDiagram,
        issues: List[ValidationIssue],
    ) -> Tuple[List[str], List[str]]:
        """Use LLM to fix complex issues"""
        changes = []
        fixed = []
        
        # Group issues by type for efficient prompting
        orphan_nodes = [i for i in issues if i.code == "ORPHANED_NODE"]
        connection_issues = [i for i in issues if i.code in ("ACTOR_NO_OUTGOING", "DATABASE_NO_INCOMING", "ISOLATED_SERVICE")]
        
        # Fix orphan nodes by suggesting connections
        if orphan_nodes:
            try:
                new_edges = self._llm_suggest_connections_for_orphans(diagram, orphan_nodes)
                if new_edges:
                    diagram.edges.extend(new_edges)
                    changes.append(f"Added {len(new_edges)} connections for orphan nodes via LLM")
                    fixed.extend(["ORPHANED_NODE"] * len(orphan_nodes))
            except Exception as e:
                print(f"[FIXER] LLM orphan fix failed: {e}")
        
        # Fix connection issues
        if connection_issues:
            try:
                new_edges = self._llm_suggest_missing_connections(diagram, connection_issues)
                if new_edges:
                    diagram.edges.extend(new_edges)
                    changes.append(f"Added {len(new_edges)} missing connections via LLM")
                    fixed.extend([i.code for i in connection_issues])
            except Exception as e:
                print(f"[FIXER] LLM connection fix failed: {e}")
        
        return changes, fixed
    
    def _llm_suggest_connections_for_orphans(
        self,
        diagram: VisualDiagram,
        orphan_issues: List[ValidationIssue],
    ) -> List[VisualEdge]:
        """Ask LLM to suggest connections for orphan nodes"""
        if not self.llm_client:
            return []
        
        orphan_ids = [i.node_id for i in orphan_issues if i.node_id]
        if not orphan_ids:
            return []
        
        # Build context
        all_nodes = [{"id": n.id, "label": n.label, "type": n.node_type} for n in diagram.nodes]
        existing_edges = [{"from": e.source, "to": e.target, "rel": e.relation} for e in diagram.edges]
        
        prompt = f"""You are an expert software architect fixing an architecture diagram.

The following nodes are ORPHANED (no connections):
{orphan_ids}

All nodes in the diagram:
{all_nodes}

Existing connections:
{existing_edges}

Suggest connections to fix the orphaned nodes. Consider:
- Actors should connect to services they use
- Services should connect to databases they access
- Services should connect to other services they depend on

Return ONLY a JSON array of new edges:
[
  {{"from": "source_node_id", "to": "target_node_id", "relation": "relationship_label"}},
  ...
]

Return [] if no sensible connections can be made.
"""
        
        try:
            from app.llm.parser import safe_load_json
            response = self.llm_client.generate(prompt)
            edges_data = safe_load_json(response)
            
            if not isinstance(edges_data, list):
                return []
            
            new_edges = []
            node_ids = {n.id for n in diagram.nodes}
            
            for edge in edges_data:
                if not isinstance(edge, dict):
                    continue
                
                source = edge.get("from", "")
                target = edge.get("to", "")
                relation = edge.get("relation", "connects to")
                
                # Validate nodes exist
                if source in node_ids and target in node_ids:
                    new_edges.append(VisualEdge(
                        source=source,
                        target=target,
                        relation=relation,
                        style="solid",
                    ))
            
            return new_edges
            
        except Exception as e:
            print(f"[FIXER] LLM edge suggestion failed: {e}")
            return []
    
    def _llm_suggest_missing_connections(
        self,
        diagram: VisualDiagram,
        issues: List[ValidationIssue],
    ) -> List[VisualEdge]:
        """Ask LLM to suggest missing required connections"""
        if not self.llm_client:
            return []
        
        # Build issue context
        issue_descriptions = []
        for issue in issues:
            node = next((n for n in diagram.nodes if n.id == issue.node_id), None)
            if node:
                issue_descriptions.append({
                    "node_id": node.id,
                    "node_label": node.label,
                    "node_type": node.node_type,
                    "issue": issue.code,
                    "message": issue.message,
                })
        
        if not issue_descriptions:
            return []
        
        all_nodes = [{"id": n.id, "label": n.label, "type": n.node_type} for n in diagram.nodes]
        
        prompt = f"""You are an expert software architect fixing an architecture diagram.

These nodes have connection issues:
{issue_descriptions}

All nodes available:
{all_nodes}

Fix the issues by suggesting appropriate connections:
- ACTOR_NO_OUTGOING: Connect actor to a service it would use
- DATABASE_NO_INCOMING: Connect a service to read/write from the database
- ISOLATED_SERVICE: Connect service to its consumers and dependencies

Return ONLY a JSON array of new edges:
[
  {{"from": "source_node_id", "to": "target_node_id", "relation": "relationship_label"}},
  ...
]
"""
        
        try:
            from app.llm.parser import safe_load_json
            response = self.llm_client.generate(prompt)
            edges_data = safe_load_json(response)
            
            if not isinstance(edges_data, list):
                return []
            
            new_edges = []
            node_ids = {n.id for n in diagram.nodes}
            
            for edge in edges_data:
                if not isinstance(edge, dict):
                    continue
                
                source = edge.get("from", "")
                target = edge.get("to", "")
                relation = edge.get("relation", "uses")
                
                if source in node_ids and target in node_ids:
                    new_edges.append(VisualEdge(
                        source=source,
                        target=target,
                        relation=relation,
                        style="solid",
                    ))
            
            return new_edges
            
        except Exception as e:
            print(f"[FIXER] LLM connection suggestion failed: {e}")
            return []
    
    # ============================================================
    # FALLBACK FIXES (When LLM fails or unavailable)
    # ============================================================
    
    def _apply_fallback_fixes(
        self,
        diagram: VisualDiagram,
        issues: List[ValidationIssue],
    ) -> Tuple[List[str], List[str]]:
        """Apply heuristic-based fallback fixes"""
        changes = []
        fixed = []
        
        for issue in issues:
            if issue.code == "ORPHANED_NODE":
                if self._fallback_fix_orphan(diagram, issue):
                    changes.append(f"Applied fallback fix for orphan: {issue.node_id}")
                    fixed.append(issue.code)
            
            elif issue.code == "ACTOR_NO_OUTGOING":
                if self._fallback_connect_actor(diagram, issue):
                    changes.append(f"Connected actor to first service: {issue.node_id}")
                    fixed.append(issue.code)
            
            elif issue.code == "DATABASE_NO_INCOMING":
                if self._fallback_connect_database(diagram, issue):
                    changes.append(f"Connected service to database: {issue.node_id}")
                    fixed.append(issue.code)
            
            elif issue.code == "ISOLATED_SERVICE":
                if self._fallback_connect_service(diagram, issue):
                    changes.append(f"Connected isolated service: {issue.node_id}")
                    fixed.append(issue.code)
            
            elif issue.code == "NO_EDGES":
                if self._fallback_create_basic_edges(diagram):
                    changes.append("Created basic edge structure")
                    fixed.append(issue.code)
        
        return changes, fixed
    
    def _fallback_fix_orphan(self, diagram: VisualDiagram, issue: ValidationIssue) -> bool:
        """Heuristic: Connect orphan to most likely related node or remove if from pattern"""
        if not issue.node_id:
            return False
        
        orphan = next((n for n in diagram.nodes if n.id == issue.node_id), None)
        if not orphan:
            return False
        
        print(f"[FIXER] Fixing orphan: {orphan.id} ({orphan.node_type}, group={orphan.group})")
        
        # Strategy based on node type
        if orphan.node_type == "actor":
            # Connect to first web_app or service
            target = next(
                (n for n in diagram.nodes if n.node_type in ("web_app", "service", "gateway")),
                None
            )
            if target:
                diagram.edges.append(VisualEdge(
                    source=orphan.id,
                    target=target.id,
                    relation="uses",
                    style="solid",
                ))
                print(f"[FIXER] Connected actor {orphan.id} -> {target.id}")
                return True
        
        elif orphan.node_type == "database":
            # Connect from first service
            source = next(
                (n for n in diagram.nodes if n.node_type in ("service", "web_app")),
                None
            )
            if source:
                diagram.edges.append(VisualEdge(
                    source=source.id,
                    target=orphan.id,
                    relation="reads/writes",
                    style="dotted",
                ))
                print(f"[FIXER] Connected service {source.id} -> database {orphan.id}")
                return True
        
        elif orphan.node_type in ("service", "web_app"):
            # Connect to/from other services or databases
            other_service = next(
                (n for n in diagram.nodes 
                 if n.node_type in ("service", "web_app") and n.id != orphan.id),
                None
            )
            database = next(
                (n for n in diagram.nodes if n.node_type == "database"),
                None
            )
            
            if other_service:
                diagram.edges.append(VisualEdge(
                    source=other_service.id,
                    target=orphan.id,
                    relation="calls",
                    style="solid",
                ))
                print(f"[FIXER] Connected service {other_service.id} -> {orphan.id}")
                return True
            elif database:
                diagram.edges.append(VisualEdge(
                    source=orphan.id,
                    target=database.id,
                    relation="accesses",
                    style="dotted",
                ))
                print(f"[FIXER] Connected {orphan.id} -> database {database.id}")
                return True
        
        elif orphan.node_type in ("cache", "queue", "gateway", "infrastructure"):
            # Pattern components - connect to nearest service
            service = next(
                (n for n in diagram.nodes if n.node_type in ("service", "web_app")),
                None
            )
            if service:
                diagram.edges.append(VisualEdge(
                    source=service.id,
                    target=orphan.id,
                    relation="uses",
                    style="solid",
                ))
                print(f"[FIXER] Connected service {service.id} -> pattern node {orphan.id}")
                return True
        
        # LAST RESORT: Remove orphan if it's from a pattern injection
        if orphan.group and orphan.group.startswith("pattern_"):
            print(f"[FIXER] Removing pattern orphan: {orphan.id}")
            diagram.nodes = [n for n in diagram.nodes if n.id != orphan.id]
            # Also remove any edges that reference this node
            diagram.edges = [
                e for e in diagram.edges 
                if e.source != orphan.id and e.target != orphan.id
            ]
            return True
        
        # If we still can't fix it, try to connect to ANY node
        any_node = next(
            (n for n in diagram.nodes if n.id != orphan.id),
            None
        )
        if any_node:
            print(f"[FIXER] Last resort: connecting {orphan.id} -> {any_node.id}")
            diagram.edges.append(VisualEdge(
                source=orphan.id,
                target=any_node.id,
                relation="connects to",
                style="dashed",
            ))
            return True
        
        return False
    
    def _fallback_connect_actor(self, diagram: VisualDiagram, issue: ValidationIssue) -> bool:
        """Connect actor to first available service"""
        if not issue.node_id:
            return False
        
        target = next(
            (n for n in diagram.nodes if n.node_type in ("web_app", "gateway", "service")),
            None
        )
        if target:
            diagram.edges.append(VisualEdge(
                source=issue.node_id,
                target=target.id,
                relation="uses",
                style="dashed",
            ))
            return True
        return False
    
    def _fallback_connect_database(self, diagram: VisualDiagram, issue: ValidationIssue) -> bool:
        """Connect first service to the database"""
        if not issue.node_id:
            return False
        
        source = next(
            (n for n in diagram.nodes if n.node_type in ("service", "web_app")),
            None
        )
        if source:
            diagram.edges.append(VisualEdge(
                source=source.id,
                target=issue.node_id,
                relation="reads/writes",
                style="dotted",
            ))
            return True
        return False
    
    def _fallback_connect_service(self, diagram: VisualDiagram, issue: ValidationIssue) -> bool:
        """Connect isolated service to something"""
        if not issue.node_id:
            return False
        
        # Try to find a database to connect to
        database = next(
            (n for n in diagram.nodes if n.node_type == "database"),
            None
        )
        if database:
            diagram.edges.append(VisualEdge(
                source=issue.node_id,
                target=database.id,
                relation="accesses",
                style="dotted",
            ))
            return True
        
        # Try to find another service
        other = next(
            (n for n in diagram.nodes 
             if n.node_type in ("service", "web_app") and n.id != issue.node_id),
            None
        )
        if other:
            diagram.edges.append(VisualEdge(
                source=issue.node_id,
                target=other.id,
                relation="calls",
                style="solid",
            ))
            return True
        
        return False
    
    def _fallback_create_basic_edges(self, diagram: VisualDiagram) -> bool:
        """Create basic hierarchical edge structure"""
        if len(diagram.nodes) < 2:
            return False
        
        # Group by type
        actors = [n for n in diagram.nodes if n.node_type == "actor"]
        services = [n for n in diagram.nodes if n.node_type in ("service", "web_app", "gateway")]
        databases = [n for n in diagram.nodes if n.node_type == "database"]
        
        created = False
        
        # Connect actors to first service
        if actors and services:
            for actor in actors:
                diagram.edges.append(VisualEdge(
                    source=actor.id,
                    target=services[0].id,
                    relation="uses",
                    style="dashed",
                ))
                created = True
        
        # Connect services to databases
        if services and databases:
            for svc in services:
                diagram.edges.append(VisualEdge(
                    source=svc.id,
                    target=databases[0].id,
                    relation="accesses",
                    style="dotted",
                ))
                created = True
        
        # Chain services together
        if len(services) > 1:
            for i in range(len(services) - 1):
                diagram.edges.append(VisualEdge(
                    source=services[i].id,
                    target=services[i + 1].id,
                    relation="calls",
                    style="solid",
                ))
                created = True
        
        return created
    
    # ============================================================
    # UTILITY METHODS
    # ============================================================
    
    def _deep_copy_diagram(self, diagram: VisualDiagram) -> VisualDiagram:
        """Create a deep copy of the diagram"""
        return VisualDiagram(
            nodes=[
                VisualNode(
                    id=n.id,
                    label=n.label,
                    node_type=n.node_type,
                    layer=n.layer,
                    shape=n.shape,
                    color=n.color,
                    icon=n.icon,
                    group=n.group,
                    details=list(n.details) if n.details else [],
                )
                for n in diagram.nodes
            ],
            edges=[
                VisualEdge(
                    source=e.source,
                    target=e.target,
                    relation=e.relation,
                    style=e.style,
                )
                for e in diagram.edges
            ],
            layout=diagram.layout,
        )


# ============================================================
# Convenience Functions
# ============================================================

def auto_fix_diagram(
    diagram: VisualDiagram,
    use_llm: bool = True,
    max_iterations: int = 3,
) -> Tuple[VisualDiagram, FixResult]:
    """
    Convenience function to auto-fix a diagram.
    
    Args:
        diagram: The diagram to fix
        use_llm: Whether to use LLM for complex fixes
        max_iterations: Maximum fix iterations
        
    Returns:
        Tuple of (fixed_diagram, fix_result)
    """
    fixer = DiagramAutoFixer(max_iterations=max_iterations, use_llm=use_llm)
    return fixer.fix(diagram)


def validate_and_fix_diagram(
    diagram: VisualDiagram,
    use_llm: bool = True,
) -> Tuple[VisualDiagram, DiagramValidationResult, FixResult]:
    """
    Validate diagram, fix if needed, return all results.
    
    Returns:
        Tuple of (fixed_diagram, final_validation, fix_result)
    """
    validator = DiagramValidator()
    initial_result = validator.validate(diagram)
    
    if initial_result.is_valid and initial_result.is_complete:
        return diagram, initial_result, FixResult(
            success=True,
            fix_type="none",
            issues_fixed=[],
            issues_remaining=[],
            changes_made=["No fixes needed"],
        )
    
    fixed_diagram, fix_result = auto_fix_diagram(diagram, use_llm=use_llm)
    final_result = validator.validate(fixed_diagram)
    
    return fixed_diagram, final_result, fix_result
