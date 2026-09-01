from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from data import load
from data.configs import SourceConfig
from data.data_source import DATASET_REGISTRY
from data.data_source.adapters.bbbc import BBBCDataset
from data.data_source.adapters.biosr import BioSRDataset
from data.data_source.adapters.fmd import FMDDataset


def _write_image(path: Path, value: int = 9) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((4, 5), value, dtype=np.uint8)).save(path)


def test_new_file_sources_are_registered_in_unified_factory() -> None:
    assert DATASET_REGISTRY["biosr"].builder is BioSRDataset
    assert DATASET_REGISTRY["fmd"].builder is FMDDataset
    assert DATASET_REGISTRY["bbbc038"].builder is BBBCDataset
    assert DATASET_REGISTRY["bbbc038"].default_kwargs == {"accession": "BBBC038"}
    assert DATASET_REGISTRY["bbbc039"].builder is BBBCDataset
    assert DATASET_REGISTRY["bbbc039"].default_kwargs == {"accession": "BBBC039"}


def test_biosr_discovers_clean_images_without_clean_in_image_id(tmp_path: Path) -> None:
    _write_image(tmp_path / "biosr" / "clean" / "ER" / "sample.png")
    _write_image(tmp_path / "biosr" / "noisy" / "ER" / "ignored.png")

    dataset = BioSRDataset(dataset_root=tmp_path, is_train=True)
    sample = dataset[0]

    assert len(dataset) == 1
    assert sample["category"] == "biosr"
    assert sample["provenance"]["dataset_name"] == "biosr"
    assert sample["provenance"]["split_name"] == "train"
    assert sample["provenance"]["image_id"] == "biosr/ER/sample"
    assert sample["provenance"]["source_path"] == "ER/sample.png"
    assert sample["provenance"]["source_metadata"]["clean_source"] == "clean"
    assert sample["provenance"]["source_metadata"]["official_split"] is False


def test_fmd_discovers_averaged_images_without_averaged_in_image_id(tmp_path: Path) -> None:
    _write_image(tmp_path / "fmd" / "averaged" / "widefield" / "sample.png")
    _write_image(tmp_path / "fmd" / "raw" / "widefield" / "ignored.png")

    dataset = FMDDataset(dataset_root=tmp_path, is_train=False)
    sample = dataset[0]

    assert len(dataset) == 1
    assert sample["category"] == "fmd"
    assert sample["provenance"]["split_name"] == "test"
    assert sample["provenance"]["image_id"] == "fmd/widefield/sample"
    assert sample["provenance"]["source_path"] == "widefield/sample.png"
    assert sample["provenance"]["source_metadata"]["clean_source"] == "averaged"
    assert sample["provenance"]["source_metadata"]["official_split"] is False


def test_bbbc_uses_accession_as_dataset_name(tmp_path: Path) -> None:
    _write_image(tmp_path / "bbbc038" / "stage1_train" / "sample" / "images" / "image.png")

    dataset = BBBCDataset(dataset_root=tmp_path, accession="BBBC038", is_train=True)
    sample = dataset[0]

    assert sample["category"] == "bbbc038"
    assert sample["provenance"]["dataset_name"] == "bbbc038"
    assert sample["provenance"]["image_id"] == "bbbc038/stage1_train/sample/images/image"
    assert sample["provenance"]["source_metadata"]["accession"] == "BBBC038"


def test_bbbc038_ignores_segmentation_masks(tmp_path: Path) -> None:
    _write_image(tmp_path / "bbbc038" / "stage1_train" / "sample" / "images" / "image.png")
    _write_image(tmp_path / "bbbc038" / "stage1_train" / "sample" / "masks" / "mask.png")

    dataset = BBBCDataset(dataset_root=tmp_path, accession="BBBC038", is_train=True)

    assert len(dataset) == 1
    assert dataset[0]["provenance"]["source_path"] == "stage1_train/sample/images/image.png"


def test_bbbc038_converts_color_images_to_luminance(tmp_path: Path) -> None:
    path = tmp_path / "bbbc038" / "stage1_train" / "sample" / "images" / "image.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((4, 5, 3), 128, dtype=np.uint8)).save(path)

    sample = BBBCDataset(dataset_root=tmp_path, accession="BBBC038", is_train=True)[0]

    assert sample["image"].shape == (1, 4, 5)


def test_bbbc039_uses_images_directory_as_clean_source(tmp_path: Path) -> None:
    _write_image(tmp_path / "bbbc039" / "images" / "image.png")

    dataset = BBBCDataset(dataset_root=tmp_path, accession="BBBC039", is_train=False)
    sample = dataset[0]

    assert sample["category"] == "bbbc039"
    assert sample["provenance"]["dataset_name"] == "bbbc039"
    assert sample["provenance"]["image_id"] == "bbbc039/images/image"
    assert sample["provenance"]["source_metadata"]["accession"] == "BBBC039"


def test_bbbc039_ignores_macos_archive_metadata(tmp_path: Path) -> None:
    _write_image(tmp_path / "bbbc039" / "images" / "image.png")
    metadata_path = tmp_path / "bbbc039" / "images" / "__MACOSX" / "images" / "._image.tif"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_bytes(b"metadata")

    dataset = BBBCDataset(dataset_root=tmp_path, accession="BBBC039", is_train=True)

    assert len(dataset) == 1
    assert dataset[0]["provenance"]["source_path"] == "images/image.png"


def test_file_sources_apply_deterministic_max_samples(tmp_path: Path) -> None:
    for index in range(5):
        _write_image(tmp_path / "fmd" / "averaged" / f"sample_{index}.png", value=index)

    first = FMDDataset(dataset_root=tmp_path, is_train=True, max_samples=2, random_seed=13)
    second = FMDDataset(dataset_root=tmp_path, is_train=True, max_samples=2, random_seed=13)

    assert len(first) == 2
    assert [record.source_index for record in first.records] == [
        record.source_index for record in second.records
    ]


def test_load_builds_file_source_with_source_specific_options(tmp_path: Path) -> None:
    _write_image(tmp_path / "biosr" / "clean" / "ER" / "sample.png")

    dataset = load(
        SourceConfig(
            dataset_name="biosr",
            dataset_root=str(tmp_path),
            is_train=True,
            samples_per_class=3,
            max_samples=1,
            random_seed=5,
        )
    )

    assert len(dataset) == 1
    assert dataset[0]["provenance"]["image_id"] == "biosr/ER/sample"


def test_missing_file_source_directory_raises_guidance(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="biosr"):
        BioSRDataset(dataset_root=tmp_path)


def test_load_builds_bbbc039_with_accession_default(tmp_path: Path) -> None:
    _write_image(tmp_path / "bbbc039" / "images" / "image.png")

    dataset = load(
        SourceConfig(
            dataset_name="bbbc039",
            dataset_root=str(tmp_path),
            is_train=False,
            max_samples=1,
        )
    )

    assert len(dataset) == 1
    sample = dataset[0]
    assert sample["provenance"]["dataset_name"] == "bbbc039"
    assert sample["provenance"]["image_id"] == "bbbc039/images/image"
    assert sample["provenance"]["source_metadata"]["accession"] == "BBBC039"
