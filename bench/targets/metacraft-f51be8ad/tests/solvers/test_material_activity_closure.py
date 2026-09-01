from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from metacraft.external_activity import ExternalActivityOrigin
from metacraft.solvers.lumerical_fdtd import probe as probe_module
from metacraft.solvers.lumerical_fdtd.material import (
    LumericalMaterialSample,
    MaterialVerificationRefusal,
    MaterialVerificationRefusalKind,
)
from metacraft.solvers.lumerical_fdtd.probe import ProductProbe
from metacraft.solvers.lumerical_fdtd.qualification import LumericalConfig


class _MaterialEngine:
    def __init__(
        self,
        *,
        has_material: bool = True,
        close_error: BaseException | None = None,
    ) -> None:
        self.has_material = has_material
        self.close_error = close_error
        self.close_count = 0

    def materialexists(self, _native_name: str) -> bool:
        return self.has_material

    def close(self) -> None:
        self.close_count += 1
        if self.close_error is not None:
            raise self.close_error


def _config(tmp_path: Path) -> LumericalConfig:
    return LumericalConfig(
        executable=None,
        python_api=tmp_path / "lumapi.py",
        license_utility=None,
        license_server=None,
        runs_directory=tmp_path / "runs",
    )


def _empty_sample(wavelength_nm: int) -> LumericalMaterialSample:
    frequency = Decimal("1")
    return LumericalMaterialSample(
        grid_wavelengths_nm=(wavelength_nm,),
        minimum_fit_frequency_hz=frequency,
        maximum_fit_frequency_hz=frequency,
        materials={},
    )


@pytest.mark.parametrize("has_material", (True, False))
def test_native_material_probe_pairs_success_or_refusal_with_one_closed_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    has_material: bool,
) -> None:
    engine = _MaterialEngine(has_material=has_material)
    monkeypatch.setattr(probe_module, "open_engine", lambda *_args, **_kwargs: engine)
    monkeypatch.setattr(
        probe_module,
        "_sample_materials",
        lambda _engine, _catalogue, *, wavelengths_nm: _empty_sample(
            wavelengths_nm[0]
        ),
    )

    outcome, activity = ProductProbe().sample_materials(
        _config(tmp_path),
        {"silicon": "Si native"},
        532,
    )

    if has_material:
        assert isinstance(outcome, LumericalMaterialSample)
    else:
        assert outcome == MaterialVerificationRefusal(
            kind=MaterialVerificationRefusalKind.NATIVE_MATERIAL_ABSENT,
            family="silicon",
            native_name="Si native",
            wavelength_nm=532,
        )
    assert engine.close_count == 1
    assert activity.origin is ExternalActivityOrigin.NATIVE
    assert activity.opened_product_session_count == 1
    assert activity.closed_product_session_count == 1
    assert activity.acquired_authority_work_count == 0
    assert activity.started_external_execution_count == 0
    assert activity.opened_local_placement_count == 0


def test_native_material_probe_groups_sampling_and_cleanup_faults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    primary = RuntimeError("sampling_failed")
    cleanup = RuntimeError("cleanup_failed")
    engine = _MaterialEngine(close_error=cleanup)
    monkeypatch.setattr(probe_module, "open_engine", lambda *_args, **_kwargs: engine)

    def fail_sampling(*_args: object, **_kwargs: object) -> LumericalMaterialSample:
        raise primary

    monkeypatch.setattr(probe_module, "_sample_materials", fail_sampling)

    with pytest.raises(BaseExceptionGroup) as raised:
        ProductProbe().sample_materials(
            _config(tmp_path),
            {"silicon": "Si native"},
            532,
        )

    assert raised.value.exceptions == (primary, cleanup)
    assert engine.close_count == 1


def test_native_material_probe_propagates_open_failure_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    injected = RuntimeError("open_failed")

    def fail_open(*_args: object, **_kwargs: object) -> object:
        raise injected

    monkeypatch.setattr(probe_module, "open_engine", fail_open)

    with pytest.raises(RuntimeError) as raised:
        ProductProbe().sample_materials(
            _config(tmp_path),
            {"silicon": "Si native"},
            532,
        )

    assert raised.value is injected


def test_native_material_probe_propagates_cleanup_failure_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    injected = RuntimeError("cleanup_failed")
    engine = _MaterialEngine(has_material=False, close_error=injected)
    monkeypatch.setattr(probe_module, "open_engine", lambda *_args, **_kwargs: engine)

    with pytest.raises(RuntimeError) as raised:
        ProductProbe().sample_materials(
            _config(tmp_path),
            {"silicon": "Si native"},
            532,
        )

    assert raised.value is injected
    assert engine.close_count == 1
