from __future__ import annotations

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADR_ROOT = PROJECT_ROOT / "docs" / "adr"

EXPECTED_ADR_FILES = frozenset(
    {
        "0001-one-pytorch-optical-core.md",
        "0002-component-and-assembly-composition.md",
        "0003-optics-numerics-workstation-boundary.md",
        "0004-example-owned-research-workflows.md",
        "0005-fixed-double-scientific-core.md",
        "0006-state-installation-and-immutable-hosting.md",
        "0007-mixed-independent-wave-ray-assembly.md",
        "0008-active-polarization-foundation.md",
        "0009-polarized-ray-foundation.md",
        "0010-exact-polarized-ray-admissibility-and-closure.md",
        "0011-assembly-topology-contract.md",
        "0012-sonnet-combination-and-evidence-contract.md",
        "0013-ssrhm-exact-topology-and-plane-local-correction.md",
        "0014-ssrhm-conic-and-sampled-wave-deepening.md",
        "0015-ssrhm-tangent-pose-migration.md",
        "0016-paraxial-ray-transfer-vocabulary-cutover.md",
    }
)
ACTIVE_STATUS_WORDS = ("Accepted", "Implemented")


def test_active_decision_set_and_statuses_are_structurally_closed() -> None:
    """
    活跃 ADR 集合固定且每份文档只声明一个可接受状态
    """

    actual_files = frozenset(path.name for path in ADR_ROOT.glob("*.md"))
    assert actual_files == EXPECTED_ADR_FILES
    for filename in sorted(actual_files):
        text = (ADR_ROOT / filename).read_text(encoding="utf-8")
        statuses = re.findall(r"^\*\*Status:\*\* (.+)$", text, re.MULTILINE)
        assert len(statuses) == 1
        assert statuses[0].startswith(ACTIVE_STATUS_WORDS)


def test_visible_supersession_targets_exist_and_are_not_self_references() -> None:
    """
    可见取代关系均指向存在的另一份 ADR
    """

    for source_path in sorted(ADR_ROOT.glob("*.md")):
        text = source_path.read_text(encoding="utf-8")
        supersession_blocks = (
            paragraph
            for paragraph in text.split("\n\n")
            if "supersession" in paragraph.lower()
        )
        for block in supersession_blocks:
            targets = re.findall(r"`([^`]+\.md)`", block)
            for target in targets:
                target_name = Path(target).name
                if not re.match(r"^\d{4}-", target_name):
                    continue
                assert target_name != source_path.name
                assert (ADR_ROOT / target_name).is_file()


def test_ssrhm_implemented_correction_truth_is_bidirectional() -> None:
    """
    SSRHM 数值纠正已实现，旧决定与活跃真相均显式指向纠正边界
    """

    superseded_decision = (
        ADR_ROOT / "0010-exact-polarized-ray-admissibility-and-closure.md"
    ).read_text(encoding="utf-8")
    correction_decision = (
        ADR_ROOT / "0013-ssrhm-exact-topology-and-plane-local-correction.md"
    ).read_text(encoding="utf-8")
    context = (PROJECT_ROOT / "CONTEXT.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8",
    )

    assert "0013-ssrhm-exact-topology-and-plane-local-correction.md" in (
        superseded_decision
    )
    assert "0010-exact-polarized-ray-admissibility-and-closure.md" in (
        correction_decision
    )
    assert "**Status:** Accepted — implemented present truth" in (
        correction_decision
    )
    assert "4503599627370497 / 2^1252 > 0" in correction_decision
    assert "`(0, -2^-600, 0)`" in correction_decision
    assert "Implemented numerical correction (ADR-0013)" in context
    assert "Implemented numerical correction (ADR-0013)" in architecture
    assert "have not landed yet" not in architecture
    assert "implementation pending" not in correction_decision


def test_ssrhm_deepening_truth_is_bidirectional() -> None:
    """
    SSRHM 两阶段深化已实现，决定、领域语言与架构清单陈述同一当前真相
    """

    decision_name = "0014-ssrhm-conic-and-sampled-wave-deepening.md"
    decision = (ADR_ROOT / decision_name).read_text(encoding="utf-8")
    context = (PROJECT_ROOT / "CONTEXT.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8",
    )

    assert "**Status:** Accepted — implemented present truth" in decision
    assert "implementation pending" not in decision
    assert "Implemented present truth (ADR-0014)" in context
    assert "Implemented SSRHM deepening (ADR-0014)" in architecture
    assert decision_name in architecture
    for filename in EXPECTED_ADR_FILES:
        assert f"`docs/adr/{filename}`" in architecture


def test_final_ssrhm_public_and_module_cutover_is_active_truth() -> None:
    """
    固定最终公共边界、直接模块切换与封档停止线
    """

    architecture = (PROJECT_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8",
    )
    required_present_truth = (
        "_numerics/cube_response.py",
        "source/collimated_ray.py",
        "two top-level public exports",
        "twenty-four public Optical Component actions",
        "## Post-seal stop line",
    )
    for statement in required_present_truth:
        assert statement in architecture


def test_tangent_pose_supersession_truth_is_bidirectional() -> None:
    """
    切线姿态决策与三份被取代决策保持双向可见链接
    """

    decision_name = "0015-ssrhm-tangent-pose-migration.md"
    decision = (ADR_ROOT / decision_name).read_text(encoding="utf-8")
    displaced_decisions = (
        ("0009-polarized-ray-foundation.md", "ADR-0009"),
        ("0010-exact-polarized-ray-admissibility-and-closure.md", "ADR-0010"),
        ("0013-ssrhm-exact-topology-and-plane-local-correction.md", "ADR-0013"),
    )
    for displaced_name, displaced_identity in displaced_decisions:
        displaced = (ADR_ROOT / displaced_name).read_text(encoding="utf-8")
        assert decision_name in displaced
        assert displaced_identity in decision


def test_paraxial_ray_transfer_cutover_is_active_truth() -> None:
    """
    完整光线传递词汇与无兼容切换在决策和活跃文档中一致
    """

    decision_name = "0016-paraxial-ray-transfer-vocabulary-cutover.md"
    decision = (ADR_ROOT / decision_name).read_text(encoding="utf-8")
    context = (PROJECT_ROOT / "CONTEXT.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8",
    )
    required_complete_names = (
        "compose_ray_transfer_matrices",
        "free_space_ray_transfer_matrix",
        "spherical_refraction_ray_transfer_matrix",
        "thin_lens_ray_transfer_matrix",
    )

    assert "**Status:** Accepted — implemented present truth" in decision
    assert "chromatix_next.optics.abcd" in decision
    for name in required_complete_names:
        assert name in decision
    assert "optics/paraxial_ray_transfer.py" in context
    assert decision_name in architecture


def test_mission_keeps_the_bounded_comparison_statement() -> None:
    """
    比较范围保留固定快照、审计边界、排除项与中性拓扑措辞
    """

    mission = (PROJECT_ROOT / "MISSION.md").read_text(encoding="utf-8")
    normalized_mission = " ".join(mission.split())
    required_phrases = (
        "727d7a39e9a0054cfe3a102440fcf931d31fd11a",
        "d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee",
        "Coverage is assessed by behaviour family",
        "fixed-double sampled Wave optics",
        "Volume/multislice/multiple scattering, fluorescence, Modified Born",
        "composed through typed Assembly topology",
        "The claim does not extend to excluded v0.4/v0.6 behaviours",
    )
    for phrase in required_phrases:
        assert phrase in normalized_mission
    assert "stronger typed topology than the pinned snapshots" not in (
        normalized_mission
    )
    assert "feature, speed, memory, performance, ecosystem, or universal-accuracy" in (
        normalized_mission
    )
