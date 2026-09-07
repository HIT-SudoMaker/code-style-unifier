
from __future__ import annotations

from typing import Literal

import pytest
import torch

from chromatix_next.errors import AssemblyError, OpticalError
from chromatix_next.optics import (
    Assembly,
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PolarizationRepresentation,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.propagation import (
    AplanaticFocus,
    FresnelTransform,
    ScalableAngularSpectrum,
    ScalarAngularSpectrum,
    ScaledAngularSpectrum,
    ScaledFresnel,
    VectorAngularSpectrum,
)
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


def _assembly_grid() -> SpatialGrid:
    # 平面波在该网格与波长下满足采样，并足够支撑各方法的目标几何
    return SpatialGrid.centered(
        sample_counts=(16, 16),
        sample_spacing=(1.0e-6, 1.0e-6),
    )


def _wavelength() -> float:
    return 2.0e-6


def _scaled_destination() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(12, 12),
        sample_spacing=(1.0e-6, 1.0e-6),
    )


def _aplanatic_destination() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(3, 3),
        sample_spacing=(0.2e-6, 0.2e-6),
    )


def _make_component(kind: str) -> torch.nn.Module:
    # 按方法键构造对应传播组件
    if kind == "scalar_angular_spectrum":
        return ScalarAngularSpectrum(axial_distance=1.0e-6)
    if kind == "fresnel_transform":
        return FresnelTransform(axial_distance=20.0e-3)
    if kind == "scaled_angular_spectrum":
        return ScaledAngularSpectrum(
            axial_distance=1.1e-6,
            destination_grid=_scaled_destination(),
        )
    if kind == "scaled_fresnel":
        return ScaledFresnel(
            axial_distance=400.0e-6,
            destination_grid=_scaled_destination(),
        )
    if kind == "scalable_angular_spectrum":
        return ScalableAngularSpectrum(
            axial_distance=550.0e-6,
            destination_grid=_scaled_destination(),
        )
    if kind == "vector_angular_spectrum":
        return VectorAngularSpectrum(axial_distance=0.5e-6)
    return AplanaticFocus(
        focal_length=8.0e-6,
        maximum_convergence_angle=0.3,
        axial_distance_from_focus=0.0,
        destination_grid=_aplanatic_destination(),
    )


def _make_source(representation: PolarizationRepresentation) -> PlaneWave:
    # 按被拒表示作者对应偏振的平面波源
    if representation is PolarizationRepresentation.SCALAR:
        polarization = Polarization.scalar()
    elif representation is PolarizationRepresentation.FULL:
        polarization = Polarization.full(components=(1.0, 0.0, 0.0))
    else:
        polarization = Polarization.linear_x()
    return PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=_wavelength()),
        polarization=polarization,
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )


# 表示门控拒绝场景：标签、裸身份、被拒表示、传播组件方法键
_REJECTION_SCENARIOS = [
    (
        "scalar_as_full",
        "scalar_angular_spectrum_polarization_full_unsupported",
        PolarizationRepresentation.FULL,
        "scalar_angular_spectrum",
    ),
    (
        "fresnel_full",
        "fresnel_transform_polarization_full_unsupported",
        PolarizationRepresentation.FULL,
        "fresnel_transform",
    ),
    (
        "scaled_as_full",
        "scaled_angular_spectrum_polarization_full_unsupported",
        PolarizationRepresentation.FULL,
        "scaled_angular_spectrum",
    ),
    (
        "scaled_fresnel_full",
        "scaled_fresnel_polarization_full_unsupported",
        PolarizationRepresentation.FULL,
        "scaled_fresnel",
    ),
    (
        "scalable_as_full",
        "scalable_angular_spectrum_polarization_full_unsupported",
        PolarizationRepresentation.FULL,
        "scalable_angular_spectrum",
    ),
    (
        "vector_as_scalar",
        "vector_angular_spectrum_polarization_scalar_unsupported",
        PolarizationRepresentation.SCALAR,
        "vector_angular_spectrum",
    ),
    (
        "aplanatic_scalar",
        "aplanatic_focus_polarization_unsupported",
        PolarizationRepresentation.SCALAR,
        "aplanatic_focus",
    ),
    (
        "aplanatic_full",
        "aplanatic_focus_polarization_unsupported",
        PolarizationRepresentation.FULL,
        "aplanatic_focus",
    ),
]


def _rejected_field(
    representation: PolarizationRepresentation,
    *,
    device: torch.device | str | None = None,
) -> OpticalField:
    # 直接与 meta 路径用：构造被拒表示的光场
    grid = _assembly_grid()
    counts_y, counts_x = grid.sample_counts
    envelope = torch.ones(
        (1, representation.component_count, counts_y, counts_x),
        dtype=torch.complex128,
        device=device,
    )
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=Spectrum.monochromatic(wavelength=_wavelength()),
        polarization_representation=representation,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )


_COMPONENT_NAME = "propagation"


def _build_assembly(
    scenario: tuple[str, str, PolarizationRepresentation, str],
) -> Assembly:
    # 装配检查与工作站路径共用：平面波源直接作者被拒表示
    _label, _identity, representation, kind = scenario
    assembly = Assembly()
    grid = _assembly_grid()
    source = _make_source(representation)
    component = _make_component(kind)
    assembly.include(source, name="source", grid=grid)
    assembly.include(component, name=_COMPONENT_NAME)
    assembly.connect(source, component)
    assembly.expose(component, name="field")
    return assembly


@pytest.mark.parametrize(
    "scenario",
    _REJECTION_SCENARIOS,
    ids=[scenario[0] for scenario in _REJECTION_SCENARIOS],
)
def test_direct_execution_rejects_with_bare_identity(
    scenario: tuple[str, str, PolarizationRepresentation, str],
) -> None:
    """
    直接执行以方法拥有的裸身份拒绝
    """
    _label, identity, _representation, kind = scenario
    component = _make_component(kind)
    with pytest.raises(OpticalError) as caught:
        component(_rejected_field(scenario[2]))
    assert caught.value.identity == identity


@pytest.mark.parametrize(
    "scenario",
    _REJECTION_SCENARIOS,
    ids=[scenario[0] for scenario in _REJECTION_SCENARIOS],
)
def test_meta_inference_rejects_with_bare_identity(
    scenario: tuple[str, str, PolarizationRepresentation, str],
) -> None:
    """
    meta 形状推导路径同样以裸身份拒绝

    表示门控不依赖真实张量值，故在 meta 设备上仍触发。
    """
    _label, identity, representation, kind = scenario
    component = _make_component(kind)
    with pytest.raises(OpticalError) as caught:
        component(_rejected_field(representation, device="meta"))
    assert caught.value.identity == identity


@pytest.mark.parametrize(
    "scenario",
    _REJECTION_SCENARIOS,
    ids=[scenario[0] for scenario in _REJECTION_SCENARIOS],
)
def test_assembly_check_rejects_with_wrapped_identity(
    scenario: tuple[str, str, PolarizationRepresentation, str],
) -> None:
    """
    装配检查把传播拒绝包装为装配包装身份
    """
    _label, identity, _representation, _kind = scenario
    assembly = _build_assembly(scenario)
    with pytest.raises(AssemblyError) as caught:
        assembly.check()
    assert caught.value.identity == (
        f"assembly_propagation_forward_failed:"
        f"{_COMPONENT_NAME}:{identity}"
    )


@pytest.mark.parametrize(
    "scenario",
    _REJECTION_SCENARIOS,
    ids=[scenario[0] for scenario in _REJECTION_SCENARIOS],
)
def test_workstation_pipeline_rejects_with_wrapped_identity(
    scenario: tuple[str, str, PolarizationRepresentation, str],
) -> None:
    """
    工作站管道把传播拒绝包装为同一装配包装身份

    工作站的托管与运行管道要求装配先冻结；冻结与装配检查共用同一 meta 推导重放，
    故表示门控拒绝在进入真实重放前即以同一包装身份拒绝——证明无法借工作站绕过
    方法拥有的偏振适用性契约。
    """
    _label, identity, _representation, _kind = scenario
    assembly = _build_assembly(scenario)
    workstation = Workstation.cpu()
    with pytest.raises(AssemblyError) as caught:
        assembly.freeze()
        workstation.host(assembly)
        workstation.run(assembly)
    assert caught.value.identity == (
        f"assembly_propagation_forward_failed:"
        f"{_COMPONENT_NAME}:{identity}"
    )


class _NonTransverseFullSource(torch.nn.Module):
    def __init__(self, *, wavelength: float) -> None:
        """
        建立作者非横向完整矢量光场的扩展 Source
        """
        super().__init__()
        self._wavelength = wavelength

    @property
    def role(self) -> Literal["source"]:
        """
        返回只读 Source 角色
        """
        return "source"

    def forward(
        self,
        grid: SpatialGrid,
        *,
        generator: torch.Generator | None = None,
    ) -> OpticalField:
        """
        构造常幅且纵向分量非零的完整矢量光场
        """
        del generator
        counts_y, counts_x = grid.sample_counts
        envelope = torch.stack(
            (
                torch.ones((counts_y, counts_x), dtype=torch.complex128),
                torch.zeros((counts_y, counts_x), dtype=torch.complex128),
                0.5 * torch.ones((counts_y, counts_x), dtype=torch.complex128),
            ),
        ).unsqueeze(0)
        return OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=Spectrum.monochromatic(wavelength=self._wavelength),
            polarization_representation=PolarizationRepresentation.FULL,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )


def _non_transverse_field(
    *,
    device: torch.device | str | None = None,
) -> OpticalField:
    # 构造常幅、纵向分量非零的完整矢量光场：DC 频箱违反横向约束
    grid = _assembly_grid()
    counts_y, counts_x = grid.sample_counts
    envelope = torch.stack(
        (
            torch.ones((counts_y, counts_x), dtype=torch.complex128),
            torch.zeros((counts_y, counts_x), dtype=torch.complex128),
            0.5 * torch.ones((counts_y, counts_x), dtype=torch.complex128),
        ),
    ).unsqueeze(0).to(device=device)
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=Spectrum.monochromatic(wavelength=_wavelength()),
        polarization_representation=PolarizationRepresentation.FULL,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )


def test_vector_as_full_not_transverse_rejects_on_direct_execution() -> None:
    """
    直接实执行拒绝非横向完整矢量场，裸身份
    """
    component = VectorAngularSpectrum(axial_distance=0.0)
    with pytest.raises(OpticalError) as caught:
        component(_non_transverse_field())
    assert (
        caught.value.identity
        == "vector_angular_spectrum_full_field_not_transverse"
    )


def test_vector_as_full_not_transverse_is_deferred_on_meta() -> None:
    """
    非横向完整性是值检查：meta 形状推导不触发，按设计返回完整表示结构

    这与表示门控拒绝不同：meta 路径没有真实张量值可验证横向约束，故不拒绝；
    仅在真实执行时以稳定身份拒绝。
    """
    component = VectorAngularSpectrum(axial_distance=0.0)
    output = component(_non_transverse_field(device="meta"))
    assert output.polarization_representation is PolarizationRepresentation.FULL
    assert output.envelope.shape[-3] == 3


def test_vector_as_full_not_transverse_rejects_on_workstation() -> None:
    """
    工作站真实重放拒绝非横向完整矢量场，裸身份

    冻结的 meta 推导不触发（值检查），故装配可冻结并进入工作站；真实重放阶段按其
    透传约定以方法拥有裸身份拒绝。自定义源作者该非横向完整场。
    """
    assembly = Assembly()
    grid = _assembly_grid()
    source = _NonTransverseFullSource(wavelength=_wavelength())
    component = VectorAngularSpectrum(axial_distance=0.0)
    assembly.include(source, name="source", grid=grid)
    assembly.include(component, name=_COMPONENT_NAME)
    assembly.connect(source, component)
    assembly.expose(component, name="field")
    assembly.freeze()
    workstation = Workstation.cpu()
    workstation.host(assembly)
    with pytest.raises(OpticalError) as caught:
        workstation.run(assembly)
    assert (
        caught.value.identity
        == "vector_angular_spectrum_full_field_not_transverse"
    )
