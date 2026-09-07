from __future__ import annotations

import ast
import base64
import os
from pathlib import Path
import pickle
import subprocess
import sys

import pytest

from chromatix_next.errors import (
    AssemblyError,
    OpticalError,
    OpticalRuntimeError,
    OpticalTypeError,
    OpticalValueError,
    WorkstationError,
)

SRC = Path(__file__).resolve().parents[2] / "src" / "chromatix_next"


DOMAIN_FAILURE_NAMES: frozenset[str] = frozenset(
    {
        "OpticalError",
        "OpticalTypeError",
        "OpticalValueError",
        "OpticalRuntimeError",
        "AssemblyError",
        "WorkstationError",
    }
)


EXEMPT_BARE_RAISES: frozenset[tuple[str, str]] = frozenset(
    {("_execution_memory.py", "OSError")}
)


def _production_modules() -> list[Path]:
    # 返回全部生产 Python 模块
    return sorted(SRC.rglob("*.py"))


def _raise_calls(module: Path) -> list[tuple[int, str, ast.Call]]:
    # 返回该模块内每个以调用形式抛出的异常及其行号与类名
    tree = ast.parse(module.read_text(encoding="utf-8"))
    found: list[tuple[int, str, ast.Call]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise):
            continue
        raised = node.exc
        if not isinstance(raised, ast.Call):
            continue
        if isinstance(raised.func, ast.Name):
            class_name = raised.func.id
        elif isinstance(raised.func, ast.Attribute):
            class_name = raised.func.attr
        else:
            continue
        found.append((node.lineno, class_name, raised))
    return found


def _is_nonempty_text(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and bool(node.value.strip())
    if isinstance(node, ast.JoinedStr):
        return bool(node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_nonempty_text(node.left) or _is_nonempty_text(node.right)
    return isinstance(node, (ast.Name, ast.Attribute))


def test_every_domain_failure_carries_an_explanation() -> None:
    """
    断言每个域失败抛出点都同时给出标识与非空说明
    """
    offenders: list[str] = []
    for module in _production_modules():
        for line, class_name, call in _raise_calls(module):
            if class_name not in DOMAIN_FAILURE_NAMES:
                continue
            relative = module.relative_to(SRC).as_posix()
            if len(call.args) < 2:
                offenders.append(f"{relative}:{line} 只给了标识没给说明")
                continue
            if not _is_nonempty_text(call.args[1]):
                offenders.append(f"{relative}:{line} 的说明不是非空文本")
    assert not offenders, "以下抛出点缺少面向使用者的说明：" + "; ".join(offenders)


def test_no_production_failure_raises_a_bare_builtin() -> None:
    """
    断言生产代码不再直接抛出携带裸标识的内建异常
    """
    banned = {"ValueError", "TypeError", "RuntimeError"}
    offenders: list[str] = []
    for module in _production_modules():
        for line, class_name, _call in _raise_calls(module):
            if class_name not in banned:
                continue
            relative = module.relative_to(SRC).as_posix()
            offenders.append(f"{relative}:{line} 抛出了内建 {class_name}")
    assert not offenders, (
        "面向使用者的失败必须用光学域类型，以便同时携带标识与说明："
        + "; ".join(offenders)
    )


def test_exempt_bare_raises_remain_the_documented_ones() -> None:
    """
    断言豁免的裸抛出仍然只有已记录的那些
    """
    observed: set[tuple[str, str]] = set()
    for module in _production_modules():
        for _line, class_name, call in _raise_calls(module):
            if class_name in DOMAIN_FAILURE_NAMES:
                continue
            if len(call.args) >= 2:
                continue
            observed.add((module.name, class_name))
    assert observed == set(EXEMPT_BARE_RAISES), (
        f"豁免的裸抛出发生了变化：{sorted(observed)}"
    )
