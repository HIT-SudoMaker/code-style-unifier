"""Form the admitted Arbabi field and test one nominal vector-ASM plane."""

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
    propagate_electromagnetic_field,
    restore_vector_angular_spectrum_binding,
)
from metacraft.science._application_root import open_existing_application_root
from metacraft.science.conduct import _recall_frontier, _try_admit_frontier
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.conduct import (
    advance_metalens,
    prepare_metalens_study,
)
from metacraft.science.metalens.aperture import Aperture
from metacraft.science.metalens.design import require_metalens_design
from metacraft.science.metalens.evidence import MetalensEvidence


PILOT = Path(__file__).parent
APPLICATION_ROOT = PILOT / "acceptance" / "arbabi-live-root"
SUMMARY_PATH = PILOT / "acceptance" / "arbabi-nominal-vector-asm-summary.json"


def main() -> None:
    brief = select_metalens_benchmark_case(
        "arbabi-2015-high-na-propagation"
    ).brief
    opened = open_existing_application_root(APPLICATION_ROOT)
    session = AuthoritySession(opened.authority)
    frontier, frontier_reference = _recall_frontier(
        session,
        brief=brief,
        initial=compile_metalens(brief),
    )
    if frontier_reference is None or len(frontier.studies) != 1:
        raise RuntimeError("arbabi_frontier_missing")
    study = frontier.studies[0]

    prepared = prepare_metalens_study(
        study,
        session=session,
        periodic_response=None,
        materials=None,
    )
    if prepared.identity != study.identity:
        frontier, frontier_reference = _checkpoint(
            session,
            frontier,
            frontier_reference,
            study,
            prepared,
        )
        study = prepared

    while True:
        if not study.ready_tasks:
            raise RuntimeError("arbabi_field_task_missing")
        task = study.ready_tasks[0]
        print(f"advance={task.method}:{task.claim}", flush=True)
        if task.method == "propagate_field":
            break
        successors = advance_metalens(
            study,
            session=session,
            periodic_response=None,
            materials=None,
        )
        if len(successors) != 1 or successors[0].identity == study.identity:
            raise RuntimeError("arbabi_local_advance_incomplete")
        successor = successors[0]
        frontier, frontier_reference = _checkpoint(
            session,
            frontier,
            frontier_reference,
            study,
            successor,
        )
        study = successor

    evidence = MetalensEvidence(session)
    aperture_reference = evidence.fact(study, "aperture").reference
    aperture = Aperture.from_document(
        Document.from_bytes(evidence.fetch(aperture_reference))
    )
    field = evidence.restore_field(study)
    binding = next(
        item
        for item in study.bindings
        if item.capability == "vector_angular_spectrum_propagation"
    )
    realization = restore_vector_angular_spectrum_binding(
        Document.from_bytes(session.fetch(binding.reference))
    )
    design = require_metalens_design(study)
    nominal_distance_m = float(design.focal_length_um) * 1e-6
    print(f"field_shape={field.surface.shape}", flush=True)
    print(f"field_spacing_m={field.surface.spacing_m!r}", flush=True)
    print(f"nominal_distance_m={nominal_distance_m!r}", flush=True)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    propagation_started = perf_counter()
    propagation = propagate_electromagnetic_field(
        field,
        distance_m=nominal_distance_m,
        realization=realization,
    )
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    propagation_elapsed_seconds = perf_counter() - propagation_started

    components = {
        name: propagation.field.electric(name)
        for name in ("x", "y", "z")
    }
    if not all(numpy.isfinite(values).all() for values in components.values()):
        raise RuntimeError("arbabi_vector_field_not_finite")
    intensity = sum(numpy.abs(values) ** 2 for values in components.values())
    peak_index = tuple(int(value) for value in numpy.unravel_index(
        numpy.argmax(intensity),
        intensity.shape,
    ))
    center = tuple((size - 1) / 2 for size in intensity.shape)
    peak_offset_m = math.hypot(
        (peak_index[0] - center[0]) * field.surface.spacing_m,
        (peak_index[1] - center[1]) * field.surface.spacing_m,
    )
    horizontal_width_m = _half_maximum_width(
        intensity[peak_index[0], :],
        peak_index[1],
        field.surface.spacing_m,
    )
    vertical_width_m = _half_maximum_width(
        intensity[:, peak_index[1]],
        peak_index[0],
        field.surface.spacing_m,
    )
    input_power = propagation.input_longitudinal_power_w
    output_power = propagation.output_longitudinal_power_w
    relative_power_error = abs(output_power - input_power) / input_power
    if relative_power_error > 1e-10:
        raise RuntimeError("arbabi_vector_power_not_conserved")
    total_intensity = float(numpy.sum(intensity))
    longitudinal_fraction = (
        float(numpy.sum(numpy.abs(components["z"]) ** 2))
        / total_intensity
    )
    expected_paraxial_width_m = (
        0.514
        * float(design.wavelength_nm)
        * 1e-9
        / float(design.numerical_aperture)
    )
    summary = {
        "aperture_lattice_shape": list(aperture.is_occupied.shape),
        "aperture_occupied_site_count": aperture.site_count,
        "aperture_period_nm": aperture.spacing_nm,
        "benchmark_case": "arbabi-2015-high-na-propagation",
        "device": realization.device,
        "field_shape": list(field.surface.shape),
        "field_spacing_m": repr(field.surface.spacing_m),
        "finite_components": True,
        "horizontal_half_maximum_width_m": repr(horizontal_width_m),
        "input_longitudinal_power_w": repr(input_power),
        "longitudinal_intensity_fraction": repr(longitudinal_fraction),
        "nominal_distance_m": repr(nominal_distance_m),
        "output_longitudinal_power_w": repr(output_power),
        "paraxial_width_reference_m": repr(expected_paraxial_width_m),
        "peak_index": list(peak_index),
        "peak_offset_m": repr(peak_offset_m),
        "propagation_elapsed_seconds": repr(propagation_elapsed_seconds),
        "relative_power_error": repr(relative_power_error),
        "schema": "metacraft.acceptance.nominal_vector_asm",
        "vertical_half_maximum_width_m": repr(vertical_width_m),
    }
    SUMMARY_PATH.write_bytes(encode_bytes(summary))
    print(json.dumps(summary, indent=2), flush=True)
    del propagation
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _checkpoint(
    session: AuthoritySession,
    frontier,
    frontier_reference,
    predecessor,
    successor,
):
    proposed = frontier.replace(predecessor.identity, (successor,))
    admitted = _try_admit_frontier(
        session,
        proposed,
        supersedes=frontier_reference,
    )
    if admitted is None:
        raise RuntimeError("arbabi_frontier_admission_conflict")
    return proposed, admitted


def _half_maximum_width(
    values: numpy.ndarray,
    peak: int,
    spacing_m: float,
) -> float:
    threshold = float(values[peak]) / 2
    lower = peak
    while lower > 0 and values[lower - 1] >= threshold:
        lower -= 1
    upper = peak
    while upper + 1 < values.size and values[upper + 1] >= threshold:
        upper += 1
    return (upper - lower + 1) * spacing_m


if __name__ == "__main__":
    main()
