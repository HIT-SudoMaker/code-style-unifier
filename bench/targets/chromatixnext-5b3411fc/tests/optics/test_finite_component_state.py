
from __future__ import annotations

import copy
from importlib import import_module

import pytest
import torch

from chromatix_next.errors import AssemblyError
from chromatix_next.optics import (
    Assembly,
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import (
    AmplitudeTransmissionMap,
    IdealThinLens,
    OpticalPathModulation,
)
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave
import chromatix_next.optics.source.plane_wave as plane_wave_module
from chromatix_next.workstation import Workstation

ideal_thin_lens_module = import_module(
    "chromatix_next.optics.element.ideal_thin_lens"
)


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(1.0e-6, 1.0e-6),
    )


def _field() -> OpticalField:
    spectrum = Spectrum.monochromatic(wavelength=0.5e-6)
    return OpticalField(
        envelope=torch.ones((1, 1, 4, 4), dtype=torch.complex128),
        grid=_grid(),
        spectrum=spectrum,
        polarization_representation=(Polarization.scalar()).representation,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


def _overwrite(parameter: torch.nn.Parameter, value: float) -> None:
    with torch.no_grad():
        parameter.fill_(value)


def _meta_field() -> OpticalField:
    # 返回包络位于 meta 设备的光场：只有形状与数据类型，没有取值
    field = _field()
    projected = copy.copy(field)
    object.__setattr__(
        projected,
        "envelope",
        torch.empty_like(field.envelope, device="meta"),
    )
    return projected


def _polluted_component(component_name: str) -> torch.nn.Module:
    # 构造一个可训练量已被原位污染为非数的元件
    if component_name == "amplitude_transmission":
        parameter = torch.nn.Parameter(
            torch.full(_grid().sample_counts, 0.5, dtype=torch.float64),
        )
        component: torch.nn.Module = AmplitudeTransmissionMap(
            grid=_grid(),
            amplitude_transmission=parameter,
        )
    elif component_name == "optical_path_modulation":
        parameter = torch.nn.Parameter(
            torch.zeros(_grid().sample_counts, dtype=torch.float64),
        )
        component = OpticalPathModulation(
            grid=_grid(),
            optical_path_variation=parameter,
        )
    elif component_name == "ideal_thin_lens":
        parameter = torch.nn.Parameter(
            torch.tensor(1.0e-3, dtype=torch.float64),
        )
        component = IdealThinLens(grid=_grid(), focal_length=parameter)
    else:
        parameter = torch.nn.Parameter(
            torch.tensor(1.0e-3, dtype=torch.float64),
        )
        component = ScalarAngularSpectrum(axial_distance=parameter)
    _overwrite(parameter, float("nan"))
    return component


class TestFiniteMutableComponentState:
    """
    所有当前可训练 Component 在消费 Parameter 时复检有限物理状态
    """

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    @pytest.mark.parametrize(
        "normalization_name",
        ["relative_amplitude", "total_power"],
    )
    def test_plane_wave_rejects_nonfinite_scale_at_consumption(
        self,
        invalid_value: float,
        normalization_name: str,
    ) -> None:
        """
        平面波相对振幅与总功率 Parameter 原位污染后均由源边界拒绝
        """

        scale = torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float64))
        arguments: dict[str, object] = {normalization_name: scale}
        source = PlaneWave(
            spectrum=Spectrum.monochromatic(wavelength=0.5e-6),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection.forward(),
            **arguments,  # type: ignore[arg-type]
        )
        _overwrite(scale, invalid_value)

        with pytest.raises(
            ValueError,
            match=f"plane_wave_{normalization_name}_invalid",
        ):
            source(_grid())

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_amplitude_transmission_rejects_nonfinite_parameter(
        self,
        invalid_value: float,
    ) -> None:
        """
        振幅透射 Parameter 原位污染后由振幅元件边界拒绝
        """

        parameter = torch.nn.Parameter(
            torch.full(_grid().sample_counts, 0.5, dtype=torch.float64),
        )
        element = AmplitudeTransmissionMap(
            grid=_grid(),
            amplitude_transmission=parameter,
        )
        _overwrite(parameter, invalid_value)

        with pytest.raises(
            ValueError,
            match="amplitude_transmission_map_values_invalid",
        ):
            element(_field())

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_optical_path_modulation_rejects_nonfinite_parameter(
        self,
        invalid_value: float,
    ) -> None:
        """
        光程变化 Parameter 原位污染后由光程元件边界拒绝
        """

        parameter = torch.nn.Parameter(
            torch.zeros(_grid().sample_counts, dtype=torch.float64),
        )
        element = OpticalPathModulation(
            grid=_grid(),
            optical_path_variation=parameter,
        )
        _overwrite(parameter, invalid_value)

        with pytest.raises(
            ValueError,
            match="optical_path_modulation_variation_invalid",
        ):
            element(_field())

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_ideal_thin_lens_rejects_nonfinite_parameter(
        self,
        invalid_value: float,
    ) -> None:
        """
        焦距 Parameter 原位污染后由透镜边界拒绝
        """

        parameter = torch.nn.Parameter(torch.tensor(1.0e-3, dtype=torch.float64))
        element = IdealThinLens(
            grid=_grid(),
            focal_length=parameter,
        )
        _overwrite(parameter, invalid_value)

        with pytest.raises(
            ValueError,
            match="ideal_thin_lens_focal_length_invalid",
        ):
            element(_field())

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_scalar_angular_spectrum_rejects_nonfinite_parameter(
        self,
        invalid_value: float,
    ) -> None:
        """
        轴向距离 Parameter 原位污染后在 FFT 前由传播边界拒绝
        """

        parameter = torch.nn.Parameter(torch.tensor(1.0e-3, dtype=torch.float64))
        propagation = ScalarAngularSpectrum(axial_distance=parameter)
        _overwrite(parameter, invalid_value)

        with pytest.raises(
            ValueError,
            match="scalar_angular_spectrum_axial_distance_invalid",
        ):
            propagation(_field())

    @pytest.mark.parametrize(
        ("component_name", "error_identity"),
        [
            ("amplitude_transmission", "amplitude_transmission_map_values_invalid"),
            (
                "optical_path_modulation",
                "optical_path_modulation_variation_invalid",
            ),
            ("ideal_thin_lens", "ideal_thin_lens_focal_length_invalid"),
            (
                "scalar_angular_spectrum",
                "scalar_angular_spectrum_axial_distance_invalid",
            ),
        ],
    )
    def test_meta_inference_revalidates_parameter(
        self,
        component_name: str,
        error_identity: str,
    ) -> None:
        """
        meta 推导执行的是同一份 forward，因此可训练量的复检一并生效
        """

        component = _polluted_component(component_name)
        meta_field = _meta_field()
        inputs = (meta_field,)

        with pytest.raises(ValueError, match=error_identity):
            component(*inputs)

    def test_hosted_assembly_rejects_pollution_before_allocation(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        验证冻结托管后元件的污染在装配检查阶段即被拒绝
        """

        parameter = torch.nn.Parameter(torch.tensor(1.0e-3, dtype=torch.float64))
        source = PlaneWave(
            spectrum=Spectrum.monochromatic(wavelength=0.5e-6),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        grid = _grid()
        lens = IdealThinLens(grid=grid, focal_length=parameter)
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(lens, name="lens")
        assembly.include(detector, name="detector")
        assembly.connect(source, lens)
        assembly.connect(lens, detector)
        assembly.expose(detector, name="intensity")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        _overwrite(parameter, float("nan"))

        def _reject_real_allocation(
            *_arguments: object,
            **_keywords: object,
        ) -> torch.Tensor:
            error_identity = "phase_factor_built_before_validation"
            raise AssertionError(error_identity)

        monkeypatch.setattr(
            ideal_thin_lens_module,
            "ideal_thin_lens_phase_factor",
            _reject_real_allocation,
        )
        error_pattern = (
            "assembly_element_forward_failed:lens:"
            "ideal_thin_lens_focal_length_invalid"
        )
        with pytest.raises(AssemblyError, match=error_pattern):
            assembly.check()
        with pytest.raises(AssemblyError, match=error_pattern):
            workstation.check(assembly)
        with pytest.raises(AssemblyError, match=error_pattern):
            workstation.run(assembly)

    def test_source_pollution_is_rejected_before_the_envelope_is_built(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        光源的可训练归一化量在合成包络之前复检，污染不会先付出一次分配
        """

        parameter = torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float64))
        source = PlaneWave(
            spectrum=Spectrum.monochromatic(wavelength=0.5e-6),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=parameter,
        )
        _overwrite(parameter, float("nan"))

        def _reject_real_allocation(
            *_arguments: object,
            **_keywords: object,
        ) -> torch.Tensor:
            error_identity = "envelope_built_before_validation"
            raise AssertionError(error_identity)

        monkeypatch.setattr(
            plane_wave_module,
            "plane_wave_envelope",
            _reject_real_allocation,
        )
        with pytest.raises(
            ValueError,
            match="plane_wave_relative_amplitude_invalid",
        ):
            source(_grid())
