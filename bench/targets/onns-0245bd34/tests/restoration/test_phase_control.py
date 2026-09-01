from __future__ import annotations

import math

import pytest
import torch

from experiments.restoration.phase_control import (
    IdealPhaseDelivery,
    PhaseCommand,
    SimulatedSlmPhaseDelivery,
    remove_phase_piston,
    wrap_phase_radians,
)


def test_remove_phase_piston_uses_only_pupil_support() -> None:
    phase = torch.tensor([[100.0, 100.0], [1.0, 3.0]])
    pupil = torch.tensor([[0.0, 0.0], [1.0, 1.0]])

    normalized = remove_phase_piston(phase, pupil=pupil)

    assert torch.mean(normalized[pupil > 0]).item() == pytest.approx(0.0)


def test_ideal_delivery_wraps_a_zero_piston_command() -> None:
    command = PhaseCommand(
        command_id="oracle",
        phase_radians=torch.tensor([[0.0, math.pi], [2.0 * math.pi, 3.0 * math.pi]]),
    )

    delivered = IdealPhaseDelivery().deliver(command)

    assert delivered.delivery_model == "ideal_continuous_phase"
    assert torch.all(delivered.phase_radians >= 0.0)
    assert torch.all(delivered.phase_radians < 2.0 * math.pi)


def test_ideal_delivery_preserves_a_declared_measurement_piston() -> None:
    command = PhaseCommand(
        command_id="quadrature-pi-over-two",
        phase_radians=torch.zeros((4, 4)),
        piston_radians=math.pi / 2.0,
    )

    delivered = IdealPhaseDelivery().deliver(command)

    assert delivered.piston_radians == pytest.approx(math.pi / 2.0)
    assert torch.mean(delivered.phase_radians).item() == pytest.approx(math.pi / 2.0)


def test_simulated_slm_delivery_quantizes_and_records_delivery_model() -> None:
    command = PhaseCommand(
        command_id="candidate",
        phase_radians=torch.tensor([[0.0, 0.2], [1.4, 2.8]]),
    )

    delivered = SimulatedSlmPhaseDelivery(
        phase_levels=8,
        response_gain=0.95,
        drift_radians=0.1,
        crosstalk_mix=0.0,
    ).deliver(command)

    quantization_step = 2.0 * math.pi / 8.0
    remainder = torch.remainder(delivered.phase_radians, quantization_step)
    distance = torch.minimum(remainder, quantization_step - remainder)
    assert torch.max(distance).item() < 1e-5
    assert delivered.delivery_model == "simulated_slm_phase"
    assert delivered.metadata["phase_levels"] == 8


def test_simulated_slm_preserves_one_spatial_state_across_piston_steps() -> None:
    spatial_phase = torch.rand(
        (16, 16),
        generator=torch.Generator().manual_seed(31),
    ) * (2.0 * math.pi)
    delivery = SimulatedSlmPhaseDelivery(
        phase_levels=32,
        response_gain=0.93,
        drift_radians=0.17,
        crosstalk_mix=0.2,
    )
    states = tuple(
        delivery.deliver(
            PhaseCommand(
                f"piston-{index}",
                spatial_phase,
                piston_radians=piston,
            )
        )
        for index, piston in enumerate(
            (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)
        )
    )

    spatial_phasors = tuple(
        torch.exp(1j * (state.phase_radians - state.piston_radians)) for state in states
    )

    assert all(
        torch.allclose(spatial_phasors[0], phasor, atol=1e-6, rtol=1e-6)
        for phasor in spatial_phasors[1:]
    )
    assert all(
        state.metadata["is_spatial_piston_separable"] is True for state in states
    )


def test_phase_command_rejects_complex_or_nonplanar_values() -> None:
    with pytest.raises(ValueError, match="real"):
        PhaseCommand("bad", torch.ones((2, 2), dtype=torch.complex64))
    with pytest.raises(ValueError, match="2D"):
        PhaseCommand("bad", torch.ones((1, 1, 2, 2)))


def test_wrap_phase_radians_is_half_open() -> None:
    wrapped = wrap_phase_radians(
        torch.tensor([[-math.pi, 0.0], [2.0 * math.pi, 3.0 * math.pi]])
    )

    assert torch.all(wrapped >= 0.0)
    assert torch.all(wrapped < 2.0 * math.pi)
