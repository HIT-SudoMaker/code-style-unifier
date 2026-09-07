from __future__ import annotations

from pathlib import Path

from examples.metalens_field_diagnostics import (
    FieldAssumptionDiagnostic,
    diagnose_field_assumptions,
)
from tests.examples.metalens_diagnostic_support import (
    DIAGNOSTIC_ENDPOINT_DISPOSITIONS,
    admitted_result,
    diagnostic_case_identity,
    diagnostic_contract_results,
    diagnostic_endpoint_identity,
)


def test_contract_diagnostics_change_one_assumption_at_a_time(
    tmp_path: Path,
) -> None:
    groups = diagnostic_contract_results(tmp_path)
    expected_names = {
        "low propagation": (
            "ideal continuous",
            "assigned target",
            "realized phase",
            "realized coefficient",
        ),
        "low geometric": (
            "ideal pb",
            "assigned orientation",
            "realized jones",
        ),
        "high propagation": (
            "ideal continuous",
            "realized phase",
            "realized coefficient",
            "sampled surface",
        ),
        "high geometric": (
            "ideal pb",
            "assigned orientation",
            "realized jones",
            "sampled surface",
        ),
    }

    for family, record in groups:
        result = admitted_result(record)
        case_identity = diagnostic_case_identity(family)
        endpoint_identity = diagnostic_endpoint_identity(result)
        result_before = result.document.to_bytes()
        root_before = _root_bytes(tmp_path)

        diagnostic = diagnose_field_assumptions(
            case_identity=case_identity,
            result=result,
            endpoint_comparison_identity=endpoint_identity,
            endpoint_dispositions=DIAGNOSTIC_ENDPOINT_DISPOSITIONS,
            fetch=record.authority.fetch,
        )

        assert tuple(item.name for item in diagnostic.variants) == (
            expected_names[family]
        )
        assert diagnostic.case_identity == case_identity
        assert diagnostic.result_reference == result.reference
        assert diagnostic.aperture_reference == record.conclusion.aperture_reference
        assert diagnostic.field_reference == record.conclusion.field_reference
        assert diagnostic.focus_reference == record.conclusion.focus_reference
        assert diagnostic.response_references
        assert diagnostic.endpoint_dispositions == DIAGNOSTIC_ENDPOINT_DISPOSITIONS
        assert diagnostic.first_divergent_step is not None or (
            diagnostic.no_divergence_reason is not None
        )
        for previous, current in zip(
            diagnostic.variants,
            diagnostic.variants[1:],
            strict=False,
        ):
            changed = tuple(
                name
                for name in previous.assumptions.names
                if previous.assumptions.value(name)
                != current.assumptions.value(name)
            )
            assert changed == (current.changed_assumption,)
            assert current.attribution

        reversed_diagnostic = diagnose_field_assumptions(
            case_identity=case_identity,
            result=result,
            endpoint_comparison_identity=endpoint_identity,
            endpoint_dispositions=DIAGNOSTIC_ENDPOINT_DISPOSITIONS,
            fetch=record.authority.fetch,
            order=tuple(reversed(expected_names[family])),
        )
        assert {
            item.name: item.document().to_bytes()
            for item in reversed_diagnostic.variants
        } == {
            item.name: item.document().to_bytes()
            for item in diagnostic.variants
        }
        assert result.document.to_bytes() == result_before
        assert _root_bytes(tmp_path) == root_before


def test_method_families_retain_finite_pointwise_and_continuous_meaning(
    tmp_path: Path,
) -> None:
    diagnostics = []
    for family, record in diagnostic_contract_results(tmp_path):
        result = admitted_result(record)
        diagnostics.append(
            (
                family,
                diagnose_field_assumptions(
                    case_identity=diagnostic_case_identity(family),
                    result=result,
                    endpoint_comparison_identity=(
                        diagnostic_endpoint_identity(result)
                    ),
                    endpoint_dispositions=DIAGNOSTIC_ENDPOINT_DISPOSITIONS,
                    fetch=record.authority.fetch,
                ),
            )
        )

    by_family: dict[str, list[FieldAssumptionDiagnostic]] = {}
    for family, diagnostic in diagnostics:
        by_family.setdefault(family, []).append(diagnostic)
    assert {
        item.assignment for item in by_family["low propagation"]
    } == {"finite 8 levels", "finite 12 levels", "finite 16 levels"}
    assert {
        item.assignment for item in by_family["low geometric"]
    } == {
        "finite 8 orientations",
        "finite 12 orientations",
        "finite 16 orientations",
    }
    assert len(by_family["low propagation"]) == 3
    assert len(by_family["low geometric"]) == 3
    assert len(by_family["high propagation"]) == 1
    assert len(by_family["high geometric"]) == 1
    first_by_family = {
        family: items[0] for family, items in by_family.items()
    }
    assert first_by_family["high propagation"].assignment == "pointwise"
    assert (
        first_by_family["high geometric"].assignment
        == "continuous orientation"
    )
    assert "assigned target" not in {
        item.name
        for item in first_by_family["high propagation"].variants
    }
    high_geometric = first_by_family["high geometric"]
    assert high_geometric.vector_provenance is not None
    assert high_geometric.vector_provenance.component_names == ("x", "y", "z")
    assert high_geometric.vector_provenance.formation == "uniform"
    assert high_geometric.vector_provenance.propagation == "vector"
    assert high_geometric.vector_provenance.longitudinal_power_reference is not None


def _root_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
