from __future__ import annotations

from pathlib import Path

from metacraft.authority import Authority, Document
from metacraft.authority.session import AuthoritySession
from metacraft.external_activity import ExternalActivityClosure
from metacraft.materials import (
    MaterialResponse,
    MaterialResponseContext,
    RecordedMaterialResponse,
)
from metacraft.science.periodic_response import (
    PeriodicResponse,
    PeriodicResponseContext,
    PeriodicResponseKind,
)
from metacraft.solvers.recorded_periodic_response import (
    RecordedPeriodicResponse,
)


class RecordedMetalensEvidenceAdapter:
    """Open the two production replay ports in one fresh application root."""

    def open(
        self,
        *,
        authority: Authority,
        runs_directory: Path,
    ) -> tuple[PeriodicResponse, MaterialResponse]:
        """Bind recorded response lookup without product or permit activity."""

        if not runs_directory.is_dir():
            raise ValueError("recorded_runs_directory_missing")
        session = AuthoritySession(authority)
        binding_reference = session.admit_document(
            Document(
                "metacraft.examples.recorded_metalens_binding",
                {"recorded": True},
            )
        )
        return (
            RecordedPeriodicResponse(
                session,
                context=PeriodicResponseContext(
                    binding_reference=binding_reference,
                    capacity_scope="examples:recorded-metalens",
                    response_kinds=tuple(PeriodicResponseKind),
                    qualification_closure=(
                        ExternalActivityClosure.recorded()
                    ),
                ),
            ),
            RecordedMaterialResponse(
                session,
                context=MaterialResponseContext(
                    binding_reference=binding_reference,
                    capacity_scope="examples:recorded-metalens",
                ),
            ),
        )


__all__ = ["RecordedMetalensEvidenceAdapter"]
