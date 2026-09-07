from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from metacraft.authority import Document
from metacraft.materials import MaterialSource
from metacraft.materials.solver import (
    SolverMaterial,
    SolverMaterialLibrary,
)
from metacraft.science.metalens.brief import MaterialIntent


_SILICA = b"""
solver = "lumerical fdtd"

[[materials]]
family = "silica"
native_name = "SiO2 (Glass) - Palik"
provenance = "confirmed against the local Lumerical 25v2 material database"
"""
_ROOT = Path(__file__).parents[2]


def test_material_source_is_one_closed_domain_value() -> None:
    assert tuple(source.value for source in MaterialSource) == (
        "local table",
        "refractiveindex.info dataset",
        "solver native",
    )
    assert (
        MaterialIntent(
            "silica",
            MaterialSource.SOLVER_NATIVE,
        ).source
        is MaterialSource.SOLVER_NATIVE
    )

    with pytest.raises(ValueError, match="material_source_invalid"):
        MaterialIntent("silica", "unknown source")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="material_family_invalid"):
        MaterialIntent(
            "Silica",
            MaterialSource.SOLVER_NATIVE,
        )
    with pytest.raises(ValueError, match="material_family_invalid"):
        MaterialIntent(
            " silica",
            MaterialSource.SOLVER_NATIVE,
        )
    with pytest.raises(ValueError, match="material_family_invalid"):
        MaterialIntent(  # type: ignore[arg-type]
            1,
            MaterialSource.SOLVER_NATIVE,
        )


def test_solver_material_round_trips_one_exact_document() -> None:
    material = SolverMaterial(
        solver="lumerical fdtd",
        family="silica",
        native_name="SiO2 (Glass) - Palik",
        provenance=("confirmed against the local Lumerical 25v2 material database"),
    )

    document = material.document()
    restored = SolverMaterial.decode_document_bytes(document.to_bytes())

    assert tuple(field.name for field in fields(SolverMaterial)) == (
        "solver",
        "family",
        "native_name",
        "provenance",
    )
    assert document.schema_identifier == "metacraft.material.solver_material"
    assert restored == material


def test_library_selects_exactly_without_alias_or_normalization() -> None:
    library = SolverMaterialLibrary.decode_bytes(_SILICA)

    selected = library.select("silica")

    assert selected is not None
    assert library.solver == "lumerical fdtd"
    assert selected.native_name == "SiO2 (Glass) - Palik"
    assert library.select("Silica") is None
    assert library.select("fused silica") is None


def test_entry_order_changes_neither_documents_nor_selection() -> None:
    first = SolverMaterialLibrary.decode_bytes(
        b"""
solver = "lumerical fdtd"

[[materials]]
family = "silicon nitride"
native_name = "Si3N4 (Silicon Nitride) - Luke"
provenance = "confirmed against the local Lumerical 25v2 material database"

[[materials]]
family = "silica"
native_name = "SiO2 (Glass) - Palik"
provenance = "confirmed against the local Lumerical 25v2 material database"
"""
    )
    second = SolverMaterialLibrary.decode_bytes(
        b"""
solver = "lumerical fdtd"

[[materials]]
family = "silica"
native_name = "SiO2 (Glass) - Palik"
provenance = "confirmed against the local Lumerical 25v2 material database"

[[materials]]
family = "silicon nitride"
native_name = "Si3N4 (Silicon Nitride) - Luke"
provenance = "confirmed against the local Lumerical 25v2 material database"
"""
    )

    for family in ("silica", "silicon nitride"):
        first_material = first.select(family)
        second_material = second.select(family)
        assert first_material is not None
        assert second_material is not None
        assert (
            first_material.document().to_bytes()
            == second_material.document().to_bytes()
        )


def test_distinct_families_may_name_one_exact_native_record() -> None:
    library = SolverMaterialLibrary.decode_bytes(
        b"""
solver = "lumerical fdtd"

[[materials]]
family = "silica"
native_name = "SiO2 (Glass) - Palik"
provenance = "reviewed selection"

[[materials]]
family = "fused silica"
native_name = "SiO2 (Glass) - Palik"
provenance = "separate reviewed selection"
"""
    )

    silica = library.select("silica")
    fused_silica = library.select("fused silica")
    assert silica is not None
    assert fused_silica is not None
    assert silica.native_name == fused_silica.native_name


def test_project_library_contains_only_locally_confirmed_registrations() -> None:
    library = SolverMaterialLibrary.decode_bytes(
        (_ROOT / "materials" / "lumerical.toml").read_bytes()
    )

    silica = library.select("silica")
    fused_silica = library.select("fused silica")
    glass = library.select("glass")
    silicon_dioxide = library.select("silicon dioxide")
    silicon = library.select("silicon")
    silicon_nitride = library.select("silicon nitride")
    titanium_dioxide = library.select("amorphous titanium dioxide")
    assert silica is not None
    assert silica.native_name == "SiO2 (Glass) - Palik"
    assert fused_silica is not None
    assert glass is not None
    assert silicon_dioxide is not None
    assert {
        fused_silica.native_name,
        glass.native_name,
        silicon_dioxide.native_name,
    } == {"SiO2 (Glass) - Palik"}
    assert silicon is not None
    assert silicon.native_name == "Si (Silicon) - Palik"
    assert silicon_nitride is not None
    assert silicon_nitride.native_name == "Si3N4 (Silicon Nitride) - Luke"
    assert titanium_dioxide is not None
    assert titanium_dioxide.native_name == (
        "TiO2 (Titanium Dioxide) - Siefke"
    )
    assert library.select("hydrogenated amorphous silicon") is None

    pending = (
        _ROOT / ".scratch" / "solver-material-sonnet" / "pending-materials.md"
    ).read_text(encoding="utf-8")
    assert "SiO2 (Glass) - Palik" not in pending
    assert "Si3N4 (Silicon Nitride) - Luke" not in pending
    assert {
        line.removeprefix("- ")
        for line in pending.splitlines()
        if line.startswith("- ")
    } == {"hydrogenated amorphous silicon"}


@pytest.mark.parametrize(
    ("source", "finding"),
    (
        (b"not = [valid", "solver_material_library_invalid"),
        (
            b'solver = "lumerical fdtd"\n',
            "solver_material_library_fields_invalid",
        ),
        (
            b'solver = "other"\nmaterials = []\n',
            "solver_material_solver_unsupported",
        ),
        (
            b'solver = "lumerical fdtd"\nmaterials = "not a list"\n',
            "solver_material_library_invalid",
        ),
        (
            b"""
solver = "lumerical fdtd"
unknown = true
materials = []
""",
            "solver_material_library_fields_invalid",
        ),
        (
            b"""
solver = "lumerical fdtd"
[[materials]]
family = "Silica"
native_name = "exact"
provenance = "reviewed"
""",
            "solver_material_family_invalid",
        ),
        (
            b"""
solver = "lumerical fdtd"
[[materials]]
family = ""
native_name = "exact"
provenance = "reviewed"
""",
            "solver_material_family_invalid",
        ),
        (
            b"""
solver = "lumerical fdtd"
[[materials]]
family = "silica"
native_name = ""
provenance = "reviewed"
""",
            "solver_material_native_name_empty",
        ),
        (
            b"""
solver = "lumerical fdtd"
[[materials]]
family = "silica"
native_name = "exact"
provenance = ""
""",
            "solver_material_provenance_empty",
        ),
        (
            b"""
solver = "lumerical fdtd"
[[materials]]
family = "silica"
native_name = "first"
provenance = "reviewed"
[[materials]]
family = "silica"
native_name = "second"
provenance = "reviewed"
""",
            "solver_material_family_duplicate",
        ),
        (
            b"""
solver = "lumerical fdtd"
[[materials]]
family = "silica"
native_name = "exact"
provenance = "reviewed"
unknown = "fact"
""",
            "solver_material_fields_invalid",
        ),
        (
            b"""
solver = "lumerical fdtd"
[[materials]]
family = "silica"
native_name = "exact"
""",
            "solver_material_fields_invalid",
        ),
    ),
)
def test_library_rejects_malformed_or_ambiguous_registration(
    source: bytes,
    finding: str,
) -> None:
    with pytest.raises(ValueError, match=finding):
        SolverMaterialLibrary.decode_bytes(source)


def test_solver_material_decoder_rejects_noncanonical_source() -> None:
    material = SolverMaterialLibrary.decode_bytes(_SILICA).select(
        "silica",
    )
    assert material is not None
    document = Document.from_bytes(material.document().to_bytes())
    values = dict(document.values)
    values["family"] = "Silica"

    with pytest.raises(ValueError, match="solver_material_family_invalid"):
        SolverMaterial.decode_document_bytes(
            Document(document.schema_identifier, values).to_bytes()
        )
