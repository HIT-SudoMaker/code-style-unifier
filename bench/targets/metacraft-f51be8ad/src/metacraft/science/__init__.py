from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .brief import Brief as Brief
    from .compile import (
        CompileOutcome as CompileOutcome,
        InvalidBrief as InvalidBrief,
        UnsupportedAim as UnsupportedAim,
        compile_study as compile_study,
    )
    from .conduct import (
        CompletedResults as CompletedResults,
        ConsultationAnswerRejected as ConsultationAnswerRejected,
        ConsultationRequired as ConsultationRequired,
        ConductOutcome as ConductOutcome,
        WaitingStudies as WaitingStudies,
        conduct as conduct,
    )
    from .study import (
        Binding as Binding,
        Capability as Capability,
        Evidence as Evidence,
        Finding as Finding,
        FindingKind as FindingKind,
        Study as Study,
    )
    from .result import Result as Result

_EXPORTS = {
    "Binding": (".study", "Binding"),
    "Brief": (".brief", "Brief"),
    "Capability": (".study", "Capability"),
    "CompileOutcome": (".compile", "CompileOutcome"),
    "CompletedResults": (".conduct", "CompletedResults"),
    "ConsultationAnswerRejected": (
        ".conduct",
        "ConsultationAnswerRejected",
    ),
    "ConsultationRequired": (".conduct", "ConsultationRequired"),
    "ConductOutcome": (".conduct", "ConductOutcome"),
    "Evidence": (".study", "Evidence"),
    "Finding": (".study", "Finding"),
    "FindingKind": (".study", "FindingKind"),
    "InvalidBrief": (".compile", "InvalidBrief"),
    "Result": (".result", "Result"),
    "Study": (".study", "Study"),
    "UnsupportedAim": (".compile", "UnsupportedAim"),
    "WaitingStudies": (".conduct", "WaitingStudies"),
    "compile_study": (".compile", "compile_study"),
    "conduct": (".conduct", "conduct"),
}

__all__ = list(_EXPORTS)  # pyright: ignore[reportUnsupportedDunderAll]


def __getattr__(name: str) -> Any:
    """
    Load one requested science value without opening unrelated realizations.
    """

    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError(name) from error
    module = import_module(module_name, __name__)
    for export_name, (export_module, export_attribute) in _EXPORTS.items():
        if export_module == module_name:
            globals()[export_name] = getattr(module, export_attribute)
    return globals()[name]
