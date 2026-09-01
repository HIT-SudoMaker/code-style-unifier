import json
from pathlib import Path

from data import load
from data.configs import SourceConfig
from data.data_source import DATASET_REGISTRY
from data.data_source.adapters.targets import (
    TargetLinePairsDataset,
    TargetSiemensDataset,
    TargetSlantedEdgeDataset,
    TargetUSAFDataset,
)


def test_target_sources_are_registered_in_unified_factory() -> None:
    assert DATASET_REGISTRY["target_usaf"].builder is TargetUSAFDataset
    assert DATASET_REGISTRY["target_siemens"].builder is TargetSiemensDataset
    assert DATASET_REGISTRY["target_slanted_edge"].builder is TargetSlantedEdgeDataset
    assert DATASET_REGISTRY["target_line_pairs"].builder is TargetLinePairsDataset


def test_target_generation_writes_deterministic_assets_and_manifest(tmp_path: Path) -> None:
    dataset = TargetUSAFDataset(dataset_root=tmp_path, is_train=True)
    sample = dataset[0]
    manifest_path = tmp_path / "targets" / "manifest.json"

    assert len(dataset) == 1
    assert manifest_path.exists()
    assert (tmp_path / "targets" / "target_usaf.png").exists()
    assert sample["provenance"]["dataset_name"] == "target_usaf"
    assert sample["provenance"]["image_id"] == "target_usaf/target_usaf"
    assert sample["provenance"]["source_metadata"]["target_type"] == "target_usaf"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target_usaf_item = next(
        item for item in manifest["items"] if item["image_id"] == "target_usaf/target_usaf"
    )

    assert manifest["version"] == 1
    assert target_usaf_item["output_path"] == "target_usaf.png"
    assert target_usaf_item["image_id"] == "target_usaf/target_usaf"
    assert target_usaf_item["operation"] == "generate_target"
    assert target_usaf_item["raw_resolution"] == [256, 256]


def test_target_dataset_prepares_generated_assets_once(tmp_path: Path, monkeypatch) -> None:
    calls: list[Path] = []

    def _fake_prepare_generated_target_assets(dataset_root=None) -> Path:
        calls.append(Path(dataset_root))
        target_root = Path(dataset_root) / "targets"
        target_root.mkdir(parents=True, exist_ok=True)
        (target_root / "target_usaf.png").write_bytes(b"image")
        return target_root / "manifest.json"

    monkeypatch.setattr(
        "data.data_source.adapters.targets.prepare_generated_target_assets",
        _fake_prepare_generated_target_assets,
    )

    dataset = TargetUSAFDataset(dataset_root=tmp_path, is_train=True)

    assert len(dataset) == 1
    assert calls == [tmp_path]


def test_load_builds_target_source(tmp_path: Path) -> None:
    dataset = load(
        SourceConfig(
            dataset_name="target_siemens",
            dataset_root=str(tmp_path),
            max_samples=1,
        )
    )

    assert len(dataset) == 1
    assert dataset[0]["category"] == "target_siemens"
