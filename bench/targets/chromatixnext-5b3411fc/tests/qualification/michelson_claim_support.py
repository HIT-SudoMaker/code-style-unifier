from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import torch

from chromatix_next import Workstation
from chromatix_next.optics import Assembly, Intensity
from examples.analytic_michelson_interferometer.example import build_assembly
from tools.qualify_example_evidence import ResponseWitnessRecord


@dataclass(frozen=True, slots=True)
class MichelsonWitnessPrograms:
    """
    Retain records and immutable snapshots around independent programs

    """

    records: tuple[ResponseWitnessRecord, ...]
    baseline_state_before: tuple[tuple[str, torch.Tensor | str], ...]
    baseline_state_after: tuple[tuple[str, torch.Tensor | str], ...]
    baseline_facts: Any


def construct_michelson_witness_programs() -> MichelsonWitnessPrograms:
    """
    Run a frozen baseline and a separately built phase-omission challenge

    """

    baseline = build_assembly(relative_phase=math.pi / 3.0)
    challenge = build_assembly(relative_phase=0.0)
    state_before = _state_snapshot(baseline)
    baseline_left = _left_ratio(baseline)
    state_after = _state_snapshot(baseline)
    challenged_left = _left_ratio(challenge)
    analytic_left = math.sin(math.pi / 6.0) ** 2
    split_then_add_wrong_model = 0.5
    phase_discrimination = abs(baseline_left - challenged_left)
    wrong_model_discrimination = abs(
        baseline_left - split_then_add_wrong_model,
    )
    records = (
        ResponseWitnessRecord(
            claim_name="michelson_relative_phase_response",
            witness_name="phase_omission_counterfactual",
            supported_baseline_point="relative_phase_pi_over_three",
            challenge_action="omit_relative_phase",
            required_observable_name="left_intensity",
            normalization="relative_dimensionless",
            expected_relation="nonzero_separation",
            finite_tolerance=2.0e-12,
            baseline_observable=(baseline_left,),
            challenged_observable=(challenged_left,),
            actual_discrimination=phase_discrimination,
            baseline_input_norm=1.0,
            normalization_denominator=1.0,
        ),
        ResponseWitnessRecord(
            claim_name="michelson_relative_phase_response",
            witness_name="analytic_port_ratio_metamorphic",
            supported_baseline_point="relative_phase_pi_over_three",
            challenge_action="split_then_add_intensity_wrong_model",
            required_observable_name="left_intensity",
            normalization="relative_dimensionless",
            expected_relation="metamorphic_equality",
            finite_tolerance=2.0e-12,
            baseline_observable=(baseline_left,),
            challenged_observable=(analytic_left,),
            actual_discrimination=wrong_model_discrimination,
            baseline_input_norm=1.0,
            normalization_denominator=1.0,
            wrong_model_name="split_then_add_intensity_wrong_model",
            wrong_model_observable=(split_then_add_wrong_model,),
        ),
    )
    return MichelsonWitnessPrograms(
        records=records,
        baseline_state_before=state_before,
        baseline_state_after=state_after,
        baseline_facts=baseline._execution_facts(),  # noqa: SLF001
    )


def _left_ratio(assembly: Assembly) -> float:
    workstation = Workstation.cpu()
    workstation.host(assembly)
    try:
        outputs, _record = workstation.run(assembly)
    finally:
        workstation.release(assembly)
    intensity = outputs["left_intensity"]
    assert isinstance(intensity, Intensity)
    return float(intensity.values.mean().item())


def _state_snapshot(
    assembly: Assembly,
) -> tuple[tuple[str, torch.Tensor | str], ...]:
    return tuple(
        (
            name,
            value.detach().clone()
            if isinstance(value, torch.Tensor)
            else repr(value),
        )
        for name, value in assembly.state_dict().items()
    )
