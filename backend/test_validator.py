"""Quick test to verify diagram validator is working"""

from app.visual.visual_schema import VisualDiagram, VisualNode, VisualEdge
from app.validation import validate_diagram

# Create a test diagram with some issues
diagram = VisualDiagram(
    nodes=[
        VisualNode(id="actor_user", label="User", node_type="actor", layer="business", shape="ellipse", color="#FFB74D"),
        VisualNode(id="svc_api", label="API Gateway", node_type="web_app", layer="service", shape="rectangle", color="#4CAF50"),
        VisualNode(id="svc_orders", label="Order Service", node_type="service", layer="service", shape="rectangle", color="#4CAF50"),
        VisualNode(id="db_orders", label="Orders DB", node_type="database", layer="data", shape="cylinder", color="#2196F3"),
        VisualNode(id="svc_orphan", label="Orphan Service", node_type="service", layer="service", shape="rectangle", color="#4CAF50"),  # No connections
    ],
    edges=[
        VisualEdge(source="actor_user", target="svc_api", relation="uses"),
        VisualEdge(source="svc_api", target="svc_orders", relation="calls"),
        VisualEdge(source="svc_orders", target="db_orders", relation="reads/writes"),
        VisualEdge(source="svc_orders", target="svc_missing", relation="calls"),  # Missing target node!
    ]
)

print("Testing Diagram Validator...")
print("=" * 50)

result = validate_diagram(diagram)

print(f"\n{result.get_summary()}\n")
print(f"Stats: {result.stats}")
print(f"\nIssues found: {len(result.issues)}")

for issue in result.issues:
    icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity.value, "?")
    print(f"  {icon} [{issue.code}] {issue.message}")
    if issue.suggestion:
        print(f"      💡 {issue.suggestion}")

print("\n" + "=" * 50)
print("✅ Validator test complete!")
