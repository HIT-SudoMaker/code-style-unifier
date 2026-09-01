from __future__ import annotations

import pytest
import torch

from experiments.restoration.pupil_aberrations import (
    PupilAberrationState,
    build_pupil_aberration_phase,
)


def test_pupil_aberration_modes_have_declared_rms_and_zero_piston() -> None:
    phase, pupil = build_pupil_aberration_phase(
        (64, 64),
        PupilAberrationState({"defocus": 1.5}),
    )
    supported = phase[pupil > 0]

    assert torch.mean(supported).item() == pytest.approx(0.0, abs=1e-5)
    assert torch.sqrt(torch.mean(supported.square())).item() == pytest.approx(
        1.5,
        abs=1e-4,
    )
    assert torch.count_nonzero(phase[pupil == 0]).item() == 0


def test_pupil_aberration_combines_declared_modes() -> None:
    phase, pupil = build_pupil_aberration_phase(
        (48, 64),
        PupilAberrationState(
            {
                "defocus": 0.8,
                "astigmatism_oblique": -0.4,
                "coma_horizontal": 0.2,
            }
        ),
    )

    assert phase.shape == (48, 64)
    assert pupil.shape == phase.shape
    assert bool(torch.isfinite(phase).all())


def test_pupil_aberration_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="pupil mode"):
        PupilAberrationState({"mystery": 1.0})
