from app.pipeline.stage import PipelineStage
from app.pipeline.context import PipelineContext
from app.ir.service_ir import ServiceIR, Service
from app.ir.validation import ValidationResult


class ServiceInferenceStage(PipelineStage):
    """
    Deterministic Service Inference (C4 L2/L3).

    RULES:
    - No LLM usage
    - Text-based semantic inference
    - Always produces services when business exists
    - Stable, repeatable output
    """

    name = "service_inference"

    def run(self, context: PipelineContext) -> ValidationResult:
        # Guard
        if not context.decomposed:
            return ValidationResult.success()

        text = context.requirements_text.lower()

        inferred_services: dict[str, Service] = {}

        # ------------------------------------------------
        #  NORMALIZATION HELPERS
        # ------------------------------------------------
        def has_any(*keywords: str) -> bool:
            return any(k in text for k in keywords)

        # ------------------------------------------------
        #  CORE DOMAIN SERVICES
        # ------------------------------------------------

        if has_any("order", "orders", "order management"):
            inferred_services["order"] = Service(
                name="Order Management Service",
                service_type="logical",
                protocol="internal",
            )

        if has_any("payment", "payments", "pay", "billing"):
            inferred_services["payment"] = Service(
                name="Payment Service",
                service_type="logical",
                protocol="internal",
            )

        if has_any("user", "users", "customer", "customers", "identity"):
            inferred_services["identity"] = Service(
                name="Customer Identity Service",
                service_type="logical",
                protocol="internal",
            )

        # ------------------------------------------------
        #  CHANNEL / EDGE SERVICES
        # ------------------------------------------------

        if has_any("web", "web application", "frontend", "ui"):
            inferred_services["web"] = Service(
                name="Web Application",
                service_type="edge",
                protocol="http",
            )

        if has_any("api", "backend"):
            inferred_services["api"] = Service(
                name="Public API",
                service_type="edge",
                protocol="http",
            )

        # ------------------------------------------------
        #  SAFETY NET (IMPORTANT)
        # ------------------------------------------------
        # If business exists but no services inferred,
        # create a generic application service
        if context.business_ir and not inferred_services:
            inferred_services["app"] = Service(
                name="Application Service",
                service_type="logical",
                protocol="internal",
            )

        # ------------------------------------------------
        #  ASSIGN TO CONTEXT
        # ------------------------------------------------
        context.service_ir = ServiceIR(
            name="Services",
            services=list(inferred_services.values()),
            dependencies=[],
        )

        return ValidationResult.success()
