from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

import torch


class OracleTerminal(str, Enum):
    """
    Test-owned names for the four physical cube interfaces
    """

    LEFT = "left"
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"


class OracleCoatingDiagonal(str, Enum):
    """
    Test-owned coating-plane orientations
    """

    RISING = "rising"
    FALLING = "falling"


class OracleRouteKind(str, Enum):
    """
    Independent geometric classification of one Terminal pair
    """

    TRANSMISSION = "transmission"
    REFLECTION = "reflection"
    STRUCTURAL_ZERO = "structural_zero"


@dataclass(frozen=True)
class CubePoseFixture:
    """
    Non-axis-aligned orthonormal owner pose for covariance checks
    """

    route_right: tuple[float, float, float]
    route_top: tuple[float, float, float]


@dataclass(frozen=True)
class TerminalFrameFixture:
    """
    Incoming and outgoing right-handed bases at one Terminal
    """

    terminal: OracleTerminal
    incident_direction: tuple[float, float, float]
    incident_horizontal: tuple[float, float, float]
    incident_vertical: tuple[float, float, float]
    outgoing_direction: tuple[float, float, float]
    outgoing_horizontal: tuple[float, float, float]
    outgoing_vertical: tuple[float, float, float]


@dataclass(frozen=True)
class RectangularGridFixture:
    """
    Asymmetric non-centred samples that expose axis and sign mistakes
    """

    sample_counts: tuple[int, int]
    sample_spacing: tuple[float, float]
    first_sample_position: tuple[float, float]
    sample_labels: tuple[tuple[int, ...], ...]


TERMINAL_ORDER = (
    OracleTerminal.LEFT,
    OracleTerminal.TOP,
    OracleTerminal.RIGHT,
    OracleTerminal.BOTTOM,
)

ROTATED_CUBE_POSE = CubePoseFixture(
    route_right=(
        1.0 / math.sqrt(2.0),
        1.0 / math.sqrt(2.0),
        0.0,
    ),
    route_top=(
        -1.0 / math.sqrt(6.0),
        1.0 / math.sqrt(6.0),
        2.0 / math.sqrt(6.0),
    ),
)

ASYMMETRIC_RECTANGULAR_GRID = RectangularGridFixture(
    sample_counts=(3, 5),
    sample_spacing=(7.0e-6, 11.0e-6),
    first_sample_position=(-13.0e-6, 19.0e-6),
    sample_labels=(
        (101, 103, 107, 109, 113),
        (127, 131, 137, 139, 149),
        (151, 157, 163, 167, 173),
    ),
)


def _as_real_vector(values: tuple[float, float, float]) -> torch.Tensor:
    return torch.tensor(values, dtype=torch.float64)


def _as_tuple(vector: torch.Tensor) -> tuple[float, float, float]:
    return tuple(float(value) for value in vector)  # type: ignore[return-value]


def _unit(vector: torch.Tensor) -> torch.Tensor:
    return vector / torch.linalg.vector_norm(vector)


def _outward_directions(
    route_right: torch.Tensor,
    route_top: torch.Tensor,
) -> dict[OracleTerminal, torch.Tensor]:
    return {
        OracleTerminal.LEFT: -route_right,
        OracleTerminal.TOP: route_top,
        OracleTerminal.RIGHT: route_right,
        OracleTerminal.BOTTOM: -route_top,
    }


def _matching_terminal(
    direction: torch.Tensor,
    outward_directions: dict[OracleTerminal, torch.Tensor],
) -> OracleTerminal:
    alignments = torch.stack(
        [
            torch.dot(direction, outward_directions[terminal])
            for terminal in TERMINAL_ORDER
        ],
    )
    index = int(torch.argmax(alignments).item())
    assert float(alignments[index]) > 1.0 - 64.0 * torch.finfo(torch.float64).eps
    return TERMINAL_ORDER[index]


def coating_plane_normal(
    coating_diagonal: OracleCoatingDiagonal,
    *,
    route_right: tuple[float, float, float] = (1.0, 0.0, 0.0),
    route_top: tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> torch.Tensor:
    """
    Derive the coating normal from owner axes and diagonal geometry
    """

    right = _as_real_vector(route_right)
    top = _as_real_vector(route_top)
    top_sign = -1.0 if coating_diagonal is OracleCoatingDiagonal.RISING else 1.0
    return _unit(right + top_sign * top)


def coating_basis(
    direction: torch.Tensor,
    coating_normal: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Derive the right-handed coating s/p basis for one direction
    """

    s_axis = _unit(torch.linalg.cross(coating_normal, direction))
    p_axis = torch.linalg.cross(direction, s_axis)
    return s_axis, p_axis


def geometry_pair_kinds(
    coating_diagonal: OracleCoatingDiagonal,
    *,
    route_right: tuple[float, float, float] = (1.0, 0.0, 0.0),
    route_top: tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> dict[tuple[OracleTerminal, OracleTerminal], OracleRouteKind]:
    """
    Classify all sixteen pairs by straight and specular geometry
    """

    right = _unit(_as_real_vector(route_right))
    top = _unit(_as_real_vector(route_top))
    normal = coating_plane_normal(
        coating_diagonal,
        route_right=route_right,
        route_top=route_top,
    )
    outward = _outward_directions(right, top)
    result: dict[tuple[OracleTerminal, OracleTerminal], OracleRouteKind] = {}
    for incident_terminal in TERMINAL_ORDER:
        incident_direction = -outward[incident_terminal]
        transmitted_terminal = _matching_terminal(incident_direction, outward)
        reflected_direction = (
            incident_direction
            - 2.0 * torch.dot(incident_direction, normal) * normal
        )
        reflected_terminal = _matching_terminal(reflected_direction, outward)
        for outgoing_terminal in TERMINAL_ORDER:
            pair = (incident_terminal, outgoing_terminal)
            if outgoing_terminal is transmitted_terminal:
                result[pair] = OracleRouteKind.TRANSMISSION
            elif outgoing_terminal is reflected_terminal:
                result[pair] = OracleRouteKind.REFLECTION
            else:
                result[pair] = OracleRouteKind.STRUCTURAL_ZERO
    return result


def terminal_frame_fixtures(
    pose: CubePoseFixture = ROTATED_CUBE_POSE,
) -> tuple[TerminalFrameFixture, ...]:
    """
    Build reverse-incidence Terminal frames for a rotated owner
    """

    right = _unit(_as_real_vector(pose.route_right))
    top = _unit(_as_real_vector(pose.route_top))
    vertical = _unit(torch.linalg.cross(right, top))
    outward = _outward_directions(right, top)
    frames: list[TerminalFrameFixture] = []
    for terminal in TERMINAL_ORDER:
        outgoing_direction = outward[terminal]
        incident_direction = -outgoing_direction
        incident_horizontal = torch.linalg.cross(vertical, incident_direction)
        outgoing_horizontal = torch.linalg.cross(vertical, outgoing_direction)
        frames.append(
            TerminalFrameFixture(
                terminal=terminal,
                incident_direction=_as_tuple(incident_direction),
                incident_horizontal=_as_tuple(incident_horizontal),
                incident_vertical=_as_tuple(vertical),
                outgoing_direction=_as_tuple(outgoing_direction),
                outgoing_horizontal=_as_tuple(outgoing_horizontal),
                outgoing_vertical=_as_tuple(vertical),
            ),
        )
    return tuple(frames)


def explicit_terminal_permutations(
    coating_diagonal: OracleCoatingDiagonal,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Return explicit row-output, column-input transmission/reflection matrices
    """

    transmission = torch.tensor(
        [
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ],
        dtype=torch.complex128,
    )
    if coating_diagonal is OracleCoatingDiagonal.RISING:
        reflection_values = [
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
    else:
        reflection_values = [
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
        ]
    reflection = torch.tensor(reflection_values, dtype=torch.complex128)
    return transmission, reflection


def dense_nbs_operator(
    coating_diagonal: OracleCoatingDiagonal,
    mixing_angle: float,
) -> torch.Tensor:
    """
    Construct the explicit ideal Jones-neutral 8-by-8 NBS operator
    """

    transmission, reflection = explicit_terminal_permutations(coating_diagonal)
    polarization_identity = torch.eye(2, dtype=torch.complex128)
    return (
        math.cos(mixing_angle) * torch.kron(transmission, polarization_identity)
        + 1j
        * math.sin(mixing_angle)
        * torch.kron(reflection, polarization_identity)
    )


def dense_pbs_operator(
    coating_diagonal: OracleCoatingDiagonal,
) -> torch.Tensor:
    """
    Construct the explicit ideal p-transmit, s-reflect 8-by-8 PBS operator
    """

    transmission, reflection = explicit_terminal_permutations(coating_diagonal)
    p_projector = torch.tensor(
        [
            [1.0, 0.0],
            [0.0, 0.0],
        ],
        dtype=torch.complex128,
    )
    s_projector = torch.tensor(
        [
            [0.0, 0.0],
            [0.0, 1.0],
        ],
        dtype=torch.complex128,
    )
    return torch.kron(transmission, p_projector) + 1j * torch.kron(
        reflection,
        s_projector,
    )


def dense_all_real_balanced_adversary(
    coating_diagonal: OracleCoatingDiagonal,
) -> torch.Tensor:
    """
    Construct the forbidden balanced model with no reflection quadrature
    """

    transmission, reflection = explicit_terminal_permutations(coating_diagonal)
    polarization_identity = torch.eye(2, dtype=torch.complex128)
    scale = 1.0 / math.sqrt(2.0)
    return scale * torch.kron(
        transmission + reflection,
        polarization_identity,
    )
