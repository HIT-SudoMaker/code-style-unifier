from __future__ import annotations

import ast
from pathlib import Path

from tools.code_style_unifier.config import Profile
from tools.code_style_unifier.rules.naming_abbreviations import (
    _split_identifier,
    NamingAbbreviationsRule,
)


def _run_rule(
    source_text: str,
    *,
    banned_tokens: dict[str, str] | None = None,
    allowed_names: list[str] | None = None,
) -> list[str]:
    profile = Profile(
        banned_abbreviation_tokens=banned_tokens or {},
        allowed_abbreviation_names=allowed_names or [],
    )
    rule = NamingAbbreviationsRule()
    rule.bind_profile(profile)
    syntax_tree = ast.parse(source_text)
    violations = rule.check_file(
        Path("sample.py"),
        source_text,
        syntax_tree,
        source_text.splitlines(),
    )
    return [violation.evidence for violation in violations]


def test_split_identifier_handles_snake_and_camel_case() -> None:
    """
    验证 token 拆分避免子串匹配
    """

    assert _split_identifier("target_name") == ["target", "name"]
    assert _split_identifier("HTTPMessageBuilder") == ["http", "message", "builder"]
    assert _split_identifier("source_metadata") == ["source", "metadata"]
    assert _split_identifier("sigmoid_value") == ["sigmoid", "value"]


def test_naming_rule_reports_abbreviation_tokens_inside_identifiers() -> None:
    """
    验证禁用缩写会作为标识符 token 被检出
    """

    source_text = """
from __future__ import annotations

def build_target(tar_name: str) -> None:
    local_msg = tar_name
    for ctx_item in []:
        pass
    with open("example.txt") as pth_handle:
        pass
    holder.obj_value = local_msg
"""
    evidence = _run_rule(
        source_text,
        banned_tokens={
            "ctx": "context",
            "msg": "message",
            "obj": "object",
            "pth": "path",
            "tar": "target",
        },
    )

    assert any("'tar_name'" in item and "'tar'" in item for item in evidence)
    assert any("'local_msg'" in item and "'msg'" in item for item in evidence)
    assert any("'ctx_item'" in item and "'ctx'" in item for item in evidence)
    assert any("'pth_handle'" in item and "'pth'" in item for item in evidence)
    assert any("'obj_value'" in item and "'obj'" in item for item in evidence)


def test_naming_rule_allows_full_words_and_exact_name_exceptions() -> None:
    """
    验证完整单词和配置的精确例外不会被报告
    """

    source_text = """
from __future__ import annotations

def extract_tar(signature_value: str) -> None:
    source_metadata = signature_value
    sigmoid_value = 1
"""
    evidence = _run_rule(
        source_text,
        banned_tokens={
            "sig": "signature",
            "tar": "target",
        },
        allowed_names=["extract_tar"],
    )

    assert evidence == []
