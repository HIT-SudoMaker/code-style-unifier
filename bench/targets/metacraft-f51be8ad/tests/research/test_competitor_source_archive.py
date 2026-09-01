from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).parents[2]
ARCHIVE = ROOT / "docs" / "research" / "2026-08-15-competitor-source-archive"
MANIFEST_PATH = ARCHIVE / "manifest.json"
README_PATH = ARCHIVE / "README.md"
EXPECTED_KINDS = {
    "article",
    "supporting_information",
    "code",
    "data",
    "weights",
}
EXPECTED_IDENTITIES = {
    "doi:10.1002/lpor.71739",
    "doi:10.1126/sciadv.adx8006",
    "arxiv:2605.22647",
}
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


def test_manifest_has_exactly_three_deduplicated_article_identities() -> None:
    manifest = _manifest()
    competitors = manifest["competitors"]

    assert len(competitors) == 3
    assert {item["article_identity"]["canonical"] for item in competitors} == (
        EXPECTED_IDENTITIES
    )
    assert len({item["competitor_id"] for item in competitors}) == 3
    assert manifest["identity_rule"].startswith("Use DOI when assigned")

    for competitor in competitors:
        artifacts = competitor["artifacts"]
        assert len(artifacts) == 5
        assert {artifact["kind"] for artifact in artifacts} == EXPECTED_KINDS
        assert len({artifact["artifact_id"] for artifact in artifacts}) == 5


def test_retained_local_artifacts_match_the_manifested_bytes() -> None:
    retained = [
        artifact
        for competitor in _manifest()["competitors"]
        for artifact in competitor["artifacts"]
        if artifact["status"] == "retained_local"
    ]

    assert {artifact["artifact_id"] for artifact in retained} == {
        "self_evolving.article",
        "metachat.code",
    }

    for artifact in retained:
        path = ROOT / artifact["local_path"]
        assert path.exists()
        assert artifact["accessed_on"] == "2026-08-15"
        assert artifact["source_locator"].startswith("https://")
        assert artifact["version"]
        assert artifact["license"]["redistribution_status"]
        assert SHA256.fullmatch(artifact["sha256"])

        if artifact["content_kind"] == "file":
            body = path.read_bytes()
            assert artifact["byte_size"] == len(body)
            assert artifact["sha256"] == _digest(body)
        else:
            file_count, byte_size, identity = _tree_identity(path)
            assert artifact["content_kind"] == "directory_tree"
            assert artifact["file_count"] == file_count
            assert artifact["byte_size"] == byte_size
            assert artifact["sha256"] == identity


def test_absence_and_link_only_entries_are_typed_and_explain_the_boundary() -> None:
    artifacts = [
        artifact
        for competitor in _manifest()["competitors"]
        for artifact in competitor["artifacts"]
    ]
    allowed = {"retained_local", "linked_only", "typed_missing", "not_applicable"}
    assert {artifact["status"] for artifact in artifacts} <= allowed

    for artifact in artifacts:
        assert artifact["accessed_on"] == "2026-08-15"
        assert "license" in artifact
        status = artifact["status"]
        if status == "linked_only":
            assert artifact["source_locator"].startswith("https://")
            assert artifact["not_copied_reason"]
            assert artifact["local_path"] is None
            assert artifact["byte_size"] is None
            assert artifact["sha256"] is None
        elif status == "typed_missing":
            assert artifact["missing_reason"]
            assert artifact["local_path"] is None
            assert artifact["byte_size"] is None
            assert artifact["sha256"] is None
        elif status == "not_applicable":
            assert artifact["not_applicable_reason"]
            assert artifact["local_path"] is None

    by_id = {artifact["artifact_id"]: artifact for artifact in artifacts}
    assert by_id["metachat.article"]["status"] == "typed_missing"
    assert by_id["metadesigner.article"]["status"] == "typed_missing"
    assert by_id["self_evolving.supporting_information"]["status"] == (
        "typed_missing"
    )
    assert by_id["metachat.supporting_information"]["status"] == "typed_missing"
    assert by_id["metachat.code"]["license"]["redistribution_status"] == (
        "not_established"
    )


def test_temporary_and_derived_outputs_cannot_satisfy_source_entries() -> None:
    manifest = _manifest()
    durable_paths = {
        artifact["local_path"]
        for competitor in manifest["competitors"]
        for artifact in competitor["artifacts"]
        if artifact["local_path"] is not None
    }
    observed = {item["path"] for item in manifest["non_durable_observations"]}

    assert ".codex_tmp/2605.22647.pdf" in observed
    assert all(not path.startswith(".codex_tmp/") for path in durable_paths)
    assert all("rendered-pages" not in path for path in durable_paths)
    assert manifest["tree_hash_rule"]["excluded"] == [
        ".git/**",
        "**/.DS_Store",
        "**/__pycache__/**",
        "**/*.pyc",
        "**/*.pyo",
    ]
    assert {
        item["category"] for item in manifest["durable_archive_exclusions"]
    } == {
        "temporary_downloads",
        "runtime_reports",
        "bytecode_caches",
        "run_projections",
        "derived_research_outputs",
    }


def test_manifest_and_bibliography_remain_research_context() -> None:
    manifest = _manifest()
    readme = README_PATH.read_text(encoding="utf-8")
    bibliography = (ROOT / manifest["bibliography_path"]).read_text(
        encoding="utf-8"
    )

    assert manifest["authority_status"] == "research_context_only"
    assert "research context, not\nscientific Authority" in readme
    assert bibliography.count("10.1002/lpor.71739") == 2
    assert bibliography.count("10.1126/sciadv.adx8006") == 2
    assert re.search(r"eprint\s*=\s*\{2605\.22647\}", bibliography)


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _tree_identity(root: Path) -> tuple[int, int, str]:
    records: list[tuple[str, int, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or _excluded_from_tree(root, path):
            continue
        body = path.read_bytes()
        records.append(
            (
                path.relative_to(root).as_posix(),
                len(body),
                hashlib.sha256(body).hexdigest(),
            )
        )
    records.sort()
    canonical = "\n".join(
        f"{relative}\t{size}\t{identity}"
        for relative, size, identity in records
    ).encode("utf-8")
    return len(records), sum(size for _, size, _ in records), _digest(canonical)


def _excluded_from_tree(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    return (
        ".git" in relative.parts
        or "__pycache__" in relative.parts
        or path.name == ".DS_Store"
        or path.suffix.lower() in {".pyc", ".pyo"}
    )


def _digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()
