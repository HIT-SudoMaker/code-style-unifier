from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import torch

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.adaptive_measurement.protocol.episode import (
    AdaptiveEpisodePolicy,
)
from experiments.restoration.adaptive_measurement.reachability import (
    CalibratedReplayReachability,
    DeliveredCorrectionProposal,
)
from experiments.restoration.observations import ObservationKind, OpticalObservation
from experiments.restoration.optical_bench import (
    DetectorNoiseModel,
    OpticalBenchConfig,
    propagate_interferometric_bench,
)
from experiments.restoration.phase_control import (
    DeliveredPhaseState,
    PhaseCommand,
    PhaseDelivery,
)
from experiments.restoration.value_contracts import finite_real
from layers import DetectionLayer


@dataclass(frozen=True, slots=True, eq=False)
class CoherentPupilScene:
    """Freeze the object field, pupil aberration, and pupil support together."""

    object_field: torch.Tensor
    aberration_phase_radians: torch.Tensor
    pupil: torch.Tensor

    def __post_init__(self) -> None:
        if not isinstance(self.object_field, torch.Tensor) or not torch.is_complex(
            self.object_field
        ):
            raise invalid_restoration_contract("object_field must be a complex tensor")
        if self.object_field.ndim < 2 or self.object_field.numel() == 0:
            raise invalid_restoration_contract(
                "object_field must have at least two non-empty dimensions"
            )
        if not bool(torch.isfinite(self.object_field).all()):
            raise invalid_restoration_contract(
                "object_field must contain finite values"
            )
        scene_shape = tuple(self.object_field.shape[-2:])
        for field_name in ("aberration_phase_radians", "pupil"):
            plane = getattr(self, field_name)
            if (
                not isinstance(plane, torch.Tensor)
                or torch.is_complex(plane)
                or tuple(plane.shape) != scene_shape
            ):
                raise invalid_restoration_contract(
                    f"{field_name} must be a real 2D plane matching object_field"
                )
            if not bool(torch.isfinite(plane).all()):
                raise invalid_restoration_contract(
                    f"{field_name} must contain finite values"
                )
            object.__setattr__(self, field_name, plane.detach().clone())
        if bool(torch.any(self.pupil < 0.0)) or float(self.pupil.sum().item()) <= 0.0:
            raise invalid_restoration_contract("pupil must have nonnegative support")
        object.__setattr__(self, "object_field", self.object_field.detach().clone())


@dataclass(frozen=True, slots=True)
class SameDeviceCompositeState:
    """Evaluator-only command and delivery for one complete SLM2 phase state."""

    observation_id: str
    command: PhaseCommand
    delivery: DeliveredPhaseState

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, str) or not self.observation_id.strip():
            raise invalid_restoration_contract("observation_id must be non-empty")
        if not isinstance(self.command, PhaseCommand):
            raise TypeError("command must be a PhaseCommand")
        if not isinstance(self.delivery, DeliveredPhaseState):
            raise TypeError("delivery must be a DeliveredPhaseState")


class CoherentPupilBench:
    """Compose a phase-delivery Adapter with coherent pupil propagation."""

    def __init__(
        self,
        bench_config: OpticalBenchConfig,
        phase_delivery: PhaseDelivery,
        *,
        photon_count: float | None = None,
        read_noise_standard_deviation: float = 0.0,
        seed: int = 2026,
        device: torch.device | str = "cpu",
    ) -> None:
        if not hasattr(phase_delivery, "deliver"):
            raise TypeError("phase_delivery must implement the PhaseDelivery Interface")
        if not isinstance(bench_config, OpticalBenchConfig):
            raise TypeError("bench_config must be an OpticalBenchConfig")
        bench_config.validate()
        self.bench_config: OpticalBenchConfig = bench_config
        self.array_resolution: tuple[int, int] = bench_config.input_array_resolution
        self.phase_delivery: PhaseDelivery = phase_delivery
        self._detector_noise = DetectorNoiseModel(
            photon_count=photon_count,
            read_noise_standard_deviation=read_noise_standard_deviation,
            seed=seed,
        )
        self.device: torch.device = torch.device(device)
        self._detector: DetectionLayer = DetectionLayer(
            self.array_resolution,
            is_normalization_enabled=False,
        ).to(self.device)

    @property
    def photon_count(self) -> float | None:
        """Return the calibrated photon scale used for each exposure."""
        return self._detector_noise.photon_count

    @torch.no_grad()
    def acquire(
        self,
        scene: CoherentPupilScene,
        command: PhaseCommand,
        *,
        observation_id: str,
        kind: ObservationKind,
        sequence_index: int,
        is_reference_enabled: bool = True,
        elapsed_time_s: float = 0.0,
    ) -> OpticalObservation:
        """Acquire one independently identified observation under a delivered action."""
        return self._acquire_with_delivery(
            scene,
            command,
            observation_id=observation_id,
            kind=kind,
            sequence_index=sequence_index,
            is_reference_enabled=is_reference_enabled,
            elapsed_time_s=elapsed_time_s,
        )

    def _acquire_with_delivery(
        self,
        scene: CoherentPupilScene,
        command: PhaseCommand,
        *,
        observation_id: str,
        kind: ObservationKind,
        sequence_index: int,
        is_reference_enabled: bool,
        elapsed_time_s: float,
        physical_delivery: DeliveredPhaseState | None = None,
        visible_delivery: DeliveredPhaseState | None = None,
    ) -> OpticalObservation:
        """Acquire with an optional evaluator-owned physical delivery state."""
        field, aberration, pupil_plane = self._prepare_scene(scene)
        if tuple(command.phase_radians.shape) != self.array_resolution:
            raise invalid_restoration_contract(
                "phase command must match the bench array resolution"
            )
        delivered_physical_state = physical_delivery
        if delivered_physical_state is None:
            delivered_physical_state = self.phase_delivery.deliver(
                command,
                pupil=pupil_plane,
            )
        delivered_visible_state = (
            delivered_physical_state if visible_delivery is None else visible_delivery
        )
        for name, state in (
            ("physical_delivery", delivered_physical_state),
            ("visible_delivery", delivered_visible_state),
        ):
            if not isinstance(state, DeliveredPhaseState):
                raise TypeError(f"{name} must be a DeliveredPhaseState")
            if tuple(state.phase_radians.shape) != self.array_resolution:
                raise invalid_restoration_contract(
                    f"{name} must match the bench array resolution"
                )
        output_fields = propagate_interferometric_bench(
            field,
            delivered_physical_state.phase_radians.to(self.device),
            self.bench_config,
            processing_aberration_radians=aberration,
            processing_pupil=pupil_plane,
            is_reference_enabled=is_reference_enabled,
        )
        intensity = self._detector_noise.sample(
            self._detector(output_fields.combined),
            sequence_index=sequence_index,
        )
        return OpticalObservation(
            observation_id=observation_id,
            kind=kind,
            sequence_index=sequence_index,
            intensity=intensity,
            command_id=command.command_id,
            command_phase_radians=command.phase_radians,
            delivered_phase_radians=delivered_visible_state.phase_radians,
            delivery_model=delivered_visible_state.delivery_model,
            is_reference_enabled=is_reference_enabled,
            command_piston_radians=command.piston_radians,
            delivered_piston_radians=delivered_visible_state.piston_radians,
            elapsed_time_s=elapsed_time_s,
            metadata={
                "delivered_phase_metadata": dict(delivered_visible_state.metadata),
                "observation_model": "shared_fixed_reference_interferometric_bench",
            },
        )

    def _prepare_scene(
        self,
        scene: CoherentPupilScene,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if not isinstance(scene, CoherentPupilScene):
            raise TypeError("scene must be a CoherentPupilScene")
        if tuple(scene.object_field.shape[-2:]) != self.array_resolution:
            raise invalid_restoration_contract(
                "scene must match the bench array resolution"
            )
        object_field = scene.object_field.to(
            device=self.device,
            dtype=torch.complex64,
        )
        if object_field.ndim == 3:
            object_field = object_field.unsqueeze(0)
        if object_field.ndim != 4 or object_field.shape[-3] != 1:
            raise invalid_restoration_contract(
                "scene object_field must resolve to [batch, 1, height, width]"
            )
        return (
            object_field,
            scene.aberration_phase_radians.to(
                device=self.device,
                dtype=torch.float32,
            ),
            scene.pupil.to(device=self.device, dtype=torch.float32),
        )


class SimulatedBench:
    """Hide one persistent same-device aberration behind the bench seam.

    The policy can request intensity observations under phase commands, but it
    cannot retrieve the injected phase or the simulated complex fields.
    """

    __slots__ = (
        "_bench",
        "_calibration_id",
        "_composite_states",
        "_frame_interval_s",
        "_hidden_baseline_delivery",
        "_hidden_phase",
        "_reachability",
        "_scene",
    )

    def __init__(
        self,
        bench_config: OpticalBenchConfig,
        phase_delivery: PhaseDelivery,
        displayed_replay_intensity: torch.Tensor,
        hidden_aberration_phase_radians: torch.Tensor,
        pupil: torch.Tensor,
        *,
        calibration_id: str,
        photon_count: float | None = None,
        read_noise_standard_deviation: float = 0.0,
        seed: int = 2026,
        frame_interval_s: float = 1.0 / 60.0,
        device: torch.device | str = "cpu",
    ) -> None:
        interval = finite_real("frame_interval_s", frame_interval_s)
        if interval <= 0.0:
            raise invalid_restoration_contract("frame_interval_s must be positive")
        if not isinstance(calibration_id, str) or not calibration_id.strip():
            raise invalid_restoration_contract("calibration_id must be non-empty")
        replay_intensity = _displayed_replay_intensity(
            displayed_replay_intensity,
            resolution=bench_config.input_array_resolution,
        )
        replay_input_field = torch.sqrt(replay_intensity).to(torch.complex64)
        self._bench = CoherentPupilBench(
            bench_config,
            phase_delivery,
            photon_count=photon_count,
            read_noise_standard_deviation=read_noise_standard_deviation,
            seed=seed,
            device=device,
        )
        emulator_scene = CoherentPupilScene(
            replay_input_field,
            hidden_aberration_phase_radians,
            pupil,
        )
        self._hidden_phase = emulator_scene.aberration_phase_radians
        self._scene = CoherentPupilScene(
            emulator_scene.object_field,
            torch.zeros_like(self._hidden_phase),
            emulator_scene.pupil,
        )
        self._hidden_baseline_delivery = phase_delivery.deliver(
            PhaseCommand(
                "same-device-hidden-baseline",
                self._hidden_phase,
            ),
            pupil=self._scene.pupil,
        )
        self._composite_states: list[SameDeviceCompositeState] = []
        self._reachability = CalibratedReplayReachability(
            replay_intensity,
            bench_config,
            pupil,
            phase_delivery,
            calibration_id=calibration_id,
            device=device,
        )
        self._calibration_id = calibration_id
        self._frame_interval_s = interval

    @property
    def calibration_id(self) -> str:
        """Return the calibration identity shared by acquisition and prediction."""
        return self._calibration_id

    @torch.no_grad()
    def acquire(
        self,
        command: PhaseCommand,
        *,
        observation_id: str,
        kind: ObservationKind,
        sequence_index: int,
        is_reference_enabled: bool = True,
    ) -> OpticalObservation:
        """Acquire intensity without exposing the bound evaluator state."""
        composite_command = PhaseCommand(
            f"{command.command_id}-physical-composite",
            self._hidden_phase.to(command.phase_radians.device) + command.phase_radians,
            piston_radians=command.piston_radians,
        )
        composite_delivery = self._bench.phase_delivery.deliver(
            composite_command,
            pupil=self._scene.pupil.to(command.phase_radians.device),
        )
        visible_delivery = _differential_delivery_view(
            command,
            composite_delivery,
            self._hidden_baseline_delivery,
        )
        observation = self._bench._acquire_with_delivery(
            self._scene,
            command,
            observation_id=observation_id,
            kind=kind,
            sequence_index=sequence_index,
            is_reference_enabled=is_reference_enabled,
            elapsed_time_s=(sequence_index + 1) * self._frame_interval_s,
            physical_delivery=composite_delivery,
            visible_delivery=visible_delivery,
        )
        self._composite_states.append(
            SameDeviceCompositeState(
                observation_id=observation_id,
                command=composite_command,
                delivery=composite_delivery,
            )
        )
        return replace(
            observation,
            metadata={
                **observation.metadata,
                "calibration_id": self._calibration_id,
                "camera_read_count": 1,
                "exposure_dose": self._bench.photon_count or 0.0,
                "settling_time_s": 0.0,
                "transfer_time_s": 0.0,
                "emulator_mode": "same_device_differential_aberration",
                "displayed_phase_composition": (
                    "hidden_aberration_plus_action_plus_piston_delivered_once"
                ),
            },
        )

    def read_evaluator_composite_states(
        self,
    ) -> tuple[SameDeviceCompositeState, ...]:
        """Return complete SLM2 states for evaluator evidence, never policy input."""
        return tuple(self._composite_states)

    def propose_correction(
        self,
        observations: Sequence[OpticalObservation],
        displayed_replay_intensity: torch.Tensor,
        policy: AdaptiveEpisodePolicy,
        *,
        command_id: str,
    ) -> DeliveredCorrectionProposal:
        """Infer and project one action using this Adapter's calibration."""
        return self._reachability.propose_correction(
            observations,
            displayed_replay_intensity,
            policy,
            command_id=command_id,
        )


def _displayed_replay_intensity(
    value: torch.Tensor,
    *,
    resolution: tuple[int, int],
) -> torch.Tensor:
    if (
        not isinstance(value, torch.Tensor)
        or value.ndim != 3
        or value.shape[0] != 1
        or tuple(value.shape[-2:]) != resolution
        or torch.is_complex(value)
        or not bool(torch.isfinite(value).all())
        or bool(torch.any(value < 0.0))
    ):
        raise invalid_restoration_contract(
            "displayed_replay_intensity must be a finite nonnegative [1, height, width] tensor matching the bench"
        )
    return value.to(dtype=torch.float32).detach().clone()


def _differential_delivery_view(
    command: PhaseCommand,
    composite_delivery: DeliveredPhaseState,
    hidden_baseline_delivery: DeliveredPhaseState,
) -> DeliveredPhaseState:
    composite_spatial_phase = (
        composite_delivery.phase_radians - composite_delivery.piston_radians
    )
    hidden_spatial_phase = (
        hidden_baseline_delivery.phase_radians - hidden_baseline_delivery.piston_radians
    ).to(composite_spatial_phase.device)
    differential_spatial_phase = torch.angle(
        torch.exp(1j * (composite_spatial_phase - hidden_spatial_phase))
    )
    return DeliveredPhaseState(
        command_id=command.command_id,
        phase_radians=(differential_spatial_phase + composite_delivery.piston_radians),
        piston_radians=composite_delivery.piston_radians,
        delivery_model=(
            f"{composite_delivery.delivery_model}_same_device_differential_view"
        ),
        metadata={
            **dict(composite_delivery.metadata),
            "phase_view": "differential_from_hidden_baseline",
            "physical_delivery_model": composite_delivery.delivery_model,
            "is_spatial_piston_separable": composite_delivery.metadata.get(
                "is_spatial_piston_separable",
                False,
            ),
        },
    )
