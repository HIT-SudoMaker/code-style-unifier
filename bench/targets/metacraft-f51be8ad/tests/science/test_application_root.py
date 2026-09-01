from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from time import sleep

import pytest

from metacraft.authority import Authority, Revision
from metacraft.science._application_root import (
    authority_workspace_path,
    create_authority_in_new_application_root,
    lock_application_root,
    open_or_create_application_root,
)


def test_application_root_owns_one_fixed_authority_path(
    tmp_path: Path,
) -> None:
    application_root = tmp_path / "application-root"

    assert authority_workspace_path(application_root) == (
        application_root.resolve() / "authority"
    )


def test_create_application_root_claims_one_absent_root_atomically(
    tmp_path: Path,
) -> None:
    application_root = tmp_path / "new-application-root"
    start = Barrier(2)

    def create() -> str:
        start.wait()
        try:
            authority = create_authority_in_new_application_root(application_root)
        except FileExistsError as error:
            assert error.args == ("application_root_must_be_new",)
            return "rejected"
        assert authority.view().revision == Revision.root()
        return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _item: create(), range(2)))

    assert sorted(results) == ["created", "rejected"]
    authority_path = authority_workspace_path(application_root)
    assert (authority_path / "workspace.marker").is_file()
    assert (application_root / "runs").is_dir()
    assert {path.name for path in application_root.iterdir()} == {
        "authority",
        "runs",
    }
    assert Authority(authority_path).view().revision == Revision.root()
    with pytest.raises(
        FileExistsError,
        match="^application_root_must_be_new$",
    ):
        create_authority_in_new_application_root(application_root)


@pytest.mark.parametrize("partial", ("empty", "authority", "runs", "extra"))
def test_existing_partial_or_foreign_root_is_not_repaired(
    tmp_path: Path,
    partial: str,
) -> None:
    root = tmp_path / "partial-root"
    root.mkdir()
    if partial in {"authority", "extra"}:
        Authority(root / "authority")
    if partial in {"runs", "extra"}:
        (root / "runs").mkdir()
    if partial == "extra":
        (root / "foreign.txt").write_text("foreign", encoding="utf-8")
    before = tuple(sorted(path.name for path in root.iterdir()))

    with pytest.raises(ValueError, match="^application_root_invalid$"):
        open_or_create_application_root(root)

    assert tuple(sorted(path.name for path in root.iterdir())) == before


def test_application_root_execution_lock_serializes_callers(
    tmp_path: Path,
) -> None:
    root = tmp_path / "application-root"
    opened = open_or_create_application_root(root)
    start = Barrier(2)
    active = 0
    maximum_active = 0

    def enter() -> None:
        nonlocal active, maximum_active
        start.wait()
        with lock_application_root(opened.runs_directory):
            active += 1
            maximum_active = max(maximum_active, active)
            sleep(0.02)
            active -= 1

    with ThreadPoolExecutor(max_workers=2) as executor:
        tuple(executor.map(lambda _item: enter(), range(2)))

    assert maximum_active == 1
