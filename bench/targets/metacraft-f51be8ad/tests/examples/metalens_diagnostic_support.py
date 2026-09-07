from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from examples.metalens_benchmark.contract import BENCHMARK_MEASURE_FRAME
from metacraft.science.result import Result
from tests.brief_fixtures import geometric_brief, propagation_brief
from tests.domain_fixtures import select_fixture_period_nm
from tests.result_fixtures import (
    RecordedResult,
    admit_result,
    geometric_results,
    pointwise_geometric_result,
    pointwise_propagation_result,
    propagation_results,
)


def diagnostic_contract_results(
    root: Path,
) -> tuple[tuple[str, RecordedResult], ...]:
    """Return paper-free contract fixtures shared by diagnostic tests."""

    low_propagation_brief = replace(
        propagation_brief(),
        focal_length_um=Decimal("2"),
        numerical_aperture=Decimal("0.1"),
        aperture=None,
    )
    low_geometric_brief = replace(
        geometric_brief(),
        focal_length_um=Decimal("2"),
        numerical_aperture=Decimal("0.1"),
        aperture=None,
    )
    high_propagation_brief = replace(
        propagation_brief(),
        focal_length_um=Decimal("0.25"),
        numerical_aperture=Decimal("0.8"),
        aperture=None,
    )
    high_geometric_brief = replace(
        geometric_brief(),
        focal_length_um=Decimal("0.25"),
        numerical_aperture=Decimal("0.8"),
        aperture=None,
    )
    high_propagation_period_nm = select_fixture_period_nm(
        high_propagation_brief,
        preferred_period_nm=250,
    )
    high_geometric_period_nm = select_fixture_period_nm(
        high_geometric_brief,
        preferred_period_nm=250,
    )
    low_propagation = propagation_results(
        root / "low-propagation",
        (8, 12, 16),
        brief=low_propagation_brief,
        period_nm=250,
        height_nm=600,
    )
    low_geometric = geometric_results(
        root / "low-geometric",
        (8, 12, 16),
        brief=low_geometric_brief,
        period_nm=250,
        height_nm=600,
    )
    records = (
        *(
            (
                "low propagation",
                low_propagation_brief,
                record,
            )
            for record in low_propagation
        ),
        *(
            (
                "low geometric",
                low_geometric_brief,
                record,
            )
            for record in low_geometric
        ),
        (
            "high propagation",
            high_propagation_brief,
            pointwise_propagation_result(
                root / "high-propagation",
                high_propagation_brief,
                period_nm=high_propagation_period_nm,
                height_nm=600,
            ),
        ),
        (
            "high geometric",
            high_geometric_brief,
            pointwise_geometric_result(
                root / "high-geometric",
                high_geometric_brief,
                period_nm=high_geometric_period_nm,
                height_nm=600,
            ),
        ),
    )
    return tuple((family, record) for family, _brief, record in records)


def admitted_result(record: RecordedResult) -> Result:
    """Admit one synthetic conclusion through the Result Interface."""

    return Result(
        reference=admit_result(record),
        document=record.conclusion.document(),
        sources=record.conclusion.references(),
        closure=record.closure,
    )


def diagnostic_case_identity(family: str) -> str:
    """Return a paper-free identity for one synthetic diagnostic family."""

    import hashlib

    return "sha256:" + hashlib.sha256(
        f"metalens-diagnostic-contract:{family}".encode()
    ).hexdigest()


def diagnostic_endpoint_identity(result: Result) -> str:
    """Identify the synthetic diagnostic endpoint without paper meaning."""

    import hashlib

    return "sha256:" + hashlib.sha256(
        b"diagnostic-endpoint:" + result.document.to_bytes()
    ).hexdigest()


DIAGNOSTIC_ENDPOINT_DISPOSITIONS = tuple(
    (measure.value, "not applicable") for measure in BENCHMARK_MEASURE_FRAME
)
