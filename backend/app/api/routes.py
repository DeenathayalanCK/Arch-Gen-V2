# from fastapi import Response
# from fastapi import APIRouter
# from app.schemas import GenerateRequest, GenerateResponse
# from app.api.serializers import serialize_ir
# from app.pipeline.controller import PipelineController
# from app.compiler.compiler import compile_diagram

# router = APIRouter()


# @router.post("/generate")
# def generate_architecture(request: GenerateRequest):
#     try:
#         controller = PipelineController()
#         context = controller.run(request.requirements)

#         ir_payload = {
#             "business": serialize_ir(context.business_ir),
#             "services": serialize_ir(context.service_ir),
#             "data": serialize_ir(context.data_ir),
#             "infra": serialize_ir(context.infra_ir),
#         }

#         diagram_source = compile_diagram(context)

#         if context.errors:
#             return {
#                 "status": "warning",
#                 "warnings": context.errors,   
#                 "mermaid": diagram_source,
#                 "diagram": {
#                     "type": "mermaid",
#                     "source": diagram_source,
#                 },
#                 "ir": ir_payload,
#             }

#         return {
#             "status": "success",
#             "mermaid": diagram_source,   # ✅ FRONTEND COMPATIBILITY
#             "d2": diagram_source,  # ✅ ADD D2
#             "diagram": {
#                 "type": "mermaid",
#                 "source": diagram_source,
#             },
#             "ir": ir_payload,
#         }

#     except Exception as e:
#         return {
#             "status": "error",
#             "mermaid": "",
#             "d2": "",  # ✅ ADD D2
#             "message": str(e),
#         }


from matplotlib.style import context
from fastapi import Response, APIRouter
from fastapi.responses import StreamingResponse
from app.schemas import (
    GenerateRequest, 
    GenerateResponse,
    RefineRequest,
    PatternInjectionRequest,
    ExplainRequest,
)
from app.api.serializers import serialize_ir
from app.pipeline.controller import PipelineController
from app.compiler.compiler import compile_diagram
from app.compiler.render_d2 import render_d2_from_visual_ir, render_d2

from app.renderer.visual_mermaid_renderer import render_mermaid_from_visual_ir

from app.renderer.svg_renderer import render_svg
from app.renderer.visual_spec_example import get_sample_visual_spec

from app.patterns.registry import get_pattern_registry
from app.patterns.injector import PatternInjector, InjectionMapping

from app.llm.client import LLMClient

import json
import asyncio
from typing import AsyncGenerator
from app.patterns import get_pattern_registry

from app.validation import validate_diagram, validate_and_fix_diagram, FixResult

router = APIRouter()


@router.post("/generate")
def generate_architecture(request: GenerateRequest):
    try:
        controller = PipelineController()

        # ============================
        # 1️⃣ PIPELINE EXECUTION (now includes domain stages)
        # ============================
        context = controller.run(
            request.requirements,
            include_system_context=request.include_system_context,
            enable_domain_adapter=getattr(request, 'enable_domain_adapter', True),
            enable_domain_enrichment=getattr(request, 'enable_domain_enrichment', True),
        )

        # ============================
        # 2️⃣ AUTO-INJECT PATTERNS (if requested)
        # ============================
        applied_patterns = getattr(context, 'applied_patterns', []) or []
        if request.patterns and len(request.patterns) > 0:
            print(f"\n===== INJECTING PATTERNS: {request.patterns} =====")
            registry = get_pattern_registry()
            injector = PatternInjector()
            
            for pattern_id in request.patterns:
                pattern = registry.get(pattern_id)
                if pattern:
                    print(f"  Found pattern: {pattern.name}")
                    if context.visual_ir:
                        # Auto-suggest mappings
                        suggestions = injector.suggest_mappings(context.visual_ir, pattern)
                        print(f"  Suggestions: {suggestions}")
                        # Use first candidate for each variable
                        mappings = []
                        for var, candidates in suggestions:
                            if candidates:
                                mappings.append(InjectionMapping(var, candidates[0]))
                        
                        if mappings:
                            injector.inject(context.visual_ir, pattern, mappings)
                            applied_patterns.append(pattern_id)
                            print(f"  ✅ Injected pattern: {pattern_id}")
                        else:
                            # Inject without mappings if no suggestions
                            injector.inject(context.visual_ir, pattern, [])
                            applied_patterns.append(pattern_id)
                            print(f"  ✅ Injected pattern (no mappings): {pattern_id}")
                    else:
                        print(f"  ⚠️ No visual_ir available for injection")
                else:
                    print(f"  ⚠️ Pattern not found: {pattern_id}")
            
            context.applied_patterns = applied_patterns

        # ============================
        # 3️⃣ VISUAL IR VERIFICATION ✅
        # ============================
        if hasattr(context, "visual_ir") and context.visual_ir:
            print("\n===== VISUAL IR OUTPUT (BEFORE FIX) =====")
            print(f"Nodes: {len(context.visual_ir.nodes)}")
            print(f"Edges: {len(context.visual_ir.edges)}")
            print("================================\n")
        else:
            print("\n[WARN] context.visual_ir NOT FOUND\n")

        # ============================
        # 4️⃣ EXISTING IR PAYLOAD
        # ============================
        ir_payload = {
            "business": serialize_ir(context.business_ir),
            "services": serialize_ir(context.service_ir),
            "data": serialize_ir(context.data_ir),
            "infra": serialize_ir(context.infra_ir),
        }

        # ============================
        # 5️⃣ VALIDATE AND AUTO-FIX
        # ============================
        validation_result = None
        fix_result = None
        
        if hasattr(context, "visual_ir") and context.visual_ir:
            from app.validation import validate_diagram, validate_and_fix_diagram
            
            # Initial validation
            initial_validation = validate_diagram(context.visual_ir)
            
            print("\n===== INITIAL DIAGRAM VALIDATION =====")
            print(initial_validation.get_summary())
            for issue in initial_validation.issues:
                print(f"  - [{issue.code}] {issue.message}")
            print("================================\n")
            
            # ============================================================
            # AUTO-FIX SECTION - Uncomment to enable auto-fixing
            # ============================================================
            if not initial_validation.is_valid or not initial_validation.is_complete:
                print("\n[AUTO-FIX] Diagram has issues, attempting auto-fix...")
                
                # Capture before state
                nodes_before = len(context.visual_ir.nodes)
                edges_before = len(context.visual_ir.edges)
                
                # Use hybrid fixer (auto + LLM)
                fixed_diagram, final_validation, fix_result = validate_and_fix_diagram(
                    context.visual_ir,
                    use_llm=True,
                )
                
                # CRITICAL: Always replace with fixed diagram
                if fixed_diagram is not None:
                    context.visual_ir = fixed_diagram
                    validation_result = final_validation
                    
                    # Log what changed
                    nodes_after = len(context.visual_ir.nodes)
                    edges_after = len(context.visual_ir.edges)
                    print(f"\n[AUTO-FIX] Nodes: {nodes_before} -> {nodes_after}")
                    print(f"[AUTO-FIX] Edges: {edges_before} -> {edges_after}")
                    print(f"[AUTO-FIX] Fix result: {fix_result.to_dict() if fix_result else 'None'}")
                else:
                    print("[AUTO-FIX] WARNING: fixed_diagram is None, using original")
                    validation_result = initial_validation
            else:
                validation_result = initial_validation
                print("[AUTO-FIX] Diagram is valid, no fix needed")
            
            print(f"\n===== FINAL VALIDATION =====")
            print(validation_result.get_summary())
            print("================================\n")
            # ============================================================
            # END AUTO-FIX SECTION
            # ============================================================
            
            # When auto-fix is disabled, use initial validation
            # validation_result = initial_validation

        # ============================
        # 6️⃣ DIAGRAM COMPILATION - AFTER FIXING
        # ============================
        mermaid_source = ""
        d2_source = ""
        
        if hasattr(context, "visual_ir") and context.visual_ir:
            # Debug: Log the FINAL visual IR being rendered
            print("\n===== RENDERING VISUAL IR (FINAL) =====")
            print(f"Nodes: {len(context.visual_ir.nodes)}")
            for n in context.visual_ir.nodes:
                print(f"  - {n.id}: {n.label} (layer={n.layer}, type={n.node_type})")
            print(f"Edges: {len(context.visual_ir.edges)}")
            for e in context.visual_ir.edges:
                print(f"  - {e.source} -> {e.target}")
            print("==========================================\n")
            
            # Generate BOTH formats from the (potentially fixed) visual IR
            mermaid_source = render_mermaid_from_visual_ir(context.visual_ir)
            d2_source = render_d2_from_visual_ir(context.visual_ir)
        else:
            # Fallback to old compiler
            mermaid_source = compile_diagram(context)
            # Also generate D2 from the graph
            from app.compiler.merge import merge_context
            from app.compiler.layout import apply_layout
            graph = merge_context(context)
            graph = apply_layout(graph)
            d2_source = render_d2(graph)

        # ============================
        # 7️⃣ SUGGEST PATTERNS
        # ============================
        registry = get_pattern_registry()
        suggested = registry.suggest_patterns(request.requirements)
        suggested_ids = [p.id for p in suggested[:5]]  # Top 5

        # ============================
        # 8️⃣ SYSTEM CONTEXT (C4 L1)
        # ============================
        system_context_payload = None
        if request.include_system_context and hasattr(context, 'system_context_ir') and context.system_context_ir:
            system_context_payload = serialize_ir(context.system_context_ir)

        # ============================
        # 9️⃣ DOMAIN CONTEXT PAYLOAD
        # ============================
        domain_payload = None
        if hasattr(context, 'domain_context') and context.domain_context is not None:
            try:
                domain_payload = context.domain_context.to_dict()
                print(f"[Routes] Domain context serialized: {domain_payload.get('domain', 'unknown')}")
            except Exception as e:
                print(f"[Routes] Warning: Could not serialize domain_context: {e}")
                domain_payload = {"error": str(e)}
        
        enrichment_payload = None
        if hasattr(context, 'enrichment_result') and context.enrichment_result is not None:
            try:
                enrichment_payload = context.enrichment_result.to_dict()
            except Exception as e:
                print(f"[Routes] Warning: Could not serialize enrichment_result: {e}")
                enrichment_payload = {"error": str(e)}
        
        domain_validation_payload = None
        if hasattr(context, 'domain_validation') and context.domain_validation is not None:
            try:
                domain_validation_payload = context.domain_validation.to_dict()
            except Exception as e:
                print(f"[Routes] Warning: Could not serialize domain_validation: {e}")
                domain_validation_payload = {"error": str(e)}

        # ============================
        # 🔟 BUILD RESPONSE
        # ============================
        # Get errors safely
        errors_list = getattr(context, 'errors', []) or []
        
        response = {
            "status": "success" if not errors_list else "warning",
            "mermaid": mermaid_source,
            "d2": d2_source,
            "diagram": {"type": "mermaid", "source": mermaid_source},
            "ir": ir_payload,
            "system_context": system_context_payload,
            "suggested_patterns": suggested_ids,
            "applied_patterns": applied_patterns,
            "validation": validation_result.to_dict() if validation_result else None,
            "auto_fix": fix_result.to_dict() if fix_result else {"fix_type": "none", "success": True, "changes_made": []},
            # Domain-aware fields
            "domain": domain_payload,
            "domain_enrichment": enrichment_payload,
            "domain_validation": domain_validation_payload,
        }
        
        if errors_list:
            response["warnings"] = errors_list
        
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "mermaid": "",
            "d2": "",
            "message": str(e),
        }


@router.get("/debug/svg")
def debug_svg():
    visual_spec = get_sample_visual_spec()
    svg = render_svg(visual_spec)
    return Response(svg, media_type="image/svg+xml")


# ============================================================
# REFINE ENDPOINT - Iterative Architecture Refinement
# ============================================================

@router.post("/refine")
def refine_architecture(request: RefineRequest):
    """
    Refine an existing architecture based on user feedback.
    
    Examples:
    - "Add caching to the order service"
    - "Split this into microservices"
    - "Add security layer with API gateway"
    """
    try:
        # Build refinement prompt
        refinement_prompt = f"""You are an expert software architect. 
The user has an existing architecture based on these requirements:

ORIGINAL REQUIREMENTS:
{request.requirements}

The user wants to make this change:
"{request.refinement}"

Generate the UPDATED architectural requirements that incorporate this change.
Return ONLY the updated requirements text, nothing else.
"""
        
        # Generate refined requirements
        llm = LLMClient()
        refined_requirements = llm.generate(refinement_prompt)
        
        # Re-run pipeline with refined requirements
        controller = PipelineController()
        context = controller.run(refined_requirements.strip())
        
        # Compile diagram
        if hasattr(context, "visual_ir") and context.visual_ir:
            diagram_source = render_mermaid_from_visual_ir(context.visual_ir)
        else:
            diagram_source = compile_diagram(context)
        
        ir_payload = {
            "business": serialize_ir(context.business_ir),
            "services": serialize_ir(context.service_ir),
            "data": serialize_ir(context.data_ir),
            "infra": serialize_ir(context.infra_ir),
        }
        
        return {
            "status": "success",
            "refinement_applied": request.refinement,
            "updated_requirements": refined_requirements.strip(),
            "mermaid": diagram_source,
            "diagram": {
                "type": "mermaid",
                "source": diagram_source,
            },
            "ir": ir_payload,
            "changes": f"Applied: {request.refinement}",
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


# ============================================================
# STREAMING ENDPOINT - Real-time Generation Progress
# ============================================================

@router.post("/generate/stream")
async def generate_stream(request: GenerateRequest):
    """
    Stream generation progress as Server-Sent Events (SSE).
    
    Yields events for each pipeline stage completion.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Stage 1: Decomposition
            yield f"data: {json.dumps({'stage': 'decomposition', 'status': 'starting', 'progress': 10})}\n\n"
            
            controller = PipelineController()
            context = controller.run(request.requirements)
            
            # Stage progress events
            yield f"data: {json.dumps({'stage': 'business', 'status': 'complete', 'progress': 25})}\n\n"
            await asyncio.sleep(0.1)  # Allow client to receive event
            
            yield f"data: {json.dumps({'stage': 'service', 'status': 'complete', 'progress': 45})}\n\n"
            await asyncio.sleep(0.1)
            
            yield f"data: {json.dumps({'stage': 'data', 'status': 'complete', 'progress': 65})}\n\n"
            await asyncio.sleep(0.1)
            
            yield f"data: {json.dumps({'stage': 'infra', 'status': 'complete', 'progress': 80})}\n\n"
            await asyncio.sleep(0.1)
            
            # Compile diagram
            yield f"data: {json.dumps({'stage': 'rendering', 'status': 'starting', 'progress': 90})}\n\n"
            
            if hasattr(context, "visual_ir") and context.visual_ir:
                if request.output_format == "d2":
                    diagram_source = render_d2_from_visual_ir(context.visual_ir)
                    diagram_type = "d2"
                else:
                    diagram_source = render_mermaid_from_visual_ir(context.visual_ir)
                    diagram_type = "mermaid"
            else:
                diagram_source = compile_diagram(context)
                diagram_type = "mermaid"
            
            ir_payload = {
                "business": serialize_ir(context.business_ir),
                "services": serialize_ir(context.service_ir),
                "data": serialize_ir(context.data_ir),
                "infra": serialize_ir(context.infra_ir),
            }
            
            # Final result
            final_result = {
                "stage": "complete",
                "status": "success",
                "progress": 100,
                "result": {
                    "mermaid": diagram_source,
                    "diagram": {"type": diagram_type, "source": diagram_source},
                    "ir": ir_payload,
                }
            }
            yield f"data: {json.dumps(final_result)}\n\n"
            
        except Exception as e:
            error_event = {"stage": "error", "status": "failed", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================
# PATTERN ENDPOINTS - Pattern Library & Injection
# ============================================================

@router.get("/patterns")
def list_patterns():
    """List all available architecture patterns"""
    registry = get_pattern_registry()
    return registry.get_pattern_summary()


@router.get("/patterns/{pattern_id}")
def get_pattern(pattern_id: str):
    """Get details of a specific pattern"""
    registry = get_pattern_registry()
    pattern = registry.get(pattern_id)
    
    if not pattern:
        return {"error": f"Pattern '{pattern_id}' not found"}
    
    # Defensive: handle patterns that may not have trade_offs (e.g., SimpleNamespace)
    trade_offs = getattr(pattern, "trade_offs", None)
    if trade_offs is None:
        trade_offs = {}

    return {
        "id": pattern.id,
        "name": pattern.name,
        "description": pattern.description,
        "category": getattr(pattern.category, "value", str(getattr(pattern, "category", ""))),
        "components": [
            {"id": c.id, "name": c.name, "type": getattr(c, "node_type", ""), "description": getattr(c, "description", "")}
            for c in getattr(pattern, "components", [])
        ],
        "connections": [
            {"from": c.from_id, "to": c.to_id, "relationship": getattr(c, "relationship", "")}
            for c in getattr(pattern, "connections", [])
        ],
        "tags": getattr(pattern, "tags", []),
        "applicable_when": getattr(pattern, "applicable_when", []),
        "trade_offs": trade_offs,
    }


@router.post("/patterns/suggest")
def suggest_patterns(request: GenerateRequest):
    """Suggest applicable patterns based on requirements"""
    registry = get_pattern_registry()
    suggestions = registry.suggest_patterns(request.requirements)
    
    return {
        "requirements_excerpt": request.requirements[:200] + "..." if len(request.requirements) > 200 else request.requirements,
        "suggestions": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "category": p.category.value,
                "tags": p.tags,
            }
            for p in suggestions[:10]
        ]
    }


@router.post("/patterns/inject")
def inject_pattern(request: PatternInjectionRequest):
    """Inject a pattern into an existing architecture"""
    registry = get_pattern_registry()
    pattern = registry.get(request.pattern_id)
    
    if not pattern:
        return {"error": f"Pattern '{request.pattern_id}' not found"}
    
    # Would need current visual_ir from session/storage
    # For now, return pattern application preview
    return {
        "status": "preview",
        "pattern": pattern.name,
        "components_to_add": [c.name for c in pattern.components],
        "connections_to_add": len(pattern.connections),
        "mappings_provided": request.mappings,
        "note": "Full injection requires current diagram state. Use /generate with patterns parameter.",
    }


# ============================================================
# EXPLAIN ENDPOINT - Architectural Decisions
# ============================================================

@router.post("/explain")
def explain_decision(request: ExplainRequest):
    """
    Explain architectural decisions or answer questions about the design.
    
    Example questions:
    - "Why did you choose PostgreSQL over MongoDB?"
    - "What are the trade-offs of this design?"
    - "How would this scale to 10x traffic?"
    """
    try:
        explain_prompt = f"""You are an expert software architect. 
The user has a question about an architectural design.

QUESTION: {request.question}

{"CONTEXT: " + json.dumps(request.context, indent=2) if request.context else ""}

Provide a clear, concise explanation addressing:
1. The reasoning behind the decision
2. Alternatives that were considered (if applicable)
3. Trade-offs involved
4. Recommendations for improvement (if any)

Keep the response focused and practical.
"""
        
        llm = LLMClient()
        explanation = llm.generate(explain_prompt)
        
        return {
            "status": "success",
            "question": request.question,
            "explanation": explanation.strip(),
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


# ============================================================
# VALIDATION ENDPOINT - With Auto-Fix Option
# ============================================================

@router.post("/validate")
def validate_generated_diagram(request: GenerateRequest):
    """
    Generate and validate a diagram, with optional auto-fix.
    """
    try:
        controller = PipelineController()
        context = controller.run(
            request.requirements,
            include_system_context=request.include_system_context,
        )
        
        if not hasattr(context, "visual_ir") or not context.visual_ir:
            return {
                "status": "error",
                "message": "No visual IR generated",
                "validation": None,
            }
        
        # Validate and optionally fix
        fixed_diagram, validation_result, fix_result = validate_and_fix_diagram(
            context.visual_ir,
            use_llm=True,
        )
        
        errors = [i.to_dict() for i in validation_result.issues if i.severity.value == "error"]
        warnings = [i.to_dict() for i in validation_result.issues if i.severity.value == "warning"]
        info = [i.to_dict() for i in validation_result.issues if i.severity.value == "info"]
        
        return {
            "status": "success" if validation_result.is_valid else "invalid",
            "summary": validation_result.get_summary(),
            "is_valid": validation_result.is_valid,
            "is_complete": validation_result.is_complete,
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "stats": validation_result.stats,
            "auto_fix": fix_result.to_dict() if fix_result else None,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

