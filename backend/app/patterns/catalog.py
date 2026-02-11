# backend/app/patterns/catalog.py
"""
Pattern Catalog - Pre-built architecture patterns

Contains common architectural patterns ready for injection.
"""

from app.patterns.registry import (
    Pattern,
    PatternCategory,
    PatternComponent,
    PatternConnection,
    PatternRegistry,
)


# ============================================================
# SCALABILITY PATTERNS
# ============================================================

CACHING_PATTERN = Pattern(
    id="caching_layer",
    name="Distributed Caching Layer",
    description="Add a distributed cache (Redis/Memcached) between services and databases to reduce latency and database load.",
    category=PatternCategory.SCALABILITY,
    components=[
        PatternComponent(
            id="cache_primary",
            name="Redis Cache",
            node_type="cache",
            description="Primary distributed cache for frequently accessed data",
            config={"technology": "redis", "cluster_mode": True},
        ),
    ],
    connections=[
        PatternConnection(
            from_id="{{service}}",
            to_id="cache_primary",
            relationship="reads/writes",
            protocol="Redis Protocol",
        ),
        PatternConnection(
            from_id="cache_primary",
            to_id="{{database}}",
            relationship="cache miss -> fetch",
        ),
    ],
    injection_points=["service", "database"],
    tags=["performance", "caching", "redis", "scalability"],
    applicable_when=["high traffic", "read heavy", "cache", "performance", "latency"],
    trade_offs={
        "pros": "Reduced database load, faster response times, handles traffic spikes",
        "cons": "Cache invalidation complexity, additional infrastructure, eventual consistency",
    },
    variables={"cache_ttl": "3600", "cache_size": "1GB"},
)


LOAD_BALANCER_PATTERN = Pattern(
    id="load_balancer",
    name="Load Balancer with Health Checks",
    description="Add a load balancer in front of services for horizontal scaling and high availability.",
    category=PatternCategory.SCALABILITY,
    components=[
        PatternComponent(
            id="lb_primary",
            name="Load Balancer",
            node_type="gateway",
            description="L7 load balancer with health checking",
            config={"algorithm": "round_robin", "health_check": True},
        ),
    ],
    connections=[
        PatternConnection(
            from_id="{{client}}",
            to_id="lb_primary",
            relationship="routes to",
            protocol="HTTPS",
        ),
        PatternConnection(
            from_id="lb_primary",
            to_id="{{service}}",
            relationship="distributes load",
            protocol="HTTP",
        ),
    ],
    injection_points=["client", "service"],
    tags=["scaling", "load-balancing", "high-availability", "ha"],
    applicable_when=["scale", "multiple instances", "high availability", "load balance", "traffic"],
    trade_offs={
        "pros": "Horizontal scaling, fault tolerance, zero-downtime deployments",
        "cons": "Session affinity complexity, additional latency, cost",
    },
)


# ============================================================
# MESSAGING PATTERNS
# ============================================================

EVENT_DRIVEN_PATTERN = Pattern(
    id="event_driven",
    name="Event-Driven Architecture",
    description="Decouple services using an event bus/message broker for async communication.",
    category=PatternCategory.MESSAGING,
    components=[
        PatternComponent(
            id="event_bus",
            name="Message Broker",
            node_type="queue",
            description="Central event bus for async messaging",
            config={"technology": "kafka", "partitions": 6},
        ),
    ],
    connections=[
        PatternConnection(
            from_id="{{producer}}",
            to_id="event_bus",
            relationship="publishes events",
            protocol="Kafka Protocol",
        ),
        PatternConnection(
            from_id="event_bus",
            to_id="{{consumer}}",
            relationship="delivers events",
            protocol="Kafka Protocol",
        ),
    ],
    injection_points=["producer", "consumer"],
    tags=["event-driven", "async", "kafka", "messaging", "decoupling"],
    applicable_when=["event", "async", "decouple", "message", "queue", "pub/sub", "real-time"],
    trade_offs={
        "pros": "Loose coupling, scalability, resilience, event sourcing support",
        "cons": "Eventual consistency, debugging complexity, message ordering challenges",
    },
    variables={"retention_days": "7", "replication_factor": "3"},
)


SAGA_PATTERN = Pattern(
    id="saga_orchestration",
    name="Saga Pattern (Orchestration)",
    description="Manage distributed transactions across microservices using a saga orchestrator.",
    category=PatternCategory.MESSAGING,
    components=[
        PatternComponent(
            id="saga_orchestrator",
            name="Saga Orchestrator",
            node_type="service",
            description="Coordinates multi-step transactions with compensation",
            config={"retry_policy": "exponential_backoff"},
        ),
        PatternComponent(
            id="saga_state_store",
            name="Saga State Store",
            node_type="database",
            description="Persists saga state for recovery",
        ),
    ],
    connections=[
        PatternConnection(
            from_id="saga_orchestrator",
            to_id="{{step_service}}",
            relationship="orchestrates step",
        ),
        PatternConnection(
            from_id="saga_orchestrator",
            to_id="saga_state_store",
            relationship="persists state",
        ),
    ],
    injection_points=["step_service"],
    tags=["saga", "transactions", "distributed", "compensation", "orchestration"],
    applicable_when=["transaction", "saga", "distributed", "compensation", "rollback", "multi-step"],
    trade_offs={
        "pros": "Maintains consistency across services, supports compensation/rollback",
        "cons": "Added complexity, orchestrator becomes critical path, debugging difficulty",
    },
)


# ============================================================
# SECURITY PATTERNS
# ============================================================

API_GATEWAY_PATTERN = Pattern(
    id="api_gateway",
    name="API Gateway with Auth",
    description="Centralized API gateway handling authentication, rate limiting, and routing.",
    category=PatternCategory.SECURITY,
    components=[
        PatternComponent(
            id="api_gateway",
            name="API Gateway",
            node_type="gateway",
            description="Entry point with auth, rate limiting, routing",
            config={"auth": "jwt", "rate_limit": "1000/min"},
        ),
        PatternComponent(
            id="identity_provider",
            name="Identity Provider",
            node_type="external",
            description="OAuth2/OIDC identity provider",
        ),
    ],
    connections=[
        PatternConnection(
            from_id="{{client}}",
            to_id="api_gateway",
            relationship="authenticates via",
            protocol="HTTPS",
        ),
        PatternConnection(
            from_id="api_gateway",
            to_id="identity_provider",
            relationship="validates tokens",
            protocol="OIDC",
        ),
        PatternConnection(
            from_id="api_gateway",
            to_id="{{service}}",
            relationship="routes to",
            protocol="HTTP",
        ),
    ],
    injection_points=["client", "service"],
    tags=["security", "api-gateway", "authentication", "authorization", "rate-limiting"],
    applicable_when=["security", "authentication", "auth", "api gateway", "rate limit", "jwt", "oauth"],
    trade_offs={
        "pros": "Centralized security, single entry point, cross-cutting concerns",
        "cons": "Single point of failure, gateway becomes bottleneck, added latency",
    },
)


SERVICE_MESH_PATTERN = Pattern(
    id="service_mesh",
    name="Service Mesh (Istio/Linkerd)",
    description="Add a service mesh for mTLS, observability, and traffic management between services.",
    category=PatternCategory.SECURITY,
    components=[
        PatternComponent(
            id="mesh_control_plane",
            name="Mesh Control Plane",
            node_type="infrastructure",
            description="Service mesh control plane (Istio/Linkerd)",
        ),
        PatternComponent(
            id="sidecar_proxy",
            name="Sidecar Proxy",
            node_type="infrastructure",
            description="Envoy sidecar for each service",
        ),
    ],
    connections=[
        PatternConnection(
            from_id="mesh_control_plane",
            to_id="sidecar_proxy",
            relationship="configures",
        ),
        PatternConnection(
            from_id="sidecar_proxy",
            to_id="{{service}}",
            relationship="intercepts traffic",
        ),
    ],
    injection_points=["service"],
    tags=["service-mesh", "mtls", "observability", "istio", "security", "zero-trust"],
    applicable_when=["service mesh", "mtls", "zero trust", "observability", "traffic management"],
    trade_offs={
        "pros": "Automatic mTLS, observability, traffic control, retries",
        "cons": "Operational complexity, resource overhead, learning curve",
    },
)


# ============================================================
# RESILIENCE PATTERNS
# ============================================================

CIRCUIT_BREAKER_PATTERN = Pattern(
    id="circuit_breaker",
    name="Circuit Breaker Pattern",
    description="Prevent cascade failures by wrapping external calls with circuit breakers.",
    category=PatternCategory.RESILIENCE,
    components=[
        PatternComponent(
            id="circuit_breaker",
            name="Circuit Breaker",
            node_type="infrastructure",
            description="Monitors failures and opens circuit when threshold exceeded",
            config={"failure_threshold": 5, "timeout": 30, "half_open_requests": 3},
        ),
    ],
    connections=[
        PatternConnection(
            from_id="{{caller}}",
            to_id="circuit_breaker",
            relationship="wraps calls",
        ),
        PatternConnection(
            from_id="circuit_breaker",
            to_id="{{callee}}",
            relationship="protected call",
        ),
    ],
    injection_points=["caller", "callee"],
    tags=["resilience", "circuit-breaker", "fault-tolerance", "reliability"],
    applicable_when=["resilience", "circuit breaker", "fault tolerance", "failure", "retry", "fallback"],
    trade_offs={
        "pros": "Prevents cascade failures, fail-fast behavior, auto-recovery",
        "cons": "Complexity in tuning thresholds, fallback logic needed",
    },
)


BULKHEAD_PATTERN = Pattern(
    id="bulkhead_isolation",
    name="Bulkhead Isolation",
    description="Isolate components to prevent failures in one area from affecting others.",
    category=PatternCategory.RESILIENCE,
    components=[
        PatternComponent(
            id="bulkhead",
            name="Bulkhead",
            node_type="infrastructure",
            description="Resource isolation boundary",
            config={"max_concurrent": 10, "max_wait": 100},
        ),
    ],
    connections=[
        PatternConnection(
            from_id="{{service}}",
            to_id="bulkhead",
            relationship="isolated by",
        ),
    ],
    injection_points=["service"],
    tags=["resilience", "bulkhead", "isolation", "fault-tolerance"],
    applicable_when=["bulkhead", "isolation", "resource pool", "thread pool"],
    trade_offs={
        "pros": "Fault isolation, prevents resource exhaustion, predictable behavior",
        "cons": "Reduced overall utilization, configuration complexity",
    },
)


# ============================================================
# DATA PATTERNS
# ============================================================

CQRS_PATTERN = Pattern(
    id="cqrs",
    name="CQRS (Command Query Responsibility Segregation)",
    description="Separate read and write models for optimized query and command handling.",
    category=PatternCategory.DATA,
    components=[
        PatternComponent(
            id="command_service",
            name="Command Service",
            node_type="service",
            description="Handles write operations",
        ),
        PatternComponent(
            id="query_service",
            name="Query Service",
            node_type="service",
            description="Handles read operations with optimized models",
        ),
        PatternComponent(
            id="write_db",
            name="Write Database",
            node_type="database",
            description="Normalized for writes",
        ),
        PatternComponent(
            id="read_db",
            name="Read Database",
            node_type="database",
            description="Denormalized for fast reads",
        ),
        PatternComponent(
            id="sync_mechanism",
            name="Sync Mechanism",
            node_type="queue",
            description="Syncs read model from write events",
        ),
    ],
    connections=[
        PatternConnection(from_id="command_service", to_id="write_db", relationship="writes"),
        PatternConnection(from_id="write_db", to_id="sync_mechanism", relationship="publishes changes"),
        PatternConnection(from_id="sync_mechanism", to_id="read_db", relationship="updates"),
        PatternConnection(from_id="query_service", to_id="read_db", relationship="reads"),
    ],
    injection_points=["command_service", "query_service"],
    tags=["cqrs", "read-write-separation", "event-sourcing", "performance"],
    applicable_when=["cqrs", "read write separation", "event sourcing", "reporting", "analytics"],
    trade_offs={
        "pros": "Optimized reads/writes, scalability, flexibility",
        "cons": "Eventual consistency, complexity, data synchronization",
    },
)


# ============================================================
# DEPLOYMENT PATTERNS
# ============================================================

BLUE_GREEN_PATTERN = Pattern(
    id="blue_green_deployment",
    name="Blue-Green Deployment",
    description="Zero-downtime deployments with two identical production environments.",
    category=PatternCategory.DEPLOYMENT,
    components=[
        PatternComponent(
            id="blue_env",
            name="Blue Environment",
            node_type="infrastructure",
            description="Current production environment",
        ),
        PatternComponent(
            id="green_env",
            name="Green Environment",
            node_type="infrastructure",
            description="New version environment",
        ),
        PatternComponent(
            id="traffic_router",
            name="Traffic Router",
            node_type="gateway",
            description="Routes traffic between blue/green",
        ),
    ],
    connections=[
        PatternConnection(from_id="traffic_router", to_id="blue_env", relationship="routes 100%"),
        PatternConnection(from_id="traffic_router", to_id="green_env", relationship="routes 0% (standby)"),
    ],
    injection_points=["traffic_router", "blue_env", "green_env"],
    tags=["deployment", "blue-green", "zero-downtime", "release"],
    applicable_when=["blue green", "zero downtime", "deployment", "release strategy"],
    trade_offs={
        "pros": "Instant rollback, zero downtime, easy validation",
        "cons": "Double infrastructure cost during deployment, database migration complexity",
    },
)


# ============================================================
# CATALOG AGGREGATION
# ============================================================

PATTERN_CATALOG = [
    # Scalability
    CACHING_PATTERN,
    LOAD_BALANCER_PATTERN,
    # Messaging
    EVENT_DRIVEN_PATTERN,
    SAGA_PATTERN,
    # Security
    API_GATEWAY_PATTERN,
    SERVICE_MESH_PATTERN,
    # Resilience
    CIRCUIT_BREAKER_PATTERN,
    BULKHEAD_PATTERN,
    # Data
    CQRS_PATTERN,
    # Deployment
    BLUE_GREEN_PATTERN,
]


def register_all_patterns(registry: PatternRegistry) -> None:
    """Register all patterns from the catalog"""
    print(f"[PATTERN DEBUG] Registering {len(PATTERN_CATALOG)} patterns...")
    for pattern in PATTERN_CATALOG:
        registry.register(pattern)
        print(f"[PATTERN DEBUG] Registered pattern: {pattern.id} - {pattern.name}")
    print(f"[PATTERN DEBUG] Total patterns registered: {len(registry.patterns)}")


def test_pattern_catalog():
    """Test function to verify pattern catalog is working"""
    print("\n" + "="*60)
    print("PATTERN CATALOG TEST")
    print("="*60)
    
    # Test 1: Check all patterns are defined
    print(f"\n[TEST 1] Pattern count: {len(PATTERN_CATALOG)}")
    for p in PATTERN_CATALOG:
        print(f"  - {p.id}: {p.name} ({p.category.value})")
    
    # Test 2: Create registry and register patterns
    print(f"\n[TEST 2] Testing PatternRegistry...")
    test_registry = PatternRegistry()
    register_all_patterns(test_registry)
    
    # Test 3: Test pattern matching
    print(f"\n[TEST 3] Testing pattern matching...")
    test_contexts = [
        "high traffic web application",
        "need authentication and security",
        "event driven microservices",
        "distributed transactions",
        "improve performance with caching",
    ]
    
    for ctx in test_contexts:
        matches = test_registry.find_applicable(ctx)
        print(f"  Context: '{ctx}'")
        print(f"    Matches: {[m.id for m in matches]}")
    
    print("\n" + "="*60)
    print("PATTERN CATALOG TEST COMPLETE")
    print("="*60 + "\n")
    
    return True


# Uncomment to run test when module is loaded
# test_pattern_catalog()
