from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .authority import Authority as Authority
    from .science.compile import compile_study as compile_study
    from .science.conduct import conduct as conduct

_EXPORTS = {
    "Authority": (".authority", "Authority"),
    "compile_study": (".science.compile", "compile_study"),
    "conduct": (".science.conduct", "conduct"),
}

__all__ = list(_EXPORTS)  # pyright: ignore[reportUnsupportedDunderAll]


def __getattr__(name: str) -> Any:
    """
    Load one application entry only when a caller requests it.
    """

    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError(name) from error
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value
