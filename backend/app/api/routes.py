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
#             "message": str(e),
#         }


from matplotlib.style import context
from fastapi import Response, APIRouter
from app.schemas import GenerateRequest, GenerateResponse
from app.api.serializers import serialize_ir
from app.pipeline.controller import PipelineController
from app.compiler.compiler import compile_diagram

from app.renderer.visual_mermaid_renderer import render_mermaid_from_visual_ir

from app.renderer.svg_renderer import render_svg
from app.renderer.visual_spec_example import get_sample_visual_spec

import json


router = APIRouter()


@router.post("/generate")
def generate_architecture(request: GenerateRequest):
    try:
        controller = PipelineController()

        # ============================
        # 1️⃣ PIPELINE EXECUTION
        # ============================
        context = controller.run(request.requirements)

        # ============================
        # 2️⃣ VISUAL IR VERIFICATION ✅
        # ============================
        if hasattr(context, "visual_ir") and context.visual_ir:
            print("\n===== VISUAL IR OUTPUT =====")
            print(json.dumps(
                context.visual_ir,
                default=lambda o: o.__dict__,
                indent=2
            ))
            print("================================\n")
        else:
            print("\n[WARN] context.visual_ir NOT FOUND\n")

        # ============================
        # 3️⃣ EXISTING IR PAYLOAD
        # ============================
        ir_payload = {
            "business": serialize_ir(context.business_ir),
            "services": serialize_ir(context.service_ir),
            "data": serialize_ir(context.data_ir),
            "infra": serialize_ir(context.infra_ir),
        }

        # ============================
        # 4️⃣ NEW DIAGRAM COMPILATION
        # ============================
        if hasattr(context, "visual_ir") and context.visual_ir:
            diagram_source = render_mermaid_from_visual_ir(context.visual_ir)
            print("\n=====VISUAL IR MERMAID OUTPUT DONE =====")
        else:
            diagram_source = compile_diagram(context)  # fallback


        if context.errors:
            return {
                "status": "warning",
                "warnings": context.errors,
                "mermaid": diagram_source,
                "diagram": {
                    "type": "mermaid",
                    "source": diagram_source,
                },
                "ir": ir_payload,
            }

        return {
            "status": "success",
            "mermaid": diagram_source,   # ✅ FRONTEND COMPATIBILITY
            "diagram": {
                "type": "mermaid",
                "source": diagram_source,
            },
            "ir": ir_payload,
            # (OPTIONAL – comment out if not needed yet)
            # "visual_ir": context.visual_ir,
        }

    except Exception as e:
        return {
            "status": "error",
            "mermaid": "",
            "message": str(e),
        }


@router.get("/debug/svg")
def debug_svg():
    visual_spec = get_sample_visual_spec()
    svg = render_svg(visual_spec)
    return Response(svg, media_type="image/svg+xml")
