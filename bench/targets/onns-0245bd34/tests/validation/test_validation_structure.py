from __future__ import annotations

from pathlib import Path

import pytest


def test_new_validation_modules_are_importable() -> None:
    """
    验证新的 validation 模块结构可导入
    """

    from experiments.validation import artifacts
    from experiments.validation import run_all
    from experiments.validation import style
    from experiments.validation.data import run_data
    from experiments.validation.data import validate_degradation
    from experiments.validation.data import validate_sources
    from experiments.validation.data import validate_transformation
    from experiments.validation.layers import run_layers
    from experiments.validation.layers import validate_detection
    from experiments.validation.layers import validate_diffraction
    from experiments.validation.layers import validate_lens
    from experiments.validation.layers import validate_modulation

    assert callable(artifacts.aggregate_status)
    assert callable(run_all.run)
    assert callable(style.save_figure_pair)
    assert callable(run_data.run)
    assert callable(run_layers.run)
    for module in (
        validate_diffraction,
        validate_modulation,
        validate_lens,
        validate_detection,
        validate_sources,
        validate_degradation,
        validate_transformation,
    ):
        assert callable(module.run)
        assert callable(module.main)


def test_clear_output_dir_rejects_workspace_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    验证清理逻辑拒绝删除仓库根目录
    """
    from experiments.validation import artifacts

    workspace_root = Path(__file__).resolve().parents[2]
    calls: list[Path] = []

    def _record_rmtree(path: Path) -> None:
        calls.append(Path(path))

    monkeypatch.setattr(artifacts.shutil, "rmtree", _record_rmtree)

    with pytest.raises(ValueError, match="Unsafe validation output directory"):
        artifacts.clear_output_dir(workspace_root)

    assert calls == []


def test_clear_output_dir_rejects_raw_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    验证清理逻辑拒绝原始数据目录及其子目录
    """
    from experiments.validation import artifacts

    data_root = Path(__file__).resolve().parents[2] / "data"
    raw_outputs = (
        data_root,
        data_root / "raw" / "fmd",
    )
    calls: list[Path] = []

    def _record_rmtree(path: Path) -> None:
        calls.append(Path(path))

    monkeypatch.setattr(artifacts.shutil, "rmtree", _record_rmtree)

    for raw_output in raw_outputs:
        with pytest.raises(ValueError, match="Unsafe validation output directory"):
            artifacts.clear_output_dir(raw_output)

    assert calls == []


def test_clear_output_dir_rejects_configured_raw_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证清理逻辑保护显式配置的原始数据根目录
    """
    from experiments.validation import artifacts

    raw_root = tmp_path / "datasets" / "raw"
    monkeypatch.setenv("ONN_DATASET_ROOT", str(raw_root))
    calls: list[Path] = []

    def _record_rmtree(path: Path) -> None:
        calls.append(Path(path))

    monkeypatch.setattr(artifacts.shutil, "rmtree", _record_rmtree)

    for raw_output in (raw_root.parent, raw_root / "fmd"):
        with pytest.raises(ValueError, match="Unsafe validation output directory"):
            artifacts.clear_output_dir(raw_output)

    assert calls == []


def test_clear_output_dir_removes_only_safe_validation_artifacts(tmp_path: Path) -> None:
    """
    验证清理逻辑只删除安全的 validation 产物目录
    """
    from experiments.validation.artifacts import clear_output_dir

    output_dir = tmp_path / "results" / "validation"
    stale_file = output_dir / "layers" / "old.txt"
    stale_file.parent.mkdir(parents=True)
    stale_file.write_text("old", encoding="utf-8")

    cleared = clear_output_dir(output_dir)

    assert cleared == output_dir
    assert output_dir.exists()
    assert not stale_file.exists()


def test_resolve_device_rejects_unavailable_explicit_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    验证显式 cuda 请求在不可用时失败
    """
    import torch

    from experiments.validation.layers._shared import resolve_device

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    with pytest.raises(RuntimeError, match="CUDA was requested"):
        resolve_device("cuda")
