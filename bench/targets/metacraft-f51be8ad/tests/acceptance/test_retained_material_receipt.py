from __future__ import annotations

from pathlib import Path
import sys

import pytest

from metacraft.authority import Authority, Document, Reference
from tests.harness_acceptance import (
    OPENING_PROMPT,
    CapsuleRequest,
    CodexAcceptanceProfile,
    RetainedMaterialReceipt,
    inspect_capsule,
)


ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize(
    (
        "case_name",
        "authority_root",
        "observation_key",
        "binding_hash",
        "observation_hash",
        "product_sample_hash",
        "expected_materials",
    ),
    (
        (
            "arbabi-2015-high-na-propagation",
            ROOT / "runs" / "brief-stage-arbabi-20260808-d401d0cb" / "authority",
            "material_observation:sha256:9dfdf84442fbe42144d58a17a6c5b3b04a954c2fb077b72934bdc31ac089fe6b",
            "sha256:6623cab3406a5c91f193f442e7ceceb1b10818b77b42418c44ba82b50e330be6",
            "sha256:4d0484a06eeb003fb03c992276e19a62afe3d6aa8212b3eab2a764483c556874",
            "sha256:e8c7a4f64d7f6c4bb27e0edc969ede21e3b9dce87f326007e4658208161d76b4",
            (
                ("silicon", "Si (Silicon) - Palik", "3.4763795526495227", "0.0"),
                ("fused silica", "SiO2 (Glass) - Palik", "1.4440023011779028", "0.0"),
            ),
        ),
        (
            "khorasaninejad-2016-high-na-geometric",
            ROOT
            / "runs"
            / "brief-stage-khorasaninejad-20260808-9192e76a"
            / "authority",
            "material_observation:sha256:3b819004a658f28bc266e1e38aa45123b08afaad3e95864898da4daf8bf91e8a",
            "sha256:6623cab3406a5c91f193f442e7ceceb1b10818b77b42418c44ba82b50e330be6",
            "sha256:01d124c33dc492ab768be895354cfd8b83fd7b8295f663151e1ef23d29ac5f3d",
            "sha256:6082944c39e992519da4621be35b0282bd38d46e041ba11137a49280a55de849",
            (
                (
                    "amorphous titanium dioxide",
                    "TiO2 (Titanium Dioxide) - Siefke",
                    "2.449972396051889",
                    "0.00000012524968996802398",
                ),
                ("glass", "SiO2 (Glass) - Palik", "1.4607226165310925", "0.0"),
            ),
        ),
        (
            "mcclung-2024-low-na-propagation",
            ROOT
            / "runs"
            / "evidence"
            / "lumerical-material-mcclung-yang-20260809T091740159805Z-ed5ddf5c"
            / "authority",
            "material_observation:sha256:643d27cadf51e6e0f0743a961df77f1b3fc5ba7f2c922fe8c6c1af1512c2e9ac",
            "sha256:b72921795d84af92a37f78fd1fe0f1ac860e9d43ba884089bce5a5a13e46cad3",
            "sha256:801b07b01b9e879628b9af321c35b8e54b729ddf85811c2e64056b230e7d64fa",
            "sha256:71214e67ff11a2da4f332823169b42e6003911d3f92550825d26bfc33528038d",
            (
                (
                    "silicon nitride",
                    "Si3N4 (Silicon Nitride) - Luke",
                    "2.0524261260858365",
                    "0.0",
                ),
                ("fused silica", "SiO2 (Glass) - Palik", "1.4599160424269468", "0.0"),
            ),
        ),
        (
            "yang-2018-low-na-geometric",
            ROOT
            / "runs"
            / "evidence"
            / "lumerical-material-mcclung-yang-20260809T091740159805Z-ed5ddf5c"
            / "authority",
            "material_observation:sha256:198d3476f976d265cf7bcbd0f31a7f601b4b5f2ad12fe7aa60c37582e9d1e43b",
            "sha256:b72921795d84af92a37f78fd1fe0f1ac860e9d43ba884089bce5a5a13e46cad3",
            "sha256:8a04130003834b6e4d27359d750119c417264f989dd47594caf6c7db6c6c2944",
            "sha256:b18b673d90b6f65711bda783f04240d2f80d916a72a119de762165f9bdfdef51",
            (
                ("silicon", "Si (Silicon) - Palik", "3.4763795526495227", "0.0"),
                ("silicon dioxide", "SiO2 (Glass) - Palik", "1.4440023011779028", "0.0"),
            ),
        ),
    ),
)
def test_fresh_capsule_replays_one_exact_retained_material_receipt(
    case_name: str,
    authority_root: Path,
    observation_key: str,
    binding_hash: str,
    observation_hash: str,
    product_sample_hash: str,
    expected_materials: tuple[tuple[str, str, str, str], ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which",
        lambda name: f"C:/reviewed/{name}.exe",
    )
    source = Authority(authority_root)
    source_revision = source.view().revision
    request = CapsuleRequest(
        root=tmp_path / case_name,
        case_name=case_name,
        repository=ROOT,
        python_executable=Path(sys.executable),
        inherited_environment={},
        opening_prompt=OPENING_PROMPT,
        material_receipt=RetainedMaterialReceipt(
            authority_root=authority_root,
            observation_key=observation_key,
        ),
    )

    capsule = CodexAcceptanceProfile().prepare(request).capsule
    inspected = inspect_capsule(capsule)

    assert source.view().revision == source_revision
    assert not (capsule.root / "fixture-provenance.json").exists()
    receipt_files = tuple(
        sorted(capsule.root.glob("reviewed-material-*.json"))
    )
    assert len(receipt_files) == 6
    assert all(authority_root.as_posix() not in path.read_text() for path in receipt_files)
    assert inspected["outcome"] == "ConsultationRequired"
    assert inspected["current_question"] == "period"
    material = inspected["material"]
    assert material is not None
    assert material["sample"]["schema_identifier"] == "metacraft.material.observation"
    assert material["sample_reference"]["content_hash"] == observation_hash
    assert material["solver_binding_reference"]["content_hash"] == binding_hash

    sample_values = material["sample"]["values"]
    actual_materials = tuple(
        (
            value["family"],
            value["native_name"],
            value["refractive_index"],
            value["extinction_coefficient"],
        )
        for value in sample_values["materials"].values()
    )
    assert actual_materials == expected_materials
    assert sample_values["product_sample_reference"]["content_hash"] == (
        product_sample_hash
    )

    destination = Authority(capsule.application_root / "authority")
    observation = Document.from_bytes(
        destination.fetch(Reference.from_mapping(material["sample_reference"]))
    )
    observation_values = observation.values
    destination.fetch(
        Reference.from_mapping(observation_values["product_sample_reference"])
    )
    request_values = observation_values["request"]
    for selection in request_values["selections"].values():
        destination.fetch(Reference.from_mapping(selection["reference"]))

    assert tuple(capsule.root.rglob("workspace.sqlite3")) == (
        capsule.application_root / "authority" / "workspace.sqlite3",
    )
    assert not any(path.is_symlink() for path in capsule.root.rglob("*"))


def test_capsule_request_keeps_fixture_preparation_as_the_default(tmp_path: Path) -> None:
    request = CapsuleRequest(
        root=tmp_path / "capsule",
        case_name="mcclung-2024-low-na-propagation",
        repository=ROOT,
        python_executable=Path(sys.executable),
        inherited_environment={},
        opening_prompt=OPENING_PROMPT,
    )

    assert request.material_receipt is None
