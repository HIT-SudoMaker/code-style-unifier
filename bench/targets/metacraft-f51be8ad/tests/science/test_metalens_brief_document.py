from __future__ import annotations

from dataclasses import replace
import json

import pytest

from examples.metalens_benchmark.arbabi import arbabi_benchmark_case
from examples.metalens_benchmark.khorasaninejad import (
    khorasaninejad_benchmark_case,
)
from examples.metalens_benchmark.yang import yang_benchmark_case
from examples.metalens_benchmark.mcclung import mcclung_benchmark_case
from metacraft.science.compile import InvalidBrief, compile_study
from metacraft.science.metalens.brief import MetalensBrief


@pytest.mark.parametrize(
    "case_factory",
    (
        mcclung_benchmark_case,
        yang_benchmark_case,
        arbabi_benchmark_case,
        khorasaninejad_benchmark_case,
    ),
)
def test_canonical_benchmark_brief_round_trips_without_case_truth(
    case_factory,
) -> None:
    brief = case_factory().brief

    restored = MetalensBrief.decode_canonical_bytes(brief.canonical_bytes())

    assert restored == brief
    assert restored.wording == brief.wording
    assert restored.canonical_bytes() == brief.canonical_bytes()
    assert set(json.loads(restored.canonical_bytes())) == {
        "aim",
        "aperture",
        "aspect_limit",
        "atom",
        "atom_height_nm",
        "budget",
        "cell_period_nm",
        "control_strategy",
        "dimension_step_nm",
        "focal_length_um",
        "incident_polarization",
        "numerical_aperture",
        "objectives",
        "omissions",
        "operating_spectrum",
        "solver_preference",
        "substrate",
        "wording",
    }


def test_retired_decorative_name_is_not_brief_meaning() -> None:
    value = json.loads(mcclung_benchmark_case().brief.canonical_bytes())
    value["name"] = "display-only-label"

    with pytest.raises(ValueError, match="^metalens_brief_document_invalid$"):
        MetalensBrief.decode_canonical_bytes(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        )


@pytest.mark.parametrize("mutation", ("absent", "unknown", "mistyped"))
def test_canonical_brief_reader_rejects_non_exact_documents(mutation: str) -> None:
    value = json.loads(mcclung_benchmark_case().brief.canonical_bytes())
    if mutation == "absent":
        del value["wording"]
    elif mutation == "unknown":
        value["paper"] = "withheld"
    else:
        value["operating_spectrum"]["wavelength_nm"] = "850"

    with pytest.raises(ValueError, match="^metalens_brief_document_invalid$"):
        MetalensBrief.decode_canonical_bytes(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        )


def test_canonical_brief_reader_rejects_duplicate_and_noncanonical_bytes() -> None:
    source = mcclung_benchmark_case().brief.canonical_bytes()
    duplicate = source[:-1] + b',"wording":"replacement"}'

    with pytest.raises(ValueError, match="^metalens_brief_document_duplicate$"):
        MetalensBrief.decode_canonical_bytes(duplicate)
    with pytest.raises(ValueError, match="^metalens_brief_document_noncanonical$"):
        MetalensBrief.decode_canonical_bytes(b" " + source)


def test_canonical_brief_reader_stabilizes_an_invalid_decimal_string() -> None:
    value = json.loads(mcclung_benchmark_case().brief.canonical_bytes())
    value["numerical_aperture"] = "not-a-decimal"

    with pytest.raises(ValueError, match="^metalens_brief_document_invalid$"):
        MetalensBrief.decode_canonical_bytes(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        )


def test_missing_required_science_remains_an_invalid_brief() -> None:
    incomplete = replace(
        mcclung_benchmark_case().brief,
        control_strategy=None,
        omissions=(
            *mcclung_benchmark_case().brief.omissions,
            "control_strategy",
        ),
    )

    restored = MetalensBrief.decode_canonical_bytes(incomplete.canonical_bytes())

    assert compile_study(restored) == InvalidBrief("brief_incomplete:control_strategy")


def test_missing_required_science_without_an_honest_omission_is_malformed() -> None:
    incomplete = replace(
        mcclung_benchmark_case().brief,
        control_strategy=None,
    )

    with pytest.raises(
        ValueError,
        match="^metalens_brief_omission_required:control_strategy$",
    ):
        MetalensBrief.decode_canonical_bytes(incomplete.canonical_bytes())


def test_nullable_user_fact_requires_its_honest_omission() -> None:
    brief = replace(
        mcclung_benchmark_case().brief,
        solver_preference=None,
        omissions=(
            *mcclung_benchmark_case().brief.omissions,
            "solver_preference",
        ),
    )

    assert MetalensBrief.decode_canonical_bytes(brief.canonical_bytes()) == brief

    undeclared = replace(brief, omissions=brief.omissions[:-1])
    with pytest.raises(
        ValueError,
        match="^metalens_brief_omission_required:solver_preference$",
    ):
        MetalensBrief.decode_canonical_bytes(undeclared.canonical_bytes())


@pytest.mark.parametrize(
    "fact",
    ("aperture", "cell_period_nm", "atom_height_nm"),
)
def test_each_nullable_design_fact_requires_an_honest_omission(
    fact: str,
) -> None:
    brief = mcclung_benchmark_case().brief
    declared = replace(
        brief,
        **{fact: None},
        omissions=tuple(dict.fromkeys((*brief.omissions, fact))),
    )

    assert MetalensBrief.decode_canonical_bytes(declared.canonical_bytes()) == declared

    undeclared = replace(
        declared,
        omissions=tuple(item for item in declared.omissions if item != fact),
    )
    with pytest.raises(
        ValueError,
        match=f"^metalens_brief_omission_required:{fact}$",
    ):
        MetalensBrief.decode_canonical_bytes(undeclared.canonical_bytes())


@pytest.mark.parametrize("value", ("NaN", "Infinity", "-Infinity"))
def test_canonical_brief_reader_rejects_nonfinite_decimals(value: str) -> None:
    document = json.loads(mcclung_benchmark_case().brief.canonical_bytes())
    document["numerical_aperture"] = value

    with pytest.raises(ValueError, match="^metalens_brief_document_invalid$"):
        MetalensBrief.decode_canonical_bytes(
            json.dumps(
                document,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
