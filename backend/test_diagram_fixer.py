"""Test script for the DiagramAutoFixer"""

from app.visual.visual_schema import VisualDiagram, VisualNode, VisualEdge
from app.validation import validate_diagram, auto_fix_diagram, validate_and_fix_diagram


def make_node(id: str, label: str, node_type: str = "service", layer: str = "service") -> VisualNode:
    return VisualNode(
        id=id,
        label=label,
        node_type=node_type,
        layer=layer,
        shape="rectangle",
        color="#4CAF50",
    )


def test_auto_fixer():
    print("\n" + "=" * 60)
    print("DIAGRAM AUTO-FIXER TEST")
    print("=" * 60)
    
    # Create a diagram with various issues
    diagram = VisualDiagram(
        nodes=[
            make_node("actor_user", "User", "actor", "business"),
            make_node("svc_api", "API Gateway", "web_app", "service"),
            make_node("svc_orders", "Order Service", "service", "service"),
            make_node("svc_orders", "Order Service DUPLICATE", "service", "service"),  # Duplicate ID!
            make_node("db_orders", "Orders DB", "database", "data"),
            make_node("svc_orphan", "Orphan Service", "service", "service"),  # No connections
            make_node("", "Empty ID Node", "service", "service"),  # Empty label test
        ],
        edges=[
            VisualEdge(source="svc_api", target="svc_orders", relation="calls"),
            VisualEdge(source="svc_api", target="svc_orders", relation="calls"),  # Duplicate edge!
            VisualEdge(source="svc_orders", target="svc_missing", relation="calls"),  # Missing target!
            VisualEdge(source="svc_api", target="svc_api", relation="self"),  # Self-loop!
        ]
    )
    
    print("\n[TEST] Initial diagram state:")
    print(f"  Nodes: {len(diagram.nodes)}")
    print(f"  Edges: {len(diagram.edges)}")
    
    # Validate first
    print("\n[TEST] Initial validation:")
    result = validate_diagram(diagram)
    print(f"  {result.get_summary()}")
    for issue in result.issues:
        print(f"    [{issue.severity.value}] {issue.code}: {issue.message}")
    
    # Now fix (without LLM for testing)
    print("\n[TEST] Applying auto-fix (no LLM):")
    fixed_diagram, fix_result = auto_fix_diagram(diagram, use_llm=False)
    
    print(f"\n[TEST] Fix result:")
    print(f"  Success: {fix_result.success}")
    print(f"  Fix type: {fix_result.fix_type}")
    print(f"  Issues fixed: {fix_result.issues_fixed}")
    print(f"  Issues remaining: {fix_result.issues_remaining}")
    print(f"  Changes made: {fix_result.changes_made}")
    
    # Final validation
    print("\n[TEST] Final validation:")
    final_result = validate_diagram(fixed_diagram)
    print(f"  {final_result.get_summary()}")
    
    print(f"\n[TEST] Final diagram state:")
    print(f"  Nodes: {len(fixed_diagram.nodes)}")
    for n in fixed_diagram.nodes:
        print(f"    - {n.id}: {n.label}")
    print(f"  Edges: {len(fixed_diagram.edges)}")
    for e in fixed_diagram.edges:
        print(f"    - {e.source} -> {e.target} ({e.relation})")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_auto_fixer()
