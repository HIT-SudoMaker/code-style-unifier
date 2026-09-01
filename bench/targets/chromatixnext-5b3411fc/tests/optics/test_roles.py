from __future__ import annotations

from typing import Literal, cast

import pytest
import torch

from chromatix_next import Workstation
from chromatix_next.errors import AssemblyError, WorkstationError
from chromatix_next.optics import (
    Assembly,
    Intensity,
    OpticalField,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.combination import (
    CoherentCombination,
    Combination,
    IntensityCombination,
)
from chromatix_next.optics.detection import Detection, IntensityDetection
from chromatix_next.optics.element import CircularPupil, Element
from chromatix_next.optics.propagation import Propagation, ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave, Source


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(8, 8),
        sample_spacing=(2.0e-6, 2.0e-6),
    )


def _plane_wave() -> PlaneWave:
    return PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=532.0e-9),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )


class _CustomSource(torch.nn.Module):
    def __init__(self) -> None:
        """
        建立不继承项目基类的扩展 Source
        """
        super().__init__()
        self.source = _plane_wave()

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
        委托真实 PlaneWave 产生 OpticalField
        """
        del generator
        return self.source(grid)


class _AmbiguousRole(torch.nn.Module):
    @property
    def role(self) -> tuple[str, str]:
        """
        返回故意非法的复合角色
        """
        return ("source", "element")

    def forward(self, grid: SpatialGrid) -> OpticalField:
        """
        提供合法 forward 以隔离角色错误
        """
        return _plane_wave()(grid)


class _DishonestRoleAnnotation(torch.nn.Module):
    @property
    def role(self) -> Literal["element"]:
        """
        运行时给出合法 Source 名而返回注解属于另一角色
        """

        return "source"  # type: ignore[reportReturnType]  # 故意类型错配的负向夹具

    def forward(self, grid: SpatialGrid) -> OpticalField:
        """
        提供合法 forward 以隔离 role 注解与运行时值不符的错误
        """
        return _plane_wave()(grid)


class _MissingForward(torch.nn.Module):
    @property
    def role(self) -> Literal["source"]:
        """
        返回 Source 角色但故意缺少 forward
        """
        return "source"


class _WrongAritySource(torch.nn.Module):
    @property
    def role(self) -> Literal["source"]:
        """
        返回 Source 角色
        """
        return "source"

    def forward(self) -> OpticalField:
        """
        提供故意缺少 SpatialGrid 的非法签名
        """
        error_identity = "wrong_arity_source_executed"
        raise AssertionError(error_identity)


class _TensorOutput(torch.nn.Module):
    @property
    def role(self) -> Literal["source"]:
        """
        返回 Source 角色
        """
        return "source"

    def forward(self, grid: SpatialGrid) -> torch.Tensor:
        """
        返回故意非法的裸 Tensor 注解
        """
        return torch.ones(grid.sample_counts)


class _DishonestOutput(_CustomSource):
    def forward(
        self,
        grid: SpatialGrid,
        *,
        generator: torch.Generator | None = None,
    ) -> OpticalField:
        """
        用合法注解伪装运行时裸 Tensor
        """
        del grid, generator
        return cast(OpticalField, torch.ones((2, 2)))


class _BrokenSource(torch.nn.Module):
    @property
    def role(self) -> Literal["source"]:
        """
        返回 Source 角色
        """
        return "source"

    def forward(self, grid: SpatialGrid) -> OpticalField:
        """
        模拟 Source forward 故障
        """
        del grid
        error_identity = "broken_source_forward"
        raise RuntimeError(error_identity)


class _BrokenElement(torch.nn.Module):
    @property
    def role(self) -> Literal["element"]:
        """
        返回 Element 角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        模拟 Element forward 故障
        """
        del field
        error_identity = "broken_element_forward"
        raise RuntimeError(error_identity)


class _BrokenPropagation(torch.nn.Module):
    @property
    def role(self) -> Literal["propagation"]:
        """
        返回 Propagation 角色
        """
        return "propagation"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        模拟传播计算故障
        """
        del field
        error_identity = "broken_propagation_forward"
        raise RuntimeError(error_identity)


class _BrokenCombination(torch.nn.Module):
    # 外部失败探针的编号端口仅验证结构角色，与公共 Combination Contract 无关

    @property
    def role(self) -> Literal["combination"]:
        """
        返回 Combination 角色
        """
        return "combination"

    @property
    def input_ports(self) -> tuple[str, str]:
        """
        返回固定双输入端口
        """
        return ("input_1", "input_2")

    def forward(
        self,
        field_1: OpticalField,
        field_2: OpticalField,
    ) -> OpticalField:
        """
        模拟组合计算故障
        """
        del field_1, field_2
        error_identity = "broken_combination_forward"
        raise RuntimeError(error_identity)


class _BrokenDetection(torch.nn.Module):
    @property
    def role(self) -> Literal["detection"]:
        """
        返回 Detection 角色
        """
        return "detection"

    def forward(self, field: OpticalField) -> Intensity:
        """
        模拟 Detection forward 故障
        """
        del field
        error_identity = "broken_detection_forward"
        raise RuntimeError(error_identity)


class _ChangingPortCombination(torch.nn.Module):
    # 外部端口缓存探针的编号端口仅验证读取次数，与公共 Combination Contract 无关

    is_port_access_allowed = True

    @property
    def role(self) -> Literal["combination"]:
        """
        返回 Combination 角色
        """
        return "combination"

    @property
    def input_ports(self) -> tuple[str, str]:
        """
        首次读取返回固定端口而重复读取故意失败
        """
        if not self.is_port_access_allowed:
            error_identity = "changing_port_access_repeated"
            raise RuntimeError(error_identity)
        return ("input_1", "input_2")

    def forward(
        self,
        field_1: OpticalField,
        field_2: OpticalField,
    ) -> OpticalField:
        """
        返回第一个输入物理值
        """
        del field_2
        return field_1


class _RaisingPortCombination(_ChangingPortCombination):
    @property
    def input_ports(self) -> tuple[str, str]:
        """
        模拟端口契约读取失败
        """
        error_identity = "raising_port_contract"
        raise RuntimeError(error_identity)


class _WrongGeneratorAnnotation(torch.nn.Module):
    def __init__(self) -> None:
        """
        建立生成器注解非法的 Source
        """
        super().__init__()
        self.source = _plane_wave()

    @property
    def role(self) -> Literal["source"]:
        """
        返回 Source 角色
        """
        return "source"

    def forward(
        self,
        grid: SpatialGrid,
        *,
        generator: int = 1,
    ) -> OpticalField:
        """
        给出故意非法的生成器类型与默认值
        """
        del generator
        return self.source(grid)


class _WrongGeneratorDefault(_CustomSource):
    def forward(
        self,
        grid: SpatialGrid,
        *,
        generator: torch.Generator | None = cast(
            torch.Generator | None,
            1,
        ),
    ) -> OpticalField:
        """
        给出故意非法的生成器默认值
        """
        del generator
        return self.source(grid)


class _MissingGeneratorAnnotation(_CustomSource):
    def forward(
        self,
        grid: SpatialGrid,
        *,
        generator: object = None,
    ) -> OpticalField:
        """
        提供随后移除生成器注解的测试入口
        """
        del generator
        return self.source(grid)


_MissingGeneratorAnnotation.forward.__annotations__.pop("generator")


def _accept_source(component: Source) -> Source:
    return component


def _accept_element(component: Element) -> Element:
    return component


def _accept_propagation(component: Propagation) -> Propagation:
    return component


def _accept_combination(component: Combination) -> Combination:
    return component


def _accept_detection(component: Detection) -> Detection:
    return component


def test_public_role_protocols_accept_structural_components() -> None:
    """
    五个公开 Role 只要求只读 role 与真实 forward，不要求项目基类或描述孪生
    """
    grid = _grid()
    field = _plane_wave()(grid)
    assert _accept_source(_CustomSource()).role == "source"
    assert _accept_element(CircularPupil(grid=grid, radius=4.0e-6)).role == "element"
    assert _accept_propagation(
        ScalarAngularSpectrum(axial_distance=1.0e-4)
    ).role == "propagation"
    assert _accept_combination(CoherentCombination()).role == "combination"
    assert _accept_detection(IntensityDetection()).role == "detection"
    assert isinstance(
        CoherentCombination()(field, field),
        OpticalField,
    )


@pytest.mark.parametrize(
    "component",
    (
        _plane_wave(),
        CircularPupil(grid=_grid(), radius=4.0e-6),
        ScalarAngularSpectrum(axial_distance=1.0e-4),
        CoherentCombination(),
        IntensityCombination(),
        IntensityDetection(),
    ),
)
def test_current_components_declare_one_immutable_role(
    component: torch.nn.Module,
) -> None:
    """
    每个公开 Component 只暴露一个不可改写的物理导航角色
    """
    assert component.role in {
        "source",
        "element",
        "propagation",
        "combination",
        "detection",
    }
    with pytest.raises(AttributeError):
        component.role = "source"  # type: ignore[misc]


def test_public_component_calls_return_only_physical_values() -> None:
    """
    五类 Role 的真实 forward 只产生 OpticalField 或 Intensity 强物理值
    """
    grid = _grid()
    source_field = _plane_wave()(grid)
    element_field = CircularPupil(grid=grid, radius=4.0e-6)(source_field)
    recombined = CoherentCombination()(element_field, element_field)
    propagated = ScalarAngularSpectrum(axial_distance=1.0e-4)(recombined)
    detected = IntensityDetection()(propagated)
    combined_intensity = IntensityCombination()(detected, detected)

    produced = (
        source_field,
        element_field,
        recombined,
        propagated,
        detected,
        combined_intensity,
    )
    assert all(isinstance(value, (OpticalField, Intensity)) for value in produced)


def test_runtime_role_contract_accepts_an_external_component() -> None:
    """
    Assembly 与 Workstation 以同一 Role 契约接纳普通 PyTorch 扩展组件
    """
    source = _CustomSource()
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.expose(source, name="field")
    assembly.freeze()

    assert assembly.check() is None
    assert Workstation.cpu().host(source) is source


def test_include_rejects_an_ordinary_pytorch_module() -> None:
    """
    Include 拒绝没有 Optical Role 的普通 PyTorch 模块
    """
    with pytest.raises(AssemblyError) as rejected:
        Assembly().include(torch.nn.Identity(), name="identity")
    assert rejected.value.identity == "optical_component_role_invalid"


def test_include_rejects_an_ambiguous_role() -> None:
    """
    Include 拒绝同时声明多个角色的组件
    """
    with pytest.raises(AssemblyError) as rejected:
        Assembly().include(_AmbiguousRole(), name="ambiguous")
    assert rejected.value.identity == "optical_component_role_invalid"


def test_include_rejects_a_role_annotation_belonging_to_another_role() -> None:
    """
    Include 拒绝运行时角色值合法但 role 注解属于另一角色的组件

    覆盖 _closed_role_of 中 annotation != semantics.role_annotation 拒绝分支：
    运行时返回 "source" 通过 isinstance 与角色名守卫，唯有注解比对能拒绝。
    """
    with pytest.raises(AssemblyError) as rejected:
        Assembly().include(
            _DishonestRoleAnnotation(),
            name="source",
        )
    assert rejected.value.identity == "optical_component_role_invalid"


def test_host_rejects_a_role_annotation_belonging_to_another_role() -> None:
    """
    Host 与 Include 对 role 注解错配给出同一角色契约身份
    """
    with pytest.raises(WorkstationError) as rejected:
        Workstation.cpu().host(_DishonestRoleAnnotation())
    assert rejected.value.identity == "optical_component_role_invalid"


def test_include_rejects_a_role_without_forward() -> None:
    """
    Include 拒绝没有真实 forward 的角色声明
    """
    with pytest.raises(AssemblyError) as rejected:
        Assembly().include(_MissingForward(), name="source")
    assert rejected.value.identity == (
        "optical_component_forward_signature_invalid:source"
    )


def test_include_rejects_a_source_with_wrong_arity() -> None:
    """
    Include 拒绝 forward 元数与 Source 契约不符的组件
    """
    with pytest.raises(AssemblyError) as rejected:
        Assembly().include(_WrongAritySource(), name="source")
    assert rejected.value.identity == (
        "optical_component_forward_signature_invalid:source"
    )


def test_include_rejects_a_declared_tensor_result() -> None:
    """
    Include 拒绝声明裸 Tensor 结果的 Source
    """
    with pytest.raises(AssemblyError) as rejected:
        Assembly().include(_TensorOutput(), name="source")
    assert rejected.value.identity == (
        "optical_component_forward_signature_invalid:source"
    )


def test_meta_check_rejects_a_dishonest_forward_result() -> None:
    """
    meta 检查拒绝注解合法但运行时返回裸 Tensor 的组件
    """
    assembly = Assembly()
    source = _DishonestOutput()
    assembly.include(source, name="source", grid=_grid())
    assembly.expose(source, name="field")

    with pytest.raises(AssemblyError) as rejected:
        assembly.check()
    assert rejected.value.identity == "assembly_output_value_invalid:source"


@pytest.mark.parametrize(
    ("component", "name", "role", "failure"),
    (
        (
            _BrokenElement(),
            "broken_element",
            "element",
            "broken_element_forward",
        ),
        (
            _BrokenPropagation(),
            "broken_propagation",
            "propagation",
            "broken_propagation_forward",
        ),
        (
            _BrokenDetection(),
            "broken_detection",
            "detection",
            "broken_detection_forward",
        ),
    ),
)
def test_meta_check_translates_unary_forward_failures(
    component: torch.nn.Module,
    name: str,
    role: str,
    failure: str,
) -> None:
    """
    一元角色 forward 故障保留角色与组件身份
    """
    assembly = Assembly()
    source = _CustomSource()
    assembly.include(source, name="source", grid=_grid())
    assembly.include(component, name=name)
    assembly.connect(source, component)
    assembly.expose(component, name="result")

    with pytest.raises(AssemblyError) as rejected:
        assembly.check()
    assert rejected.value.identity == (
        f"assembly_{role}_forward_failed:{name}:{failure}"
    )


def test_meta_check_translates_source_forward_failure() -> None:
    """
    Source forward 故障映射为稳定 Assembly Error
    """
    assembly = Assembly()
    source = _BrokenSource()
    assembly.include(source, name="broken_source", grid=_grid())
    assembly.expose(source, name="field")

    with pytest.raises(AssemblyError) as rejected:
        assembly.check()
    assert rejected.value.identity == (
        "assembly_source_forward_failed:broken_source:broken_source_forward"
    )


def test_meta_check_translates_combination_forward_failure() -> None:
    """
    组合计算故障映射为稳定装配错误
    """
    assembly = Assembly()
    source_1 = _CustomSource()
    source_2 = _CustomSource()
    combination = _BrokenCombination()
    assembly.include(source_1, name="source_1", grid=_grid())
    assembly.include(source_2, name="source_2", grid=_grid())
    assembly.include(combination, name="broken_combination")
    assembly.connect(source_1, combination, destination_port="input_1")
    assembly.connect(source_2, combination, destination_port="input_2")
    assembly.expose(combination, name="result")

    with pytest.raises(AssemblyError) as rejected:
        assembly.check()
    assert rejected.value.identity == (
        "assembly_combination_forward_failed:broken_combination:"
        "broken_combination_forward"
    )


def test_include_caches_fixed_ports_once() -> None:
    """
    Include 冻结端口后检查不再重复推断端口
    """
    assembly = Assembly()
    component = _ChangingPortCombination()
    source_1 = _CustomSource()
    source_2 = _CustomSource()
    assembly.include(source_1, name="source_1", grid=_grid())
    assembly.include(source_2, name="source_2", grid=_grid())
    assembly.include(component, name="combination")
    assembly.connect(
        source_1,
        component,
        destination_port="input_1",
    )
    assembly.connect(
        source_2,
        component,
        destination_port="input_2",
    )
    assembly.expose(component, name="field")
    component.is_port_access_allowed = False

    assert assembly.check() is None


def test_include_translates_raising_port_property() -> None:
    """
    Include 把端口读取故障收束为端口契约错误
    """
    with pytest.raises(AssemblyError) as rejected:
        Assembly().include(
            _RaisingPortCombination(),
            name="combination",
        )
    assert rejected.value.identity == "optical_component_input_ports_invalid"


@pytest.mark.parametrize(
    "source_type",
    (
        _WrongGeneratorAnnotation,
        _WrongGeneratorDefault,
        _MissingGeneratorAnnotation,
    ),
)
def test_generator_contract_is_identical_at_include_and_host(
    source_type: type[torch.nn.Module],
) -> None:
    """
    Include 与 Host 对非法生成器签名给出同一契约身份
    """
    source = source_type()
    with pytest.raises(AssemblyError) as rejected:
        Assembly().include(source, name="source")
    assert rejected.value.identity == (
        "optical_component_forward_signature_invalid:source"
    )

    with pytest.raises(WorkstationError) as rejected:
        Workstation.cpu().host(source)
    assert rejected.value.identity == (
        "optical_component_forward_signature_invalid:source"
    )


def test_host_rejects_an_independent_module_without_an_optical_role() -> None:
    """
    Host 拒绝没有 Optical Role 的独立 PyTorch 模块
    """
    with pytest.raises(WorkstationError) as rejected:
        Workstation.cpu().host(torch.nn.Identity())
    assert rejected.value.identity == "optical_component_role_invalid"
