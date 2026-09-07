from __future__ import annotations

import math

import torch

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    SameDeviceCompositeState,
)
from experiments.restoration.adaptive_measurement.evidence import (
    build_optical_observation_payload,
)
from experiments.restoration.adaptive_measurement.validation.delivered_phase_oracle import (
    DeliveredPhaseOracleSearch,
)
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.observations import OpticalObservation


def build_delivered_phase_oracle_trace(
    search: DeliveredPhaseOracleSearch,
) -> dict[str, object]:
    """Build the complete raw candidate trace for immutable evaluator evidence."""
    if not isinstance(search, DeliveredPhaseOracleSearch):
        raise TypeError("search must be a DeliveredPhaseOracleSearch")
    return {
        "schema_version": "delivered_phase_oracle_trace_v1",
        "selected_candidate_index": search.selected_candidate_index,
        "selected_candidate_observation_id": (search.selected_candidate_observation_id),
        "selected_command": {
            "command_id": search.command.command_id,
            "phase_radians": search.command.phase_radians.detach().cpu(),
            "piston_radians": search.command.piston_radians,
        },
        "candidates": tuple(
            {
                "command_multiplier": candidate.command_multiplier,
                "spatial_detail_strength": candidate.spatial_detail_strength,
                "mean_square_error": candidate.mean_square_error,
                "observation": build_optical_observation_payload(candidate.observation),
            }
            for candidate in search.candidates
        ),
    }


def build_same_device_oracle_search_evidence(
    target_observation: OpticalObservation,
    search: DeliveredPhaseOracleSearch,
    composite_states: tuple[SameDeviceCompositeState, ...],
    *,
    calibration_id: str,
) -> dict[str, object]:
    """Join a raw oracle trace to every complete same-device delivery state."""
    if not isinstance(target_observation, OpticalObservation):
        raise TypeError("target_observation must be an OpticalObservation")
    if not isinstance(search, DeliveredPhaseOracleSearch):
        raise TypeError("search must be a DeliveredPhaseOracleSearch")
    if not isinstance(calibration_id, str) or not calibration_id.strip():
        raise invalid_restoration_contract("calibration_id must be non-empty")
    if not isinstance(composite_states, tuple) or any(
        not isinstance(state, SameDeviceCompositeState) for state in composite_states
    ):
        raise invalid_restoration_contract(
            "composite_states must contain SameDeviceCompositeState values"
        )

    candidate_ids = tuple(
        candidate.observation.observation_id for candidate in search.candidates
    )
    if len(set(candidate_ids)) != len(candidate_ids):
        raise invalid_restoration_contract(
            "oracle candidate observation IDs must be unique"
        )
    composite_state_by_id = {state.observation_id: state for state in composite_states}
    if len(composite_state_by_id) != len(composite_states):
        raise invalid_restoration_contract(
            "oracle composite-state observation IDs must be unique"
        )
    if set(candidate_ids) != set(composite_state_by_id):
        raise invalid_restoration_contract(
            "every oracle candidate must have one complete composite state"
        )

    selected_observation = search.selected_candidate.observation
    if not torch.allclose(
        selected_observation.command_phase_radians,
        search.command.phase_radians,
        atol=1e-7,
        rtol=1e-7,
    ) or not math.isclose(
        selected_observation.command_piston_radians,
        search.command.piston_radians,
        abs_tol=1e-9,
    ):
        raise invalid_restoration_contract(
            "selected oracle candidate must match the final B3 command"
        )

    target_intensity = target_observation.intensity
    for candidate in search.candidates:
        reconstructed_error = float(
            torch.mean(
                (candidate.observation.intensity - target_intensity).square()
            ).item()
        )
        if not math.isclose(
            reconstructed_error,
            candidate.mean_square_error,
            rel_tol=1e-6,
            abs_tol=1e-12,
        ):
            raise invalid_restoration_contract(
                "oracle candidate error must be reconstructible from raw evidence"
            )

    return {
        "schema_version": "same_device_b3_oracle_search_v1",
        "calibration_id": calibration_id,
        "target_observation": build_optical_observation_payload(target_observation),
        "search": build_delivered_phase_oracle_trace(search),
        "candidate_composite_states": tuple(
            build_same_device_composite_payload(composite_state_by_id[observation_id])
            for observation_id in candidate_ids
        ),
    }


def build_same_device_composite_payload(
    state: SameDeviceCompositeState,
) -> dict[str, object]:
    """Build one complete evaluator-only same-device delivery payload."""
    if not isinstance(state, SameDeviceCompositeState):
        raise TypeError("state must be a SameDeviceCompositeState")
    return {
        "observation_id": state.observation_id,
        "command": {
            "command_id": state.command.command_id,
            "phase_radians": state.command.phase_radians.detach().cpu(),
            "piston_radians": state.command.piston_radians,
        },
        "delivery": {
            "command_id": state.delivery.command_id,
            "phase_radians": state.delivery.phase_radians.detach().cpu(),
            "piston_radians": state.delivery.piston_radians,
            "delivery_model": state.delivery.delivery_model,
            "metadata": dict(state.delivery.metadata),
        },
    }
