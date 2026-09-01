from __future__ import annotations

import copy
import io

import pytest
import torch

from chromatix_next import (
    Workstation,
    _execution_memory,
    _state_installation,
    install_state,
)
from chromatix_next.errors import OpticalError, OpticalRuntimeError, WorkstationError
from chromatix_next.optics import Assembly
from chromatix_next.optics._meta_inference import (
    _DIRECTIONAL_METADATA_STORAGE_IDS,
    _meta_inference,
    _MetaFactoryGuard,
)
from chromatix_next.optics.element.ideal_cube_beam_splitter import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
)
from chromatix_next.optics.element.ideal_planar_mirror import (
    IdealPlanarMirror,
    MirrorTerminal,
)
from chromatix_next.optics.field import _SourceLineage
from chromatix_next.optics.ray_bundle import RayBundle
from chromatix_next.workstation import NamedOutputs
from tests.assembly import test_ray_cube_encounters as _ray_fixtures
from tests.assembly import test_wave_cube_encounters as _wave_fixtures


def _cube(
    *,
    mixing_angle: float | torch.Tensor | torch.nn.Parameter = 0.37,
) -> IdealNonpolarizingCubeBeamSplitter:
    return IdealNonpolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=mixing_angle,
    )


def _wave_assembly(
    *,
    encounter_count: int = 1,
    sample_counts: tuple[int, int] = (4, 5),
    end_reflection: bool = False,
    owner: (
        IdealNonpolarizingCubeBeamSplitter
        | IdealPolarizingCubeBeamSplitter
        | None
    ) = None,
) -> Assembly:
    assembly = Assembly()
    resolved_owner = _cube() if owner is None else owner
    lineage = _SourceLineage()
    assembly.include_directional(resolved_owner, name="cube")
    for index in range(encounter_count):
        source = _wave_fixtures._source(
            _wave_fixtures._constant_envelope(
                sample_counts=sample_counts,
            ),
            lineage=lineage,
        )
        assembly.include(
            source,
            name=f"source_{index}",
            grid=_wave_fixtures._grid(sample_counts=sample_counts),
        )
        encounter = assembly.wave_encounter(
            resolved_owner,
            name=f"cube_use_{index}",
            incident_terminals=(CubeTerminal.LEFT,),
        )
        assembly.connect(
            source,
            encounter,
            destination_terminal=CubeTerminal.LEFT,
        )
        assembly.expose(
            encounter,
            name=f"right_{index}",
            source_terminal=CubeTerminal.RIGHT,
        )
        if end_reflection:
            assembly.end_route(
                encounter,
                source_terminal=CubeTerminal.TOP,
                reason="outside_modeled_system",
            )
        else:
            assembly.expose(
                encounter,
                name=f"top_{index}",
                source_terminal=CubeTerminal.TOP,
            )
    assembly.freeze()
    return assembly


def _mirror_wave_assembly() -> Assembly:
    owner = IdealPlanarMirror(
        origin=(0.0, 0.0, 0.0),
        outward_normal=(0.0, 0.0, -1.0),
        transverse_up=(0.0, 1.0, 0.0),
    )
    source = _wave_fixtures._source(
        _wave_fixtures._constant_envelope(sample_counts=(4, 5)),
        lineage=_SourceLineage(),
    )
    assembly = Assembly()
    assembly.include(
        source,
        name="source",
        grid=_wave_fixtures._grid(sample_counts=(4, 5)),
    )
    assembly.include_directional(owner, name="mirror")
    encounter = assembly.wave_encounter(
        owner,
        name="mirror_turn",
        incident_terminals=(MirrorTerminal.FRONT,),
    )
    assembly.connect(
        source,
        encounter,
        destination_terminal=MirrorTerminal.FRONT,
    )
    assembly.expose(
        encounter,
        name="reflected",
        source_terminal=MirrorTerminal.FRONT,
    )
    assembly.freeze()
    return assembly


def _polarizing_cube() -> IdealPolarizingCubeBeamSplitter:
    return IdealPolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
    )


def _frozen_directional_assembly(owner_kind: str) -> Assembly:
    if owner_kind == "nbs":
        return _wave_assembly()
    if owner_kind == "pbs":
        return _wave_assembly(owner=_polarizing_cube())
    return _mirror_wave_assembly()


def _ray_assembly(*, lane_count: int = 8) -> Assembly:
    base = _ray_fixtures._central_bundle(CubeTerminal.LEFT)

    def repeated(value: torch.Tensor) -> torch.Tensor:
        repetitions = [1, lane_count] + [1] * (value.ndim - 2)
        return value.repeat(*repetitions)

    bundle = RayBundle(
        position=repeated(base.position),
        direction=repeated(base.direction),
        polarization_vector=repeated(base.polarization_vector),
        power=repeated(base.power),
        refractive_index=repeated(base.refractive_index),
        optical_path=repeated(base.optical_path),
        status=repeated(base.status),
        spectrum=base.spectrum,
    )
    source = _ray_fixtures._ReplayRaySource(bundle)
    owner = _cube()
    assembly = Assembly()
    assembly.include(source, name="source", grid=_ray_fixtures._grid())
    assembly.include_directional(owner, name="cube")
    encounter = assembly.ray_encounter(
        owner,
        name="cube_use",
        incident_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        source,
        encounter,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.expose(
        encounter,
        name="right",
        source_terminal=CubeTerminal.RIGHT,
    )
    assembly.expose(
        encounter,
        name="top",
        source_terminal=CubeTerminal.TOP,
    )
    assembly.freeze()
    return assembly


def _state_root() -> torch.nn.Module:
    root = torch.nn.Module()
    root.add_module("nbs", _cube())
    root.add_module(
        "pbs",
        IdealPolarizingCubeBeamSplitter(
            origin=(0.0, 0.0, 0.0),
            route_right=(1.0, 0.0, 0.0),
            route_top=(0.0, 1.0, 0.0),
            coating_diagonal=CubeCoatingDiagonal.FALLING,
        ),
    )
    root.add_module(
        "mirror",
        IdealPlanarMirror(
            origin=(0.0, 0.0, 0.0),
            outward_normal=(0.0, 0.0, -1.0),
            transverse_up=(0.0, 1.0, 0.0),
        ),
    )
    return root


def _cloned_state(root: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {
        name: value.detach().clone()
        for name, value in root.state_dict().items()
    }


def _assert_state_equal(
    root: torch.nn.Module,
    expected: dict[str, torch.Tensor],
) -> None:
    actual = root.state_dict()
    assert tuple(actual) == tuple(expected)
    for name, value in expected.items():
        assert torch.equal(actual[name], value)


def _measure(
    assembly: Assembly,
    workstation: Workstation,
) -> tuple[int, tuple[int, ...], int, tuple[int, ...]]:
    request = workstation._prepare_replay_request(  # noqa: SLF001
        assembly,
        root=None,
        inputs=None,
    )
    meta_peak, meta_trace, meta_schema = (
        workstation._measure_meta_replay(  # noqa: SLF001
            request,
            seed=42,
        )
    )
    _outputs, real_peak, real_trace, real_schema = (
        workstation._measure_real_replay(  # noqa: SLF001
            request,
            seed=42,
        )
    )
    assert meta_schema == real_schema
    return meta_peak, meta_trace, real_peak, real_trace


def test_one_owner_state_and_lifetime_facts_ignore_encounter_count() -> None:
    one = _wave_assembly(encounter_count=1, end_reflection=True)
    three = _wave_assembly(encounter_count=3, end_reflection=True)
    one_owner_keys = tuple(
        name for name in one.state_dict() if name.startswith("cube.")
    )
    three_owner_keys = tuple(
        name for name in three.state_dict() if name.startswith("cube.")
    )
    assert one_owner_keys == three_owner_keys
    assert all("cube_use" not in name for name in three.state_dict())
    assert _execution_memory._owned_memory_bytes((_cube(),) * 3) == (
        _execution_memory._owned_memory_bytes((_cube(),))
    )
    validation_reserves: list[int] = []
    workstation = Workstation.cpu()
    for assembly in (one, three):
        workstation.host(assembly)
        owned = _execution_memory._owned_memory_bytes(
            tuple(assembly.modules()),
        )
        meta_peak, meta_trace, real_peak, _real_trace = _measure(
            assembly,
            workstation,
        )
        validation_reserves.append(meta_peak - owned - meta_trace[-1])
        assert real_peak <= meta_peak
        workstation.release(assembly)
    assert validation_reserves[0] == validation_reserves[1]

    facts = three._execution_facts()  # noqa: SLF001
    exposed = {exposure.value for exposure in facts.directional_exposures}
    released = {release.value for release in facts.releases}
    assert exposed.isdisjoint(released)
    for disposition in facts.dispositions:
        if disposition.exposure_names:
            assert disposition.value not in released
        elif disposition.route_end_reason is not None:
            assert disposition.value in released
    assert len(facts.encounters) == 3
    assert len(facts.route_ends) == 3
    assert facts.ancestry


def test_deepcopy_and_save_load_resolve_owner_by_stable_name() -> None:
    original = _wave_assembly(encounter_count=2)
    copied = copy.deepcopy(original)
    buffer = io.BytesIO()
    torch.save(original, buffer)
    buffer.seek(0)
    loaded = torch.load(buffer, weights_only=False)

    original_owner = original._component("cube")  # noqa: SLF001
    for restored in (copied, loaded):
        restored_owner = restored._component("cube")  # noqa: SLF001
        assert restored_owner is not original_owner
        facts = restored._execution_facts()  # noqa: SLF001
        assert {fact.owner_name for fact in facts.encounters} == {"cube"}
        before = restored._replay()["right_0"].envelope  # noqa: SLF001
        with torch.no_grad():
            restored_owner.mixing_angle.fill_(0.0)
        after = restored._replay()["right_0"].envelope  # noqa: SLF001
        assert not torch.equal(before, after)
        assert float(original_owner.mixing_angle) == pytest.approx(0.37)


@pytest.mark.parametrize(
    ("invalid_name", "invalid_value"),
    (
        ("nbs.origin", torch.zeros(3, dtype=torch.float32)),
        ("mirror.origin", torch.zeros(4, dtype=torch.float64)),
        ("pbs._coating_diagonal_code", torch.tensor(2, dtype=torch.uint8)),
        (
            "mirror.outward_normal",
            torch.tensor((0.0, 0.0, -2.0), dtype=torch.float64),
        ),
    ),
)
def test_directional_state_installation_rejects_atomically(
    invalid_name: str,
    invalid_value: torch.Tensor,
) -> None:
    target = _state_root()
    baseline = _cloned_state(target)
    donor = _cloned_state(target)
    donor["nbs.mixing_angle"] = torch.tensor(0.91, dtype=torch.float64)
    donor[invalid_name] = invalid_value

    with pytest.raises(OpticalError):
        install_state(target, donor)

    _assert_state_equal(target, baseline)


@pytest.mark.parametrize(
    ("owner_kind", "state_name", "replacement"),
    (
        (
            "nbs",
            "cube.origin",
            torch.tensor((1.0e-3, 0.0, 0.0), dtype=torch.float64),
        ),
        (
            "nbs",
            "cube.route_right",
            torch.tensor((0.0, 0.0, 1.0), dtype=torch.float64),
        ),
        (
            "nbs",
            "cube.route_top",
            torch.tensor((0.0, 0.0, 1.0), dtype=torch.float64),
        ),
        (
            "nbs",
            "cube._coating_diagonal_code",
            torch.tensor(1, dtype=torch.uint8),
        ),
        (
            "pbs",
            "cube._coating_diagonal_code",
            torch.tensor(1, dtype=torch.uint8),
        ),
        (
            "mirror",
            "mirror.origin",
            torch.tensor((0.0, 0.0, 1.0e-3), dtype=torch.float64),
        ),
        (
            "mirror",
            "mirror.outward_normal",
            torch.tensor((1.0, 0.0, 0.0), dtype=torch.float64),
        ),
        (
            "mirror",
            "mirror.transverse_up",
            torch.tensor((1.0, 0.0, 0.0), dtype=torch.float64),
        ),
    ),
)
def test_frozen_directional_fixed_state_rejects_before_native_copy(
    owner_kind: str,
    state_name: str,
    replacement: torch.Tensor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _frozen_directional_assembly(owner_kind)
    baseline = _cloned_state(target)
    donor = _cloned_state(target)
    donor[state_name] = replacement
    native_load_count = 0
    native_load = _state_installation._run_native_state_load  # noqa: SLF001

    def observed_native_load(
        root: torch.nn.Module,
        state_dict: dict[str, torch.Tensor],
    ) -> None:
        nonlocal native_load_count
        native_load_count += 1
        native_load(root, state_dict)

    monkeypatch.setattr(
        _state_installation,
        "_run_native_state_load",
        observed_native_load,
    )

    with pytest.raises(OpticalRuntimeError) as captured:
        install_state(target, donor)

    assert captured.value.identity == (
        "state_installation_frozen_directional_state_mismatch"
    )
    assert "新 Assembly" in captured.value.explanation
    assert native_load_count == 0
    _assert_state_equal(target, baseline)


def test_nested_frozen_cube_rejection_is_atomic_and_reenterable() -> None:
    assembly = _wave_assembly()
    unchanged_assembly = _mirror_wave_assembly()
    target = torch.nn.Module()
    target.add_module("unchanged", unchanged_assembly)
    target.add_module("program", assembly)
    owner = assembly._component("cube")  # noqa: SLF001
    facts = assembly._execution_facts()  # noqa: SLF001
    unchanged_facts = unchanged_assembly._execution_facts()  # noqa: SLF001
    baseline = _cloned_state(target)
    baseline_outputs = {
        name: value.envelope.detach().clone()
        for name, value in assembly._replay().items()  # noqa: SLF001
    }
    donor = _cloned_state(target)
    donor["program.source_0.envelope"] = (
        2.0 * donor["program.source_0.envelope"]
    )
    donor["program.cube._coating_diagonal_code"] = torch.tensor(
        1,
        dtype=torch.uint8,
    )
    donor["program.cube.mixing_angle"] = torch.tensor(
        0.91,
        dtype=torch.float64,
    )

    with pytest.raises(OpticalRuntimeError) as captured:
        install_state(target, donor)

    assert captured.value.identity == (
        "state_installation_frozen_directional_state_mismatch"
    )
    _assert_state_equal(target, baseline)
    assert assembly.is_frozen
    assert assembly._component("cube") is owner  # noqa: SLF001
    assert assembly._execution_facts() is facts  # noqa: SLF001
    assert unchanged_assembly._execution_facts() is unchanged_facts  # noqa: SLF001
    after_outputs = assembly._replay()  # noqa: SLF001
    for name, expected in baseline_outputs.items():
        assert torch.equal(after_outputs[name].envelope, expected)

    install_state(target, baseline)
    workstation = Workstation.cpu()
    workstation.host(assembly)
    try:
        outputs, _record = workstation.run(assembly)
        for name, expected in baseline_outputs.items():
            assert torch.equal(outputs[name].envelope, expected)
    finally:
        workstation.release(assembly)


def test_same_fixed_state_mixing_angle_install_keeps_gradient() -> None:
    mixing_angle = torch.nn.Parameter(
        torch.tensor(0.37, dtype=torch.float64),
    )
    assembly = _wave_assembly(owner=_cube(mixing_angle=mixing_angle))
    owner = assembly._component("cube")  # noqa: SLF001
    parameter_identity = id(owner.mixing_angle)
    fixed_names = (
        "origin",
        "route_right",
        "route_top",
        "_coating_diagonal_code",
    )
    fixed_state = {
        name: getattr(owner, name).detach().clone()
        for name in fixed_names
    }
    donor = _cloned_state(assembly)
    donor["cube.mixing_angle"] = torch.tensor(0.91, dtype=torch.float64)

    install_state(assembly, donor)

    assert id(owner.mixing_angle) == parameter_identity
    assert float(owner.mixing_angle.detach()) == pytest.approx(0.91)
    for name, expected in fixed_state.items():
        assert torch.equal(getattr(owner, name), expected)
    workstation = Workstation.cpu()
    workstation.host(assembly)
    try:
        outputs, _record = workstation.run(assembly)
        loss = outputs["right_0"].envelope.real.square().sum()
        loss.backward()
        assert owner.mixing_angle.grad is not None
        assert bool(torch.isfinite(owner.mixing_angle.grad))
        assert float(owner.mixing_angle.grad.abs()) > 0.0
    finally:
        workstation.release(assembly)


@pytest.mark.parametrize(
    ("owner_kind", "unfrozen_assembly"),
    (
        ("cube", False),
        ("cube", True),
        ("mirror", False),
        ("mirror", True),
    ),
)
def test_unfrozen_directional_fixed_state_remains_installable(
    owner_kind: str,
    unfrozen_assembly: bool,
) -> None:
    if owner_kind == "cube":
        target_owner = _cube()
        donor_owner: torch.nn.Module = IdealNonpolarizingCubeBeamSplitter(
            origin=(1.0e-3, 0.0, 0.0),
            route_right=(0.0, 0.0, 1.0),
            route_top=(0.0, 1.0, 0.0),
            coating_diagonal=CubeCoatingDiagonal.FALLING,
            mixing_angle=0.91,
        )
    else:
        target_owner = IdealPlanarMirror(
            origin=(0.0, 0.0, 0.0),
            outward_normal=(0.0, 0.0, -1.0),
            transverse_up=(0.0, 1.0, 0.0),
        )
        donor_owner = IdealPlanarMirror(
            origin=(0.0, 0.0, 1.0e-3),
            outward_normal=(1.0, 0.0, 0.0),
            transverse_up=(0.0, 1.0, 0.0),
        )
    if unfrozen_assembly:
        target = Assembly()
        target.include_directional(target_owner, name="owner")
        donor = Assembly()
        donor.include_directional(donor_owner, name="owner")
    else:
        target = target_owner
        donor = donor_owner
    expected_state = _cloned_state(donor)

    install_state(target, donor.state_dict())

    _assert_state_equal(target, expected_state)
    if isinstance(target, Assembly):
        assert not target.is_frozen


def test_directional_meta_snapshot_is_exact_readonly_and_temporary() -> None:
    owner = _cube()
    owner.register_buffer(
        "unlisted_geometry",
        torch.ones(3, dtype=torch.float64),
    )
    owner.register_buffer(
        "unlisted_topology",
        torch.ones(3, dtype=torch.uint8),
    )
    owner.register_buffer(
        "unlisted_precision",
        torch.ones((), dtype=torch.float32),
    )
    state_keys = tuple(owner.state_dict())
    with _meta_inference(tuple(owner.modules())) as sandbox:
        isolated = sandbox.module(owner)
        assert isolated.origin.device.type == "cpu"
        assert isolated.route_right.device.type == "cpu"
        assert isolated._coating_diagonal_code.device.type == "cpu"
        assert isolated.mixing_angle.is_meta
        assert isolated.unlisted_geometry.is_meta
        assert isolated.unlisted_topology.is_meta
        assert isolated.unlisted_precision.is_meta
        copied_origin = isolated.origin.to(
            device="cpu",
            dtype=torch.float64,
            copy=True,
        )
        assert torch.equal(copied_origin, isolated.origin)
        with pytest.raises(OpticalRuntimeError):
            torch.empty((), dtype=torch.uint8, device="cpu")
        with pytest.raises(OpticalRuntimeError):
            torch.zeros((1,), dtype=torch.uint8, device="cpu")
        with pytest.raises(OpticalRuntimeError):
            torch.zeros((), dtype=torch.float64, device="cpu")
        with pytest.raises(OpticalRuntimeError):
            isolated.origin.add_(1.0)
    assert not _DIRECTIONAL_METADATA_STORAGE_IDS.get()
    assert tuple(owner.state_dict()) == state_keys

    with pytest.raises(OpticalRuntimeError):
        with _meta_inference(tuple(owner.modules())) as sandbox:
            isolated = sandbox.module(owner)
            isolated._buffers["origin"] = isolated.route_right
    assert not _DIRECTIONAL_METADATA_STORAGE_IDS.get()

    with pytest.raises(RuntimeError, match="probe"):
        with _meta_inference(tuple(owner.modules())):
            raise RuntimeError("probe")
    assert not _DIRECTIONAL_METADATA_STORAGE_IDS.get()
    with torch.device("meta"), _MetaFactoryGuard():
        with pytest.raises(OpticalRuntimeError):
            torch.ones((), dtype=torch.uint8, device="cpu")


def test_meta_sandbox_only_projects_fixed_real_inputs_to_meta() -> None:
    owner = _cube()
    real_scalar = torch.tensor(2.0, dtype=torch.float64)
    real_vector = torch.ones(4, dtype=torch.complex128)
    real_topology = torch.ones((), dtype=torch.uint8)
    with _meta_inference(tuple(owner.modules())):
        scalar_projection = real_scalar.to(
            device="meta",
            dtype=torch.float64,
        )
        vector_projection = real_vector.to(
            device="meta",
            dtype=torch.complex128,
        )
        assert scalar_projection.is_meta
        assert scalar_projection.shape == real_scalar.shape
        assert scalar_projection.dtype is real_scalar.dtype
        assert vector_projection.is_meta
        assert vector_projection.shape == real_vector.shape
        assert vector_projection.dtype is real_vector.dtype
        with pytest.raises(OpticalRuntimeError):
            real_scalar.to(device="meta", dtype=torch.float32)
        with pytest.raises(OpticalRuntimeError):
            real_topology.to(device="meta")
        with pytest.raises(OpticalRuntimeError):
            real_scalar.add(1.0)
        with pytest.raises(OpticalRuntimeError):
            real_scalar.item()
        with pytest.raises(OpticalRuntimeError):
            real_scalar.to(device="cpu", dtype=torch.float64, copy=True)


def test_cpu_meta_real_memory_and_ray_are_closed() -> None:
    wave = _wave_assembly(sample_counts=(4, 5))
    workstation = Workstation.cpu()
    workstation.host(wave)
    owned = _execution_memory._owned_memory_bytes(tuple(wave.modules()))
    meta_peak, meta_trace, real_peak, _real_trace = _measure(
        wave,
        workstation,
    )
    assert meta_trace[-1] + owned < real_peak
    assert real_peak <= meta_peak
    outputs, record = workstation.run(wave)
    assert tuple(outputs) == ("right_0", "top_0")
    assert record.peak_memory_bytes == meta_peak
    for value in outputs.values():
        assert value.envelope.device.type == "cpu"
        assert value.envelope.dtype is torch.complex128
    workstation.release(wave)

    ray = _ray_assembly(lane_count=8)
    workstation.host(ray)
    ray_owned = _execution_memory._owned_memory_bytes(tuple(ray.modules()))
    ray_meta, ray_trace, ray_real, _ray_real_trace = _measure(
        ray,
        workstation,
    )
    assert ray_meta == ray_owned + ray_trace[-1]
    assert ray_real <= ray_meta
    ray_outputs, _record = workstation.run(ray)
    for value in ray_outputs.values():
        assert value.position.dtype is torch.float64
        assert value.polarization_vector.dtype is torch.complex128
    workstation.release(ray)


def test_failed_host_and_run_are_atomic_and_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assembly = _wave_assembly()
    owner = assembly._component("cube")  # noqa: SLF001
    workstation = Workstation.cpu()
    original_origin = owner.origin
    owner._buffers["origin"] = original_origin.to(torch.float32)
    with pytest.raises(WorkstationError):
        workstation.host(assembly)
    owner._buffers["origin"] = original_origin
    workstation.host(assembly)

    publications = 0
    original_publication = NamedOutputs._from_run  # noqa: SLF001

    def publish(
        cls: type[NamedOutputs],
        values: tuple[tuple[str, object], ...],
    ) -> NamedOutputs:
        del cls
        nonlocal publications
        publications += 1
        return original_publication(values)  # type: ignore[arg-type]

    monkeypatch.setattr(NamedOutputs, "_from_run", classmethod(publish))
    with torch.no_grad():
        owner.mixing_angle.fill_(float("nan"))
    with pytest.raises(OpticalError):
        workstation.run(assembly)
    assert publications == 0
    with torch.no_grad():
        owner.mixing_angle.fill_(0.37)
    workstation.run(assembly)
    assert publications == 1
    workstation.release(assembly)
    workstation.host(assembly)
    workstation.run(assembly)
    assert publications == 2
    workstation.release(assembly)


def test_directional_owner_cannot_be_hosted_or_run_standalone() -> None:
    owner = _cube()
    workstation = Workstation.cpu()
    with pytest.raises(WorkstationError) as rejected:
        workstation.host(owner)
    assert rejected.value.identity == "optical_component_role_invalid"
    with pytest.raises(WorkstationError):
        workstation.run(owner)  # type: ignore[arg-type]


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="directional Workstation evidence requires a native CUDA device",
)
def test_windows_cuda_uses_fixed_double_without_fallback() -> None:
    assembly = _wave_assembly(sample_counts=(4, 5))
    workstation = Workstation.cuda(0)
    workstation.host(assembly)
    try:
        outputs, _record = workstation.run(assembly)
        assert workstation.device == torch.device("cuda", 0)
        for value in outputs.values():
            assert value.envelope.device == torch.device("cuda", 0)
            assert value.envelope.dtype is torch.complex128
        owner = assembly._component("cube")  # noqa: SLF001
        assert owner.origin.device == torch.device("cuda", 0)
        assert owner.origin.dtype is torch.float64
        assert owner.mixing_angle.device == torch.device("cuda", 0)
        assert owner.mixing_angle.dtype is torch.float64
    finally:
        workstation.release(assembly)
