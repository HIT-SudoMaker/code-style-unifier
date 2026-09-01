from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
from importlib.machinery import ModuleSpec
import sys

import pytest


STRICT_ROOT_PUBLIC_NAMES = (
    "ClassificationONN",
    "ClassificationDataset",
    "BasicConfig",
    "ModelConfig",
    "TrainingConfig",
    "SearchConfig",
    "run_training",
    "run_optuna_search",
)

VISUALIZE_HELPER_NAMES = (
    "visualize_training_dynamics",
    "visualize_optical_readout_examples",
    "visualize_topology_comparison",
    "visualize_training_curves",
    "visualize_confusion_matrix",
    "visualize_per_class_accuracy",
    "visualize_detector_layout",
    "visualize_phase_mask",
    "visualize_prediction_example",
    "visualize_training_history",
)

REMOVED_ROOT_EXPORT_NAMES = (
    "SingleLayerClassificationONN",
    "SUPPORTED_TOPOLOGIES",
    "build_d2nn_reference_comparison",
    "build_default_training_config",
    "build_classification_dataloaders",
    "build_run_paths",
    "build_target_distribution",
    "evaluate_checkpoint",
    "evaluate_model",
    "normalize_topology",
    "resolve_default_epochs",
    *VISUALIZE_HELPER_NAMES,
)

REMOVED_CONFIG_EXPORT_NAMES = (
    "ClassificationBasicConfig",
    "ClassificationModelConfig",
    "ClassificationTrainingConfig",
    "TrainConfig",
    "build_default_train_config",
)

REMOVED_DATASET_EXPORT_NAMES = (
    "Classification" + "ONNDataset",
)


class _BlockedRuntimeDependencyFinder(importlib.abc.MetaPathFinder):
    def find_spec(
        self,
        fullname: str,
        path: object,
        target: object = None,
    ) -> ModuleSpec | None:
        """
        阻断导入检查期间的运行时依赖
        """
        del path, target
        if fullname in {"data", "layers"} or fullname.startswith("data."):
            raise ImportError(f"blocked runtime-only dependency: {fullname}")
        return None


def _is_classification_surface_module(module_name: str) -> bool:
    return (
        module_name == "experiments.classification"
        or module_name.startswith("experiments.classification.")
        or module_name == "data"
        or module_name.startswith("data.")
        or module_name == "layers"
        or module_name.startswith("layers.")
    )


def _purge_classification_surface_modules() -> dict[str, object]:
    removed_modules: dict[str, object] = {}
    for module_name in list(sys.modules):
        if _is_classification_surface_module(module_name):
            removed_modules[module_name] = sys.modules.pop(module_name)
    return removed_modules


def _restore_classification_surface_modules(
    removed_modules: dict[str, object],
) -> None:
    for module_name in list(sys.modules):
        if _is_classification_surface_module(module_name):
            del sys.modules[module_name]
    sys.modules.update(removed_modules)
    for module_name, module in removed_modules.items():
        if "." not in module_name:
            continue
        parent_name, child_name = module_name.rsplit(".", 1)
        parent = sys.modules.get(parent_name)
        if parent is not None:
            setattr(parent, child_name, module)


def test_classification_onn_surface_exports_strict_public_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    removed_modules = _purge_classification_surface_modules()
    try:
        monkeypatch.setattr(
            sys,
            "meta_path",
            [_BlockedRuntimeDependencyFinder(), *sys.meta_path],
        )

        classification = importlib.import_module("experiments.classification")

        assert tuple(classification.__all__) == STRICT_ROOT_PUBLIC_NAMES

        for export_name in classification.__all__:
            assert hasattr(classification, export_name)
            assert getattr(classification, export_name) is not None
    finally:
        _restore_classification_surface_modules(removed_modules)


def test_public_topologies_do_not_include_reference_or_passive_names() -> None:
    """
    验证分类测试契约保持稳定
    """
    from experiments.classification.model import SUPPORTED_TOPOLOGIES

    assert SUPPORTED_TOPOLOGIES == ("without_lens", "with_lens")
    assert "passive" not in SUPPORTED_TOPOLOGIES
    assert not any(name.startswith("reference") for name in SUPPORTED_TOPOLOGIES)


def test_classification_onn_surface_routes_training_exports() -> None:
    """
    验证分类测试契约保持稳定
    """
    classification = importlib.import_module("experiments.classification")

    assert classification.BasicConfig.__module__.endswith(".config")
    assert classification.ModelConfig.__module__.endswith(".config")
    assert classification.TrainingConfig.__module__.endswith(".config")
    assert classification.SearchConfig.__module__.endswith(".config")
    assert classification.run_optuna_search.__module__.endswith(".optuna_search")
    assert classification.run_training.__module__.endswith(".train")


def test_classification_surface_exports_dataset_adapter_name() -> None:
    """
    验证分类测试契约保持稳定
    """
    classification = importlib.import_module("experiments.classification")

    assert "ClassificationDataset" in classification.__all__
    assert classification.ClassificationDataset.__module__.endswith(".dataset_adapter")


def test_classification_onn_surface_removes_non_root_api_names() -> None:
    """
    验证分类测试契约保持稳定
    """
    removed_modules = _purge_classification_surface_modules()
    try:
        classification = importlib.import_module("experiments.classification")

        removed_names = (
            *REMOVED_ROOT_EXPORT_NAMES,
            *REMOVED_CONFIG_EXPORT_NAMES,
            *REMOVED_DATASET_EXPORT_NAMES,
        )

        for name in removed_names:
            assert name not in classification.__all__
            assert not hasattr(classification, name)
    finally:
        _restore_classification_surface_modules(removed_modules)


def test_replot_module_is_not_root_public_api() -> None:
    """
    验证分类测试契约保持稳定
    """
    removed_modules = _purge_classification_surface_modules()
    try:
        classification = importlib.import_module("experiments.classification")

        assert "replot" not in classification.__all__
        assert not hasattr(classification, "replot")
    finally:
        _restore_classification_surface_modules(removed_modules)


def test_classification_onn_surface_excludes_removed_modules() -> None:
    """
    验证分类测试契约保持稳定
    """
    assert importlib.util.find_spec("experiments.classification.configs") is None
    assert importlib.util.find_spec("experiments.classification.dataset") is None
    assert importlib.util.find_spec("experiments.classification.detector") is None
    assert importlib.util.find_spec("experiments.classification.evaluate") is None
    assert importlib.util.find_spec("experiments.classification.prediction_utils") is None
    assert importlib.util.find_spec("experiments.classification.repeated_runs") is None
    assert importlib.util.find_spec("experiments.classification.search") is None
