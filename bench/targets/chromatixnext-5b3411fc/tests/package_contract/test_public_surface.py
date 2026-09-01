from __future__ import annotations

from collections.abc import Callable
import importlib
import inspect

import torch

import chromatix_next
import chromatix_next.errors as errors
import chromatix_next.optics as optics
from chromatix_next.optics import (
    FieldNormalization,
    PolarizationRepresentation,
    PropagationExterior,
    combination,
    detection,
    element,
    paraxial_ray_transfer,
    propagation,
    source,
    surface,
)
from chromatix_next.optics.combination import role as combination_role
from chromatix_next.optics.detection import role as detection_role
from chromatix_next.optics.element import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPlanarMirror,
    IdealPolarizingCubeBeamSplitter,
    MirrorTerminal,
    RetarderAt,
    retarder_at,
)
from chromatix_next.optics.element import role as element_role
from chromatix_next.optics.propagation import role as propagation_role
from chromatix_next.optics.source import role as source_role

EXPECTED_ACTIONS = frozenset(
    {
        "AmplitudeTransmissionMap",
        "AplanaticFocus",
        "CircularPupil",
        "CoherentCombination",
        "CollimatedRaySource",
        "FresnelTransform",
        "GaussianBeam",
        "IdealThinLens",
        "IntensityCombination",
        "IntensityDetection",
        "OpticalPathModulation",
        "PlaneWave",
        "PointSource",
        "ReflectAt",
        "RefractAt",
        "Retarder",
        "RetarderAt",
        "ScalableAngularSpectrum",
        "ScalarAngularSpectrum",
        "ScaledAngularSpectrum",
        "ScaledFresnel",
        "SquarePupil",
        "TraceTo",
        "VectorAngularSpectrum",
    }
)

EXPECTED_DIRECTIONAL_OWNERS = frozenset(
    {
        "IdealNonpolarizingCubeBeamSplitter",
        "IdealPlanarMirror",
        "IdealPolarizingCubeBeamSplitter",
    }
)

EXPECTED_DIRECTIONAL_ENUMS = frozenset(
    {
        "CubeCoatingDiagonal",
        "CubeTerminal",
        "MirrorTerminal",
    }
)

EXPECTED_ENCOUNTER_REFERENCES = frozenset({"RayEncounter", "WaveEncounter"})

EXPECTED_PUBLIC_EXPORTS = {
    "root": ("Workstation", "install_state"),
    "errors": (
        "AssemblyError",
        "OpticalError",
        "OpticalRuntimeError",
        "OpticalTypeError",
        "OpticalValueError",
        "WorkstationError",
    ),
    "optics": (
        "Assembly",
        "ConstantMedium",
        "FieldNormalization",
        "Intensity",
        "Medium",
        "OpticalField",
        "OpticalPathReference",
        "Polarization",
        "PolarizationRepresentation",
        "PropagationExterior",
        "PropagationDirection",
        "RayBundle",
        "RayEncounter",
        "SellmeierMedium",
        "SpatialGrid",
        "Spectrum",
        "TabulatedMedium",
        "TransverseWavevector",
        "Vacuum",
        "WaveEncounter",
    ),
    "paraxial_ray_transfer": (
        "compose_ray_transfer_matrices",
        "free_space_ray_transfer_matrix",
        "spherical_refraction_ray_transfer_matrix",
        "thin_lens_ray_transfer_matrix",
    ),
    "source": (
        "CollimatedRaySource",
        "GaussianBeam",
        "PlaneWave",
        "PointSource",
        "Source",
    ),
    "source_role": None,
    "surface": ("Plane", "Sphere", "ConicEvenAsphere"),
    "element": (
        "amplitude_transmission_map",
        "AmplitudeTransmissionMap",
        "CubeCoatingDiagonal",
        "CubeTerminal",
        "IdealNonpolarizingCubeBeamSplitter",
        "IdealPolarizingCubeBeamSplitter",
        "IdealPlanarMirror",
        "MirrorTerminal",
        "ideal_thin_lens",
        "IdealThinLens",
        "optical_path_modulation",
        "OpticalPathModulation",
        "circular_pupil",
        "CircularPupil",
        "square_pupil",
        "SquarePupil",
        "retarder",
        "Retarder",
        "refract_at",
        "RefractAt",
        "reflect_at",
        "ReflectAt",
        "retarder_at",
        "RetarderAt",
        "Element",
    ),
    "element_role": None,
    "propagation": (
        "aplanatic_focus",
        "AplanaticFocus",
        "fresnel_transform",
        "FresnelTransform",
        "scalable_angular_spectrum",
        "ScalableAngularSpectrum",
        "scalar_angular_spectrum",
        "ScalarAngularSpectrum",
        "ScalarAngularSpectrumDiagnostic",
        "scaled_angular_spectrum",
        "ScaledAngularSpectrum",
        "scaled_fresnel",
        "ScaledFresnel",
        "trace_to",
        "TraceTo",
        "vector_angular_spectrum",
        "VectorAngularSpectrum",
        "Propagation",
    ),
    "propagation_role": None,
    "combination": (
        "coherent_combination",
        "CoherentCombination",
        "intensity_combination",
        "IntensityCombination",
        "Combination",
    ),
    "combination_role": None,
    "detection": (
        "intensity_detection",
        "IntensityDetection",
        "Detection",
    ),
    "detection_role": None,
}

EXPECTED_PUBLIC_SIGNATURES = {
    "root.install_state": "P:root|P:state_dict",
    "paraxial_ray_transfer.compose_ray_transfer_matrices": "P:matrices",
    "paraxial_ray_transfer.free_space_ray_transfer_matrix": "P:distance|K:device",
    "paraxial_ray_transfer.spherical_refraction_ray_transfer_matrix": (
        "P:curvature|P:incident_index|P:destination_index|K:device"
    ),
    "paraxial_ray_transfer.thin_lens_ray_transfer_matrix": "P:focal_length|K:device",
    "source.CollimatedRaySource": (
        "K:spectrum|K:polarization|K:medium=Vacuum()|"
        "K:launch_origin=(0.0, 0.0, 0.0)|"
        "K:launch_tangent_x=(1.0, 0.0, 0.0)|"
        "K:launch_tangent_y=(0.0, 1.0, 0.0)|K:ray_power"
    ),
    "source.GaussianBeam": (
        "K:spectrum|K:polarization|K:medium=Vacuum()|K:waist|"
        "K:waist_location=0.0|K:relative_amplitude=None|K:total_power=None"
    ),
    "source.PlaneWave": (
        "K:spectrum|K:polarization|K:medium=Vacuum()|"
        "K:propagation_direction=None|K:transverse_wavevector=None|"
        "K:relative_amplitude=None|K:total_power=None"
    ),
    "source.PointSource": (
        "K:spectrum|K:polarization|K:medium=Vacuum()|K:position|"
        "K:relative_amplitude=None|K:total_power=None"
    ),
    "surface.Plane": (
        "K:origin=(0.0, 0.0, 0.0)|"
        "K:tangent_x=(1.0, 0.0, 0.0)|"
        "K:tangent_y=(0.0, 1.0, 0.0)|K:clear_aperture_radius=None"
    ),
    "surface.Sphere": (
        "K:vertex=(0.0, 0.0, 0.0)|"
        "K:tangent_x=(1.0, 0.0, 0.0)|"
        "K:tangent_y=(0.0, 1.0, 0.0)|K:radius_of_curvature|"
        "K:clear_aperture_radius=None"
    ),
    "surface.ConicEvenAsphere": (
        "K:vertex=(0.0, 0.0, 0.0)|"
        "K:tangent_x=(1.0, 0.0, 0.0)|"
        "K:tangent_y=(0.0, 1.0, 0.0)|K:curvature=0.0|"
        "K:conic_constant=0.0|K:even_coefficients=()|"
        "K:clear_aperture_radius=None"
    ),
    "element.amplitude_transmission_map": (
        "P:field|K:grid|K:amplitude_transmission"
    ),
    "element.AmplitudeTransmissionMap": "K:grid|K:amplitude_transmission",
    "element.IdealNonpolarizingCubeBeamSplitter": (
        "K:origin|K:route_right|K:route_top|K:coating_diagonal|K:mixing_angle"
    ),
    "element.IdealPolarizingCubeBeamSplitter": (
        "K:origin|K:route_right|K:route_top|K:coating_diagonal"
    ),
    "element.IdealPlanarMirror": (
        "K:origin|K:outward_normal|K:transverse_up"
    ),
    "element.ideal_thin_lens": (
        "P:field|K:grid|K:focal_length|K:lens_center=(0.0, 0.0)"
    ),
    "element.IdealThinLens": (
        "K:grid|K:focal_length|K:lens_center=(0.0, 0.0)"
    ),
    "element.optical_path_modulation": (
        "P:field|K:grid|K:optical_path_variation|"
        "K:optical_path_baseline=0.0"
    ),
    "element.OpticalPathModulation": (
        "K:grid|K:optical_path_variation|K:optical_path_baseline=0.0"
    ),
    "element.circular_pupil": "P:field|K:grid|K:radius",
    "element.CircularPupil": "K:grid|K:radius",
    "element.square_pupil": "P:field|K:grid|K:width",
    "element.SquarePupil": "K:grid|K:width",
    "element.retarder": (
        "P:field|K:retardance_cycles|"
        "K:retarded_eigenstate_azimuth_radians|"
        "K:retarded_eigenstate_ellipticity_radians"
    ),
    "element.Retarder": (
        "K:retardance_cycles|K:retarded_eigenstate_azimuth_radians|"
        "K:retarded_eigenstate_ellipticity_radians"
    ),
    "element.refract_at": "P:bundle|K:surface|K:destination_medium",
    "element.RefractAt": "K:surface|K:destination_medium",
    "element.reflect_at": "P:bundle|K:surface",
    "element.ReflectAt": "K:surface",
    "element.retarder_at": (
        "P:bundle|K:surface|K:retardance_cycles|"
        "K:retarded_eigenstate_azimuth_radians|"
        "K:retarded_eigenstate_ellipticity_radians"
    ),
    "element.RetarderAt": (
        "K:surface|K:retardance_cycles|"
        "K:retarded_eigenstate_azimuth_radians|"
        "K:retarded_eigenstate_ellipticity_radians"
    ),
    "propagation.aplanatic_focus": (
        "P:field|K:focal_length|K:maximum_convergence_angle|"
        "K:axial_distance_from_focus|K:destination_grid"
    ),
    "propagation.AplanaticFocus": (
        "K:focal_length|K:maximum_convergence_angle|"
        "K:axial_distance_from_focus|K:destination_grid"
    ),
    "propagation.fresnel_transform": "P:field|K:axial_distance",
    "propagation.FresnelTransform": "K:axial_distance",
    "propagation.scalable_angular_spectrum": (
        "P:field|K:axial_distance|K:destination_grid|"
        "K:exterior=<PropagationExterior.PERIODIC: 'periodic'>"
    ),
    "propagation.ScalableAngularSpectrum": (
        "K:axial_distance|K:destination_grid|"
        "K:exterior=<PropagationExterior.PERIODIC: 'periodic'>"
    ),
    "propagation.scalar_angular_spectrum": (
        "P:field|K:axial_distance|"
        "K:exterior=<PropagationExterior.PERIODIC: 'periodic'>|"
        "K:destination_grid=None"
    ),
    "propagation.ScalarAngularSpectrum": (
        "K:axial_distance|K:exterior="
        "<PropagationExterior.PERIODIC: 'periodic'>|K:destination_grid=None"
    ),
    "propagation.scaled_angular_spectrum": (
        "P:field|K:axial_distance|K:destination_grid|"
        "K:exterior=<PropagationExterior.PERIODIC: 'periodic'>"
    ),
    "propagation.ScaledAngularSpectrum": (
        "K:axial_distance|K:destination_grid|"
        "K:exterior=<PropagationExterior.PERIODIC: 'periodic'>"
    ),
    "propagation.scaled_fresnel": (
        "P:field|K:axial_distance|K:destination_grid|"
        "K:exterior=<PropagationExterior.PERIODIC: 'periodic'>"
    ),
    "propagation.ScaledFresnel": (
        "K:axial_distance|K:destination_grid|"
        "K:exterior=<PropagationExterior.PERIODIC: 'periodic'>"
    ),
    "propagation.trace_to": "P:bundle|K:surface",
    "propagation.TraceTo": "K:surface",
    "propagation.vector_angular_spectrum": (
        "P:field|K:axial_distance|"
        "K:exterior=<PropagationExterior.PERIODIC: 'periodic'>|"
        "K:destination_grid=None"
    ),
    "propagation.VectorAngularSpectrum": (
        "K:axial_distance|K:exterior="
        "<PropagationExterior.PERIODIC: 'periodic'>|K:destination_grid=None"
    ),
    "combination.coherent_combination": "P:field_1|P:field_2",
    "combination.CoherentCombination": "",
    "combination.intensity_combination": "P:intensity_1|P:intensity_2",
    "combination.IntensityCombination": "",
    "detection.intensity_detection": "P:field",
    "detection.IntensityDetection": "",
}


def _signature_contract(target: Callable[..., object]) -> str:
    kind_codes = {
        inspect.Parameter.POSITIONAL_ONLY: "O",
        inspect.Parameter.POSITIONAL_OR_KEYWORD: "P",
        inspect.Parameter.VAR_POSITIONAL: "V",
        inspect.Parameter.KEYWORD_ONLY: "K",
        inspect.Parameter.VAR_KEYWORD: "W",
    }
    parameters = inspect.signature(target).parameters.values()
    return "|".join(
        f"{kind_codes[parameter.kind]}:{parameter.name}"
        + (
            ""
            if parameter.default is inspect.Parameter.empty
            else f"={parameter.default!r}"
        )
        for parameter in parameters
    )


def _public_function_and_component_signatures() -> dict[str, str]:
    public_modules = {
        "paraxial_ray_transfer": paraxial_ray_transfer,
        "source": source,
        "surface": surface,
        "element": element,
        "propagation": propagation,
        "combination": combination,
        "detection": detection,
    }
    signatures = {
        "root.install_state": _signature_contract(chromatix_next.install_state),
    }
    for module_name, module in public_modules.items():
        for export_name in module.__all__:
            target = getattr(module, export_name)
            is_component = inspect.isclass(target) and issubclass(
                target,
                torch.nn.Module,
            )
            if inspect.isfunction(target) or is_component:
                signatures[f"{module_name}.{export_name}"] = (
                    _signature_contract(target)
                )
    return signatures


def test_public_modules_have_exact_export_surfaces() -> None:
    """
    所有公开模块与角色模块保持显式冻结的完整导出集合
    """

    public_modules = {
        "root": chromatix_next,
        "errors": errors,
        "optics": optics,
        "paraxial_ray_transfer": paraxial_ray_transfer,
        "source": source,
        "source_role": source_role,
        "surface": surface,
        "element": element,
        "element_role": element_role,
        "propagation": propagation,
        "propagation_role": propagation_role,
        "combination": combination,
        "combination_role": combination_role,
        "detection": detection,
        "detection_role": detection_role,
    }
    for module_name, expected_exports in EXPECTED_PUBLIC_EXPORTS.items():
        module = public_modules[module_name]
        if expected_exports is None:
            assert not hasattr(module, "__all__")
        else:
            assert tuple(module.__all__) == expected_exports


def test_public_functions_and_components_have_exact_signatures() -> None:
    """
    冻结公共函数与组件的参数顺序、参数种类和默认值
    """

    assert _public_function_and_component_signatures() == (
        EXPECTED_PUBLIC_SIGNATURES
    )


def test_public_budget_is_exact_after_directional_migration() -> None:
    """
    根模块保留两个生命周期入口并分别冻结动作、owner、enum 与 Encounter 清单
    """

    packages = (source, element, propagation, combination, detection)
    published_actions = frozenset(
        export_name
        for package in packages
        for export_name in package.__all__
        if inspect.isclass(getattr(package, export_name))
        and export_name not in {
            "Source",
            "Element",
            "Propagation",
            "Combination",
            "Detection",
            "ScalarAngularSpectrumDiagnostic",
        }
        and export_name not in EXPECTED_DIRECTIONAL_OWNERS
        and export_name not in EXPECTED_DIRECTIONAL_ENUMS
    )
    published_directional_owners = frozenset(
        name for name in element.__all__ if name in EXPECTED_DIRECTIONAL_OWNERS
    )
    published_directional_enums = frozenset(
        name for name in element.__all__ if name in EXPECTED_DIRECTIONAL_ENUMS
    )
    published_encounters = frozenset(
        name for name in optics.__all__ if name in EXPECTED_ENCOUNTER_REFERENCES
    )

    assert chromatix_next.__all__ == ["Workstation", "install_state"]
    assert published_actions == EXPECTED_ACTIONS
    assert len(published_actions) == 24
    assert published_directional_owners == EXPECTED_DIRECTIONAL_OWNERS
    assert published_directional_enums == EXPECTED_DIRECTIONAL_ENUMS
    assert published_encounters == EXPECTED_ENCOUNTER_REFERENCES


def test_directional_import_paths_replace_retired_splitter_paths_atomically() -> None:
    """
    新类型可从定义模块和正常公共路径导入，旧模块、公开属性与顶层转发均不存在

    """

    cube_module = importlib.import_module(
        "chromatix_next.optics.element.ideal_cube_beam_splitter"
    )
    mirror_module = importlib.import_module(
        "chromatix_next.optics.element.ideal_planar_mirror"
    )
    assembly_module = importlib.import_module("chromatix_next.optics.assembly")
    assert cube_module.CubeTerminal is CubeTerminal
    assert cube_module.CubeCoatingDiagonal is CubeCoatingDiagonal
    assert cube_module.IdealNonpolarizingCubeBeamSplitter is (
        IdealNonpolarizingCubeBeamSplitter
    )
    assert cube_module.IdealPolarizingCubeBeamSplitter is (
        IdealPolarizingCubeBeamSplitter
    )
    assert mirror_module.MirrorTerminal is MirrorTerminal
    assert mirror_module.IdealPlanarMirror is IdealPlanarMirror
    assert assembly_module.WaveEncounter is optics.WaveEncounter
    assert assembly_module.RayEncounter is optics.RayEncounter

    element_star: dict[str, object] = {}
    optics_star: dict[str, object] = {}
    exec("from chromatix_next.optics.element import *", {}, element_star)
    exec("from chromatix_next.optics import *", {}, optics_star)
    assert EXPECTED_DIRECTIONAL_OWNERS <= element_star.keys()
    assert EXPECTED_DIRECTIONAL_ENUMS <= element_star.keys()
    assert EXPECTED_ENCOUNTER_REFERENCES <= optics_star.keys()

    retired_stems = (
        "nonpolarizing" + "_beam_splitter",
        "polarizing" + "_beam_splitter",
        "nonpolarizing" + "_beam_splitter_at",
        "polarizing" + "_beam_splitter_at",
    )
    for stem in retired_stems:
        assert not hasattr(element, stem)
        assert not hasattr(chromatix_next, stem)
        assert importlib.util.find_spec(
            f"chromatix_next.optics.element.{stem}"
        ) is None
    for name in EXPECTED_DIRECTIONAL_OWNERS | EXPECTED_DIRECTIONAL_ENUMS:
        assert not hasattr(chromatix_next, name)
    for name in EXPECTED_ENCOUNTER_REFERENCES:
        assert not hasattr(chromatix_next, name)


def test_combination_ports_and_absent_alias_exports_are_exact() -> None:
    """
    两种组合以物理值命名输入端口且不保留退役的不相干别名
    """

    assert combination.CoherentCombination().input_ports == (
        "field_1",
        "field_2",
    )
    assert combination.IntensityCombination().input_ports == (
        "intensity_1",
        "intensity_2",
    )
    assert not hasattr(combination, "incoherent_combination")
    assert not hasattr(combination, "IncoherentCombination")
    assert "__getattr__" not in combination.__dict__


def test_remaining_plane_local_ray_action_publishes_exact_surface_signature() -> None:
    """
    保留的 Ray Retarder 函数与组件均显式要求 Plane 曲面
    """

    function_actions = (retarder_at,)
    component_actions = (RetarderAt,)
    for action in function_actions:
        surface = inspect.signature(action).parameters["surface"]
        assert surface.kind is inspect.Parameter.KEYWORD_ONLY
        assert surface.annotation == "Plane"
    for action in component_actions:
        surface = inspect.signature(action.__init__).parameters["surface"]
        assert surface.kind is inspect.Parameter.KEYWORD_ONLY
        assert surface.annotation == "Plane"


def test_public_enums_keep_their_exact_members() -> None:
    """
    发布枚举保留固定成员和值
    """

    assert {member.name: member.value for member in PolarizationRepresentation} == {
        "SCALAR": "scalar",
        "TRANSVERSE": "transverse",
        "FULL": "full",
    }
    assert {member.name: member.value for member in FieldNormalization} == {
        "RELATIVE": "relative",
        "POWER": "power",
    }
    assert {member.name: member.value for member in PropagationExterior} == {
        "PERIODIC": "periodic",
        "ISOLATED": "isolated",
    }
    assert {member.name: member.value for member in CubeTerminal} == {
        "LEFT": "left",
        "TOP": "top",
        "RIGHT": "right",
        "BOTTOM": "bottom",
    }
    assert {member.name: member.value for member in CubeCoatingDiagonal} == {
        "RISING": "rising",
        "FALLING": "falling",
    }
    assert {member.name: member.value for member in MirrorTerminal} == {
        "FRONT": "front",
    }
