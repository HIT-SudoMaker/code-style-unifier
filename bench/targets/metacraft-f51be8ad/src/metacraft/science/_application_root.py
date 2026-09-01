from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from time import monotonic, sleep

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

from ..authority import Authority


@dataclass(frozen=True, slots=True)
class OpenedApplicationRoot:
    """
    Hold one validated application root and whether this call claimed it.
    """

    authority: Authority
    runs_directory: Path
    is_fresh: bool


def authority_workspace_path(
    application_root: str | Path,
) -> Path:
    """
    Locate Authority at its fixed place inside one application root.
    """

    return Path(application_root).expanduser().resolve() / "authority"


def create_authority_in_new_application_root(
    application_root: str | Path,
) -> Authority:
    """
    Claim one absent application root and create its fixed children.

    A failed initialization deliberately leaves the create-only root claim in
    place, so a partial first attempt cannot later be accepted as fresh.
    """

    root = Path(application_root).expanduser().resolve()
    try:
        root.mkdir(parents=False, exist_ok=False)
    except FileExistsError:
        raise FileExistsError("application_root_must_be_new") from None
    authority = Authority(authority_workspace_path(root))
    (root / "runs").mkdir()
    return authority


def open_or_create_application_root(
    application_root: str | Path,
) -> OpenedApplicationRoot:
    """
    Claim one fresh root or reopen one exact, complete MetaCraft root.
    """

    root = Path(application_root).expanduser().resolve()
    try:
        authority = create_authority_in_new_application_root(root)
    except FileExistsError:
        _validate_existing_application_root(root)
        return OpenedApplicationRoot(
            authority=Authority(authority_workspace_path(root)),
            runs_directory=root / "runs",
            is_fresh=False,
        )
    return OpenedApplicationRoot(
        authority=authority,
        runs_directory=root / "runs",
        is_fresh=True,
    )


def open_existing_application_root(
    application_root: str | Path,
) -> OpenedApplicationRoot:
    """
    Reopen one exact MetaCraft root without ever claiming an absent path.
    """

    root = Path(application_root).expanduser().resolve()
    try:
        _validate_existing_application_root(root)
    except ValueError as error:
        if not root.exists():
            raise FileNotFoundError("application_root_missing") from error
        raise
    return OpenedApplicationRoot(
        authority=Authority(authority_workspace_path(root)),
        runs_directory=root / "runs",
        is_fresh=False,
    )


def _validate_existing_application_root(root: Path) -> None:
    try:
        children = {child.name for child in root.iterdir()}
    except (FileNotFoundError, NotADirectoryError, OSError) as error:
        raise ValueError("application_root_invalid") from error
    authority_root = authority_workspace_path(root)
    if (
        children != {"authority", "runs"}
        or not authority_root.is_dir()
        or not (authority_root / "workspace.marker").is_file()
        or not (root / "runs").is_dir()
    ):
        raise ValueError("application_root_invalid")


@contextmanager
def lock_application_root(
    runs_directory: Path,
    *,
    timeout_seconds: float = 30.0,
) -> Iterator[None]:
    """
    Serialize one non-scientific conduct execution for this root.
    """

    lock_path = runs_directory / ".conduct.lock"
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_EXCL | os.O_RDWR,
        )
        os.write(descriptor, b"\0")
    except FileExistsError:
        descriptor = os.open(lock_path, os.O_RDWR)
    lock_file = os.fdopen(descriptor, "r+b")
    deadline = monotonic() + timeout_seconds
    while True:
        try:
            _lock_file(lock_file.fileno())
            break
        except OSError as error:
            if monotonic() >= deadline:
                lock_file.close()
                raise RuntimeError("application_root_busy") from error
            sleep(0.01)
    try:
        yield
    finally:
        _unlock_file(lock_file.fileno())
        lock_file.close()


def _lock_file(file_descriptor: int) -> None:
    if os.name == "nt":
        os.lseek(file_descriptor, 0, os.SEEK_SET)
        msvcrt.locking(file_descriptor, msvcrt.LK_NBLCK, 1)
        return
    fcntl.flock(file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(file_descriptor: int) -> None:
    if os.name == "nt":
        os.lseek(file_descriptor, 0, os.SEEK_SET)
        msvcrt.locking(file_descriptor, msvcrt.LK_UNLCK, 1)
        return
    fcntl.flock(file_descriptor, fcntl.LOCK_UN)
