from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil
import tarfile
from urllib.request import urlopen
from zipfile import ZipFile

from PIL import Image, UnidentifiedImageError
import numpy as np

from data.data_source.assets.manifests import ManifestItem, write_manifest
from data.data_source.assets.specs import (
    ArchiveNames,
    BBBC038_SOURCE_URL,
    BBBC038_STAGE1_TRAIN_URL,
    BBBC039_IMAGES_URL,
    BBBC039_SOURCE_URL,
    BIOSR_ARCHIVE_URLS,
    BIOSR_SOURCE_URL,
    DownloadFunction,
    FMD_ARCHIVE_URLS,
    FMD_SOURCE_URL,
    PathInput,
)
from data.data_source.dataset_root import resolve_dataset_root

TARGET_PROVENANCE_URL = "generated://deterministic-optical-targets"
TARGET_LICENSE_NAME = "project-generated"
TARGET_IMAGE_SIZE = 256


def prepare_generated_target_assets(*, dataset_root: PathInput = None) -> Path:
    """
    生成确定性target raw资产并返回manifest路径
    """
    root = Path(resolve_dataset_root(dataset_root))
    return generate_target_assets(target_root=root / "targets")


def generate_target_assets(*, target_root: str | Path) -> Path:
    """
    写入确定性光学目标图像和统一manifest文件
    """
    root = Path(target_root)
    root.mkdir(parents=True, exist_ok=True)
    builders: dict[str, Callable[[], np.ndarray]] = {
        "target_usaf": _build_usaf_array,
        "target_siemens": _build_siemens_array,
        "target_slanted_edge": _build_slanted_edge_array,
        "target_line_pairs": _build_line_pairs_array,
    }
    items: list[ManifestItem] = []
    for target_asset_id, builder in builders.items():
        file_name = f"{target_asset_id}.png"
        Image.fromarray(builder(), mode="L").save(root / file_name)
        items.append(
            ManifestItem(
                dataset_name="targets",
                source_archive="generated",
                source_member=target_asset_id,
                output_path=file_name,
                image_id=f"{target_asset_id}/{target_asset_id}",
                operation="generate_target",
                channel_policy="single",
                raw_resolution=(TARGET_IMAGE_SIZE, TARGET_IMAGE_SIZE),
                source_url=TARGET_PROVENANCE_URL,
                license=TARGET_LICENSE_NAME,
            )
        )
    return write_manifest(root / "manifest.json", items)


def download_bbbc038_stage1_train_archive(
    *,
    dataset_root: PathInput = None,
    downloader: DownloadFunction | None = None,
) -> Path:
    """
    下载BBBC038 stage1_train归档文件
    """
    root = Path(resolve_dataset_root(dataset_root))
    archive_path = root / "bbbc038" / "downloads" / "stage1_train.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    selected_downloader = downloader or _download_file
    selected_downloader(BBBC038_STAGE1_TRAIN_URL, archive_path)
    return archive_path


def download_bbbc039_images_archive(
    *,
    dataset_root: PathInput = None,
    downloader: DownloadFunction | None = None,
) -> Path:
    """
    下载BBBC039 images归档文件
    """
    root = Path(resolve_dataset_root(dataset_root))
    archive_path = root / "bbbc039" / "downloads" / "images.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    selected_downloader = downloader or _download_file
    selected_downloader(BBBC039_IMAGES_URL, archive_path)
    return archive_path


def download_biosr_archives(
    *,
    dataset_root: PathInput = None,
    archive_names: ArchiveNames = None,
    downloader: DownloadFunction | None = None,
) -> tuple[Path, ...]:
    """
    从Figshare文件站点下载BioSR归档
    """
    root = Path(resolve_dataset_root(dataset_root))
    return _download_archives(
        archive_urls=BIOSR_ARCHIVE_URLS,
        download_root=root / "biosr" / "downloads",
        archive_names=archive_names,
        downloader=downloader,
    )


def download_fmd_archives(
    *,
    dataset_root: PathInput = None,
    archive_names: ArchiveNames = None,
    downloader: DownloadFunction | None = None,
) -> tuple[Path, ...]:
    """
    从Figshare文件站点下载FMD归档
    """
    root = Path(resolve_dataset_root(dataset_root))
    return _download_archives(
        archive_urls=FMD_ARCHIVE_URLS,
        download_root=root / "fmd" / "downloads",
        archive_names=archive_names,
        downloader=downloader,
    )


def extract_bbbc038_stage1_train_archive(*, dataset_root: PathInput = None) -> Path:
    """
    解压BBBC038 stage1_train归档并返回图像根目录
    """
    root = Path(resolve_dataset_root(dataset_root))
    accession_root = root / "bbbc038"
    archive_path = accession_root / "downloads" / "stage1_train.zip"
    extracted_root = accession_root / "stage1_train"
    _require_archive(archive_path)
    extracted_root.mkdir(parents=True, exist_ok=True)
    resolved_root = extracted_root.resolve()

    items: list[ManifestItem] = []
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.parts and member_path.parts[0] == "stage1_train":
                member_path = Path(*member_path.parts[1:])
            if not member_path.parts:
                continue

            target_path = extracted_root / member_path
            resolved_target = target_path.resolve()
            if not resolved_target.is_relative_to(resolved_root):
                raise ValueError(
                    f"归档成员越过解压根目录: {member.filename}"
                )
            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target_path.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            relative_output = target_path.relative_to(accession_root).as_posix()
            items.append(
                ManifestItem(
                    dataset_name="BBBC038",
                    source_archive="downloads/stage1_train.zip",
                    source_member=member.filename,
                    output_path=relative_output,
                    image_id=f"bbbc038/{member_path.as_posix()}",
                    operation="extract_zip",
                    channel_policy="single",
                    raw_resolution=_image_resolution_or_zero(target_path),
                    source_url=BBBC038_SOURCE_URL,
                    license="unknown",
                )
            )
    write_manifest(accession_root / "manifest.json", items)
    return extracted_root


def extract_bbbc039_images_archive(*, dataset_root: PathInput = None) -> Path:
    """
    解压BBBC039 images归档并返回图像根目录
    """
    root = Path(resolve_dataset_root(dataset_root))
    accession_root = root / "bbbc039"
    archive_path = accession_root / "downloads" / "images.zip"
    extracted_root = accession_root / "images"
    _require_archive(archive_path)
    extracted_root.mkdir(parents=True, exist_ok=True)
    resolved_root = extracted_root.resolve()

    items: list[ManifestItem] = []
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.parts and member_path.parts[0] == "images":
                member_path = Path(*member_path.parts[1:])
            if not member_path.parts:
                continue

            target_path = extracted_root / member_path
            resolved_target = target_path.resolve()
            if not resolved_target.is_relative_to(resolved_root):
                raise ValueError(
                    f"归档成员越过解压根目录: {member.filename}"
                )
            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target_path.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            relative_output = target_path.relative_to(accession_root).as_posix()
            items.append(
                ManifestItem(
                    dataset_name="BBBC039",
                    source_archive="downloads/images.zip",
                    source_member=member.filename,
                    output_path=relative_output,
                    image_id=f"bbbc039/{member_path.as_posix()}",
                    operation="extract_zip",
                    channel_policy="single",
                    raw_resolution=_image_resolution_or_zero(target_path),
                    source_url=BBBC039_SOURCE_URL,
                    license="unknown",
                )
            )
    write_manifest(accession_root / "manifest.json", items)
    return extracted_root


def extract_fmd_averaged_archives(
    *,
    dataset_root: PathInput = None,
    archive_names: ArchiveNames = None,
) -> Path:
    """
    将FMD ground truth平均图像整理到统一averaged根目录
    """
    root = Path(resolve_dataset_root(dataset_root))
    accession_root = root / "fmd"
    download_root = accession_root / "downloads"
    averaged_root = accession_root / "averaged"
    selected_archive_names = _select_archive_names(FMD_ARCHIVE_URLS, archive_names)
    for archive_name in selected_archive_names:
        _require_archive(download_root / archive_name)
    averaged_root.mkdir(parents=True, exist_ok=True)
    items: list[ManifestItem] = []
    for archive_name in selected_archive_names:
        archive_path = download_root / archive_name
        with tarfile.open(archive_path) as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                target_relative_path = _fmd_averaged_relative_path(member.name)
                if target_relative_path is None:
                    continue
                target_path = _safe_output_path(averaged_root, target_relative_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    continue
                with source, target_path.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                relative_output = target_path.relative_to(accession_root).as_posix()
                items.append(
                    ManifestItem(
                        dataset_name="FMD",
                        source_archive=f"downloads/{archive_name}",
                        source_member=member.name,
                        output_path=relative_output,
                        image_id=f"fmd/{target_relative_path.as_posix()}",
                        operation="extract_tar",
                        channel_policy="single",
                        raw_resolution=_image_resolution_or_zero(target_path),
                        source_url=FMD_SOURCE_URL,
                        license="CC BY-SA 4.0",
                    )
                )
    write_manifest(accession_root / "manifest.json", items)
    return averaged_root


def extract_biosr_clean_archives(
    *,
    dataset_root: PathInput = None,
    archive_names: ArchiveNames = None,
) -> Path:
    """
    将BioSR ground truth图像整理到统一clean根目录
    """
    root = Path(resolve_dataset_root(dataset_root))
    accession_root = root / "biosr"
    download_root = accession_root / "downloads"
    clean_root = accession_root / "clean"
    selected_archive_names = _select_archive_names(BIOSR_ARCHIVE_URLS, archive_names)
    for archive_name in selected_archive_names:
        _require_archive(download_root / archive_name)
    clean_root.mkdir(parents=True, exist_ok=True)
    items: list[ManifestItem] = []
    for archive_name in selected_archive_names:
        archive_path = download_root / archive_name
        with ZipFile(archive_path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                target_relative_path = _biosr_clean_relative_path(member.filename)
                if target_relative_path is None:
                    continue
                target_path = _safe_output_path(clean_root, target_relative_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target_path.open("wb") as destination:
                    if member.filename.lower().endswith(".mrc"):
                        resolution = _write_mrc_as_tiff(source.read(), destination)
                        operation = "mrc_to_tiff"
                    else:
                        shutil.copyfileobj(source, destination)
                        resolution = _image_resolution_or_zero(target_path)
                        operation = "extract_zip"
                relative_output = target_path.relative_to(accession_root).as_posix()
                items.append(
                    ManifestItem(
                        dataset_name="BioSR",
                        source_archive=f"downloads/{archive_name}",
                        source_member=member.filename,
                        output_path=relative_output,
                        image_id=f"biosr/{target_relative_path.as_posix()}",
                        operation=operation,
                        channel_policy="single",
                        raw_resolution=resolution,
                        source_url=BIOSR_SOURCE_URL,
                        license="CC BY 4.0",
                    )
                )
    write_manifest(accession_root / "manifest.json", items)
    return clean_root


def _download_archives(
    *,
    archive_urls: dict[str, str],
    download_root: Path,
    archive_names: ArchiveNames,
    downloader: DownloadFunction | None,
) -> tuple[Path, ...]:
    download_root.mkdir(parents=True, exist_ok=True)
    selected_downloader = downloader or _download_file
    archive_paths = []
    for archive_name in _select_archive_names(archive_urls, archive_names):
        archive_path = download_root / archive_name
        selected_downloader(archive_urls[archive_name], archive_path)
        archive_paths.append(archive_path)
    return tuple(archive_paths)


def _download_file(source_url: str, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(source_url) as response, destination_path.open("wb") as destination:
        shutil.copyfileobj(response, destination)


def _select_archive_names(
    archive_urls: dict[str, str],
    archive_names: ArchiveNames,
) -> tuple[str, ...]:
    if archive_names is None:
        return tuple(archive_urls.keys())
    selected_names = tuple(archive_names)
    missing_names = [
        archive_name
        for archive_name in selected_names
        if archive_name not in archive_urls
    ]
    if missing_names:
        raise ValueError(
            f"未知归档名称: {missing_names}"
        )
    return selected_names


def _require_archive(archive_path: Path) -> None:
    if not archive_path.exists():
        raise FileNotFoundError(
            f"缺失数据归档: {archive_path}"
        )


def _safe_output_path(root: Path, relative_path: Path) -> Path:
    output_path = root / relative_path
    resolved_root = root.resolve()
    resolved_output = output_path.resolve()
    if not resolved_output.is_relative_to(resolved_root):
        raise ValueError(
            f"归档成员越过输出根目录: {relative_path.as_posix()}"
        )
    return output_path


def _fmd_averaged_relative_path(member_name: str) -> Path | None:
    parts = _normalized_archive_parts(member_name)
    if len(parts) >= 4 and parts[-1] == "avg50.png" and parts[-3] == "gt":
        return Path(parts[0], parts[-2], parts[-1])
    if len(parts) >= 3 and parts[-2] == "gt" and parts[-1].lower().endswith(".png"):
        return Path(parts[0], parts[-1])
    return None


def _biosr_clean_relative_path(member_name: str) -> Path | None:
    parts = _normalized_archive_parts(member_name)
    if not parts:
        return None
    lowered_parts = [part.lower() for part in parts]
    member_path = Path(*parts)
    if member_path.stem.lower().startswith("sim_gt") or "gtsim" in lowered_parts:
        return member_path.with_suffix(".tif")
    return None


def _normalized_archive_parts(member_name: str) -> tuple[str, ...]:
    return tuple(part for part in Path(member_name).parts if part not in ("", "."))


def _write_mrc_as_tiff(content: bytes, destination: object) -> tuple[int, int]:
    width, height, depth, mode = np.frombuffer(content[:16], dtype="<i4", count=4).tolist()
    extended_header_bytes = int(np.frombuffer(content[92:96], dtype="<i4", count=1)[0])
    if depth != 1:
        raise ValueError(
            f"BioSR clean MRC应为单层图像，实际层数为: {depth}"
        )
    dtype = _mrc_dtype(mode)
    start = 1024 + extended_header_bytes
    count = width * height * depth
    image_array = np.frombuffer(
        content,
        dtype=dtype,
        count=count,
        offset=start,
    ).reshape((height, width))
    Image.fromarray(image_array).save(destination, format="TIFF")
    return (height, width)


def _mrc_dtype(mode: int) -> np.dtype:
    if mode == 0:
        return np.dtype("int8")
    if mode == 1:
        return np.dtype("<i2")
    if mode == 2:
        return np.dtype("<f4")
    if mode == 6:
        return np.dtype("<u2")
    raise ValueError(
        f"不支持的MRC mode: {mode}"
    )


def _image_resolution_or_zero(image_path: Path) -> tuple[int, int]:
    try:
        with Image.open(image_path) as image:
            width, height = image.size
            return (height, width)
    except (OSError, ValueError, UnidentifiedImageError):
        return (0, 0)


def _build_usaf_array() -> np.ndarray:
    array = np.zeros((TARGET_IMAGE_SIZE, TARGET_IMAGE_SIZE), dtype=np.uint8)
    for group_index, period in enumerate((32, 16, 8, 4)):
        top = 16 + group_index * 56
        left = 16
        for bar_index in range(3):
            x_start = left + bar_index * period * 2
            array[top : top + 36, x_start : x_start + period] = 255
        horizontal_top = top + 40
        for bar_index in range(3):
            y_start = horizontal_top + bar_index * max(1, period)
            array[y_start : y_start + max(1, period // 2), 144:224] = 255
    return array


def _build_siemens_array() -> np.ndarray:
    y_grid, x_grid = np.indices((TARGET_IMAGE_SIZE, TARGET_IMAGE_SIZE))
    centered_x = x_grid - TARGET_IMAGE_SIZE / 2
    centered_y = y_grid - TARGET_IMAGE_SIZE / 2
    angle = np.arctan2(centered_y, centered_x)
    radius = np.sqrt(centered_x**2 + centered_y**2)
    spokes = np.sin(36 * angle) > 0
    disk = radius <= TARGET_IMAGE_SIZE * 0.45
    return np.where(spokes & disk, 255, 0).astype(np.uint8)


def _build_slanted_edge_array() -> np.ndarray:
    y_grid, x_grid = np.indices((TARGET_IMAGE_SIZE, TARGET_IMAGE_SIZE))
    edge = x_grid + 0.2 * y_grid > TARGET_IMAGE_SIZE * 0.55
    return np.where(edge, 255, 0).astype(np.uint8)


def _build_line_pairs_array() -> np.ndarray:
    array = np.zeros((TARGET_IMAGE_SIZE, TARGET_IMAGE_SIZE), dtype=np.uint8)
    periods = (32, 16, 8, 4, 2)
    for band_index, period in enumerate(periods):
        top = band_index * TARGET_IMAGE_SIZE // len(periods)
        bottom = (band_index + 1) * TARGET_IMAGE_SIZE // len(periods)
        x_grid = np.arange(TARGET_IMAGE_SIZE)
        stripe = ((x_grid // period) % 2) == 0
        array[top:bottom, stripe] = 255
    return array
