from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from metacraft.authority.reference import reference_for
from metacraft.canonical import encode_bytes
from metacraft.science.study import Caution
from metacraft.solvers.lumerical_fdtd.artifacts import RunDirectory


def test_identical_manifests_converge_under_concurrent_writers(
    tmp_path: Path,
) -> None:
    """
    Publish one immutable manifest without leaking a temporary artifact.
    """

    run = RunDirectory(tmp_path / "run")
    start = Barrier(2)

    def record_manifest() -> None:
        start.wait(timeout=5)
        run.record_manifest(
            period_nm=630,
            order_regime="multi order",
            cautions=(),
        )

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = tuple(
            future.result(timeout=5)
            for future in (
                workers.submit(record_manifest),
                workers.submit(record_manifest),
            )
        )

    assert outcomes == (None, None)
    assert (run.root / "manifest.json").read_bytes() == encode_bytes(
        {
            "cautions": [],
            "order_regime": "multi order",
            "period_nm": 630,
        }
    )
    assert {path.name for path in run.root.iterdir()} == {"manifest.json"}


def test_response_directories_are_isolated_by_exact_request_identity(
    tmp_path: Path,
) -> None:
    """
    Reopen one request path while keeping another request physically separate.
    """

    run = RunDirectory(tmp_path / "run")
    first_identity = reference_for(b"first request").content_hash
    second_identity = reference_for(b"second request").content_hash

    first = run.for_response(first_identity)
    reopened = run.for_response(first_identity)
    second = run.for_response(second_identity)

    assert first.root == reopened.root
    assert first.root != second.root
    assert first.root == run.root / "r" / first_identity.removeprefix("sha256:")[:16]
    assert second.root == run.root / "r" / second_identity.removeprefix("sha256:")[:16]
    assert first.root.is_dir()
    assert second.root.is_dir()
    assert {path.name for path in (run.root / "r").iterdir()} == {
        first.root.name,
        second.root.name,
    }


def test_run_manifest_is_the_idempotent_record_of_cell_physics(
    tmp_path: Path,
) -> None:
    """
    Keep period, order regime, and cautions immutable inside one run.
    """

    run = RunDirectory(tmp_path / "run")
    caution = Caution(
        concern="higher orders possible",
        explanation=(
            "Nonzero diffraction orders may propagate; the declared "
            "solver-response channels do not represent the complete output "
            "field."
        ),
        source_reference=reference_for(b"height-domain"),
    )

    run.record_manifest(
        period_nm=630,
        order_regime="multi order",
        cautions=(caution,),
    )
    run.record_manifest(
        period_nm=630,
        order_regime="multi order",
        cautions=(caution,),
    )

    assert (run.root / "manifest.json").read_bytes() == encode_bytes(
        {
            "cautions": [caution.as_mapping()],
            "order_regime": "multi order",
            "period_nm": 630,
        }
    )
    with pytest.raises(RuntimeError, match="run_manifest_mismatch"):
        run.record_manifest(
            period_nm=200,
            order_regime="zeroth order",
            cautions=(),
        )
