import json
from io import BytesIO
from pathlib import Path
from tarfile import TarInfo
from zipfile import ZipFile
from tarfile import open as open_tar_file
import pytest
import numpy as np
from PIL import Image
from data.data_source.assets.organizers import (
    download_biosr_archives,
    download_bbbc038_stage1_train_archive,
    download_bbbc039_images_archive,
    download_fmd_archives,
    extract_biosr_clean_archives,
    extract_bbbc038_stage1_train_archive,
    extract_bbbc039_images_archive,
    extract_fmd_averaged_archives,
    prepare_generated_target_assets,
)
from data.data_source.assets.specs import (
    BBBC038_STAGE1_TRAIN_URL,
    BBBC039_IMAGES_URL,
    BIOSR_ARCHIVE_URLS,
    EXPECTED_RAW_DATASET_NAMES,
    FMD_ARCHIVE_URLS,
    inspect_raw_dataset_assets,
)


def test_expected_raw_dataset_names_include_unified_sources() -> None:
    """Verify unified raw dataset asset names."""
    assert EXPECTED_RAW_DATASET_NAMES == (
        "mnist",
        "fashion_mnist",
        "biosr",
        "fmd",
        "bbbc038",
        "bbbc039",
        "targets",
    )


def test_asset_specs_define_expected_readable_roots(tmp_path: Path) -> None:
    from data.data_source.assets.specs import RAW_DATASET_ASSETS

    by_name = {asset.dataset_name: asset for asset in RAW_DATASET_ASSETS}

    assert by_name["biosr"].path_parts == ("biosr", "clean")
    assert by_name["fmd"].path_parts == ("fmd", "averaged")
    assert by_name["bbbc038"].path_parts == ("bbbc038",)
    assert by_name["bbbc039"].path_parts == ("bbbc039",)
    assert by_name["targets"].is_generated is True


def test_inspect_raw_dataset_assets_reports_expected_paths(tmp_path: Path) -> None:
    """Verify raw dataset asset path statuses."""
    (tmp_path / "mnist").mkdir()
    (tmp_path / "biosr" / "clean").mkdir(parents=True)
    (tmp_path / "bbbc038").mkdir(parents=True)

    statuses = inspect_raw_dataset_assets(dataset_root=tmp_path)
    by_name = {status.dataset_name: status for status in statuses}

    assert by_name["mnist"].expected_path == tmp_path / "mnist"
    assert by_name["mnist"].is_ready is True
    assert by_name["biosr"].expected_path == tmp_path / "biosr" / "clean"
    assert by_name["biosr"].is_ready is True
    assert by_name["fmd"].expected_path == tmp_path / "fmd" / "averaged"
    assert by_name["fmd"].is_ready is False
    assert by_name["bbbc038"].expected_path == tmp_path / "bbbc038"
    assert by_name["bbbc038"].is_ready is True
    assert by_name["bbbc039"].expected_path == tmp_path / "bbbc039"
    assert by_name["bbbc039"].is_ready is False


def test_prepare_generated_target_assets_writes_manifest_under_raw_root(tmp_path: Path) -> None:
    """Verify deterministic target assets are written under the raw root."""
    manifest_path = prepare_generated_target_assets(dataset_root=tmp_path)

    assert manifest_path == tmp_path / "targets" / "manifest.json"
    assert manifest_path.exists()
    assert (tmp_path / "targets" / "target_usaf.png").exists()


def test_download_bbbc038_stage1_train_archive_uses_official_url(tmp_path: Path) -> None:
    """
    验证 BBBC038 下载定义。
    """
    calls: list[tuple[str, Path]] = []

    def _fake_downloader(source_url: str, destination_path: Path) -> None:
        calls.append((source_url, destination_path))
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(b"zip")

    archive_path = download_bbbc038_stage1_train_archive(
        dataset_root=tmp_path,
        downloader=_fake_downloader,
    )

    assert archive_path == tmp_path / "bbbc038" / "downloads" / "stage1_train.zip"
    assert calls == [(BBBC038_STAGE1_TRAIN_URL, archive_path)]
    assert archive_path.read_bytes() == b"zip"


def test_download_bbbc039_images_archive_uses_official_url(tmp_path: Path) -> None:
    """
    验证 BBBC039 图像归档下载定义。
    """
    calls: list[tuple[str, Path]] = []

    def _fake_downloader(source_url: str, destination_path: Path) -> None:
        calls.append((source_url, destination_path))
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(b"zip")

    archive_path = download_bbbc039_images_archive(
        dataset_root=tmp_path,
        downloader=_fake_downloader,
    )

    assert archive_path == tmp_path / "bbbc039" / "downloads" / "images.zip"
    assert calls == [(BBBC039_IMAGES_URL, archive_path)]


def test_download_biosr_archives_uses_figshare_file_urls(tmp_path: Path) -> None:
    """
    验证 BioSR 归档下载定义。
    """
    calls: list[tuple[str, Path]] = []

    def _fake_downloader(source_url: str, destination_path: Path) -> None:
        calls.append((source_url, destination_path))
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(b"zip")

    archive_paths = download_biosr_archives(
        dataset_root=tmp_path,
        archive_names=("CCPs.zip",),
        downloader=_fake_downloader,
    )

    expected_path = tmp_path / "biosr" / "downloads" / "CCPs.zip"
    assert archive_paths == (expected_path,)
    assert calls == [(BIOSR_ARCHIVE_URLS["CCPs.zip"], expected_path)]


def test_download_fmd_archives_uses_figshare_file_urls(tmp_path: Path) -> None:
    """
    验证 FMD 归档下载定义。
    """
    calls: list[tuple[str, Path]] = []

    def _fake_downloader(source_url: str, destination_path: Path) -> None:
        calls.append((source_url, destination_path))
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(b"tar")

    archive_paths = download_fmd_archives(
        dataset_root=tmp_path,
        archive_names=("Confocal_BPAE_B.tar",),
        downloader=_fake_downloader,
    )

    expected_path = tmp_path / "fmd" / "downloads" / "Confocal_BPAE_B.tar"
    assert archive_paths == (expected_path,)
    assert calls == [(FMD_ARCHIVE_URLS["Confocal_BPAE_B.tar"], expected_path)]


def test_extract_bbbc038_stage1_train_archive_expands_under_accession_root(tmp_path: Path) -> None:
    """
    验证 BBBC038 归档解压位置。
    """
    archive_path = tmp_path / "bbbc038" / "downloads" / "stage1_train.zip"
    archive_path.parent.mkdir(parents=True)
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("stage1_train/image_001.png", b"image")

    extracted_root = extract_bbbc038_stage1_train_archive(dataset_root=tmp_path)

    assert extracted_root == tmp_path / "bbbc038" / "stage1_train"
    assert (extracted_root / "image_001.png").read_bytes() == b"image"


def test_extract_bbbc039_images_archive_expands_under_images_root(tmp_path: Path) -> None:
    """
    验证 BBBC039 图像归档解压位置。
    """
    archive_path = tmp_path / "bbbc039" / "downloads" / "images.zip"
    archive_path.parent.mkdir(parents=True)
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("images/image_001.tif", b"image")

    extracted_root = extract_bbbc039_images_archive(dataset_root=tmp_path)

    assert extracted_root == tmp_path / "bbbc039" / "images"
    assert (extracted_root / "image_001.tif").read_bytes() == b"image"


def test_extract_bbbc039_images_archive_records_height_width_resolution(tmp_path: Path) -> None:
    archive_path = tmp_path / "bbbc039" / "downloads" / "images.zip"
    archive_path.parent.mkdir(parents=True)
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "images/non_square.png",
            _build_png_bytes(np.ones((4, 5), dtype=np.uint8)),
        )

    extract_bbbc039_images_archive(dataset_root=tmp_path)

    manifest = json.loads((tmp_path / "bbbc039" / "manifest.json").read_text())
    assert manifest["items"][0]["raw_resolution"] == [4, 5]


def test_extract_fmd_averaged_archives_keeps_only_ground_truth_averages(tmp_path: Path) -> None:
    """
    验证 FMD 干净图像整理位置。
    """
    archive_path = tmp_path / "fmd" / "downloads" / "Confocal_BPAE_B.tar"
    archive_path.parent.mkdir(parents=True)
    with open_tar_file(archive_path, "w") as archive:
        _add_tar_bytes(archive, "Confocal_BPAE_B/gt/1/avg50.png", b"clean")
        _add_tar_bytes(archive, "Confocal_BPAE_B/raw/1/01.png", b"noisy")

    averaged_root = extract_fmd_averaged_archives(
        dataset_root=tmp_path,
        archive_names=("Confocal_BPAE_B.tar",),
    )

    assert averaged_root == tmp_path / "fmd" / "averaged"
    assert (averaged_root / "Confocal_BPAE_B" / "1" / "avg50.png").read_bytes() == b"clean"
    assert not (averaged_root / "Confocal_BPAE_B" / "raw" / "1" / "01.png").exists()


def test_extract_biosr_clean_archives_keeps_ground_truth_images(tmp_path: Path) -> None:
    """
    验证 BioSR 干净图像整理位置。
    """
    archive_path = tmp_path / "biosr" / "downloads" / "Microtubules.zip"
    archive_path.parent.mkdir(parents=True)
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("Microtubules/Cell_001/SIM_gt.mrc", _build_mrc_bytes(np.array([[1, 2], [3, 4]], dtype=np.uint16)))
        archive.writestr("Microtubules/training_wf/0001.tif", b"widefield")

    clean_root = extract_biosr_clean_archives(
        dataset_root=tmp_path,
        archive_names=("Microtubules.zip",),
    )

    assert clean_root == tmp_path / "biosr" / "clean"
    assert (clean_root / "Microtubules" / "Cell_001" / "SIM_gt.tif").exists()
    assert not (clean_root / "Microtubules" / "training_wf" / "0001.tif").exists()


def test_extract_fmd_averaged_archives_rejects_missing_archive(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Confocal_BPAE_B.tar"):
        extract_fmd_averaged_archives(
            dataset_root=tmp_path,
            archive_names=("Confocal_BPAE_B.tar",),
        )
    assert not (tmp_path / "fmd" / "averaged").exists()


def test_extract_biosr_clean_archives_rejects_missing_archive(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Microtubules.zip"):
        extract_biosr_clean_archives(
            dataset_root=tmp_path,
            archive_names=("Microtubules.zip",),
        )
    assert not (tmp_path / "biosr" / "clean").exists()


def test_raw_dataset_asset_modules_expose_direct_public_surface() -> None:
    assert callable(inspect_raw_dataset_assets)
    assert callable(prepare_generated_target_assets)
    assert callable(download_bbbc038_stage1_train_archive)
    assert callable(download_bbbc039_images_archive)
    assert callable(download_biosr_archives)
    assert callable(download_fmd_archives)
    assert callable(extract_bbbc038_stage1_train_archive)
    assert callable(extract_bbbc039_images_archive)
    assert callable(extract_fmd_averaged_archives)
    assert callable(extract_biosr_clean_archives)


def _add_tar_bytes(archive: object, member_name: str, content: bytes) -> None:
    member = TarInfo(member_name)
    member.size = len(content)
    archive.addfile(member, fileobj=_BytesReader(content))


class _BytesReader:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._content) - self._offset
        chunk = self._content[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def _build_mrc_bytes(array: np.ndarray) -> bytes:
    header = bytearray(1024)
    header[0:16] = np.array([array.shape[1], array.shape[0], 1, 6], dtype="<i4").tobytes()
    header[92:96] = np.array([0], dtype="<i4").tobytes()
    return bytes(header) + array.astype("<u2").tobytes()


def _build_png_bytes(array: np.ndarray) -> bytes:
    buffer = BytesIO()
    Image.fromarray(array).save(buffer, format="PNG")
    return buffer.getvalue()
