from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from data.data_source.indexing.file_index import FileIndexRecord
from data.data_source.datasets.image_file_dataset import ImageFileDataset
from data.preparation.dataset import PreparedDataset


def _record(source_path: Path) -> FileIndexRecord:
    return FileIndexRecord(
        dataset_name="fmd",
        split_name="train",
        image_id="fmd/widefield/a",
        source_index=4,
        source_path=source_path,
        category="fmd",
        label=0,
        provenance_url="https://curate.nd.edu/articles/dataset/Fluorescence_Microscopy_Denoising_FMD_dataset/24744648",
        license_name="CC BY-SA 4.0",
        source_metadata={"microscope": "widefield"},
    )


def test_image_file_dataset_returns_raw_sample_with_required_provenance(tmp_path: Path) -> None:
    image_path = tmp_path / "widefield" / "a.png"
    image_path.parent.mkdir(parents=True)
    Image.fromarray(np.array([[0, 128], [255, 64]], dtype=np.uint8)).save(image_path)

    dataset = ImageFileDataset(dataset_root=tmp_path, records=[_record(Path("widefield/a.png"))])
    sample = dataset[0]

    assert tuple(sample["image"].shape) == (1, 2, 2)
    assert sample["image"].dtype.is_floating_point
    assert sample["label"] == 0
    assert sample["category"] == "fmd"
    assert sample["provenance"]["dataset_name"] == "fmd"
    assert sample["provenance"]["split_name"] == "train"
    assert sample["provenance"]["image_id"] == "fmd/widefield/a"
    assert sample["provenance"]["source_index"] == 4
    assert sample["provenance"]["sampled_index"] == 0
    assert sample["provenance"]["source_path"] == "widefield/a.png"
    assert sample["provenance"]["raw_resolution"] == (2, 2)
    assert sample["provenance"]["provenance_url"].startswith("https://curate.nd.edu")
    assert sample["provenance"]["license"] == "CC BY-SA 4.0"
    assert sample["provenance"]["source_metadata"] == {"microscope": "widefield"}


def test_image_file_dataset_rejects_rgb_without_channel_policy(tmp_path: Path) -> None:
    image_path = tmp_path / "rgb.png"
    Image.new("RGB", (2, 2), color=(1, 2, 3)).save(image_path)
    dataset = ImageFileDataset(dataset_root=tmp_path, records=[_record(Path("rgb.png"))])

    with pytest.raises(ValueError, match="单通道"):
        dataset[0]


def test_image_file_dataset_can_convert_rgb_to_luminance(tmp_path: Path) -> None:
    image_path = tmp_path / "rgb.png"
    Image.new("RGB", (2, 2), color=(10, 20, 30)).save(image_path)

    dataset = ImageFileDataset(
        dataset_root=tmp_path,
        records=[_record(Path("rgb.png"))],
        channel_policy="luminance",
    )

    assert tuple(dataset[0]["image"].shape) == (1, 2, 2)


def test_image_file_dataset_preserves_uint16_scale_for_auto_normalization(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "low_uint16.tif"
    Image.fromarray(np.array([[0, 255]], dtype=np.uint16)).save(image_path)
    raw_dataset = ImageFileDataset(
        dataset_root=tmp_path,
        records=[_record(Path("low_uint16.tif"))],
    )

    prepared_dataset = PreparedDataset(
        source_dataset=raw_dataset,
        image_resolution=(1, 2),
        array_resolution=(1, 2),
        normalization_method="auto",
    )
    sample = prepared_dataset[0]

    assert sample["image"].flatten().tolist() == pytest.approx([0.0, 255.0 / 65535.0])
