from __future__ import annotations

from itertools import combinations

import pytest
import torch

from chromatix_next import install_state
from chromatix_next.errors import OpticalRuntimeError
import chromatix_next.optics as optics
from chromatix_next.optics import Assembly
import chromatix_next.optics.element as element
from chromatix_next.optics.element.ideal_cube_beam_splitter import (
    CubeCoatingDiagonal,
    CubeTerminal,
)
from chromatix_next.optics.field import _SourceLineage
from tests.assembly.test_wave_cube_encounters import (
    _constant_envelope,
    _cube,
    _grid,
    _ps_to_local_hv,
    _run_cube,
    _source,
)

_TERMINALS = tuple(CubeTerminal)
_WAVELENGTH = 632.8e-9


def _all_incident_masks() -> tuple[tuple[CubeTerminal, ...], ...]:
    # 返回四个 Terminal 的十五个非空组合
    return tuple(
        mask
        for size in range(1, len(_TERMINALS) + 1)
        for mask in combinations(_TERMINALS, size)
    )


def test_reciprocity_outside_the_closed_operator_relation_is_not_claimed() -> None:
    """
    把当前闭合 Terminal 关系之外的 reciprocity 明确保持为未主张

    """
    admission_boundary = {
        "reciprocity_outside_closed_terminal_operator_relation": "NOT_CLAIMED",
    }
    public_names = set(optics.__all__) | set(element.__all__)

    assert admission_boundary == {
        "reciprocity_outside_closed_terminal_operator_relation": "NOT_CLAIMED",
    }
    assert not any("reciproc" in name.lower() for name in public_names)


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
@pytest.mark.parametrize("incident_mask", _all_incident_masks())
def test_shared_owner_gradient_covers_every_mask_jones_and_unequal_opr(
    diagonal: CubeCoatingDiagonal,
    incident_mask: tuple[CubeTerminal, ...],
) -> None:
    """
    证明每个 Wave incidence mask 都保留 Jones、OPR 与共享 owner 梯度

    """
    angle = torch.nn.Parameter(torch.tensor(0.31, dtype=torch.float64))
    owner = _cube(diagonal, mixing_angle=angle)
    lineage = _SourceLineage()
    envelopes = {
        terminal: _constant_envelope(
            horizontal=complex(0.71 + 0.23 * index, 0.17 - 0.09 * index),
            vertical=complex(0.37 + 0.19 * index, -0.29 + 0.07 * index),
            requires_grad=True,
        )
        for index, terminal in enumerate(incident_mask)
    }
    _assembly, outputs = _run_cube(
        owner=owner,
        incident_sources={
            terminal: _source(
                envelope,
                lineage=lineage,
                path_length=(index + 1) * _WAVELENGTH / 17.0,
            )
            for index, (terminal, envelope) in enumerate(envelopes.items())
        },
    )
    loss = sum(
        (index + 1.25) * output.envelope.real.square().sum()
        + (index + 0.75) * output.envelope.imag.square().sum()
        + (index + 0.33) * output.envelope.real.sum()
        for index, output in enumerate(outputs.values())
    )

    loss.backward()

    assert angle.grad is not None
    assert bool(torch.isfinite(angle.grad))
    assert float(angle.grad.abs()) > 0.0
    for envelope in envelopes.values():
        assert envelope.grad is not None
        assert bool(torch.isfinite(envelope.grad).all())
        assert torch.count_nonzero(envelope.grad[:, 0]) > 0
        assert torch.count_nonzero(envelope.grad[:, 1]) > 0


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
def test_exact_cancellation_output_retains_jones_and_owner_gradient(
    diagonal: CubeCoatingDiagonal,
) -> None:
    """
    证明精确相消输出仍存在并保留两条 Jones lane 与 owner 的梯度图

    """
    angle = torch.nn.Parameter(torch.tensor(torch.pi / 4.0, dtype=torch.float64))
    owner = _cube(diagonal, mixing_angle=angle)
    cosine = torch.cos(angle).detach()
    sine = torch.sin(angle).detach()
    reflected_terminal = (
        CubeTerminal.TOP
        if diagonal is CubeCoatingDiagonal.RISING
        else CubeTerminal.BOTTOM
    )
    reflected_ps = torch.stack(
        (
            1j * cosine * torch.ones((1, 3, 5), dtype=torch.complex128),
            (0.37 - 0.19j)
            * 1j
            * cosine
            * torch.ones((1, 3, 5), dtype=torch.complex128),
        ),
        dim=1,
    )
    transmitted_ps = torch.stack(
        (
            sine * torch.ones((1, 3, 5), dtype=torch.complex128),
            (0.37 - 0.19j)
            * sine
            * torch.ones((1, 3, 5), dtype=torch.complex128),
        ),
        dim=1,
    )
    reflected = _ps_to_local_hv(
        reflected_ps,
        terminal=reflected_terminal,
        diagonal=diagonal,
        direction="incident",
    ).requires_grad_()
    transmitted = _ps_to_local_hv(
        transmitted_ps,
        terminal=CubeTerminal.RIGHT,
        diagonal=diagonal,
        direction="incident",
    ).requires_grad_()
    lineage = _SourceLineage()
    _assembly, outputs = _run_cube(
        owner=owner,
        incident_sources={
            reflected_terminal: _source(reflected, lineage=lineage),
            CubeTerminal.RIGHT: _source(transmitted, lineage=lineage),
        },
    )
    cancelled = outputs[CubeTerminal.LEFT.value].envelope
    loss = cancelled.real.sum() + 0.73 * cancelled.imag.sum()

    loss.backward()

    assert float(cancelled.detach().abs().amax()) <= 5.0e-15
    assert angle.grad is not None
    assert float(angle.grad.abs()) > 0.0
    for envelope in (reflected, transmitted):
        assert envelope.grad is not None
        assert torch.count_nonzero(envelope.grad[:, 0]) > 0
        assert torch.count_nonzero(envelope.grad[:, 1]) > 0


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
def test_shared_owner_gradient_is_the_sum_across_two_encounters(
    diagonal: CubeCoatingDiagonal,
) -> None:
    """
    证明一个物理 owner 在两个 Encounter 中只注册一次且梯度精确相加

    """
    angle = torch.nn.Parameter(torch.tensor(0.29, dtype=torch.float64))
    owner = _cube(diagonal, mixing_angle=angle)
    lineage = _SourceLineage()
    assembly = Assembly()
    first_source = _source(
        _constant_envelope(1.0 + 0.2j, 0.4 - 0.1j),
        lineage=lineage,
        path_length=_WAVELENGTH / 19.0,
    )
    second_source = _source(
        _constant_envelope(0.7 - 0.3j, 0.2 + 0.5j),
        lineage=lineage,
        path_length=3.0 * _WAVELENGTH / 19.0,
    )
    assembly.include(first_source, name="first_source", grid=_grid())
    assembly.include(second_source, name="second_source", grid=_grid())
    assembly.include_directional(owner, name="cube")
    first = assembly.wave_encounter(
        owner,
        name="first_use",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    second = assembly.wave_encounter(
        owner,
        name="second_use",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    assembly.connect(
        first_source,
        first,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        second_source,
        second,
        destination_terminal=CubeTerminal.LEFT,
    )
    for prefix, encounter in (("first", first), ("second", second)):
        assembly.expose(
            encounter,
            name=f"{prefix}_right",
            source_terminal=CubeTerminal.RIGHT,
        )
        reflected_terminal = (
            CubeTerminal.TOP
            if diagonal is CubeCoatingDiagonal.RISING
            else CubeTerminal.BOTTOM
        )
        assembly.expose(
            encounter,
            name=f"{prefix}_reflected",
            source_terminal=reflected_terminal,
        )
    assembly.freeze()
    outputs = assembly._replay()  # noqa: SLF001
    first_loss = outputs["first_right"].envelope.real.sum() + (
        0.7 * outputs["first_reflected"].envelope.imag.sum()
    )
    second_loss = 1.3 * outputs["second_right"].envelope.imag.sum() + (
        outputs["second_reflected"].envelope.real.sum()
    )

    first_gradient = torch.autograd.grad(
        first_loss,
        angle,
        retain_graph=True,
    )[0]
    second_gradient = torch.autograd.grad(
        second_loss,
        angle,
        retain_graph=True,
    )[0]
    summed_gradient = torch.autograd.grad(
        first_loss + second_loss,
        angle,
    )[0]

    torch.testing.assert_close(
        summed_gradient,
        first_gradient + second_gradient,
        atol=2.0e-12,
        rtol=2.0e-12,
    )
    assert first_gradient.abs() > 0.0
    assert second_gradient.abs() > 0.0
    assert tuple(
        name
        for name, _parameter in assembly.named_parameters()
        if name == "cube.mixing_angle"
    ) == ("cube.mixing_angle",)


@pytest.mark.parametrize("target_is_polarizing", (False, True))
def test_wrong_directional_owner_donor_rejects_before_any_state_copy(
    target_is_polarizing: bool,
) -> None:
    """
    证明 NBS 与 PBS 的错误 donor 不能跨 owner 类型安装且拒绝保持原子性

    """
    target = _cube(
        CubeCoatingDiagonal.RISING,
        mixing_angle=0.37,
        polarizing=target_is_polarizing,
    )
    donor = _cube(
        CubeCoatingDiagonal.FALLING,
        mixing_angle=0.91,
        polarizing=not target_is_polarizing,
    )
    baseline = {
        name: value.detach().clone()
        for name, value in target.state_dict().items()
    }

    with pytest.raises(OpticalRuntimeError) as rejected:
        install_state(target, donor.state_dict())

    assert rejected.value.identity == "state_installation_keys_mismatch"
    assert target.state_dict().keys() == baseline.keys()
    assert all(
        torch.equal(target.state_dict()[name], expected)
        for name, expected in baseline.items()
    )
