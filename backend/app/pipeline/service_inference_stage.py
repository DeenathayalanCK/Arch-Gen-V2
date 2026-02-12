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
        #  CORE DOMAIN SERVICES (KEYWORD BASED)
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
        #  DOMAIN BASELINE INJECTION (CONFIG-DRIVEN)
        # ------------------------------------------------

        domain_context = getattr(context, "domain_context", None)

        if domain_context and domain_context.domain_rules:
            baseline_services = domain_context.domain_rules.get("baseline_services", [])

            for svc in baseline_services:
                svc_id = svc.get("id")
                if not svc_id:
                    continue

                inferred_services.setdefault(
                    svc_id,
                    Service(
                        name=svc.get("name", svc_id.replace("_", " ").title()),
                        service_type=svc.get("type", "logical"),
                        protocol=svc.get("protocol", "internal"),
                    )
                )


        # ------------------------------------------------
        #  SAFETY NET
        # ------------------------------------------------

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

