from __future__ import annotations

import pytest

from metacraft.materials import (
    MaterialConfirmationQuestion,
    SolverMaterialLibrary,
)


_LIBRARY = b'''solver = "lumerical fdtd"

[[materials]]
family = "fused silica"
native_name = "SiO2 (Glass) - Palik"
provenance = "reviewed fixture"

[[materials]]
family = "silicon"
native_name = "Si (Silicon) - Palik"
provenance = "reviewed fixture"
'''


def test_material_library_frames_only_an_explicit_registered_candidate() -> None:
    library = SolverMaterialLibrary.decode_bytes(_LIBRARY)

    question = library.confirm_material_family(
        fact="atom_material",
        candidate="silicon",
    )

    assert question == MaterialConfirmationQuestion(
        fact="atom_material",
        candidate="silicon",
    )
    assert question.wording == "Did you mean silicon?"


@pytest.mark.parametrize(
    ("fact", "candidate", "reason"),
    (
        (
            "coating_material",
            "silicon",
            "material_confirmation_fact_invalid",
        ),
        (
            "atom_material",
            "Si",
            "material_confirmation_candidate_invalid",
        ),
        (
            "substrate_material",
            "silicon nitride",
            "material_confirmation_candidate_unregistered",
        ),
    ),
)
def test_material_library_never_infers_ranks_or_rewrites_a_candidate(
    fact: str,
    candidate: str,
    reason: str,
) -> None:
    library = SolverMaterialLibrary.decode_bytes(_LIBRARY)

    with pytest.raises(ValueError, match=f"^{reason}$"):
        library.confirm_material_family(fact=fact, candidate=candidate)


def test_material_confirmation_value_cannot_bypass_canonical_language() -> None:
    with pytest.raises(
        ValueError,
        match="^material_confirmation_candidate_invalid$",
    ):
        MaterialConfirmationQuestion(
            fact="atom_material",
            candidate="Si",
        )
