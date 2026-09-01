"""Measure the admitted Arbabi array across its complete focal interval."""

from __future__ import annotations

import json
import math
from pathlib import Path
from time import perf_counter

import numpy
import torch

from examples import select_metalens_benchmark_case
from metacraft.authority import Document
from metacraft.authority.session import AuthoritySession
from metacraft.canonical import encode_bytes
from metacraft.field.vector_angular_spectrum import (
    restore_vector_angular_spectrum_binding,
    survey_electromagnetic_field,
)
from metacraft.science._application_root import open_existing_application_root
from metacraft.science.conduct import _recall_frontier
from metacraft.science.metalens.aperture import Aperture
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.design import require_metalens_design
from metacraft.science.metalens.evidence import MetalensEvidence
from metacraft.science.metalens.focus import (
    FocalRegion,
    evaluate_vector_focus,
)


PILOT = Path(__file__).parent
APPLICATION_ROOT = PILOT / "acceptance" / "arbabi-live-root"
SUMMARY_PATH = PILOT / "acceptance" / "arbabi-focus-survey-summary.json"


def main() -> None:
    brief = select_metalens_benchmark_case(
        "arbabi-2015-high-na-propagation"
    ).brief
    opened = open_existing_application_root(APPLICATION_ROOT)
    authority = AuthoritySession(opened.authority)
    frontier, frontier_reference = _recall_frontier(
        authority,
        brief=brief,
        initial=compile_metalens(brief),
    )
    if frontier_reference is None or len(frontier.studies) != 1:
        raise RuntimeError("arbabi_frontier_missing")
    study = frontier.studies[0]
    evidence = MetalensEvidence(authority)
    field = evidence.restore_field(study)
    aperture_reference = evidence.fact(study, "aperture").reference
    aperture = Aperture.from_document(
        Document.from_bytes(evidence.fetch(aperture_reference))
    )
    binding = next(
        item
        for item in study.bindings
        if item.capability == "vector_angular_spectrum_propagation"
    )
    realization = restore_vector_angular_spectrum_binding(
        Document.from_bytes(authority.fetch(binding.reference))
    )
    design = require_metalens_design(study)
    expected_focus_m = float(design.focal_length_um) * 1e-6
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    survey_started = perf_counter()
    survey = survey_electromagnetic_field(
        field,
        distance_range_m=(0.8 * expected_focus_m, 1.2 * expected_focus_m),
        preferred_distance_m=expected_focus_m,
        realization=realization,
    )
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    survey_elapsed_seconds = perf_counter() - survey_started
    selected = survey.selected_propagation
    region = FocalRegion(
        wavelength_m=selected.field.wavelength_m,
        spacing_m=selected.field.surface.spacing_m,
        expected_focus_m=expected_focus_m,
        found_focus_m=selected.distance_m,
        observed_components=("x", "y", "z"),
        axial_distances_m=survey.distances_m,
        axial_peak_intensities=survey.peak_intensities,
        component_axial_peak_intensities=(
            survey.component_peak_intensities
        ),
        frame=selected.field.frame,
        medium=selected.field.medium,
        basis=selected.field.basis,
        electric_components=selected.field.electric_components,
        magnetic_components=selected.field.magnetic_components,
        source_references=selected.field.source_references,
        incident_reference_power=selected.input_longitudinal_power_w,
        transmitted_aperture_power={},
        vector_output_power_w=selected.output_longitudinal_power_w,
        realization=selected.realization,
    )
    focus = evaluate_vector_focus(
        region,
        numerical_aperture=float(design.numerical_aperture),
        propagation=selected,
    )
    intensity_components = {
        name: numpy.abs(selected.field.electric(name)) ** 2
        for name in ("x", "y", "z")
    }
    total_intensity = sum(intensity_components.values())
    peak_index = tuple(
        int(value)
        for value in numpy.unravel_index(
            numpy.argmax(total_intensity),
            total_intensity.shape,
        )
    )
    center = tuple((size - 1) / 2 for size in total_intensity.shape)
    peak_offset_m = math.hypot(
        (peak_index[0] - center[0]) * region.spacing_m,
        (peak_index[1] - center[1]) * region.spacing_m,
    )
    total_intensity_sum = float(numpy.sum(total_intensity))
    longitudinal_fraction = (
        float(numpy.sum(intensity_components["z"]))
        / total_intensity_sum
    )
    power_error = abs(
        selected.output_longitudinal_power_w
        - selected.input_longitudinal_power_w
    ) / selected.input_longitudinal_power_w
    summary = {
        "aperture_lattice_shape": list(aperture.is_occupied.shape),
        "aperture_occupied_site_count": aperture.site_count,
        "aperture_period_nm": aperture.spacing_nm,
        "axial_component_peaks": {
            name: [repr(value) for value in values]
            for name, values in survey.component_peak_intensities.items()
        },
        "benchmark_case": "arbabi-2015-high-na-propagation",
        "device": realization.device,
        "field_shape": list(field.surface.shape),
        "focus": focus.as_mapping(),
        "longitudinal_intensity_fraction": repr(longitudinal_fraction),
        "peak_index": list(peak_index),
        "peak_offset_m": repr(peak_offset_m),
        "relative_power_error": repr(power_error),
        "schema": "metacraft.acceptance.vector_focus_survey",
        "survey_elapsed_seconds": repr(survey_elapsed_seconds),
    }
    SUMMARY_PATH.write_bytes(encode_bytes(summary))
    print(json.dumps(summary, indent=2), flush=True)
    del selected
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
