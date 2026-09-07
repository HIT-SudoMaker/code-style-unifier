from pathlib import Path

import pytest
from PIL import Image

from data.data_source.indexing.file_index import (
    FileIndexRecord,
    build_image_id,
    discover_image_files,
    sample_max_indices,
    select_index_records,
)


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("L", (3, 2), color=7).save(path)


def test_build_image_id_uses_dataset_name_and_relative_path_stem(tmp_path: Path) -> None:
    root = tmp_path / "biosr" / "clean"
    image_path = root / "ER" / "photon_100" / "sample_001.tif"

    image_id = build_image_id(
        dataset_name="biosr",
        dataset_root=root,
        image_path=image_path,
    )

    assert image_id == "biosr/ER/photon_100/sample_001"


def test_discover_image_files_returns_stable_records(tmp_path: Path) -> None:
    root = tmp_path / "fmd" / "averaged"
    _write_png(root / "widefield" / "b.png")
    _write_png(root / "widefield" / "a.png")

    records = discover_image_files(
        dataset_name="fmd",
        dataset_root=root,
        split_name="train",
        category="fmd",
        provenance_url="https://curate.nd.edu/articles/dataset/Fluorescence_Microscopy_Denoising_FMD_dataset/24744648",
        license_name="CC BY-SA 4.0",
    )

    assert [record.image_id for record in records] == [
        "fmd/widefield/a",
        "fmd/widefield/b",
    ]
    assert records[0].source_index == 0
    assert records[0].source_path == Path("widefield/a.png")
    assert records[0].source_metadata == {}


def test_discover_image_files_rejects_paths_outside_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside.png"
    _write_png(outside)

    with pytest.raises(ValueError, match="dataset_root"):
        build_image_id(
            dataset_name="bad",
            dataset_root=tmp_path / "root",
            image_path=outside,
        )


def test_select_index_records_preserves_source_index_and_local_order() -> None:
    records = [
        FileIndexRecord(
            dataset_name="bbbc038",
            split_name="train",
            image_id=f"bbbc038/image_{index}",
            source_index=index,
            source_path=Path(f"image_{index}.png"),
            category="bbbc038",
            label=0,
            provenance_url="https://bbbc.broadinstitute.org/BBBC038",
            license_name="CC0",
            source_metadata={"accession": "BBBC038"},
        )
        for index in range(3)
    ]

    selected = select_index_records(records, selected_indices=[2, 0])

    assert [record.source_index for record in selected] == [2, 0]
    assert [record.image_id for record in selected] == [
        "bbbc038/image_2",
        "bbbc038/image_0",
    ]


def test_sample_max_indices_is_deterministic_and_optional() -> None:
    assert sample_max_indices(5, max_samples=None, random_seed=3) is None

    first = sample_max_indices(5, max_samples=3, random_seed=3)
    second = sample_max_indices(5, max_samples=3, random_seed=3)

    assert first == second
    assert len(first) == 3
    assert first == sorted(first)
    assert all(0 <= index < 5 for index in first)


@pytest.mark.parametrize("max_samples", [0, -1, True])
def test_sample_max_indices_rejects_invalid_limits(max_samples: object) -> None:
    with pytest.raises(ValueError, match="max_samples"):
        sample_max_indices(5, max_samples=max_samples, random_seed=3)  # type: ignore[arg-type]
