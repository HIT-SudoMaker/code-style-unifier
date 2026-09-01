from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_ROOT = PROJECT_ROOT / "data" / "raw"
FORBIDDEN_RAW_SUFFIXES = {
    ".bat",
    ".cmd",
    ".ipynb",
    ".m",
    ".ps1",
    ".py",
    ".pyc",
    ".sh",
}


def test_raw_assets_do_not_contain_executable_helper_files() -> None:
    forbidden_files = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in RAW_DATA_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in FORBIDDEN_RAW_SUFFIXES
    ]

    assert forbidden_files == []
