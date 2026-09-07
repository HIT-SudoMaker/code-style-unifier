from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import torch
from torch.utils.data import Dataset

from experiments.restoration.fixed_measurement.learning import splits
from experiments.restoration.fixed_measurement.learning.splits import (
    FMD_ARCHIVE_SPLIT_SCHEMA_VERSION,
    FMD_STANDARD_SPLIT_SEED,
    SplitFilteredDataset,
    build_fmd_group_key,
    build_real_fmd_split_manifest,
    build_split_manifest,
    is_fmd_group_key_matched,
    read_split_manifest,
    select_split_records,
    validate_split_manifest,
    write_split_manifest,
)


class _TinyProvenanceDataset(Dataset):
    """
    鎻愪緵娴嬭瘯杈呭姪鏇胯韩
    """
    def __init__(self, image_ids: list[str]) -> None:
        """
        鎻愪緵娴嬭瘯杈呭姪閫昏緫
        """
        self.image_ids = image_ids

    def __len__(self) -> int:
        """
        鎻愪緵娴嬭瘯杈呭姪閫昏緫
        """
        return len(self.image_ids)

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        鎻愪緵娴嬭瘯杈呭姪閫昏緫
        """
        return {
            "clean_image": torch.full((1, 2, 2), float(index)),
            "provenance": {"image_id": self.image_ids[index]},
        }


@dataclass(frozen=True)
class _ImageIdRecord:
    """
    鎻愪緵娴嬭瘯杈呭姪鏇胯韩
    """
    image_id: str


class _MetadataOnlyDataset(Dataset):
    """
    鎻愪緵娴嬭瘯杈呭姪鏇胯韩
    """
    def __init__(self, image_ids: list[str]) -> None:
        """
        鎻愪緵娴嬭瘯杈呭姪閫昏緫
        """
        self.records = [_ImageIdRecord(image_id) for image_id in image_ids]
        self.getitem_calls = 0

    def __len__(self) -> int:
        """
        鎻愪緵娴嬭瘯杈呭姪閫昏緫
        """
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        鎻愪緵娴嬭瘯杈呭姪閫昏緫
        """
        self.getitem_calls += 1
        image_id = self.records[index].image_id
        return {
            "clean_image": torch.full((1, 2, 2), float(index)),
            "provenance": {"image_id": image_id},
        }


class _ExplodingMetadataDataset(_MetadataOnlyDataset):
    """
    鎻愪緵娴嬭瘯杈呭姪鏇胯韩
    """
    def __getitem__(self, index: int) -> dict[str, object]:
        """
        鎻愪緵娴嬭瘯杈呭姪閫昏緫
        """
        if self.getitem_calls == 0:
            raise AssertionError("construction should not materialize samples")
        return super().__getitem__(index)


@dataclass(frozen=True)
class _FileIndexRecord:
    """
    鎻愪緵娴嬭瘯杈呭姪鏇胯韩
    """
    image_id: str
    source_path: Path


def _manifest() -> splits.SplitManifest:
    """
    鎻愪緵娴嬭瘯杈呭姪閫昏緫
    """
    image_ids = [
        "fmd/Confocal_BPAE_G/1/avg50",
        "fmd/Confocal_BPAE_B/1/avg50",
        "fmd/Confocal_BPAE_G/2/avg50",
        "fmd/Confocal_BPAE_B/2/avg50",
        "fmd/TwoPhoton_BPAE_G/3/avg50",
        "fmd/TwoPhoton_BPAE_B/3/avg50",
    ]
    return build_split_manifest(
        image_ids=image_ids,
        source_paths=[f"data/raw/{image_id}.png" for image_id in image_ids],
        split_seed=FMD_STANDARD_SPLIT_SEED,
        train_fraction=1 / 3,
        val_fraction=1 / 3,
        test_fraction=1 / 3,
    )


def test_build_fmd_group_key_groups_channel_variants_by_scene() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    assert build_fmd_group_key("fmd/Confocal_BPAE_G/13/avg50") == "Confocal_BPAE/13"
    assert build_fmd_group_key("fmd/Confocal_BPAE_B/13/avg50") == "Confocal_BPAE/13"
    assert build_fmd_group_key("fmd/TwoPhoton_BPAE_G/4/avg50") == "TwoPhoton_BPAE/4"
    assert (
        build_fmd_group_key("fmd/test_mix/TwoPhoton_BPAE_B_5")
        == "test_mix/TwoPhoton_BPAE/5"
    )


def test_build_fmd_group_key_falls_back_to_parent_path() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    assert build_fmd_group_key("fmd/unmatched/path/image") == "fmd/unmatched/path"


def test_is_fmd_group_key_matched_identifies_known_patterns() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    assert is_fmd_group_key_matched("fmd/Confocal_BPAE_G/13/avg50")
    assert not is_fmd_group_key_matched("fmd/unmatched/path/image")


def test_build_split_manifest_creates_group_disjoint_splits() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()

    validate_split_manifest(manifest)
    assert manifest["split_summary"]["test"]["image_count"] > 0

    group_splits: dict[str, str] = {}
    for record in manifest["records"]:
        previous = group_splits.setdefault(record["group_key"], record["split"])
        assert previous == record["split"]

    assert {record["split"] for record in manifest["records"]} == {
        "train",
        "val",
        "test",
    }


def test_write_and_read_split_manifest_round_trip(tmp_path: Path) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    path = tmp_path / "splits" / "manifest.json"

    written_path = write_split_manifest(path, manifest)
    loaded = read_split_manifest(written_path)

    assert written_path == path
    assert loaded == manifest


def test_validate_split_manifest_rejects_group_key_crossing_splits() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    records_by_group: dict[str, list[splits.SplitRecord]] = {}
    for record in manifest["records"]:
        records_by_group.setdefault(record["group_key"], []).append(record)
    paired_records = next(
        records for records in records_by_group.values() if len(records) >= 2
    )
    assert paired_records[0]["image_id"] != paired_records[1]["image_id"]
    paired_records[1]["split"] = (
        "val" if paired_records[0]["split"] != "val" else "test"
    )

    with pytest.raises(ValueError, match="group_key appears in multiple splits"):
        validate_split_manifest(manifest)


def test_validate_split_manifest_rejects_duplicate_image_id() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    manifest["records"][1]["image_id"] = manifest["records"][0]["image_id"]

    with pytest.raises(ValueError, match="duplicate image_id"):
        validate_split_manifest(manifest)


def test_validate_split_manifest_rejects_group_key_mismatch() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    manifest["records"][0]["group_key"] = "wrong/group"

    with pytest.raises(ValueError, match="group_key"):
        validate_split_manifest(manifest)


def test_validate_split_manifest_rejects_stratification_key_mismatch() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    manifest["records"][0]["stratification_key"] = "wrong-stratum"

    with pytest.raises(ValueError, match="stratification_key"):
        validate_split_manifest(manifest)


def test_validate_split_manifest_rejects_missing_split_name() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    manifest["records"] = [
        record for record in manifest["records"] if record["split"] != "test"
    ]

    with pytest.raises(ValueError, match="missing splits: test"):
        validate_split_manifest(manifest)


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("source_dataset_root_hint", "", "source_dataset_root_hint"),
        ("source_dataset_root_hint", None, "source_dataset_root_hint"),
        ("split_seed", True, "split_seed"),
        ("split_seed", -1, "split_seed"),
        ("split_seed", 1.5, "split_seed"),
    ],
)
def test_validate_split_manifest_rejects_invalid_schema_fields(
    field: str,
    bad_value: object,
    message: str,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    manifest[field] = bad_value  # type: ignore[literal-required]

    with pytest.raises(ValueError, match=message):
        validate_split_manifest(manifest)


def test_validate_split_manifest_rejects_split_summary_mismatch() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    manifest["split_summary"]["train"]["image_count"] = -1

    with pytest.raises(ValueError, match="split_summary mismatch"):
        validate_split_manifest(manifest)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "image_ids": ["fmd/Confocal_BPAE_G/1/avg50"],
                "source_paths": [],
            },
            "same length",
        ),
        (
            {
                "image_ids": [],
                "source_paths": [],
            },
            "must not be empty",
        ),
        (
            {
                "image_ids": ["fmd/Confocal_BPAE_G/1/avg50"],
                "source_paths": ["data/raw/fmd/Confocal_BPAE_G/1/avg50.png"],
                "train_fraction": -0.1,
                "val_fraction": 0.6,
                "test_fraction": 0.5,
            },
            "non-negative",
        ),
        (
            {
                "image_ids": ["fmd/Confocal_BPAE_G/1/avg50"],
                "source_paths": ["data/raw/fmd/Confocal_BPAE_G/1/avg50.png"],
                "train_fraction": 0.5,
                "val_fraction": 0.25,
                "test_fraction": 0.1,
            },
            "sum to 1.0",
        ),
    ],
)
def test_build_split_manifest_rejects_invalid_inputs(
    kwargs: dict[str, object],
    message: str,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match=message):
        build_split_manifest(**kwargs)  # type: ignore[arg-type]


def test_select_split_records_returns_requested_split_only() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()

    selected = select_split_records(manifest, split="val")

    assert selected
    assert {record["split"] for record in selected} == {"val"}


def test_split_filtered_dataset_keeps_requested_manifest_records() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    selected_ids = {
        record["image_id"] for record in select_split_records(manifest, split="test")
    }
    dataset = _TinyProvenanceDataset(
        [record["image_id"] for record in manifest["records"]]
    )

    filtered = SplitFilteredDataset(dataset, manifest=manifest, split="test")

    assert len(filtered) == len(selected_ids)
    assert {
        filtered[index]["provenance"]["image_id"]  # type: ignore[index]
        for index in range(len(filtered))
    } == selected_ids


def test_split_filtered_dataset_uses_metadata_without_materializing_samples() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    selected_ids = {
        record["image_id"] for record in select_split_records(manifest, split="test")
    }
    dataset = _ExplodingMetadataDataset(
        [record["image_id"] for record in manifest["records"]]
    )

    filtered = SplitFilteredDataset(dataset, manifest=manifest, split="test")

    assert dataset.getitem_calls == 0
    dataset.getitem_calls = 1
    assert len(filtered) == len(selected_ids)
    assert {
        filtered[index]["provenance"]["image_id"]  # type: ignore[index]
        for index in range(len(filtered))
    } == selected_ids
    assert dataset.getitem_calls > 1


def test_split_filtered_dataset_rejects_duplicate_selected_source_image_ids() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    train_id = select_split_records(manifest, split="train")[0]["image_id"]
    dataset = _MetadataOnlyDataset(
        [record["image_id"] for record in manifest["records"]] + [train_id]
    )

    with pytest.raises(ValueError, match=f"duplicate image_id.*{train_id}"):
        SplitFilteredDataset(dataset, manifest=manifest, split="train")


def test_split_filtered_dataset_rejects_missing_manifest_samples() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    manifest = _manifest()
    train_ids = [
        record["image_id"] for record in select_split_records(manifest, split="train")
    ]
    remaining_ids = [
        record["image_id"]
        for record in manifest["records"]
        if record["image_id"] not in train_ids
    ]

    with pytest.raises(ValueError, match="missing split train image_id"):
        SplitFilteredDataset(
            _TinyProvenanceDataset(remaining_ids),
            manifest=manifest,
            split="train",
        )


def test_build_real_fmd_split_manifest_rejects_group_key_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    monkeypatch.setattr(
        splits,
        "build_file_source_records",
        lambda **kwargs: (
            Path("data/raw/fmd/averaged"),
            [_FileIndexRecord("fmd/unmatched/path/image", Path("image.png"))],
            "single",
        ),
    )

    with pytest.raises(ValueError, match="FMD group-key fallback"):
        build_real_fmd_split_manifest(dataset_root="data/raw")


def test_build_real_fmd_split_manifest_builds_valid_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    captured_kwargs: dict[str, object] = {}
    source_root = tmp_path / "data/raw/fmd/averaged"
    image_ids = [
        "fmd/Confocal_BPAE_G/1/avg50",
        "fmd/Confocal_BPAE_B/1/avg50",
        "fmd/Confocal_BPAE_G/2/avg50",
        "fmd/Confocal_BPAE_B/2/avg50",
        "fmd/TwoPhoton_BPAE_G/3/avg50",
        "fmd/TwoPhoton_BPAE_B/3/avg50",
        "fmd/test_mix/Confocal_BPAE_G_19",
    ]
    file_records = []
    for index, image_id in enumerate(image_ids):
        source_path = source_root / f"{image_id.removeprefix('fmd/')}.png"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(f"unique-image-{index}".encode("utf-8"))
        file_records.append(_FileIndexRecord(image_id, source_path))

    def fake_build_file_source_records(
        **kwargs: object,
    ) -> tuple[Path, list[_FileIndexRecord], str]:
        """
        鎻愪緵娴嬭瘯鏇胯韩瀹炵幇
        """
        captured_kwargs.update(kwargs)
        return source_root, file_records, "single"

    monkeypatch.setattr(
        splits,
        "build_file_source_records",
        fake_build_file_source_records,
    )

    manifest = build_real_fmd_split_manifest(
        dataset_root=tmp_path / "data/raw",
        split_seed=123,
        minimum_test_groups=1,
        minimum_test_images=1,
    )

    assert captured_kwargs == {
        "source_name": "fmd",
        "dataset_root": tmp_path / "data/raw",
        "is_train": True,
        "max_samples": None,
        "random_seed": 123,
    }
    assert manifest["schema_version"] == FMD_ARCHIVE_SPLIT_SCHEMA_VERSION
    assert manifest["source_selection_policy"] == "canonical_avg50_excluding_test_mix"
    assert manifest["source_dataset_root_hint"] == source_root.as_posix()
    assert {record["image_id"] for record in manifest["records"]} == {
        record.image_id
        for record in file_records
        if not record.image_id.startswith("fmd/test_mix/")
    }
    assert all("content_sha256" in record for record in manifest["records"])
    assert len({record["content_sha256"] for record in manifest["records"]}) == 6
    assert len(manifest["content_inventory_sha256"]) == 64
    assert all("\\" not in record["source_path"] for record in manifest["records"])
    assert all("/" in record["source_path"] for record in manifest["records"])
    validate_split_manifest(manifest)


def test_archival_split_rejects_duplicate_clean_image_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    楠岃瘉涓嶅悓缂栧彿涓嶈兘鎶婂悓涓€骞插噣鍥惧儚閲嶅甯﹀叆姝ｅ紡鍒掑垎
    """
    source_root = tmp_path / "data/raw/fmd/averaged"
    records = []
    for image_id in (
        "fmd/Confocal_BPAE_G/1/avg50",
        "fmd/Confocal_BPAE_G/2/avg50",
        "fmd/Confocal_BPAE_G/3/avg50",
    ):
        source_path = source_root / f"{image_id.removeprefix('fmd/')}.png"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(b"same-clean-image")
        records.append(_FileIndexRecord(image_id, source_path))
    monkeypatch.setattr(
        splits,
        "build_file_source_records",
        lambda **kwargs: (source_root, records, "single"),
    )

    with pytest.raises(ValueError, match="duplicate clean-image content"):
        build_real_fmd_split_manifest(
            dataset_root=tmp_path / "data/raw",
            minimum_test_groups=1,
            minimum_test_images=1,
        )


@pytest.mark.parametrize(
    ("minimum_test_groups", "minimum_test_images", "message"),
    [
        (99, 1, "minimum_test_groups"),
        (1, 99, "minimum_test_images"),
    ],
)
def test_build_real_fmd_split_manifest_rejects_too_high_test_minimums(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    minimum_test_groups: int,
    minimum_test_images: int,
    message: str,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    source_root = tmp_path / "data/raw/fmd/averaged"
    file_records = []
    for index, image_id in enumerate(
        (
            "fmd/Confocal_BPAE_G/1/avg50",
            "fmd/Confocal_BPAE_B/1/avg50",
            "fmd/Confocal_BPAE_G/2/avg50",
            "fmd/Confocal_BPAE_B/2/avg50",
            "fmd/TwoPhoton_BPAE_G/3/avg50",
            "fmd/TwoPhoton_BPAE_B/3/avg50",
        )
    ):
        source_path = source_root / f"{image_id.removeprefix('fmd/')}.png"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(f"unique-{index}".encode("utf-8"))
        file_records.append(_FileIndexRecord(image_id, source_path))
    monkeypatch.setattr(
        splits,
        "build_file_source_records",
        lambda **kwargs: (source_root, file_records, "single"),
    )

    with pytest.raises(ValueError, match=message):
        build_real_fmd_split_manifest(
            dataset_root=tmp_path / "data/raw",
            minimum_test_groups=minimum_test_groups,
            minimum_test_images=minimum_test_images,
        )
