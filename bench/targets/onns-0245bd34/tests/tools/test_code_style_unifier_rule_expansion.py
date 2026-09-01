from __future__ import annotations

import ast
from pathlib import Path

from tools.code_style_unifier.rules.boolean_naming import BooleanNamingRule
from tools.code_style_unifier.rules.docstring_physical_layout import (
    DocstringPhysicalLayoutRule,
)
from tools.code_style_unifier.rules.file_name_specificity import FileNameSpecificityRule
from tools.code_style_unifier.rules.function_annotations import FunctionAnnotationsRule
from tools.code_style_unifier.rules.import_grouping import ImportGroupingRule
from tools.code_style_unifier.rules.import_sorting import ImportSortingRule
from tools.code_style_unifier.rules.line_length import LineLengthRule
from tools.code_style_unifier.rules.source_text_language import SourceTextLanguageRule


def _parse(source_text: str) -> ast.AST:
    return ast.parse(source_text)


def test_function_annotations_rule_reports_missing_parts() -> None:
    """
    验证缺失参数和返回值注解会被报告
    """
    source_text = """
from __future__ import annotations

def build_value(raw_value):
    return raw_value
"""
    rule = FunctionAnnotationsRule()

    violations = rule.check_file(
        Path("sample.py"),
        source_text,
        _parse(source_text),
        source_text.splitlines(),
    )

    assert len(violations) == 1
    assert "raw_value" in violations[0].evidence
    assert "return" in violations[0].evidence


def test_docstring_physical_layout_rule_rejects_one_line_docstrings() -> None:
    """
    验证单行 docstring 违反物理布局规则
    """
    source_text = '''
from __future__ import annotations

def build_value() -> int:
    """Return value"""
    return 1
'''
    rule = DocstringPhysicalLayoutRule()

    violations = rule.check_file(
        Path("sample.py"),
        source_text,
        _parse(source_text),
        source_text.splitlines(),
    )

    assert len(violations) == 1
    assert violations[0].line_number == 5


def test_docstring_physical_layout_rule_rejects_blank_before_summary() -> None:
    """
    验证摘要前空行违反紧凑布局规则
    """
    source_text = '''
from __future__ import annotations

def build_value() -> int:
    """

    返回值
    """
    return 1
'''
    rule = DocstringPhysicalLayoutRule()

    violations = rule.check_file(
        Path("sample.py"),
        source_text,
        _parse(source_text),
        source_text.splitlines(),
    )

    assert len(violations) == 1
    assert violations[0].line_number == 5


def test_boolean_naming_rule_reports_unprefixed_bool_names() -> None:
    """
    验证 bool 名称需要状态或能力前缀
    """
    source_text = """
from __future__ import annotations

def build_value(enabled: bool, is_ready: bool) -> None:
    can_run: bool = is_ready
"""
    rule = BooleanNamingRule()

    violations = rule.check_file(
        Path("sample.py"),
        source_text,
        _parse(source_text),
        source_text.splitlines(),
    )

    assert len(violations) == 1
    assert "enabled" in violations[0].evidence


def test_file_name_specificity_rule_reports_broad_names() -> None:
    """
    验证宽泛文件名会被报告
    """
    rule = FileNameSpecificityRule()

    violations = rule.check_file(Path("helpers.py"), "", None, [])

    assert len(violations) == 1
    assert "helpers.py" in violations[0].evidence


def test_source_text_language_rule_reports_english_docstrings() -> None:
    """
    验证英文 docstring 会被报告
    """
    source_text = '''
from __future__ import annotations

def build_value() -> int:
    """
    Return value
    """
    return 1
'''
    rule = SourceTextLanguageRule()

    violations = rule.check_file(
        Path("sample.py"),
        source_text,
        _parse(source_text),
        source_text.splitlines(),
    )

    assert len(violations) == 1
    assert "Return value" in violations[0].evidence


def test_source_text_language_rule_allows_chinese_with_technical_terms() -> None:
    """
    验证包含技术词的中文 docstring 不会被报告
    """
    source_text = '''
from __future__ import annotations

def build_value() -> int:
    """
    返回 JSON 报告
    """
    return 1
'''
    rule = SourceTextLanguageRule()

    violations = rule.check_file(
        Path("sample.py"),
        source_text,
        _parse(source_text),
        source_text.splitlines(),
    )

    assert violations == []


def test_line_length_rule_ignores_multiline_string_lines() -> None:
    """
    验证多行字符串内部长行不会触发行长规则
    """
    source_text = '''
from __future__ import annotations

TEXT_VALUE = """
这是一段非常长的文本，用来模拟嵌入式模板、说明文本或快照内容，超过一百字符时不应被物理行长规则报告，因为它位于多行字符串内部
"""
'''
    rule = LineLengthRule()

    violations = rule.check_file(
        Path("sample.py"),
        source_text,
        _parse(source_text),
        source_text.splitlines(),
    )

    assert violations == []


def test_import_grouping_rule_reports_group_order_and_blank_line() -> None:
    """
    验证导入分组规则只报告组顺序和组间空行
    """
    wrong_order_source = """
from __future__ import annotations

import requests
import os
"""
    rule = ImportGroupingRule()

    wrong_order_violations = rule.check_file(
        Path("sample.py"),
        wrong_order_source,
        _parse(wrong_order_source),
        wrong_order_source.splitlines(),
    )

    missing_blank_source = """
from __future__ import annotations

import os
import requests
"""
    missing_blank_violations = rule.check_file(
        Path("sample.py"),
        missing_blank_source,
        _parse(missing_blank_source),
        missing_blank_source.splitlines(),
    )

    assert [violation.rule_id for violation in wrong_order_violations] == ["L003"]
    assert "顺序排列导入组" in wrong_order_violations[0].action
    assert [violation.rule_id for violation in missing_blank_violations] == ["L003"]
    assert "保留一个空行" in missing_blank_violations[0].action


def test_import_sorting_rule_reports_only_within_group_order() -> None:
    """
    验证导入排序规则只报告同组来源和成员顺序
    """
    source_text = """
from __future__ import annotations

import sys
import os
from pathlib import Path, PurePath
"""
    rule = ImportSortingRule()

    violations = rule.check_file(
        Path("sample.py"),
        source_text,
        _parse(source_text),
        source_text.splitlines(),
    )

    assert [violation.rule_id for violation in violations] == ["L004", "L004"]
    assert all("组别" not in violation.action for violation in violations)
