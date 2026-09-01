from __future__ import annotations

import importlib

__all__ = [
    "ClassificationONN",
    "ClassificationDataset",
    "BasicConfig",
    "ModelConfig",
    "TrainingConfig",
    "SearchConfig",
    "run_training",
    "run_optuna_search",
]

_EXPORTS = {
    "ClassificationONN": ("model", "ClassificationONN"),
    "ClassificationDataset": ("dataset_adapter", "ClassificationDataset"),
    "BasicConfig": ("config", "BasicConfig"),
    "ModelConfig": ("config", "ModelConfig"),
    "TrainingConfig": ("config", "TrainingConfig"),
    "SearchConfig": ("config", "SearchConfig"),
    "run_training": ("train", "run_training"),
    "run_optuna_search": ("optuna_search", "run_optuna_search"),
}


def __getattr__(name: str) -> object:
    """
    按名称加载公开导出
    """
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attribute_name = _EXPORTS[name]
    module = importlib.import_module(f"{__name__}.{module_name}")
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
