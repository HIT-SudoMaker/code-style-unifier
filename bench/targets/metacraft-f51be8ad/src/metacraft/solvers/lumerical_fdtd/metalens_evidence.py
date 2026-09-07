from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ...authority import Authority
from ...authority.session import AuthoritySession
from ...materials import (
    MaterialResponse,
    SolverMaterialLibrary,
    open_material_response,
)
from .artifacts import RunDirectory
from .material_response import LumericalMaterialVerifier
from .periodic_response import LumericalPeriodicResponse
from .qualification import LumericalConfig


@dataclass(frozen=True, slots=True)
class LumericalMetalensEvidence:
    """
    Open one metalens evidence pair from one Lumerical product binding.
    """

    config: LumericalConfig
    material_library: SolverMaterialLibrary

    def open(
        self,
        *,
        authority: Authority,
        runs_directory: Path,
    ) -> tuple[LumericalPeriodicResponse, MaterialResponse]:
        """
        Bind qualification, periodic work, and material work to one root.
        """

        run_root = Path(runs_directory).expanduser().resolve()
        if not run_root.is_dir():
            raise FileNotFoundError("lumerical_runs_directory_missing")
        config = replace(self.config, runs_directory=run_root)
        periodic_response = LumericalPeriodicResponse.open(
            authority=authority,
            config=config,
            run=RunDirectory(run_root),
        )
        session = AuthoritySession(authority)
        response_context = periodic_response.context
        session.observe_admitted(response_context.binding_reference)
        material_verifier = LumericalMaterialVerifier(
            session=session,
            config=config,
            binding_reference=response_context.binding_reference,
        )
        material_response = open_material_response(
            session=session,
            library=self.material_library,
            binding_reference=material_verifier.binding_reference,
            capacity_scope=response_context.capacity_scope,
            verify_materials=material_verifier.verify,
        )
        return periodic_response, material_response
