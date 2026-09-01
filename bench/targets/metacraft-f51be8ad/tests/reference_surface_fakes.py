from __future__ import annotations

import cmath
import math
from typing import Any


def bounded_reference_surface(session: Any) -> dict[str, object]:
    """
    Return a bounded periodic reference surface from a fake solver session.
    """

    objects = session._objects
    grating = objects["grating_response"]
    atom = objects["meta_atom"]
    period_nm = int(grating["span_x_nm"])
    transmission_plane_nm = (
        int(grating["position_z_nm"])
        + int(grating["span_z_nm"]) // 2
    )
    input_angle = int(grating["polarization_angle_degrees"])
    if "diameter_nm" in atom or "width_nm" in atom:
        feature_nm = int(atom.get("diameter_nm", atom.get("width_nm")))
        phase = math.tau * ((feature_nm // 10) % 16) / 16
        electric_x = 0.95 * cmath.exp(1j * phase)
        electric_y = 0j
    elif input_angle == 0:
        electric_x = 1 + 0j
        electric_y = 0j
    else:
        electric_x = 0j
        electric_y = -1 + 0j
    return {
        "electric_components": {
            "x": _complex_patch(electric_x),
            "y": _complex_patch(electric_y),
            "z": _complex_patch(0j),
        },
        "frame": {
            "normal_axis": "z",
            "propagation_direction": "positive",
            "sample_order": ["y", "x"],
        },
        "incident_reference_power": "1",
        "medium": "transmission medium",
        "order_regime": "multi order",
        "output_basis": "cartesian",
        "requested_input_basis": (
            "x linear" if input_angle == 0 else "y linear"
        ),
        "surface": {
            "position_m": format(
                transmission_plane_nm * 1e-9,
                ".17g",
            ),
            "x_coordinates_m": _closed_axis(period_nm),
            "y_coordinates_m": _closed_axis(period_nm),
        },
        "transmitted_power": (
            "0.9025"
            if "diameter_nm" in atom or "width_nm" in atom
            else "1"
        ),
        "wavelength_m": format(
            int(grating["start_wavelength_nm"]) * 1e-9,
            ".17g",
        ),
    }


def _closed_axis(period_nm: int) -> list[str]:
    half_period_m = period_nm * 1e-9 / 2
    return [
        format(-half_period_m, ".17g"),
        "0",
        format(half_period_m, ".17g"),
    ]


def _complex_patch(value: complex) -> dict[str, list[list[float]]]:
    return {
        "imaginary": [[value.imag] * 3 for _ in range(3)],
        "real": [[value.real] * 3 for _ in range(3)],
    }
