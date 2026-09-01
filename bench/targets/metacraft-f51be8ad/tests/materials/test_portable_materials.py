from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from metacraft.authority import (
    Authority,
    Document,
    Proposal,
    Revision,
    Structure,
)
from metacraft.materials import (
    MaterialRecord,
    MaterialSample,
    MaterialSource,
    parse_local_table,
    parse_refractiveindex_info,
)


def test_local_csv_interpolates_without_extrapolation() -> None:
    record = parse_local_table(
        b"wavelength,n,k\n400,2.0,0.01\n500,2.2,0.03\n",
        wavelength_unit="nm",
        source_name="silicon-nitride.csv",
    )

    sample = record.sample(Decimal("450"))

    assert sample.refractive_index == Decimal("2.10")
    assert sample.extinction_coefficient == Decimal("0.020")
    assert record.declared_wavelength_unit == "nm"
    assert record.columns.wavelength == "wavelength"
    assert sample.record_identity == record.record_identity
    with pytest.raises(ValueError, match="outside_covered_band"):
        record.sample(Decimal("350"))


def test_duplicate_wavelengths_are_rejected() -> None:
    with pytest.raises(ValueError, match="wavelength_duplicate"):
        parse_local_table(
            b"wavelength n k\n400 2.0 0.01\n400 2.1 0.02\n",
            wavelength_unit="nm",
            source_name="duplicate.txt",
        )


def test_refractiveindex_info_source_bytes_remain_identified() -> None:
    source = b"""
DATA:
  - type: tabulated nk
    data: |
      0.4 2.0 0.01
      0.5 2.2 0.03
"""

    record = parse_refractiveindex_info(
        source,
        source_url="https://refractiveindex.info/database/data-nk/test.yml",
    )

    assert (
        record.source_kind
        is MaterialSource.REFRACTIVEINDEX_INFO_DATASET
    )
    assert record.covered_band_nm == (Decimal("400.0"), Decimal("500.0"))
    assert record.source_identity.startswith("sha256:")


def test_material_record_round_trips_through_authority(tmp_path: Path) -> None:
    record = parse_local_table(
        b"wavelength,n,k\n400,2.0,0.01\n500,2.2,0.03\n",
        wavelength_unit="nm",
        source_name="material.csv",
    )
    authority = Authority(tmp_path / "workspace")

    decision = authority.decide(
        Proposal.record(record.encode_document()),
        at=Revision.root(),
    )

    assert decision.body_reference is not None
    restored = MaterialRecord.decode_document_bytes(
        authority.fetch(decision.body_reference)
    )
    assert restored == record

    sample = record.sample(Decimal("450")).with_record(decision.body_reference)
    sample_document = sample.encode_document()
    sample_structure = Structure.for_document(
        sample_document,
        references=(decision.body_reference,),
    )
    structure_decision = authority.decide(
        Proposal.structure(sample_structure),
        at=decision.resulting_revision,
    )
    assert structure_decision.body_reference is not None
    sample_decision = authority.decide(
        Proposal.structured(
            sample_document,
            structure_reference=structure_decision.body_reference,
            references=(decision.body_reference,),
        ),
        at=structure_decision.resulting_revision,
    )
    assert sample_decision.body_reference is not None
    assert (
        MaterialSample.decode_document_bytes(
            authority.fetch(sample_decision.body_reference)
        )
        == sample
    )


def test_interpretation_changes_material_record_identity() -> None:
    source = b"wavelength,n,k\n0.4,2.0,0.01\n0.5,2.2,0.03\n"

    nanometres = parse_local_table(
        source,
        wavelength_unit="nm",
        source_name="material.csv",
    )
    micrometres = parse_local_table(
        source,
        wavelength_unit="um",
        source_name="material.csv",
    )

    assert nanometres.source_identity == micrometres.source_identity
    assert nanometres.record_identity != micrometres.record_identity


def test_canonical_source_spelling_names_the_material_record_identity() -> None:
    record = parse_local_table(
        b"wavelength,n,k\n400,2.0,0.01\n500,2.2,0.03\n",
        wavelength_unit="nm",
        source_name="silicon-nitride.csv",
    )

    # This golden changed only when MaterialSource adopted the canonical
    # spelling "local table".
    assert record.record_identity == (
        "sha256:"
        "b658de3ef83cdccc63f82b17ea5e967fff85ef0a9efdd81ef7f957db5f30725a"
    )


def test_portable_record_rejects_a_solver_native_source() -> None:
    record = parse_local_table(
        b"wavelength,n,k\n400,2.0,0.01\n500,2.2,0.03\n",
        wavelength_unit="nm",
        source_name="silicon-nitride.csv",
    )
    document = record.encode_document()
    values = dict(document.values)
    values["source_kind"] = MaterialSource.SOLVER_NATIVE

    with pytest.raises(ValueError, match="material_record_source_invalid"):
        MaterialRecord.decode_document_bytes(
            Document(document.schema_identifier, values).to_bytes()
        )
