from __future__ import annotations

from pathlib import Path

from tools.check_csu import (
    _enabled_native_rules,
    _managed_file_paths,
    _nonproduction_prose_findings,
    _rejects_finding,
    _retain_enabled_native_findings,
    _source_structure_findings,
)


def _write_source(tmp_path: Path, source: str) -> Path:
    root = tmp_path / "src" / "chromatix_next"
    root.mkdir(parents=True)
    (root / "sample.py").write_text(source, encoding="utf-8")
    return tmp_path


def test_source_structure_rejects_module_docstring_and_leading_dossier(tmp_path):
    findings = _source_structure_findings(
        _write_source(tmp_path, '# dossier\n"""module"""\nvalue = 1\n')
    )
    rules = {finding["rule"] for finding in findings}
    assert {"SourceStructure001", "SourceStructure002"} <= rules


def test_source_structure_rejects_private_function_docstring(tmp_path):
    findings = _source_structure_findings(
        _write_source(tmp_path, 'def _private():\n    """not public"""\n')
    )
    assert any(finding["rule"] == "SourceStructure003" for finding in findings)


def test_source_structure_rejects_durable_fact_class_without_docstring(tmp_path):
    findings = _source_structure_findings(
        _write_source(tmp_path, "class _InternalFacts:\n    value: int\n")
    )
    assert any(finding["rule"] == "SourceStructure008" for finding in findings)


def test_source_structure_accepts_internal_class_docstring(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "class _InternalFacts:\n"
            "    \"\"\"承载内部事实\"\"\"\n"
            "    value: int\n",
        )
    )
    assert findings == []


def test_source_structure_rejects_durable_dataclass_without_docstring(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "@dataclass(frozen=True)\n"
            "class _TransactionSnapshot:\n"
            "    value: int\n",
        )
    )
    assert any(finding["rule"] == "SourceStructure008" for finding in findings)


def test_source_structure_rejects_private_class_with_instance_state(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "class _TransactionGuard:\n"
            "    def __init__(self):\n"
            "        self.active = True\n",
        )
    )
    assert any(finding["rule"] == "SourceStructure008" for finding in findings)


def test_source_structure_rejects_class_comment_before_docstring(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "class _InternalFacts:\n"
            "    # 承载内部事实\n"
            "    \"\"\"记录内部事实\"\"\"\n"
            "    value: int\n",
        )
    )
    assert any(finding["rule"] == "SourceStructure009" for finding in findings)


def test_managed_inventory_excludes_the_frozen_example_boundary(tmp_path):
    managed_paths = (
        "src/chromatix_next/module.py",
        "tests/architecture/test_contract.py",
        "tools/check.py",
        "docs/architecture.md",
        "README.md",
    )
    excluded_paths = (
        "examples/demo.py",
        "tests/package_contract/test_examples.py",
        ".scratch/report.md",
    )
    for relative in (*managed_paths, *excluded_paths):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n", encoding="utf-8")

    inventory = {
        path.relative_to(tmp_path).as_posix()
        for path in _managed_file_paths(tmp_path)
    }

    assert set(managed_paths) <= inventory
    assert set(excluded_paths).isdisjoint(inventory)


def test_gate_rejects_only_hard_or_unadjudicated_review_findings():
    assert _rejects_finding({"kind": "hard_violation"})
    assert _rejects_finding({"kind": "under_review"})
    assert _rejects_finding(
        {
            "kind": "under_review",
            "adjudication_owner": "owner",
            "adjudication": "rationale",
        }
    )
    assert not _rejects_finding(
        {
            "kind": "under_review",
            "adjudication_owner": "owner",
            "adjudication": "rationale",
            "adjudication_evidence": "evidence",
        }
    )
    assert not _rejects_finding({"kind": "soft_violation"})


def test_csu_defers_import_order_to_isort():
    profile = Path("csu.toml").read_text(encoding="utf-8")
    assert '"Core009"' not in profile


def test_source_structure_allows_incidental_private_class_without_docstring(tmp_path):
    findings = _source_structure_findings(
        _write_source(tmp_path, "class _IncidentalHelper:\n    pass\n")
    )
    assert findings == []


def test_source_structure_allows_stateless_private_helper_without_docstring(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "class _IncidentalHelper:\n"
            "    @staticmethod\n"
            "    def preserve(value):\n"
            "        return value\n",
        )
    )
    assert findings == []


def test_source_structure_rejects_tracker_comment(tmp_path):
    findings = _source_structure_findings(
        _write_source(tmp_path, "# ticket 12\nvalue = 1\n")
    )
    assert any(finding["rule"] == "SourceStructure004" for finding in findings)


def test_source_structure_rejects_pure_document_pointer_comment(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "value = 1\n"
            "# 实现依据见 《光学接口实现说明》的“光学-006”条目\n"
            "result = value\n",
        )
    )
    assert any(
        finding["rule"] == "SourceStructure007" for finding in findings
    )


def test_source_structure_allows_local_mathematical_comment(tmp_path):
    findings = _source_structure_findings(
        _write_source(tmp_path, "value = 1\n# 保留平方根前的符号判定以避免 NaN\n")
    )
    assert findings == []


def test_source_structure_rejects_sentence_and_comment_dossier(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "value = 1\n"
            "# 第一条实现说明。\n"
            "# 第二条实现说明\n"
            "result = value\n",
        )
    )
    rules = {finding["rule"] for finding in findings}
    assert {"SourceStructure005", "SourceStructure006"} <= rules


def test_source_interface_rejects_missing_local_docstring(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class PublicValue:\n"
            "    value: int\n"
            "def public_function(value: int) -> int:\n"
            "    return value\n",
        )
    )
    missing = [
        finding
        for finding in findings
        if finding["rule"] == "SourceInterface001"
    ]
    assert {finding["symbol"] for finding in missing} == {
        "PublicValue",
        "public_function",
    }


def test_source_interface_requires_semantic_sections(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def public_function(first: int, second: int) -> int:\n"
            "    \"\"\"执行公共计算\"\"\"\n"
            "    if first < 0:\n"
            "        raise ValueError('negative')\n"
            "    return first + second\n",
        )
    )
    rules = {finding["rule"] for finding in findings}
    assert {
        "SourceInterface002",
        "SourceInterface003",
        "SourceInterface004",
    } <= rules


def test_source_interface_rejects_incomplete_argument_inventory(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def public_function(first: int, second: int) -> int:\n"
            "    \"\"\"\n"
            "    执行公共计算\n"
            "\n"
            "    Args:\n"
            "        first: 第一输入\n"
            "\n"
            "    Returns:\n"
            "        两个输入之和\n"
            "    \"\"\"\n"
            "    return first + second\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface005" for finding in findings
    )


def test_source_interface_accepts_complete_function_and_dataclass(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "from dataclasses import dataclass\n"
            "__all__ = ['PublicValue', 'public_function']\n"
            "@dataclass\n"
            "class PublicValue:\n"
            "    \"\"\"\n"
            "    保存公开值\n"
            "\n"
            "    Attributes:\n"
            "        value: 公开整数值\n"
            "    \"\"\"\n"
            "    value: int\n"
            "def public_function(value: int) -> int:\n"
            "    \"\"\"\n"
            "    返回非负公开值\n"
            "\n"
            "    Args:\n"
            "        value: 待验证的整数\n"
            "\n"
            "    Returns:\n"
            "        非负整数\n"
            "\n"
            "    Raises:\n"
            "        ValueError: 输入为负数\n"
            "    \"\"\"\n"
            "    if value < 0:\n"
            "        raise ValueError('negative')\n"
            "    return value\n",
        )
    )
    assert findings == []


def test_source_interface_uses_explicit_constructor_over_annotations(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['PublicValue']\n"
            "class PublicValue:\n"
            "    \"\"\"\n"
            "    保存公开值\n"
            "\n"
            "    Args:\n"
            "        value: 公开整数值\n"
            "    \"\"\"\n"
            "    value: int\n"
            "    def __init__(self, value: int, *, scale: float):\n"
            "        self.value = value\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface005" for finding in findings
    )


def test_native_rule_inventory_is_owned_by_the_profile(tmp_path):
    profile = tmp_path / "csu.toml"
    profile.write_text(
        'enabled_rules = ["Core001", "Core022"]\n',
        encoding="utf-8",
    )
    assert _enabled_native_rules(profile) == frozenset(
        {"Core001", "Core022"},
    )


def test_disabled_native_finding_is_not_silently_adjudicated():
    enabled_finding: dict[str, object] = {
        "rule": "Core022",
        "kind": "hard_violation",
    }
    disabled_finding: dict[str, object] = {
        "rule": "Core021",
        "kind": "hard_violation",
    }
    retained = _retain_enabled_native_findings(
        [enabled_finding, disabled_finding],
        frozenset({"Core022"}),
    )
    assert retained == [enabled_finding]
    assert _rejects_finding(retained[0])


def test_test_prose_rejects_leading_and_multiline_sentence_comments(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "# 开发证据\n"
        "def test_value():\n"
        "    # 第一条说明。\n"
        "    # 第二条说明\n"
        "    assert True\n",
        encoding="utf-8",
    )
    findings = _nonproduction_prose_findings(tests)
    assert {finding["rule"] for finding in findings} == {
        "ProseStructure002",
        "ProseStructure004",
        "ProseStructure005",
    }


def test_test_prose_accepts_named_claim_and_local_reason(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_value():\n"
        "    # 避免在断言前物化不可读张量\n"
        "    assert True\n",
        encoding="utf-8",
    )
    assert _nonproduction_prose_findings(tests) == []


def test_source_interface_rejects_generic_result_template(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def public_function(value: int) -> int:\n"
            "    \"\"\"\n"
            "    返回一个物理结果\n"
            "\n"
            "    Args:\n"
            "        value: 待处理的采样数量\n"
            "\n"
            "    Returns:\n"
            "        该 Interface 计算或查询得到的结果\n"
            "    \"\"\"\n"
            "    return value\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface007" for finding in findings
    )


def test_protocol_property_rejects_generic_result_template(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "from typing import Protocol\n"
            "__all__ = ['PublicContract']\n"
            "class PublicContract(Protocol):\n"
            "    \"\"\"公开角色契约\"\"\"\n"
            "    @property\n"
            "    def forward(self) -> int:\n"
            "        \"\"\"角色计算\n\n"
            "        Returns:\n"
            "            返回 Element 组件作用后的物理值\n"
            "        \"\"\"\n"
            "        ...\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface007"
        and finding.get("symbol") == "PublicContract.forward"
        for finding in findings
    )


def test_source_interface_rejects_repeated_tuple_result_template(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def public_function(value: int) -> tuple[int, int]:\n"
            "    \"\"\"\n"
            "    返回两个物理分支\n"
            "\n"
            "    Args:\n"
            "        value: 待处理的数值\n"
            "\n"
            "    Returns:\n"
            "        输出按公开字段声明顺序排列的元组值\n"
            "    \"\"\"\n"
            "    return value, value\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface007" for finding in findings
    )


def test_source_interface_rejects_empty_semantic_argument_and_result(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def public_function(value: int) -> int:\n"
            "    \"\"\"\n"
            "    返回采样数量\n"
            "\n"
            "    Args:\n"
            "        value:\n"
            "\n"
            "    Returns:\n"
            "        int\n"
            "    \"\"\"\n"
            "    return value\n",
        )
    )
    rules = {finding["rule"] for finding in findings}
    assert {"SourceInterface008", "SourceInterface009"} <= rules


def test_source_interface_requires_result_order_for_multi_result(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def public_function(value: int) -> tuple[int, int]:\n"
            "    \"\"\"\n"
            "    返回两个端口值\n"
            "\n"
            "    Args:\n"
            "        value: 待处理的采样数量\n"
            "\n"
            "    Returns:\n"
            "        两个端口值\n"
            "    \"\"\"\n"
            "    return value, value\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface010" for finding in findings
    )


def test_source_interface_rejects_return_order_that_disagrees_with_tuple_value(
    tmp_path,
):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def public_function(value: int) -> tuple[int, int]:\n"
            "    \"\"\"\n"
            "    返回两个分支\n"
            "\n"
            "    Args:\n"
            "        value: 待处理的数值\n"
            "\n"
            "    Returns:\n"
            "        返回顺序为 (transmitted, reflected)，"
            "第一个是 transmitted，第二个是 reflected\n"
            "    \"\"\"\n"
            "    reflected = value\n"
            "    transmitted = value\n"
            "    return reflected, transmitted\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface010" for finding in findings
    )


def test_source_interface_rejects_unrelated_order_without_tuple_members(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def public_function(value: int) -> tuple[int, int]:\n"
            "    \"\"\"\n"
            "    返回两个物理分支\n"
            "\n"
            "    Args:\n"
            "        value: 待处理的采样数值\n"
            "\n"
            "    Returns:\n"
            "        返回两个物理分支，按照通道顺序排列\n"
            "    \"\"\"\n"
            "    transmitted = value\n"
            "    reflected = value\n"
            "    return transmitted, reflected\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface010" for finding in findings
    )


def test_source_interface_requires_exception_type_in_raises(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def public_function(value: int) -> int:\n"
            "    \"\"\"\n"
            "    返回采样数量\n"
            "\n"
            "    Args:\n"
            "        value: 待处理的采样数量\n"
            "\n"
            "    Returns:\n"
            "        采样数量，单位为 count\n"
            "\n"
            "    Raises:\n"
            "        输入无效时失败\n"
            "    \"\"\"\n"
            "    if value < 0:\n"
            "        raise ValueError('negative')\n"
            "    return value\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface011" for finding in findings
    )


def test_source_interface_detects_one_hop_delegated_failure(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def _validate(value: int) -> None:\n"
            "    if value < 0:\n"
            "        raise ValueError('negative')\n"
            "\n"
            "def public_function(value: int) -> int:\n"
            "    \"\"\"\n"
            "    返回采样数量\n"
            "\n"
            "    Args:\n"
            "        value: 待处理的采样数量\n"
            "\n"
            "    Returns:\n"
            "        采样数量，单位为 count\n"
            "    \"\"\"\n"
            "    _validate(value)\n"
            "    return value\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface012" for finding in findings
    )


def test_source_interface_rejects_placeholder_delegated_failure_condition(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def _validate(value: int) -> None:\n"
            "    if value < 0:\n"
            "        raise ValueError('negative')\n"
            "\n"
            "def public_function(value: int) -> int:\n"
            "    \"\"\"\n"
            "    返回采样数量\n"
            "\n"
            "    Args:\n"
            "        value: 待处理的采样数量\n"
            "\n"
            "    Returns:\n"
            "        采样数量，单位为 count\n"
            "\n"
            "    Raises:\n"
            "        ValueError: delegated validation rejects the physical input\n"
            "    \"\"\"\n"
            "    _validate(value)\n"
            "    return value\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface013" for finding in findings
    )


def test_source_interface_accepts_bounded_delegated_failure_condition(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['public_function']\n"
            "def _validate(value: int) -> None:\n"
            "    if value < 0:\n"
            "        raise ValueError('negative')\n"
            "\n"
            "def public_function(value: int) -> int:\n"
            "    \"\"\"\n"
            "    返回采样数量\n"
            "\n"
            "    Args:\n"
            "        value: 待处理的数值\n"
            "\n"
            "    Returns:\n"
            "        采样数量，单位为 count\n"
            "\n"
            "    Raises:\n"
            "        ValueError: 输入数值/形状/精度/适用域不满足契约\n"
            "    \"\"\"\n"
            "    _validate(value)\n"
            "    return value\n",
        )
    )
    assert findings == []


def test_source_interface_detects_delegated_failure_on_public_class_method(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['PublicValue']\n"
            "class PublicValue:\n"
            "    \"\"\"公开测量组件\"\"\"\n"
            "\n"
            "    def _validate(self, value: int) -> None:\n"
            "        if value < 0:\n"
            "            raise ValueError('negative')\n"
            "\n"
            "    def measure(self, value: int) -> int:\n"
            "        \"\"\"\n"
            "        返回采样数量\n"
            "\n"
            "        Args:\n"
            "            value: 待处理的采样数量\n"
            "\n"
            "        Returns:\n"
            "            采样数量，单位为 count\n"
            "        \"\"\"\n"
            "        self._validate(value)\n"
            "        return value\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface012"
        and finding.get("symbol") == "PublicValue.measure"
        for finding in findings
    )


def test_source_interface_requires_local_docstring_for_inherited_method(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "class Base:\n"
            "    def measure(self) -> int:\n"
            "        \"\"\"基类测量\n\n        Returns:\n"
            "            采样数量，单位为 count\n        \"\"\"\n"
            "        return 1\n"
            "\n"
            "__all__ = ['PublicValue']\n"
            "class PublicValue(Base):\n"
            "    \"\"\"公开测量组件\"\"\"\n",
        )
    )
    assert any(
        finding["rule"] == "SourceInterface001"
        and finding.get("symbol") == "PublicValue.measure"
        for finding in findings
    )


def test_source_interface_accepts_contract_inherited_from_exported_base(tmp_path):
    findings = _source_structure_findings(
        _write_source(
            tmp_path,
            "__all__ = ['Base', 'PublicValue']\n"
            "class Base:\n"
            "    def measure(self) -> int:\n"
            "        \"\"\"\n"
            "        测量固定双精度物理值\n"
            "\n"
            "        Returns:\n"
            "            物理测量值，单位为米\n"
            "        \"\"\"\n"
            "        return 1\n"
            "\n"
            "class PublicValue(Base):\n"
            "    \"\"\"继承公开物理值契约\"\"\"\n",
        )
    )
    assert not any(
        finding["rule"] == "SourceInterface001"
        and finding.get("symbol") == "PublicValue.measure"
        for finding in findings
    )
