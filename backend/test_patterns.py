"""
Test script for Phase 1 - Pattern Catalog verification
Run with: python test_patterns.py
"""

import sys
sys.path.insert(0, '.')

def main():
    print("\n" + "="*70)
    print("PHASE 1 VERIFICATION: Pattern Catalog and Registry")
    print("="*70)
    
    # Test 1: Import patterns module
    print("\n[Step 1] Importing patterns module...")
    try:
        from app.patterns import (
            Pattern,
            PatternCategory,
            PatternRegistry,
            get_pattern_registry,
            PATTERN_CATALOG,
            test_pattern_catalog,
        )
        print("  ✓ Import successful")
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False
    
    # Test 2: Check catalog contents
    print("\n[Step 2] Checking pattern catalog...")
    print(f"  Total patterns in catalog: {len(PATTERN_CATALOG)}")
    
    categories = {}
    for p in PATTERN_CATALOG:
        cat = p.category.value
        categories[cat] = categories.get(cat, 0) + 1
    
    print("  Patterns by category:")
    for cat, count in categories.items():
        print(f"    - {cat}: {count}")
    
    # Test 3: Get global registry
    print("\n[Step 3] Getting global pattern registry...")
    registry = get_pattern_registry()
    print(f"  Registry has {len(registry.patterns)} patterns")
    
    # Test 4: Test pattern lookup
    print("\n[Step 4] Testing pattern lookup...")
    test_ids = ["caching_layer", "api_gateway", "event_driven", "nonexistent"]
    for pid in test_ids:
        pattern = registry.get(pid)
        if pattern:
            print(f"  ✓ Found '{pid}': {pattern.name}")
        else:
            print(f"  ✗ Not found: '{pid}'")
    
    # Test 5: Test pattern matching
    print("\n[Step 5] Testing pattern matching...")
    test_cases = [
        ("Our app has high traffic and needs caching", ["caching_layer"]),
        ("We need authentication and API security", ["api_gateway"]),
        ("Looking for event-driven async messaging", ["event_driven"]),
        ("Need to handle distributed transactions", ["saga_orchestration"]),
        ("Improve resilience with circuit breakers", ["circuit_breaker"]),
    ]
    
    all_passed = True
    for context, expected in test_cases:
        matches = registry.find_applicable(context, max_results=3)
        match_ids = [m.id for m in matches]
        
        # Check if expected patterns are in results
        found_expected = all(e in match_ids for e in expected)
        
        if found_expected:
            print(f"  ✓ Context: '{context[:40]}...'")
            print(f"      Matched: {match_ids}")
        else:
            print(f"  ✗ Context: '{context[:40]}...'")
            print(f"      Expected: {expected}, Got: {match_ids}")
            all_passed = False
    
    # Test 6: Run catalog self-test
    print("\n[Step 6] Running catalog self-test...")
    test_pattern_catalog()
    
    # Summary
    print("\n" + "="*70)
    if all_passed:
        print("PHASE 1 VERIFICATION: ✓ ALL TESTS PASSED")
    else:
        print("PHASE 1 VERIFICATION: ✗ SOME TESTS FAILED")
    print("="*70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
