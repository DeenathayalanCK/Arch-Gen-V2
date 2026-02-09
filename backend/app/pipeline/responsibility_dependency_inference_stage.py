from app.pipeline.stage import PipelineStage
from app.pipeline.context import PipelineContext
from app.ir.validation import ValidationResult
from app.ir.responsibility_ir import ResponsibilityDependency, ResponsibilityDataAccess


class ResponsibilityDependencyInferenceStage(PipelineStage):
    name = "Responsibility Dependency Inference Stage"

    # Verb keywords for matching responsibilities across services
    VERB_KEYWORDS = [
        "processing",
        "validation",
        "retrieval",
        "lifecycle",
        "create",
        "update",
    ]

    # PRIMARY responsibilities that drive cross-service calls
    # Only these responsibilities create dependency edges
    PRIMARY_RESPONSIBILITIES = [
        "processing",
        "create",
        "update",
    ]

    # Responsibilities that access data
    DATA_ACCESS_RESPONSIBILITIES = {
        "processing": "read_write",
        "create": "write",
        "update": "write",
        "retrieval": "read",
        "validation": "read",
    }

    def run(self, context: PipelineContext) -> ValidationResult:
        # Guard: nothing to infer
        if not context.service_ir or not context.responsibility_map:
            return ValidationResult.success()

        inferred: list[ResponsibilityDependency] = []

        # service_id -> list[Responsibility]
        responsibilities_by_service: dict[str, list] = {}

        for bundle in context.responsibility_map.values():
            responsibilities_by_service.setdefault(
                bundle.service_id, []
            ).extend(bundle.responsibilities)

        # Infer responsibility dependencies ONLY through service dependencies
        # AND only from PRIMARY responsibilities
        for dep in context.service_ir.dependencies:
            from_service_id = dep.from_service_id
            to_service_id = dep.to_service_id

            from_resps = responsibilities_by_service.get(from_service_id, [])
            to_resps = responsibilities_by_service.get(to_service_id, [])

            if not from_resps or not to_resps:
                continue

            for fr in from_resps:
                fr_verb = self._extract_verb(fr.name)
                if not fr_verb:
                    continue

                # 🔑 GATE: Only primary responsibilities create edges
                if not self._is_primary_responsibility(fr_verb):
                    continue

                for tr in to_resps:
                    tr_verb = self._extract_verb(tr.name)
                    if fr_verb != tr_verb:
                        continue

                    inferred.append(
                        ResponsibilityDependency(
                            from_service=from_service_id,
                            from_responsibility=fr.name,
                            to_service=to_service_id,
                            to_responsibility=tr.name,
                            interaction=dep.interaction or "calls",
                        )
                    )

        # Deduplicate (stable + explicit)
        unique: dict[
            tuple[str, str, str, str], ResponsibilityDependency
        ] = {}

        for d in inferred:
            key = (
                d.from_service,
                d.from_responsibility,
                d.to_service,
                d.to_responsibility,
            )
            unique[key] = d

        context.responsibility_dependencies = list(unique.values())

        # 🔑 Infer responsibility → data access
        self._infer_responsibility_data_access(context, responsibilities_by_service)

        return ValidationResult.success()

    def _is_primary_responsibility(self, verb: str) -> bool:
        """Check if the verb represents a primary (driving) responsibility."""
        return verb in self.PRIMARY_RESPONSIBILITIES

    def _extract_verb(self, name: str) -> str | None:
        lname = name.lower()
        for verb in self.VERB_KEYWORDS:
            if verb in lname:
                return verb
        return None

    def _infer_responsibility_data_access(
        self,
        context: PipelineContext,
        responsibilities_by_service: dict[str, list],
    ):
        """Infer responsibility → datastore access based on service data access patterns."""
        if not context.data_ir:
            return

        # Build service_name -> service_id lookup
        service_name_to_id = {
            svc.name: svc.id for svc in context.service_ir.services
        }
        service_id_to_name = {
            svc.id: svc.name for svc in context.service_ir.services
        }

        # Build datastore_id -> datastore_name lookup
        datastore_id_to_name = {
            ds.id: ds.name for ds in context.data_ir.datastores
        }

        # Initialize responsibility data access list
        responsibility_data_access: list[ResponsibilityDataAccess] = []

        # For each access pattern, find matching responsibilities
        for access in context.data_ir.access_patterns:
            # access.service_id is the service NAME
            service_name = access.service_id
            service_id = service_name_to_id.get(service_name)

            if not service_id:
                continue

            datastore_name = datastore_id_to_name.get(access.datastore_id)
            if not datastore_name:
                continue

            # Get responsibilities for this service
            resps = responsibilities_by_service.get(service_id, [])

            for resp in resps:
                verb = self._extract_verb(resp.name)
                if not verb:
                    continue

                # Only primary responsibilities access data
                if not self._is_primary_responsibility(verb):
                    continue

                # Determine access type based on responsibility
                resp_access_type = self.DATA_ACCESS_RESPONSIBILITIES.get(verb, "read")

                responsibility_data_access.append(
                    ResponsibilityDataAccess(
                        service_name=service_name,
                        responsibility_name=resp.name,
                        datastore_name=datastore_name,
                        access_type=resp_access_type,
                    )
                )

        # Deduplicate
        unique_access: dict[tuple[str, str, str], ResponsibilityDataAccess] = {}
        for ra in responsibility_data_access:
            key = (ra.service_name, ra.responsibility_name, ra.datastore_name)
            unique_access[key] = ra

        context.responsibility_data_access = list(unique_access.values())
