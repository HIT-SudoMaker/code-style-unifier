# Independently derives the two reviewed propagation-envelope candidates.
# This is a review aid, not a fixture updater. It imports nothing from
# metacraft; reviewers preserve bytes only after inspecting the JSON.

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
import hashlib
import json


DECIMAL_PRECISION = 28
CUTOFF_PRECISION = 50
ROOT_CUTOFF = Decimal("2.404825557695772768621631879")
PI = Decimal(
    "3.1415926535897932384626433832795028841971693993751"
)
LEVELS = (8, 12, 16)
SCHEMA = (
    "metacraft.science.metalens."
    "propagation_phase.phase_envelope"
)

INPUTS = {
    940: {
        "brief_identity": "reviewed-propagation-940-nm",
        "heights_nm": (500, 550),
        "period_nm": 520,
        "dimension_step_nm": 10,
    },
    1550: {
        "brief_identity": "reviewed-propagation-1550-nm",
        "heights_nm": (800, 850, 900),
        "period_nm": 870,
        "dimension_step_nm": 10,
    },
}

PILLAR_INDEX = Decimal("2.05")
SUBSTRATE_INDEX = Decimal("1.48")
AMBIENT_INDEX = Decimal("1")
ASPECT_LIMIT = 8


def derive_documents() -> dict[int, bytes]:
    """
    Return canonical candidate bytes for independent human review.
    """

    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        return {
            wavelength_nm: _canonical_bytes(
                _document(wavelength_nm, values)
            )
            for wavelength_nm, values in INPUTS.items()
        }


def _document(
    wavelength_nm: int,
    values: dict[str, object],
) -> dict[str, object]:
    period_nm = int(values["period_nm"])
    dimension_step_nm = int(values["dimension_step_nm"])
    heights_nm = tuple(int(value) for value in values["heights_nm"])
    return {
        "schema_identifier": SCHEMA,
        "values": {
            "bound_checks": _bound_checks(),
            "brief_identity": str(values["brief_identity"]),
            "reaches": [
                _height_reach(
                    wavelength_nm=wavelength_nm,
                    period_nm=period_nm,
                    dimension_step_nm=dimension_step_nm,
                    height_nm=height_nm,
                )
                for height_nm in heights_nm
            ],
            "source_references": {
                "height_domain": _reference(
                    "height-domain",
                    wavelength_nm,
                ),
                "material_binding": _reference(
                    "material-binding",
                    wavelength_nm,
                ),
                "material_sample": _reference(
                    "material-sample",
                    wavelength_nm,
                ),
            },
            "wavelength_nm": wavelength_nm,
        },
    }


def _bound_checks() -> dict[str, object]:
    return {
        "ceiling_reaches_pillar": {
            "certified": True,
            "certified_interval": {
                "lower": _decimal(PILLAR_INDEX),
                "upper": _decimal(PILLAR_INDEX),
            },
            "expected_endpoint": _decimal(PILLAR_INDEX),
            "holds": True,
        },
        "floor_reaches_ambient": {
            "certified": True,
            "certified_interval": {
                "lower": _decimal(AMBIENT_INDEX),
                "upper": _decimal(AMBIENT_INDEX),
            },
            "expected_endpoint": _decimal(AMBIENT_INDEX),
            "holds": True,
        },
        "floor_stays_below_ceiling": {
            "certified": True,
            "holds": AMBIENT_INDEX < PILLAR_INDEX,
            "minimum_certified_separation": _decimal(
                PILLAR_INDEX - AMBIENT_INDEX
            ),
        },
    }


def _height_reach(
    *,
    wavelength_nm: int,
    period_nm: int,
    dimension_step_nm: int,
    height_nm: int,
) -> dict[str, object]:
    minimum_feature_nm = _ceil_to_step(
        Decimal(height_nm) / Decimal(ASPECT_LIMIT),
        dimension_step_nm,
    )
    maximum_feature_nm = period_nm - minimum_feature_nm
    candidate_count = (
        0
        if maximum_feature_nm < minimum_feature_nm
        else (
            (maximum_feature_nm - minimum_feature_nm)
            // dimension_step_nm
        )
        + 1
    )
    rigorous_turns_ceiling = (
        Decimal(height_nm)
        * (PILLAR_INDEX - AMBIENT_INDEX)
        / Decimal(wavelength_nm)
    )
    cutoff_diameter = _single_mode_cutoff(wavelength_nm)
    affected_count = sum(
        Decimal(feature_nm) >= cutoff_diameter
        for feature_nm in range(
            minimum_feature_nm,
            maximum_feature_nm + 1,
            dimension_step_nm,
        )
    )
    affected_fraction = (
        Decimal(0)
        if candidate_count == 0
        else Decimal(affected_count) / Decimal(candidate_count)
    )
    return {
        "applicability": {
            "affected_candidate_count": affected_count,
            "affected_candidate_fraction": _decimal(
                affected_fraction
            ),
            "single_mode_cutoff_diameter_nm": _decimal(
                cutoff_diameter
            ),
        },
        "bounded_reasoning": {
            "ceiling_index_at_maximum_feature": _decimal(
                PILLAR_INDEX
            ),
            "ceiling_polarization": "polarization independent",
            "floor_index_at_minimum_feature": _decimal(AMBIENT_INDEX),
            "rigorous_turns_ceiling": _decimal(
                rigorous_turns_ceiling
            ),
        },
        "forecast": {
            "annotation": "forecast insufficient",
            "level_budgets": [
                {
                    "levels": levels,
                    "maximum_adjacent_step_turns": _decimal(
                        Decimal(1) / Decimal(levels)
                    ),
                }
                for levels in LEVELS
            ],
            "model_spans": [],
        },
        "grid": {
            "candidate_count": candidate_count,
            "dimension_step_nm": dimension_step_nm,
            "maximum_feature_nm": maximum_feature_nm,
            "minimum_feature_nm": minimum_feature_nm,
        },
        "height_nm": height_nm,
        "standings": [
            _standing(
                levels=levels,
                candidate_count=candidate_count,
                rigorous_turns_ceiling=rigorous_turns_ceiling,
            )
            for levels in LEVELS
        ],
    }


def _standing(
    *,
    levels: int,
    candidate_count: int,
    rigorous_turns_ceiling: Decimal,
) -> dict[str, object]:
    if candidate_count < levels:
        return {
            "deciding_tier": "arithmetic",
            "levels": levels,
            "reason": (
                f"{candidate_count} candidates cannot fill "
                f"{levels} levels"
            ),
            "standing": "ruled out",
        }
    if rigorous_turns_ceiling < (
        Decimal(levels - 1) / Decimal(levels)
    ):
        return {
            "deciding_tier": "bounded",
            "levels": levels,
            "reason": (
                "certified phase-span ceiling is short of the "
                "level span"
            ),
            "standing": "ruled out",
        }
    return {
        "deciding_tier": "none",
        "levels": levels,
        "reason": "no hard exclusion applies",
        "standing": "not ruled out",
    }


def _single_mode_cutoff(wavelength_nm: int) -> Decimal:
    contrast = (
        PILLAR_INDEX * PILLAR_INDEX
        - AMBIENT_INDEX * AMBIENT_INDEX
    )
    with localcontext() as context:
        context.prec = CUTOFF_PRECISION
        cutoff = (
            ROOT_CUTOFF
            * Decimal(wavelength_nm)
            / (PI * contrast.sqrt())
        )
        return cutoff.quantize(
            Decimal("0.000001"),
            rounding=ROUND_FLOOR,
        )


def _ceil_to_step(value: Decimal, step_nm: int) -> int:
    return (
        int(
            (value / Decimal(step_nm)).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
        * step_nm
    )


def _reference(name: str, wavelength_nm: int) -> dict[str, object]:
    identity = f"{name}-{wavelength_nm}"
    return {
        "content_hash": _reference_hash(identity),
        "media_type": "application/json",
        "metadata_content_hash": _reference_hash("metadata-" + identity),
        "size_bytes": len(identity),
    }


def _reference_hash(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


if __name__ == "__main__":
    for wavelength, document in derive_documents().items():
        print(f"{wavelength} nm")
        print(document.decode("utf-8"))
