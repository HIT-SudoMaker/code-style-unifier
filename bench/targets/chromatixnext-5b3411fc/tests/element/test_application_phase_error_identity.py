
from __future__ import annotations

import pytest
import torch

from chromatix_next.errors import OpticalError
from chromatix_next.optics import (
    FieldNormalization,
    Intensity,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PolarizationRepresentation,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.combination import (
    coherent_combination,
    intensity_combination,
)
from chromatix_next.optics.combination.coherent_combination import CoherentCombination
from chromatix_next.optics.combination.intensity_combination import IntensityCombination
from chromatix_next.optics.detection import IntensityDetection, intensity_detection
from chromatix_next.optics.element import (
    AmplitudeTransmissionMap,
    CircularPupil,
    IdealThinLens,
    OpticalPathModulation,
    SquarePupil,
    amplitude_transmission_map,
    circular_pupil,
    ideal_thin_lens,
    optical_path_modulation,
    square_pupil,
)
from chromatix_next.optics.source import (
    CollimatedRaySource,
    GaussianBeam,
    PlaneWave,
    PointSource,
)


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(1.0e-6, 1.0e-6),
    )


def _spectrum() -> Spectrum:
    return Spectrum.monochromatic(wavelength=2.0e-6)


def _scalar_field() -> OpticalField:
    grid = _grid()
    counts_y, counts_x = grid.sample_counts
    envelope = torch.ones(
        (1, 1, counts_y, counts_x),
        dtype=torch.complex128,
    )
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=_spectrum(),
        polarization_representation=PolarizationRepresentation.SCALAR,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )


def _intensity() -> Intensity:
    return Intensity(
        values=torch.ones(_grid().sample_counts, dtype=torch.float64),
        grid=_grid(),
        normalization=FieldNormalization.RELATIVE,
    )


class TestNeutralElementFieldInvalidIdentity:
    """
    五个偏振中性元件应用期 ``*_field_invalid`` 身份的直接与二元证据
    """

    @pytest.mark.parametrize(
        ("function", "kwargs", "component_factory"),
        (
            (
                amplitude_transmission_map,
                dict(
                    grid=_grid(),
                    amplitude_transmission=torch.full(
                        _grid().sample_counts,
                        0.8,
                        dtype=torch.float64,
                    ),
                ),
                lambda: AmplitudeTransmissionMap(
                    grid=_grid(),
                    amplitude_transmission=torch.full(
                        _grid().sample_counts,
                        0.8,
                        dtype=torch.float64,
                    ),
                ),
            ),
            (
                optical_path_modulation,
                dict(
                    grid=_grid(),
                    optical_path_variation=torch.zeros(
                        _grid().sample_counts,
                        dtype=torch.float64,
                    ),
                ),
                lambda: OpticalPathModulation(
                    grid=_grid(),
                    optical_path_variation=torch.zeros(
                        _grid().sample_counts,
                        dtype=torch.float64,
                    ),
                ),
            ),
            (
                ideal_thin_lens,
                dict(grid=_grid(), focal_length=1.0e-3),
                lambda: IdealThinLens(grid=_grid(), focal_length=1.0e-3),
            ),
            (
                circular_pupil,
                dict(grid=_grid(), radius=1.0e-6),
                lambda: CircularPupil(grid=_grid(), radius=1.0e-6),
            ),
            (
                square_pupil,
                dict(grid=_grid(), width=2.0e-6),
                lambda: SquarePupil(grid=_grid(), width=2.0e-6),
            ),
        ),
        ids=(
            "amplitude_transmission_map",
            "optical_path_modulation",
            "ideal_thin_lens",
            "circular_pupil",
            "square_pupil",
        ),
    )
    def test_field_invalid_identity_matches_function_and_component(
        self,
        function: object,
        kwargs: dict,
        component_factory: object,
    ) -> None:
        """
        非光场输入 ⇒ function 与 component 抛同一 ``<prefix>_field_invalid``
        """

        prefix = function.__name__  # type: ignore[attr-defined]
        expected_identity = f"{prefix}_field_invalid"
        # 函数路径：提供合法关键字参数，仅 field 非法 ⇒ 进入函数体抛 field_invalid
        with pytest.raises(OpticalError) as function_path:
            function(object(), **kwargs)  # type: ignore[operator]
        assert function_path.value.identity == expected_identity
        # 组件路径：forward 委托同一函数，抛同一身份
        component = component_factory()  # type: ignore[operator]
        with pytest.raises(OpticalError) as component_path:
            component(object())  # type: ignore[operator]
        assert component_path.value.identity == expected_identity


class TestSourceGridInvalidIdentity:
    """
    四个源的应用期 ``*_grid_invalid`` 类型身份证据（源的角色使函数与组件同一）
    """

    @pytest.mark.parametrize(
        ("source_factory", "expected_identity"),
        (
            (
                lambda: PlaneWave(
                    spectrum=_spectrum(),
                    polarization=Polarization.scalar(),
                    medium=Vacuum(),
                    propagation_direction=PropagationDirection.forward(),
                    relative_amplitude=1.0,
                ),
                "plane_wave_grid_invalid",
            ),
            (
                lambda: GaussianBeam(
                    spectrum=_spectrum(),
                    polarization=Polarization.scalar(),
                    medium=Vacuum(),
                    waist=3.0e-6,
                    waist_location=0.0,
                    relative_amplitude=1.0,
                ),
                "gaussian_beam_grid_invalid",
            ),
            (
                lambda: PointSource(
                    spectrum=_spectrum(),
                    polarization=Polarization.scalar(),
                    medium=Vacuum(),
                    position=(0.0, 0.0, 5.0e-6),
                    relative_amplitude=1.0,
                ),
                "point_source_grid_invalid",
            ),
            (
                lambda: CollimatedRaySource(
                    spectrum=_spectrum(),

                    polarization=Polarization.linear_x(),
                    medium=Vacuum(),
                    ray_power=1.0,
                ),
                "collimated_ray_source_grid_invalid",
            ),
        ),
        ids=("plane_wave", "gaussian_beam", "point_source", "collimated_ray_source"),
    )
    def test_grid_invalid_identity_at_application(
        self,
        source_factory: object,
        expected_identity: str,
    ) -> None:
        """
        非 SpatialGrid 输入 ⇒ 源在应用期抛 ``<source>_grid_invalid``
        """

        source = source_factory()  # type: ignore[operator]
        with pytest.raises(OpticalError) as rejected:
            source(object())  # type: ignore[operator]
        assert rejected.value.identity == expected_identity


class TestCombinationApplicationIdentity:
    """
    相干/强度组合的应用期类型身份直接 + 二元证据
    """

    def test_coherent_combination_field_invalid_identity(self) -> None:
        """
        非光场输入 ⇒ 函数与组件抛同一 ``coherent_combination_field_*_invalid``
        """

        field = _scalar_field()
        with pytest.raises(OpticalError) as function_first:
            coherent_combination(object(), field)  # type: ignore[arg-type]
        assert (
            function_first.value.identity
            == "coherent_combination_field_1_invalid"
        )
        with pytest.raises(OpticalError) as function_second:
            coherent_combination(field, object())  # type: ignore[arg-type]
        assert (
            function_second.value.identity
            == "coherent_combination_field_2_invalid"
        )
        component = CoherentCombination()
        with pytest.raises(OpticalError) as component_path:
            component(object(), field)  # type: ignore[arg-type]
        assert (
            component_path.value.identity
            == "coherent_combination_field_1_invalid"
        )

    def test_intensity_combination_invalid_identity(self) -> None:
        """
        非光强输入使函数与组件抛同一强度组合稳定身份
        """

        intensity = _intensity()
        with pytest.raises(OpticalError) as function_first:
            intensity_combination(object(), intensity)  # type: ignore[arg-type]
        assert (
            function_first.value.identity
            == "intensity_combination_intensity_1_invalid"
        )
        with pytest.raises(OpticalError) as function_second:
            intensity_combination(intensity, object())  # type: ignore[arg-type]
        assert (
            function_second.value.identity
            == "intensity_combination_intensity_2_invalid"
        )
        component = IntensityCombination()
        with pytest.raises(OpticalError) as component_path:
            component(object(), intensity)  # type: ignore[arg-type]
        assert (
            component_path.value.identity
            == "intensity_combination_intensity_1_invalid"
        )


class TestIntensityDetectionApplicationIdentity:
    """
    光强探测的应用期类型身份直接 + 二元证据（补 Component.forward 路径）
    """

    def test_field_invalid_identity_matches_function_and_component(self) -> None:
        """
        非光场输入 ⇒ 组件入口抛 ``intensity_detection_field_invalid``
        """

        with pytest.raises(OpticalError) as direct_rejection:
            intensity_detection(object())  # type: ignore[arg-type]
        component = IntensityDetection()
        with pytest.raises(OpticalError) as component_rejection:
            component(object())  # type: ignore[arg-type]
        assert direct_rejection.value.identity == "intensity_detection_field_invalid"
        assert component_rejection.value.identity == direct_rejection.value.identity
