# backend/app/pipeline/service_dependency_stage.py

from app.pipeline.stage import PipelineStage
from app.ir.validation import ValidationResult
from app.ir.service_ir import ServiceDependency
from app.pipeline.context import PipelineContext


class ServiceDependencyStage(PipelineStage):
    """
    Deterministic Service → Service dependency inference.

    Rules:
    1. Edge services depend on logical services
    2. Shared datastore access implies dependency
    3. Responsibility semantics imply dependency
    4. Domain-specific mandatory dependencies

    """

    name = "service_dependency"

    def run(self, context: PipelineContext) -> ValidationResult:
        if not context.service_ir:
            return ValidationResult.success()

        services = context.service_ir.services
        data_ir = context.data_ir
        responsibility_map = context.responsibility_map

        dependencies: list[ServiceDependency] = []
        seen: set[tuple[str, str]] = set()

        # --------------------------------------------------
        # Helper maps
        # --------------------------------------------------

        service_by_name = {svc.name.lower(): svc for svc in services}
        service_by_id = {svc.id: svc for svc in services}

        logical_services = [
            svc for svc in services if svc.service_type == "logical"
        ]

        edge_services = [
            svc for svc in services
            if svc.service_type == "edge"
            or svc.protocol in ("http", "https", "grpc")
        ]

        # --------------------------------------------------
        # Rule 1: Edge → Logical
        # --------------------------------------------------

        for edge in edge_services:
            for logical in logical_services:
                if edge.id == logical.id:
                    continue

                key = (edge.id, logical.id)
                if key in seen:
                    continue

                dependencies.append(
                    ServiceDependency(
                        from_service_id=edge.id,
                        to_service_id=logical.id,
                        interaction="calls",
                    )
                )
                seen.add(key)

        # --------------------------------------------------
        # Rule 2: Shared datastore access
        # --------------------------------------------------

        if data_ir:
            datastore_writers: dict[str, set[str]] = {}
            datastore_readers: dict[str, set[str]] = {}

            for access in data_ir.access_patterns:
                svc_name = access.service_id
                datastore_id = access.datastore_id

                if svc_name not in service_by_name:
                    continue

                svc_id = service_by_name[svc_name].id

                if access.access_type in ("write", "read_write"):
                    datastore_writers.setdefault(datastore_id, set()).add(svc_id)

                if access.access_type in ("read", "read_write"):
                    datastore_readers.setdefault(datastore_id, set()).add(svc_id)

            for datastore_id in datastore_writers:
                writers = datastore_writers.get(datastore_id, set())
                readers = datastore_readers.get(datastore_id, set())

                for reader in readers:
                    for writer in writers:
                        if reader == writer:
                            continue

                        key = (reader, writer)
                        if key in seen:
                            continue

                        dependencies.append(
                            ServiceDependency(
                                from_service_id=reader,
                                to_service_id=writer,
                                interaction="uses data from",
                            )
                        )
                        seen.add(key)

        # --------------------------------------------------
        # Rule 3: Responsibility semantics
        # --------------------------------------------------

        KEYWORDS = {
            "identity": "Customer Identity Service",
            "auth": "Customer Identity Service",
            "user": "Customer Identity Service",
            "payment": "Payment Service",
            "order": "Order Management Service",
        }

        for svc_id, bundle in responsibility_map.items():
            src_service = service_by_id.get(svc_id)
            if not src_service:
                continue

            for resp in bundle.responsibilities:
                resp_name = resp.name.lower()

                for keyword, target_name in KEYWORDS.items():
                    if keyword not in resp_name:
                        continue

                    target_service = service_by_name.get(target_name)
                    if not target_service:
                        continue

                    if target_service.id == src_service.id:
                        continue

                    key = (src_service.id, target_service.id)
                    if key in seen:
                        continue

                    dependencies.append(
                        ServiceDependency(
                            from_service_id=src_service.id,
                            to_service_id=target_service.id,
                            interaction="uses",
                        )
                    )
                    seen.add(key)

        # --------------------------------------------------
        # Rule 4: Domain-specific mandatory dependencies (CONFIG-DRIVEN)
        # --------------------------------------------------

        domain_context = getattr(context, "domain_context", None)

        if domain_context and domain_context.domain_rules:
            mandatory_deps = domain_context.domain_rules.get("mandatory_dependencies", [])

            for dep in mandatory_deps:
                source_name = dep.get("from")
                target_name = dep.get("to")
                interaction = dep.get("interaction", "uses")

                source_service = service_by_name.get(source_name.lower()) if source_name else None
                target_service = service_by_name.get(target_name.lower()) if target_name else None


                if not source_service or not target_service:
                    continue

                key = (source_service.id, target_service.id)
                if key in seen:
                    continue

                dependencies.append(
                    ServiceDependency(
                        from_service_id=source_service.id,
                        to_service_id=target_service.id,
                        interaction=interaction,
                    )
                )
                seen.add(key)



        # --------------------------------------------------
        # Finalize
        # --------------------------------------------------

        #context.service_ir.dependencies.extend(dependencies)

        # --------------------------------------------------
        # Finalize (DEDUP SAFE VERSION)
        # --------------------------------------------------

        # Combine old + new (if any)
        all_deps = context.service_ir.dependencies + dependencies

        unique_map = {}

        for dep in all_deps:
            key = (dep.from_service_id, dep.to_service_id, dep.interaction)
            unique_map[key] = dep  # overwrite duplicates safely

        context.service_ir.dependencies = list(unique_map.values())

        
        
        print("[DEBUG] Final dependencies:")
        for d in context.service_ir.dependencies:
            print(f"{d.from_service_id} -> {d.to_service_id} ({d.interaction})")
    

        return ValidationResult.success()
