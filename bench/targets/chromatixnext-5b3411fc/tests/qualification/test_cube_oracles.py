from __future__ import annotations

import ast
from collections import Counter
import math
from pathlib import Path

import pytest
import torch

from tests.qualification.cube_oracles import (
    ASYMMETRIC_RECTANGULAR_GRID,
    ROTATED_CUBE_POSE,
    TERMINAL_ORDER,
    OracleCoatingDiagonal,
    OracleRouteKind,
    OracleTerminal,
    coating_basis,
    coating_plane_normal,
    dense_all_real_balanced_adversary,
    dense_nbs_operator,
    dense_pbs_operator,
    explicit_terminal_permutations,
    geometry_pair_kinds,
    terminal_frame_fixtures,
)

EXPECTED_REFLECTIONS = {
    OracleCoatingDiagonal.RISING: {
        OracleTerminal.LEFT: OracleTerminal.TOP,
        OracleTerminal.TOP: OracleTerminal.LEFT,
        OracleTerminal.RIGHT: OracleTerminal.BOTTOM,
        OracleTerminal.BOTTOM: OracleTerminal.RIGHT,
    },
    OracleCoatingDiagonal.FALLING: {
        OracleTerminal.LEFT: OracleTerminal.BOTTOM,
        OracleTerminal.TOP: OracleTerminal.RIGHT,
        OracleTerminal.RIGHT: OracleTerminal.TOP,
        OracleTerminal.BOTTOM: OracleTerminal.LEFT,
    },
}

EXPECTED_TRANSMISSIONS = {
    OracleTerminal.LEFT: OracleTerminal.RIGHT,
    OracleTerminal.TOP: OracleTerminal.BOTTOM,
    OracleTerminal.RIGHT: OracleTerminal.LEFT,
    OracleTerminal.BOTTOM: OracleTerminal.TOP,
}


def _terminal_slice(terminal: OracleTerminal) -> slice:
    index = TERMINAL_ORDER.index(terminal)
    return slice(2 * index, 2 * index + 2)


def _real_vector(values: tuple[float, float, float]) -> torch.Tensor:
    return torch.tensor(values, dtype=torch.float64)


@pytest.mark.parametrize("diagonal", tuple(OracleCoatingDiagonal))
def test_coating_geometry_enumerates_all_terminal_pairs(
    diagonal: OracleCoatingDiagonal,
) -> None:
    """
    Both coating planes classify every pair and every exact structural zero
    """

    pair_kinds = geometry_pair_kinds(diagonal)
    assert len(pair_kinds) == 16
    assert Counter(pair_kinds.values()) == {
        OracleRouteKind.TRANSMISSION: 4,
        OracleRouteKind.REFLECTION: 4,
        OracleRouteKind.STRUCTURAL_ZERO: 8,
    }
    for incident in TERMINAL_ORDER:
        assert pair_kinds[
            incident,
            EXPECTED_TRANSMISSIONS[incident],
        ] is OracleRouteKind.TRANSMISSION
        assert pair_kinds[
            incident,
            EXPECTED_REFLECTIONS[diagonal][incident],
        ] is OracleRouteKind.REFLECTION
        structural_zeros = {
            outgoing
            for outgoing in TERMINAL_ORDER
            if pair_kinds[incident, outgoing] is OracleRouteKind.STRUCTURAL_ZERO
        }
        assert incident in structural_zeros
        assert len(structural_zeros) == 2


@pytest.mark.parametrize("diagonal", tuple(OracleCoatingDiagonal))
def test_explicit_terminal_matrices_match_independent_coating_geometry(
    diagonal: OracleCoatingDiagonal,
) -> None:
    """
    Explicit permutation locations agree with specular coating geometry
    """

    pair_kinds = geometry_pair_kinds(diagonal)
    transmission, reflection = explicit_terminal_permutations(diagonal)
    identity = torch.eye(4, dtype=torch.complex128)
    assert torch.equal(transmission.mH @ transmission, identity)
    assert torch.equal(reflection.mH @ reflection, identity)
    assert torch.equal(transmission @ reflection, reflection @ transmission)
    for input_index, incident in enumerate(TERMINAL_ORDER):
        for output_index, outgoing in enumerate(TERMINAL_ORDER):
            kind = pair_kinds[incident, outgoing]
            expected_transmission = 1.0 if kind is OracleRouteKind.TRANSMISSION else 0.0
            expected_reflection = 1.0 if kind is OracleRouteKind.REFLECTION else 0.0
            assert transmission[output_index, input_index] == expected_transmission
            assert reflection[output_index, input_index] == expected_reflection


@pytest.mark.parametrize("diagonal", tuple(OracleCoatingDiagonal))
@pytest.mark.parametrize(
    "mixing_angle",
    (
        0.0,
        math.pi / 11.0,
        math.pi / 4.0,
        -math.pi / 3.0,
        2.5 * math.pi,
    ),
)
def test_dense_nbs_is_unitary_at_several_finite_angles(
    diagonal: OracleCoatingDiagonal,
    mixing_angle: float,
) -> None:
    """
    The complete complex NBS law is unitary beyond one-input checks
    """

    operator = dense_nbs_operator(diagonal, mixing_angle)
    identity = torch.eye(8, dtype=torch.complex128)
    torch.testing.assert_close(
        operator.mH @ operator,
        identity,
        atol=5.0e-13,
        rtol=0.0,
    )


@pytest.mark.parametrize("diagonal", tuple(OracleCoatingDiagonal))
def test_dense_nbs_preserves_random_complex_multi_input_power(
    diagonal: OracleCoatingDiagonal,
) -> None:
    """
    Random simultaneous Terminal/Jones inputs retain total modal power
    """

    generator = torch.Generator(device="cpu")
    generator.manual_seed(20260824)
    real = torch.randn((41, 8), generator=generator, dtype=torch.float64)
    imaginary = torch.randn((41, 8), generator=generator, dtype=torch.float64)
    inputs = torch.complex(real, imaginary)
    for mixing_angle in (-0.91, 0.17, math.pi / 4.0, 1.83):
        operator = dense_nbs_operator(diagonal, mixing_angle)
        outputs = torch.einsum("ij,bj->bi", operator, inputs)
        input_power = inputs.abs().square().sum(dim=-1)
        output_power = outputs.abs().square().sum(dim=-1)
        torch.testing.assert_close(
            output_power,
            input_power,
            atol=5.0e-13,
            rtol=5.0e-13,
        )


@pytest.mark.parametrize("diagonal", tuple(OracleCoatingDiagonal))
def test_ideal_pbs_routes_p_and_s_for_every_incident_terminal(
    diagonal: OracleCoatingDiagonal,
) -> None:
    """
    Ideal p and s states occupy only their geometric output Terminals
    """

    operator = dense_pbs_operator(diagonal)
    pair_kinds = geometry_pair_kinds(diagonal)
    for incident in TERMINAL_ORDER:
        p_input = torch.zeros(8, dtype=torch.complex128)
        s_input = torch.zeros(8, dtype=torch.complex128)
        p_input[_terminal_slice(incident).start] = 1.0
        s_input[_terminal_slice(incident).start + 1] = 1.0
        p_output = operator @ p_input
        s_output = operator @ s_input
        for outgoing in TERMINAL_ORDER:
            block = _terminal_slice(outgoing)
            kind = pair_kinds[incident, outgoing]
            if kind is OracleRouteKind.TRANSMISSION:
                assert torch.equal(
                    p_output[block],
                    torch.tensor([1.0, 0.0], dtype=torch.complex128),
                )
                assert torch.count_nonzero(s_output[block]) == 0
            elif kind is OracleRouteKind.REFLECTION:
                assert torch.equal(
                    s_output[block],
                    torch.tensor([0.0, 1.0j], dtype=torch.complex128),
                )
                assert torch.count_nonzero(p_output[block]) == 0
            else:
                assert torch.count_nonzero(p_output[block]) == 0
                assert torch.count_nonzero(s_output[block]) == 0


@pytest.mark.parametrize("diagonal", tuple(OracleCoatingDiagonal))
def test_ideal_pbs_is_passive_and_excludes_every_structural_zero(
    diagonal: OracleCoatingDiagonal,
) -> None:
    """
    The full PBS is lossless while geometric zero blocks stay exact zero
    """

    operator = dense_pbs_operator(diagonal)
    gram = operator.mH @ operator
    identity = torch.eye(8, dtype=torch.complex128)
    torch.testing.assert_close(gram, identity, atol=5.0e-13, rtol=0.0)
    largest_power_gain = torch.linalg.eigvalsh(gram).amax()
    assert float(largest_power_gain) <= 1.0 + 5.0e-13
    pair_kinds = geometry_pair_kinds(diagonal)
    for incident in TERMINAL_ORDER:
        for outgoing in TERMINAL_ORDER:
            block = operator[
                _terminal_slice(outgoing),
                _terminal_slice(incident),
            ]
            if pair_kinds[incident, outgoing] is OracleRouteKind.STRUCTURAL_ZERO:
                assert torch.count_nonzero(block) == 0


@pytest.mark.parametrize("diagonal", tuple(OracleCoatingDiagonal))
def test_all_real_balanced_adversary_changes_legal_power_two_to_four(
    diagonal: OracleCoatingDiagonal,
) -> None:
    """
    A missing reflection quadrature constructively doubles legal input power
    """

    first_incident = OracleTerminal.TOP
    second_incident = OracleTerminal.RIGHT
    if diagonal is OracleCoatingDiagonal.FALLING:
        first_incident = OracleTerminal.LEFT
        second_incident = OracleTerminal.TOP
    inputs = torch.zeros(8, dtype=torch.complex128)
    inputs[_terminal_slice(first_incident).start] = 1.0
    inputs[_terminal_slice(second_incident).start] = 1.0
    assert float(inputs.abs().square().sum()) == 2.0
    adversarial_outputs = dense_all_real_balanced_adversary(diagonal) @ inputs
    physical_outputs = dense_nbs_operator(diagonal, math.pi / 4.0) @ inputs
    assert float(adversarial_outputs.abs().square().sum()) == pytest.approx(4.0)
    assert float(physical_outputs.abs().square().sum()) == pytest.approx(2.0)


@pytest.mark.parametrize("diagonal", tuple(OracleCoatingDiagonal))
def test_rotated_geometry_and_reverse_incidence_fixtures_are_covariant(
    diagonal: OracleCoatingDiagonal,
) -> None:
    """
    A non-axis-aligned pose keeps topology and both directional bases sound
    """

    rotated_kinds = geometry_pair_kinds(
        diagonal,
        route_right=ROTATED_CUBE_POSE.route_right,
        route_top=ROTATED_CUBE_POSE.route_top,
    )
    assert rotated_kinds == geometry_pair_kinds(diagonal)
    normal = coating_plane_normal(
        diagonal,
        route_right=ROTATED_CUBE_POSE.route_right,
        route_top=ROTATED_CUBE_POSE.route_top,
    )
    identity = torch.eye(3, dtype=torch.float64)
    for frame in terminal_frame_fixtures():
        incident_direction = _real_vector(frame.incident_direction)
        incident_horizontal = _real_vector(frame.incident_horizontal)
        incident_vertical = _real_vector(frame.incident_vertical)
        outgoing_direction = _real_vector(frame.outgoing_direction)
        outgoing_horizontal = _real_vector(frame.outgoing_horizontal)
        outgoing_vertical = _real_vector(frame.outgoing_vertical)
        incident_basis = torch.stack(
            (incident_horizontal, incident_vertical, incident_direction),
            dim=1,
        )
        outgoing_basis = torch.stack(
            (outgoing_horizontal, outgoing_vertical, outgoing_direction),
            dim=1,
        )
        torch.testing.assert_close(
            incident_basis.mT @ incident_basis,
            identity,
            atol=5.0e-15,
            rtol=0.0,
        )
        torch.testing.assert_close(
            outgoing_basis.mT @ outgoing_basis,
            identity,
            atol=5.0e-15,
            rtol=0.0,
        )
        assert torch.linalg.det(incident_basis) > 0.0
        assert torch.linalg.det(outgoing_basis) > 0.0
        torch.testing.assert_close(
            incident_direction,
            -outgoing_direction,
            atol=0.0,
            rtol=0.0,
        )
        torch.testing.assert_close(
            incident_horizontal,
            -outgoing_horizontal,
            atol=0.0,
            rtol=0.0,
        )
        torch.testing.assert_close(
            incident_vertical,
            outgoing_vertical,
            atol=0.0,
            rtol=0.0,
        )
        for direction in (incident_direction, outgoing_direction):
            s_axis, p_axis = coating_basis(direction, normal)
            assert abs(float(torch.dot(s_axis, direction))) < 5.0e-15
            assert abs(float(torch.dot(p_axis, direction))) < 5.0e-15
            torch.testing.assert_close(
                torch.linalg.cross(s_axis, p_axis),
                direction,
                atol=5.0e-15,
                rtol=0.0,
            )


def test_asymmetric_rectangular_grid_fixture_exposes_axis_and_mirror_errors() -> None:
    """
    The later adapter fixture distinguishes swaps and both mirror directions
    """

    fixture = ASYMMETRIC_RECTANGULAR_GRID
    labels = torch.tensor(fixture.sample_labels, dtype=torch.int64)
    assert tuple(labels.shape) == fixture.sample_counts
    assert fixture.sample_counts[0] != fixture.sample_counts[1]
    assert fixture.sample_spacing[0] != fixture.sample_spacing[1]
    swapped = labels.mT.contiguous()
    mirrored_y = labels.flip(0)
    mirrored_x = labels.flip(1)
    assert tuple(swapped.shape) == fixture.sample_counts[::-1]
    assert not torch.equal(labels, mirrored_y)
    assert not torch.equal(labels, mirrored_x)
    assert not torch.equal(mirrored_y, mirrored_x)
    assert torch.equal(swapped.mT.contiguous(), labels)
    y_positions = (
        torch.arange(fixture.sample_counts[0], dtype=torch.float64)
        * fixture.sample_spacing[0]
        + fixture.first_sample_position[0]
    )
    x_positions = (
        torch.arange(fixture.sample_counts[1], dtype=torch.float64)
        * fixture.sample_spacing[1]
        + fixture.first_sample_position[1]
    )
    assert y_positions.numel() == 3
    assert x_positions.numel() == 5
    assert not torch.equal(y_positions, x_positions[:3])


def test_cube_oracle_has_no_production_dependency_or_reverse_import() -> None:
    """
    The red-team reference stays test-owned on both dependency directions
    """

    project_root = Path(__file__).resolve().parents[2]
    oracle_path = project_root / "tests" / "qualification" / "cube_oracles.py"
    oracle_tree = ast.parse(oracle_path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(oracle_tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
    assert not any(
        module == "chromatix_next" or module.startswith("chromatix_next.")
        for module in imported_modules
    )
    reverse_imports = []
    for production_path in (project_root / "src").rglob("*.py"):
        source = production_path.read_text(encoding="utf-8")
        if "tests.qualification" in source or "cube_oracles" in source:
            reverse_imports.append(production_path.relative_to(project_root).as_posix())
    assert not reverse_imports
