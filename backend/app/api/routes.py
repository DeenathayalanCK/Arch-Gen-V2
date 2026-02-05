from fastapi import APIRouter
from app.schemas import GenerateRequest, GenerateResponse
from app.api.serializers import serialize_ir
from app.pipeline.controller import PipelineController
from app.compiler.compiler import compile_diagram

router = APIRouter()


@router.post("/generate")
def generate_architecture(request: GenerateRequest):
    try:
        controller = PipelineController()
        context = controller.run(request.requirements)

        ir_payload = {
            "business": serialize_ir(context.business_ir),
            "services": serialize_ir(context.service_ir),
            "data": serialize_ir(context.data_ir),
            "infra": serialize_ir(context.infra_ir),
        }

        diagram_source = compile_diagram(context)

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
        }

    except Exception as e:
        return {
            "status": "error",
            "mermaid": "",
            "message": str(e),
        }