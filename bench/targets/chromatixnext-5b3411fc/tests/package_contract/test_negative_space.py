from __future__ import annotations

from dataclasses import fields
import importlib
import importlib.util

import pytest

import chromatix_next
from chromatix_next import optics
from chromatix_next.optics import element
from chromatix_next.optics.field import OpticalField
from chromatix_next.optics.ray_bundle import RayBundle
from tests.architecture._negative_space_facts import (
    RETIRED_SPLITTER_MODULE_STEMS,
    RETIRED_SPLITTER_PUBLIC_NAMES,
)


def test_retired_splitter_modules_are_not_importable() -> None:
    """
    Definition modules and their private numerical implementation remain absent.
    """

    module_names = tuple(
        f"chromatix_next.optics.element.{stem}"
        for stem in RETIRED_SPLITTER_MODULE_STEMS
    ) + ("chromatix_next._numerics." + "beam_splitting",)
    for module_name in module_names:
        assert importlib.util.find_spec(module_name) is None
        with pytest.raises(ModuleNotFoundError) as rejected:
            importlib.import_module(module_name)
        assert rejected.value.name == module_name


def test_retired_splitter_names_are_unreachable_by_all_public_paths() -> None:
    """
    Direct, qualified, star, module, root, alias, and descendant paths are closed.
    """

    element_star: dict[str, object] = {}
    exec("from chromatix_next.optics.element import *", {}, element_star)
    for public_name in RETIRED_SPLITTER_PUBLIC_NAMES:
        definition_stem = (
            "polarizing_beam_splitter"
            if "Polarizing" in public_name
            else "nonpolarizing_beam_splitter"
        )
        direct_namespace: dict[str, object] = {}
        with pytest.raises(ModuleNotFoundError):
            exec(
                f"from chromatix_next.optics.element.{definition_stem} "
                f"import {public_name}",
                {},
                direct_namespace,
            )
        with pytest.raises(ImportError):
            exec(
                "from chromatix_next.optics.element import "
                f"{public_name} as retired_alias",
                {},
                {},
            )
        assert public_name not in element.__dict__
        assert public_name not in element_star
        assert public_name not in optics.__dict__
        assert public_name not in chromatix_next.__dict__
        assert not hasattr(element, public_name)


def test_public_negative_space_has_no_speculative_runtime_family() -> None:
    """
    Normal public modules expose no forbidden Root, base, registry, or runtime family.
    """

    public_names = {
        name
        for module in (chromatix_next, optics, element)
        for name in getattr(module, "__all__", ())
    }
    forbidden_fragments = (
        "OpticalState",
        "DirectionalElementBase",
        "TerminalBase",
        "Registry",
        "Capability",
        "NPort",
        "ScatteringMatrix",
        "Recurrent",
        "EvidenceGraph",
        "ExperimentRoot",
    )
    assert not {
        name
        for name in public_names
        if any(fragment in name for fragment in forbidden_fragments)
    }


def test_physical_values_and_occurrence_language_register_no_universal_state() -> None:
    """
    Public Physical Values have no pose/state wrapper and no retired state prefix.
    """

    forbidden_value_fields = {
        "pose",
        "reference_plane",
        "wave_reference_plane",
        "state",
        "optical_state",
    }
    for value_type in (OpticalField, RayBundle):
        assert forbidden_value_fields.isdisjoint(
            field.name for field in fields(value_type)
        )

    owners = (
        element.IdealNonpolarizingCubeBeamSplitter(
            origin=(0.0, 0.0, 0.0),
            route_right=(1.0, 0.0, 0.0),
            route_top=(0.0, 1.0, 0.0),
            coating_diagonal=element.CubeCoatingDiagonal.RISING,
            mixing_angle=0.25,
        ),
        element.IdealPolarizingCubeBeamSplitter(
            origin=(0.0, 0.0, 0.0),
            route_right=(1.0, 0.0, 0.0),
            route_top=(0.0, 1.0, 0.0),
            coating_diagonal=element.CubeCoatingDiagonal.RISING,
        ),
        element.IdealPlanarMirror(
            origin=(0.0, 0.0, 0.0),
            outward_normal=(1.0, 0.0, 0.0),
            transverse_up=(0.0, 0.0, 1.0),
        ),
    )
    retired_state_fragments = (
        "power_transmissivity",
        "transmitted_eigenstate",
        "encounter",
        "claim",
    )
    for owner in owners:
        assert not {
            key
            for key in owner.state_dict()
            if any(fragment in key for fragment in retired_state_fragments)
        }
