from __future__ import annotations

from metacraft.authority import Document

from .arbabi import arbabi_benchmark_case
from .case import _BENCHMARK_CASE_SCHEMA, MetalensBenchmarkCase
from .khorasaninejad import khorasaninejad_benchmark_case
from .mcclung import mcclung_benchmark_case
from .yang import yang_benchmark_case


def _declare_metalens_benchmark_cases() -> tuple[MetalensBenchmarkCase, ...]:
    """Declare McClung, Yang, Arbabi, and Khorasaninejad in stable order."""

    return (
        mcclung_benchmark_case(),
        yang_benchmark_case(),
        arbabi_benchmark_case(),
        khorasaninejad_benchmark_case(),
    )


_METALENS_BENCHMARK_CASES = _declare_metalens_benchmark_cases()
_METALENS_BENCHMARK_CASES_BY_NAME = {
    case.name: case for case in _METALENS_BENCHMARK_CASES
}


def metalens_benchmark_cases() -> tuple[MetalensBenchmarkCase, ...]:
    """Return the exact four-case catalogue in stable order."""

    return _METALENS_BENCHMARK_CASES


def select_metalens_benchmark_case(name: str) -> MetalensBenchmarkCase:
    """Return one named case from the fixed catalogue."""

    if not isinstance(name, str):
        raise TypeError("benchmark_case_name_required")
    try:
        return _METALENS_BENCHMARK_CASES_BY_NAME[name]
    except KeyError as error:
        raise ValueError("benchmark_case_name_invalid") from error


def restore_metalens_benchmark_case(
    document: Document,
) -> MetalensBenchmarkCase:
    """Restore one exact catalogue member from its canonical document."""

    if not isinstance(document, Document):
        raise TypeError("benchmark_case_document_required")
    if document.schema_identifier != _BENCHMARK_CASE_SCHEMA:
        raise ValueError("metalens_benchmark_case_schema_invalid")
    body = document.to_bytes()
    for case in _METALENS_BENCHMARK_CASES:
        if body == case.document().to_bytes():
            return case
    raise ValueError("metalens_benchmark_case_document_mismatch")
