from __future__ import annotations

import cmath
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
import math
from pathlib import Path
from typing import Any

import metacraft.solvers.lumerical_fdtd.periodic_response as response_module
import metacraft.solvers.lumerical_fdtd.material_response as material_response_module
from metacraft.materials import SolverMaterialLibrary
from metacraft.science.metalens.brief import (
    MetalensBrief,
    require_monochromatic_wavelength,
)
from metacraft.solvers.lumerical_fdtd.lane import (
    SessionPool as NativeSessionPool,
)
from metacraft.solvers.lumerical_fdtd.material import (
    LumericalMaterialSample,
    NativeIndexPoint,
    NativeMaterialSample,
    sample_frequency_hz,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    PeriodicResponseProof,
)
from metacraft.solvers.lumerical_fdtd import (
    LumericalMetalensEvidence,
)
from tests.lumerical_fixtures import (
    lumerical_config,
    probe_facts,
    workstation_layout,
)
from tests.solver_fakes import (
    ActiveEngines,
    FakeProbe,
    FakeSessionFactory,
)


def fake_metalens_ports(
    brief: MetalensBrief,
    application_root: Path,
    monkeypatch: Any,
    *,
    response_proof: PeriodicResponseProof,
) -> dict[str, object]:
    """
    Compose public conduct ports without an application/lifecycle carrier.
    """

    now = datetime.now(UTC)
    catalogue_names = {
        "amorphous silicon": "a-Si fixture",
        "silica": "SiO2 fixture",
        "silicon nitride": "SiN fixture",
    }
    selected_names = {
        family: catalogue_names[family]
        for family in dict.fromkeys(
            (
                brief.atom.material.family,
                brief.substrate.family,
            )
        )
    }
    probe = FakeProbe(
        replace(
            probe_facts(now),
            lumerical_gui_limit=4,
            lumerical_solve_limit=4,
        ),
        proof=response_proof,
        material_sample=_material_sample(
            selected_names,
            require_monochromatic_wavelength(brief.operating_spectrum),
        ),
    )
    session_factory = FakeSessionFactory(
        active=ActiveEngines(),
        result=_phase_covering_response,
    )
    monkeypatch.setattr(
        response_module,
        "SessionPool",
        lambda execution, lanes, **facts: NativeSessionPool(
            execution,
            lanes,
            **facts,
            _open_session=session_factory,
        ),
    )
    monkeypatch.setattr(response_module, "ProductProbe", lambda: probe)
    monkeypatch.setattr(
        response_module,
        "plan",
        lambda _demand: workstation_layout(now, physical_cores=16),
    )
    monkeypatch.setattr(
        material_response_module,
        "ProductProbe",
        lambda: probe,
    )
    catalogue = SolverMaterialLibrary.decode_bytes(
        (
            'solver = "lumerical fdtd"\n'
            + "".join(
                (
                    "\n[[materials]]\n"
                    f'family = "{family}"\n'
                    f'native_name = "{native_name}"\n'
                    'provenance = "reviewed fixture"\n'
                )
                for family, native_name in sorted(catalogue_names.items())
            )
        ).encode("utf-8")
    )
    return {
        "application_root": application_root,
        "evidence_adapter": LumericalMetalensEvidence(
            config=lumerical_config(
                application_root.parent / f"{application_root.name}-fixture-product"
            ),
            material_library=catalogue,
        ),
    }


def _material_sample(
    catalogue: dict[str, str],
    wavelength_nm: int,
) -> LumericalMaterialSample:
    frequency = Decimal(str(sample_frequency_hz(wavelength_nm)))
    return LumericalMaterialSample(
        grid_wavelengths_nm=(wavelength_nm,),
        minimum_fit_frequency_hz=frequency,
        maximum_fit_frequency_hz=frequency,
        materials={
            family: NativeMaterialSample(
                family=family,
                native_name=native_name,
                fit_tolerance=Decimal("0.1"),
                fit_maximum_coefficients=6,
                minimum_tabulated_frequency_hz=frequency,
                maximum_tabulated_frequency_hz=frequency,
                points=(
                    NativeIndexPoint(
                        wavelength_nm=wavelength_nm,
                        frequency_hz=frequency,
                        refractive_index=(
                            Decimal("1.45") if family == "silica" else Decimal("3.5")
                        ),
                        extinction_coefficient=Decimal("0"),
                        fit_residual=Decimal("0.001"),
                    ),
                ),
                findings=(),
            )
            for family, native_name in catalogue.items()
        },
    )


def _phase_covering_response(
    objects: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    atom = objects["meta_atom"]
    feature_nm = int(
        atom["diameter_nm"] if "diameter_nm" in atom else atom["span_x_nm"]
    )
    phase = math.tau * ((feature_nm // 10) % 16) / 16
    transmission = 0.95 * cmath.exp(1j * phase)
    return {
        "complex_transmission": transmission,
        "power_transmission": abs(transmission) ** 2,
        "phase_planes": "grating_s_params",
        "solver_status": "complete",
        "warnings": [],
    }
