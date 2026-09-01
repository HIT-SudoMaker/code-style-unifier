from __future__ import annotations

import importlib
import importlib.abc
from importlib.machinery import ModuleSpec
import sys

import pytest


_BLOCKED_RUNTIME_DEPENDENCY = "blocked runtime-only dependency: {name}"


class _BlockedRuntimeDependencyFinder(importlib.abc.MetaPathFinder):
    def find_spec(
        self,
        fullname: str,
        path: object,
        target: object = None,
    ) -> ModuleSpec | None:
        """
        阻止公开接口提前加载运行期依赖
        """
        del path, target
        if fullname in {"data", "layers"} or fullname.startswith(("data.", "layers.")):
            message = _BLOCKED_RUNTIME_DEPENDENCY.format(name=fullname)
            raise ImportError(message)
        return None


def _is_surface_module(module_name: str) -> bool:
    return (
        module_name == "experiments.restoration"
        or module_name.startswith("experiments.restoration.")
        or module_name == "data"
        or module_name.startswith("data.")
        or module_name == "layers"
        or module_name.startswith("layers.")
    )


def _purge_surface_modules() -> dict[str, object]:
    removed: dict[str, object] = {}
    for module_name in list(sys.modules):
        if _is_surface_module(module_name):
            removed[module_name] = sys.modules.pop(module_name)
    return removed


def _restore_surface_modules(removed: dict[str, object]) -> None:
    for module_name in list(sys.modules):
        if _is_surface_module(module_name):
            del sys.modules[module_name]
    sys.modules.update(removed)
    for module_name, module in removed.items():
        if "." not in module_name:
            continue
        parent_name, child_name = module_name.rsplit(".", 1)
        parent = sys.modules.get(parent_name)
        if parent is not None:
            setattr(parent, child_name, module)


def test_restoration_surface_exposes_shared_bench_and_research_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    验证顶层仅公开研究线命名空间
    """
    removed = _purge_surface_modules()
    monkeypatch.setattr(
        sys,
        "meta_path",
        [_BlockedRuntimeDependencyFinder(), *sys.meta_path],
    )
    try:
        restoration = importlib.import_module("experiments.restoration")

        assert tuple(restoration.__all__) == (
            "optical_bench",
            "fixed_measurement",
            "adaptive_measurement",
        )
        assert restoration.optical_bench.__name__.endswith(".optical_bench")
        assert restoration.fixed_measurement.__name__.endswith(".fixed_measurement")
        assert restoration.adaptive_measurement.__name__.endswith(
            ".adaptive_measurement"
        )
    finally:
        _restore_surface_modules(removed)


def test_legacy_root_names_are_not_available_after_migration() -> None:
    """
    验证迁移期旧名称可显式读取但不再公开
    """
    restoration = importlib.import_module("experiments.restoration")

    assert "TrainingConfig" not in restoration.__all__
    assert "run_training" not in restoration.__all__
    with pytest.raises(AttributeError):
        getattr(restoration, "TrainingConfig")
    with pytest.raises(AttributeError):
        getattr(restoration, "run_training")
