from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).parents[1]))

from examples import (
    MetalensBenchmarkCase,
    metalens_benchmark_cases,
)


def inspect_metalens_benchmarks() -> tuple[MetalensBenchmarkCase, ...]:
    """
    Return the four immutable benchmark cases without conducting science.
    """

    return metalens_benchmark_cases()


if __name__ == "__main__":
    for case in inspect_metalens_benchmarks():
        print(case.document().to_bytes().decode("utf-8"))
