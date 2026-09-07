from __future__ import annotations

from pathlib import Path


VALIDATION_ROOT = Path(__file__).resolve().parents[2] / "experiments" / "validation"


def test_validation_sources_do_not_use_bom() -> None:
    """
    验证 validation 源文件不含 UTF-8 BOM
    """
    files_with_bom = [
        path.relative_to(VALIDATION_ROOT).as_posix()
        for path in sorted(VALIDATION_ROOT.rglob("*.py"))
        if path.read_bytes().startswith(b"\xef\xbb\xbf")
    ]

    assert files_with_bom == []


def test_validation_sources_do_not_contain_private_use_characters() -> None:
    """
    验证 validation 源文件不含私用区乱码字符
    """
    files_with_pua: dict[str, list[int]] = {}
    for path in sorted(VALIDATION_ROOT.rglob("*.py")):
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        bad_lines = [
            line_number
            for line_number, line in enumerate(lines, start=1)
            if any(0xE000 <= ord(character) <= 0xF8FF for character in line)
        ]
        if bad_lines:
            files_with_pua[path.relative_to(VALIDATION_ROOT).as_posix()] = bad_lines

    assert files_with_pua == {}
