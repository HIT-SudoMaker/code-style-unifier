from __future__ import annotations

import base64
import os
from pathlib import Path
import pickle
import subprocess
import sys

import pytest

from chromatix_next.errors import (
    AssemblyError,
    OpticalError,
    OpticalRuntimeError,
    OpticalTypeError,
    OpticalValueError,
    WorkstationError,
)
from chromatix_next.optics import Polarization, PropagationDirection, Spectrum, Vacuum
from chromatix_next.optics.element import RetarderAt
from chromatix_next.optics.source import PlaneWave
from chromatix_next.optics.surface import Plane

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "failure_class",
    [
        OpticalError,
        OpticalTypeError,
        OpticalValueError,
        OpticalRuntimeError,
        AssemblyError,
        WorkstationError,
    ],
)
def test_public_failures_reconstruct_in_a_fresh_process(
    failure_class: type[OpticalError],
) -> None:
    """
    公开失败可跨进程重建，且保留稳定身份与说明
    """

    failure = failure_class("probe_identity", "跨进程重建仍保留完整说明")
    payload = base64.b64encode(pickle.dumps(failure)).decode("ascii")
    environment = dict(os.environ)
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        part
        for part in (str(PROJECT_ROOT / "src"), existing_pythonpath)
        if part
    )
    script = """
import base64
import pickle
import sys

failure = pickle.loads(base64.b64decode(sys.argv[1]))
assert type(failure).__module__ == "chromatix_next.errors"
assert failure.identity == "probe_identity"
assert failure.explanation == "跨进程重建仍保留完整说明"
assert str(failure) == "probe_identity：跨进程重建仍保留完整说明"
"""
    result = subprocess.run(
        [sys.executable, "-c", script, payload],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_public_errors_preserve_identity_explanation_and_builtin_ancestry() -> None:
    """
    公开失败保留稳定身份、中文解释、进程参数与内建异常祖先
    """

    error = OpticalValueError("contract_value_invalid", "契约值无效")
    assert error.identity == "contract_value_invalid"
    assert error.explanation == "契约值无效"
    assert error.args == ("contract_value_invalid", "契约值无效")
    assert str(error) == "contract_value_invalid：契约值无效"
    assert isinstance(OpticalTypeError("kind_invalid", "类型无效"), TypeError)
    assert isinstance(error, ValueError)


def test_representative_public_state_keys_remain_exact() -> None:
    """
    光源与曲面元件投影保留公开状态键语法
    """

    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=532.0e-9),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    assert tuple(source.state_dict()) == (
        "wavelengths",
        "spectral_weights",
        "polarization_state",
        "direction_cosine_y",
        "direction_cosine_x",
        "relative_amplitude",
        "_extra_state",
    )

    surface = Plane(
        origin=(0.0, 0.0, 0.0),
        tangent_x=(0.0, 1.0, 0.0),
        tangent_y=(1.0, 0.0, 0.0),
    )
    retarder = RetarderAt(
        surface=surface,
        retardance_cycles=0.25,
        retarded_eigenstate_azimuth_radians=0.0,
        retarded_eigenstate_ellipticity_radians=0.0,
    )
    assert tuple(retarder.state_dict()) == (
        "retardance_cycles",
        "retarded_eigenstate_azimuth_radians",
        "retarded_eigenstate_ellipticity_radians",
        "surface.origin",
        "surface.tangent_x",
        "surface.tangent_y",
    )


def test_invalid_public_value_retains_a_stable_identity() -> None:
    """
    无效公开值在边界处以稳定领域身份失败
    """

    with pytest.raises(OpticalValueError) as information:
        Spectrum.monochromatic(wavelength=0.0)
    assert information.value.identity == "spectrum_wavelength_nonpositive"
