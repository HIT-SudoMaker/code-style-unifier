from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from data.data_source.indexing.file_sources import build_file_source_records


def _write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.ones((4, 5), dtype=np.uint8)).save(path)


def test_biosr_file_source_scans_clean_root(tmp_path: Path) -> None:
    _write_image(tmp_path / "biosr" / "clean" / "ER" / "sample.png")
    _write_image(tmp_path / "biosr" / "noisy" / "ER" / "ignored.png")

    root, records, channel_policy = build_file_source_records(
        source_name="biosr",
        dataset_root=tmp_path,
        is_train=True,
        max_samples=None,
        random_seed=42,
    )

    assert root == tmp_path / "biosr" / "clean"
    assert channel_policy == "single"
    assert len(records) == 1
    assert records[0].image_id == "biosr/ER/sample"


def test_bbbc039_file_source_excludes_macos_metadata(tmp_path: Path) -> None:
    _write_image(tmp_path / "bbbc039" / "images" / "image.png")
    metadata = tmp_path / "bbbc039" / "images" / "__MACOSX" / "._image.png"
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_bytes(b"metadata")

    root, records, channel_policy = build_file_source_records(
        source_name="bbbc039",
        dataset_root=tmp_path,
        is_train=False,
        max_samples=None,
        random_seed=42,
    )

    assert root == tmp_path / "bbbc039"
    assert channel_policy == "luminance"
    assert len(records) == 1
    assert records[0].source_path == Path("images/image.png")


def test_unknown_file_source_reports_supported_names(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as error_info:
        build_file_source_records(
            source_name="unknown",
            dataset_root=tmp_path,
            is_train=True,
            max_samples=None,
            random_seed=42,
        )
    message = str(error_info.value)
    assert "不支持的文件数据源" in message
    assert "可选:" in message
    assert "biosr" in message
    assert "bbbc039" in message


def test_bbbc039_file_source_scans_images_directory_only(tmp_path: Path) -> None:
    _write_image(tmp_path / "bbbc039" / "images" / "image.png")
    _write_image(tmp_path / "bbbc039" / "masks" / "mask.png")

    root, records, channel_policy = build_file_source_records(
        source_name="bbbc039",
        dataset_root=tmp_path,
        is_train=True,
        max_samples=None,
        random_seed=42,
    )

    assert root == tmp_path / "bbbc039"
    assert channel_policy == "luminance"
    assert [record.source_path for record in records] == [Path("images/image.png")]
