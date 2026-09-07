from pathlib import Path
import pytest
from data.data_source.assets.manifests import (
    ManifestItem,
    read_manifest,
    validate_manifest_paths,
    write_manifest,
)


def test_write_and_read_manifest_round_trip(tmp_path: Path) -> None:
    image_path = tmp_path / "BioSR" / "clean" / "sample.tif"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"image")

    manifest_path = write_manifest(
        tmp_path / "BioSR" / "manifest.json",
        [
            ManifestItem(
                dataset_name="BioSR",
                source_archive="downloads/sample.zip",
                source_member="sample.mrc",
                output_path="clean/sample.tif",
                image_id="biosr/sample",
                operation="mrc_to_tiff",
                channel_policy="single",
                raw_resolution=(1, 1),
                source_url="https://example.test/source",
                license="CC BY 4.0",
            )
        ],
    )

    loaded = read_manifest(manifest_path)

    assert loaded["version"] == 1
    assert loaded["items"][0]["dataset_name"] == "BioSR"
    assert loaded["items"][0]["output_path"] == "clean/sample.tif"


def test_validate_manifest_paths_reports_missing_output(tmp_path: Path) -> None:
    manifest_path = write_manifest(
        tmp_path / "FMD" / "manifest.json",
        [
            ManifestItem(
                dataset_name="FMD",
                source_archive="downloads/archive.tar",
                source_member="gt/avg50.png",
                output_path="averaged/missing.png",
                image_id="fmd/missing",
                operation="extract",
                channel_policy="single",
                raw_resolution=(1, 1),
                source_url="https://example.test/source",
                license="CC BY-SA 4.0",
            )
        ],
    )

    with pytest.raises(ValueError, match="averaged/missing.png"):
        validate_manifest_paths(manifest_path)
