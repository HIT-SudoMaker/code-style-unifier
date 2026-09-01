from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import re
from typing import Literal, NotRequired, TypedDict, cast

import numpy as np
from torch.utils.data import Dataset

from data.data_source.indexing.file_sources import build_file_source_records
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.fixed_measurement.evidence.integrity import sha256_file

FMD_SPLIT_SCHEMA_VERSION = "restoration_fmd_split_v1"
FMD_ARCHIVE_SPLIT_SCHEMA_VERSION = "restoration_fmd_split_v2"
FMD_STANDARD_SPLIT_SEED = 2026
FMD_SPLITS = ("train", "val", "test")
FMD_ARCHIVE_SOURCE_SELECTION_POLICY = "canonical_avg50_excluding_test_mix"

_FMD_STANDARD_CHANNEL_PATTERN = re.compile(
    r"^fmd/(?P<microscope>[^/_]+)_(?P<sample>.+)_(?P<channel>[^_/]+)/"
    r"(?P<scene>[^/]+)/(?P<frame>[^/]+)$"
)
_FMD_STANDARD_NON_CHANNEL_PATTERN = re.compile(
    r"^fmd/(?P<microscope>[^/_]+)_(?P<sample>[^/]+)/"
    r"(?P<scene>[^/]+)/(?P<frame>[^/]+)$"
)
_FMD_TEST_MIX_CHANNEL_PATTERN = re.compile(
    r"^fmd/test_mix/(?P<microscope>[^/_]+)_(?P<sample>.+)_"
    r"(?P<channel>[^_/]+)_(?P<scene>[^_/]+)$"
)
_FMD_TEST_MIX_NON_CHANNEL_PATTERN = re.compile(
    r"^fmd/test_mix/(?P<microscope>[^/_]+)_(?P<sample>.+)_"
    r"(?P<scene>\d+)$"
)
_SPLIT_ORDER = {split: index for index, split in enumerate(FMD_SPLITS)}


class SplitRecord(TypedDict):
    """
    鎻忚堪鍗曟潯鍒嗗壊璁板綍
    """
    image_id: str
    source_path: str
    split: str
    group_key: str
    stratification_key: str
    content_sha256: NotRequired[str]


class SplitManifest(TypedDict):
    """
    鎻忚堪澶嶅師鏁版嵁鍒嗗壊娓呭崟
    """
    schema_version: str
    dataset_name: str
    source_dataset_root_hint: str
    split_seed: int
    split_strategy: str
    group_key_strategy: str
    train_fraction: float
    val_fraction: float
    test_fraction: float
    split_summary: dict[str, dict[str, object]]
    records: list[SplitRecord]
    source_selection_policy: NotRequired[str]
    content_inventory_sha256: NotRequired[str]


class SplitFilteredDataset(Dataset):
    """
    鎸夊垎鍓叉竻鍗曡繃婊ゆ暟鎹泦
    """
    def __init__(
        self,
        source_dataset: Dataset,
        *,
        manifest: Mapping[str, object],
        split: Literal["train", "val", "test"],
    ) -> None:
        """
        鍒嗗壊杩囨护鏁版嵁闆?        """
        validate_split_manifest(manifest)
        split_ids = {
            record["image_id"] for record in select_split_records(manifest, split=split)
        }
        if not split_ids:
            raise invalid_restoration_contract(
                f"split {split} has no records in split manifest"
            )

        selected_indices: list[int] = []
        found_ids: set[str] = set()
        source_image_ids = _image_ids_from_dataset_metadata(source_dataset)
        if source_image_ids is None:
            source_image_ids = []
            for index in range(len(source_dataset)):
                sample = source_dataset[index]
                source_image_ids.append(_image_id_from_sample(sample))

        selected_counts: Counter[str] = Counter()
        for index, image_id in enumerate(source_image_ids):
            if image_id in split_ids:
                selected_indices.append(index)
                found_ids.add(image_id)
                selected_counts[image_id] += 1

        duplicate_selected_ids = [
            image_id for image_id, count in selected_counts.items() if count > 1
        ]
        if duplicate_selected_ids:
            duplicate_id = sorted(duplicate_selected_ids)[0]
            raise invalid_restoration_contract(
                "duplicate image_id in source dataset selected by "
                f"split {split}: {duplicate_id}"
            )

        missing_ids = split_ids - found_ids
        if missing_ids:
            preview = ", ".join(sorted(missing_ids)[:5])
            raise invalid_restoration_contract(
                f"missing split {split} image_id(s) in source dataset: {preview}"
            )

        self.source_dataset = source_dataset
        self.selected_indices = tuple(selected_indices)

    def __len__(self) -> int:
        """
        杩斿洖绛涢€夋牱鏈暟閲?        """
        return len(self.selected_indices)

    def __getitem__(self, index: int) -> object:
        """
        杩斿洖绛涢€夊悗鐨勬牱鏈?        """
        return self.source_dataset[self.selected_indices[int(index)]]


def is_fmd_group_key_matched(image_id: str) -> bool:
    """
    鍒ゆ柇鍥惧儚缂栧彿鏄惁鍖归厤鏍囧噯鍒嗙粍瑙勫垯
    """
    return any(
        pattern.match(image_id) is not None
        for pattern in (
            _FMD_STANDARD_CHANNEL_PATTERN,
            _FMD_STANDARD_NON_CHANNEL_PATTERN,
            _FMD_TEST_MIX_CHANNEL_PATTERN,
            _FMD_TEST_MIX_NON_CHANNEL_PATTERN,
        )
    )


def build_fmd_group_key(image_id: str) -> str:
    """
    鏋勫缓 FMD 鍦烘櫙绾у垎缁勯敭
    """
    standard_channel = _FMD_STANDARD_CHANNEL_PATTERN.match(image_id)
    if standard_channel is not None:
        return (
            f"{standard_channel.group('microscope')}_"
            f"{standard_channel.group('sample')}/{standard_channel.group('scene')}"
        )

    standard_non_channel = _FMD_STANDARD_NON_CHANNEL_PATTERN.match(image_id)
    if standard_non_channel is not None:
        return (
            f"{standard_non_channel.group('microscope')}_"
            f"{standard_non_channel.group('sample')}/"
            f"{standard_non_channel.group('scene')}"
        )

    test_mix_channel = _FMD_TEST_MIX_CHANNEL_PATTERN.match(image_id)
    if test_mix_channel is not None:
        return (
            f"test_mix/{test_mix_channel.group('microscope')}_"
            f"{test_mix_channel.group('sample')}/{test_mix_channel.group('scene')}"
        )

    test_mix_non_channel = _FMD_TEST_MIX_NON_CHANNEL_PATTERN.match(image_id)
    if test_mix_non_channel is not None:
        return (
            f"test_mix/{test_mix_non_channel.group('microscope')}_"
            f"{test_mix_non_channel.group('sample')}/"
            f"{test_mix_non_channel.group('scene')}"
        )

    parts = image_id.split("/")
    return image_id if len(parts) <= 1 else "/".join(parts[:-1])


def build_fmd_stratification_key(image_id: str) -> str:
    """
    鏋勫缓 FMD 鍒嗗眰閿?    """
    standard_channel = _FMD_STANDARD_CHANNEL_PATTERN.match(image_id)
    if standard_channel is not None:
        return (
            f"{standard_channel.group('microscope')}_"
            f"{standard_channel.group('sample')}"
        )

    standard_non_channel = _FMD_STANDARD_NON_CHANNEL_PATTERN.match(image_id)
    if standard_non_channel is not None:
        return (
            f"{standard_non_channel.group('microscope')}_"
            f"{standard_non_channel.group('sample')}"
        )

    test_mix_channel = _FMD_TEST_MIX_CHANNEL_PATTERN.match(image_id)
    if test_mix_channel is not None:
        return (
            f"test_mix/{test_mix_channel.group('microscope')}_"
            f"{test_mix_channel.group('sample')}"
        )

    test_mix_non_channel = _FMD_TEST_MIX_NON_CHANNEL_PATTERN.match(image_id)
    if test_mix_non_channel is not None:
        return (
            f"test_mix/{test_mix_non_channel.group('microscope')}_"
            f"{test_mix_non_channel.group('sample')}"
        )

    return build_fmd_group_key(image_id)


def build_real_fmd_split_manifest(
    *,
    dataset_root: str | Path | None,
    split_seed: int = FMD_STANDARD_SPLIT_SEED,
    minimum_test_groups: int = 1,
    minimum_test_images: int = 1,
) -> SplitManifest:
    """
    浠庣湡瀹?FMD 鏂囦欢绱㈠紩鏋勫缓鍒掑垎娓呭崟
    """
    source_root, records, _channel_policy = build_file_source_records(
        source_name="fmd",
        dataset_root=dataset_root,
        is_train=True,
        max_samples=None,
        random_seed=split_seed,
    )
    canonical_records = [
        record
        for record in records
        if not record.image_id.startswith("fmd/test_mix/")
    ]
    fallback_image_ids = [
        record.image_id
        for record in canonical_records
        if not is_fmd_group_key_matched(record.image_id)
    ]
    if fallback_image_ids:
        examples = ", ".join(sorted(fallback_image_ids)[:5])
        raise invalid_restoration_contract(
            f"FMD group-key fallback for image_id(s): {examples}"
        )

    noncanonical_frames = [
        record.image_id
        for record in canonical_records
        if not record.image_id.endswith("/avg50")
    ]
    if noncanonical_frames:
        examples = ", ".join(sorted(noncanonical_frames)[:5])
        raise invalid_restoration_contract(
            f"FMD archive requires canonical avg50 images: {examples}"
        )

    resolved_source_paths = {
        record.image_id: _resolve_source_path(source_root, record.source_path)
        for record in canonical_records
    }
    manifest = build_split_manifest(
        image_ids=[record.image_id for record in canonical_records],
        source_paths=[
            resolved_source_paths[record.image_id].as_posix()
            for record in canonical_records
        ],
        split_seed=split_seed,
        dataset_root_hint=source_root.as_posix(),
    )
    content_sha256 = {
        record.image_id: sha256_file(resolved_source_paths[record.image_id])
        for record in canonical_records
    }
    manifest["schema_version"] = FMD_ARCHIVE_SPLIT_SCHEMA_VERSION
    manifest["source_selection_policy"] = FMD_ARCHIVE_SOURCE_SELECTION_POLICY
    for split_record in manifest["records"]:
        split_record["content_sha256"] = content_sha256[split_record["image_id"]]
    manifest["content_inventory_sha256"] = _content_inventory_sha256(
        manifest["records"]
    )
    validate_split_manifest(manifest)

    test_summary = manifest["split_summary"]["test"]
    test_group_count = int(test_summary["group_count"])
    test_image_count = int(test_summary["image_count"])
    if test_group_count < minimum_test_groups:
        raise invalid_restoration_contract(
            "FMD test split too small: "
            f"group_count={test_group_count}, minimum_test_groups={minimum_test_groups}"
        )
    if test_image_count < minimum_test_images:
        raise invalid_restoration_contract(
            "FMD test split too small: "
            f"image_count={test_image_count}, minimum_test_images={minimum_test_images}"
        )
    return manifest


def build_split_manifest(
    *,
    image_ids: Sequence[str],
    source_paths: Sequence[str],
    split_seed: int = FMD_STANDARD_SPLIT_SEED,
    train_fraction: float = 0.7,
    val_fraction: float = 0.15,
    test_fraction: float = 0.15,
    dataset_root_hint: str = "data/raw",
) -> SplitManifest:
    """
    鏋勫缓鍒嗙粍浜掓枼鐨勫垎鍓叉竻鍗?    """
    if len(image_ids) != len(source_paths):
        raise invalid_restoration_contract(
            "image_ids and source_paths must have the same length"
        )
    if not image_ids:
        raise invalid_restoration_contract("image_ids must not be empty")
    fractions = {
        "train": float(train_fraction),
        "val": float(val_fraction),
        "test": float(test_fraction),
    }
    if any(fraction < 0 for fraction in fractions.values()):
        raise invalid_restoration_contract("split fractions must be non-negative")
    if not np.isclose(sum(fractions.values()), 1.0):
        raise invalid_restoration_contract("split fractions must sum to 1.0")

    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for image_id, source_path in zip(image_ids, source_paths, strict=True):
        image_id = str(image_id)
        groups[build_fmd_group_key(image_id)].append((image_id, str(source_path)))

    group_keys = sorted(groups)
    shuffled_groups = list(group_keys)
    np.random.default_rng(split_seed).shuffle(shuffled_groups)
    counts = _split_group_counts(group_count=len(shuffled_groups), fractions=fractions)

    group_to_split: dict[str, str] = {}
    start = 0
    for split in FMD_SPLITS:
        end = start + counts[split]
        for group_key in shuffled_groups[start:end]:
            group_to_split[group_key] = split
        start = end

    records: list[SplitRecord] = []
    for group_key in group_keys:
        split = group_to_split[group_key]
        for image_id, source_path in sorted(groups[group_key]):
            records.append(
                {
                    "image_id": image_id,
                    "source_path": source_path,
                    "split": split,
                    "group_key": group_key,
                    "stratification_key": build_fmd_stratification_key(image_id),
                }
            )
    records.sort(
        key=lambda record: (
            _SPLIT_ORDER[record["split"]],
            record["group_key"],
            record["image_id"],
        )
    )

    manifest: SplitManifest = {
        "schema_version": FMD_SPLIT_SCHEMA_VERSION,
        "dataset_name": "fmd",
        "source_dataset_root_hint": dataset_root_hint,
        "split_seed": int(split_seed),
        "split_strategy": "group_shuffle",
        "group_key_strategy": "fmd_scene_channel_collapsed",
        "train_fraction": train_fraction,
        "val_fraction": val_fraction,
        "test_fraction": test_fraction,
        "split_summary": _build_split_summary(records),
        "records": records,
    }
    validate_split_manifest(manifest)
    return manifest


def validate_split_manifest(manifest: Mapping[str, object]) -> None:
    """
    鏍￠獙鍒嗗壊娓呭崟
    """
    schema_version = manifest.get("schema_version")
    if schema_version not in {
        FMD_SPLIT_SCHEMA_VERSION,
        FMD_ARCHIVE_SPLIT_SCHEMA_VERSION,
    }:
        raise invalid_restoration_contract("unsupported split manifest schema_version")
    if manifest.get("dataset_name") != "fmd":
        raise invalid_restoration_contract("split manifest dataset_name must be fmd")
    if manifest.get("split_strategy") != "group_shuffle":
        raise invalid_restoration_contract(
            "split manifest split_strategy must be group_shuffle"
        )
    if manifest.get("group_key_strategy") != "fmd_scene_channel_collapsed":
        raise invalid_restoration_contract(
            "split manifest group_key_strategy must be fmd_scene_channel_collapsed"
        )
    source_dataset_root_hint = manifest.get("source_dataset_root_hint")
    if (
        not isinstance(source_dataset_root_hint, str)
        or not source_dataset_root_hint
    ):
        raise invalid_restoration_contract(
            "source_dataset_root_hint must be a non-empty string"
        )
    split_seed = manifest.get("split_seed")
    if not isinstance(split_seed, int) or isinstance(split_seed, bool) or split_seed < 0:
        raise invalid_restoration_contract(
            "split_seed must be a non-negative integer"
        )

    fractions: dict[str, float] = {}
    for split in FMD_SPLITS:
        fraction_key = f"{split}_fraction"
        fraction = manifest.get(fraction_key)
        if (
            not isinstance(fraction, (int, float))
            or isinstance(fraction, bool)
            or fraction < 0
        ):
            raise invalid_restoration_contract(
                f"{fraction_key} must be a non-negative number"
            )
        fractions[split] = float(fraction)
    if not np.isclose(sum(fractions.values()), 1.0):
        raise invalid_restoration_contract("split fractions must sum to 1.0")

    records_object = manifest.get("records")
    if not isinstance(records_object, list) or not records_object:
        raise invalid_restoration_contract(
            "split manifest records must be a non-empty list"
        )

    seen_image_splits: dict[str, str] = {}
    seen_group_splits: dict[str, str] = {}
    observed_splits: set[str] = set()
    for record_object in records_object:
        if not isinstance(record_object, Mapping):
            raise invalid_restoration_contract(
                "split manifest records must be mappings"
            )
        record = cast(Mapping[str, object], record_object)
        split = record.get("split")
        image_id = record.get("image_id")
        source_path = record.get("source_path")
        group_key = record.get("group_key")
        stratification_key = record.get("stratification_key")
        if split not in FMD_SPLITS:
            raise invalid_restoration_contract(f"invalid split: {split}")
        if not isinstance(image_id, str) or not image_id:
            raise invalid_restoration_contract(
                "record image_id must be a non-empty string"
            )
        if not isinstance(source_path, str) or not source_path:
            raise invalid_restoration_contract(
                "record source_path must be a non-empty string"
            )
        if not isinstance(group_key, str) or not group_key:
            raise invalid_restoration_contract(
                "record group_key must be a non-empty string"
            )
        if not isinstance(stratification_key, str) or not stratification_key:
            raise invalid_restoration_contract(
                "record stratification_key must be a non-empty string"
            )
        expected_group_key = build_fmd_group_key(image_id)
        if group_key != expected_group_key:
            raise invalid_restoration_contract(
                "record group_key does not match image_id: "
                f"{image_id} expected {expected_group_key}, found {group_key}"
            )
        expected_stratification_key = build_fmd_stratification_key(image_id)
        if stratification_key != expected_stratification_key:
            raise invalid_restoration_contract(
                "record stratification_key does not match image_id: "
                f"{image_id} expected {expected_stratification_key}, "
                f"found {stratification_key}"
            )

        split_name = str(split)
        previous_image_split = seen_image_splits.get(image_id)
        if previous_image_split is not None:
            if previous_image_split != split_name:
                raise invalid_restoration_contract(
                    "image_id appears in multiple splits: "
                    f"{image_id} ({previous_image_split}, {split_name})"
                )
            raise invalid_restoration_contract(
                f"duplicate image_id in split {split_name}: {image_id}"
            )
        seen_image_splits[image_id] = split_name

        previous_group_split = seen_group_splits.get(group_key)
        if previous_group_split is not None and previous_group_split != split_name:
            raise invalid_restoration_contract(
                "group_key appears in multiple splits: "
                f"{group_key} ({previous_group_split}, {split_name})"
            )
        seen_group_splits[group_key] = split_name
        observed_splits.add(split_name)

    missing_splits = set(FMD_SPLITS) - observed_splits
    if missing_splits:
        raise invalid_restoration_contract(
            f"split manifest missing splits: {', '.join(sorted(missing_splits))}"
        )

    if schema_version == FMD_ARCHIVE_SPLIT_SCHEMA_VERSION:
        _validate_archive_content(manifest, records_object)
    _validate_split_summary(manifest.get("split_summary"), records_object)


def _validate_archive_content(
    manifest: Mapping[str, object],
    records: list[object],
) -> None:
    if (
        manifest.get("source_selection_policy")
        != FMD_ARCHIVE_SOURCE_SELECTION_POLICY
    ):
        raise invalid_restoration_contract(
            "archive split source_selection_policy must exclude test_mix"
        )
    seen_content: dict[str, str] = {}
    typed_records: list[Mapping[str, object]] = []
    for record_object in records:
        record = cast(Mapping[str, object], record_object)
        typed_records.append(record)
        image_id = str(record["image_id"])
        if image_id.startswith("fmd/test_mix/") or not image_id.endswith("/avg50"):
            raise invalid_restoration_contract(
                f"archive split contains noncanonical image: {image_id}"
            )
        content_hash = record.get("content_sha256")
        if (
            not isinstance(content_hash, str)
            or not re.fullmatch(r"[0-9a-f]{64}", content_hash)
        ):
            raise invalid_restoration_contract(
                f"archive split content_sha256 is invalid: {image_id}"
            )
        duplicate_image_id = seen_content.get(content_hash)
        if duplicate_image_id is not None:
            raise invalid_restoration_contract(
                "duplicate clean-image content in archive split: "
                f"{duplicate_image_id}, {image_id}"
            )
        seen_content[content_hash] = image_id
    expected_inventory_hash = _content_inventory_sha256(typed_records)
    if manifest.get("content_inventory_sha256") != expected_inventory_hash:
        raise invalid_restoration_contract(
            "archive split content_inventory_sha256 mismatch"
        )


def _content_inventory_sha256(records: Sequence[Mapping[str, object]]) -> str:
    inventory = [
        {
            "image_id": str(record["image_id"]),
            "content_sha256": str(record["content_sha256"]),
        }
        for record in sorted(records, key=lambda item: str(item["image_id"]))
    ]
    encoded = json.dumps(
        inventory,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_source_path(source_root: Path, source_path: Path) -> Path:
    if source_path.is_absolute():
        return source_path
    return source_root / source_path


def select_split_records(
    manifest: Mapping[str, object],
    *,
    split: Literal["train", "val", "test"],
) -> list[SplitRecord]:
    """
    杩斿洖鎸囧畾鍒嗗壊璁板綍
    """
    validate_split_manifest(manifest)
    records = cast(list[Mapping[str, object]], manifest["records"])
    return [
        cast(SplitRecord, dict(record))
        for record in records
        if record.get("split") == split
    ]


def write_split_manifest(path: str | Path, manifest: Mapping[str, object]) -> Path:
    """
    鍐欏叆鍒嗗壊娓呭崟鏂囦欢
    """
    validate_split_manifest(manifest)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def read_split_manifest(path: str | Path) -> SplitManifest:
    """
    璇诲彇骞舵牎楠屽垎鍓叉竻鍗曟枃浠?    """
    loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise invalid_restoration_contract("split manifest JSON must be an object")
    validate_split_manifest(loaded)
    return cast(SplitManifest, loaded)


def _image_id_from_sample(sample: object) -> str:
    if not isinstance(sample, Mapping):
        raise invalid_restoration_contract(
            "sample must be a mapping with provenance.image_id"
        )
    provenance = sample.get("provenance")
    if not isinstance(provenance, Mapping):
        raise invalid_restoration_contract(
            "sample provenance must include image_id"
        )
    image_id = provenance.get("image_id")
    if not isinstance(image_id, str) or not image_id:
        raise invalid_restoration_contract(
            "sample provenance.image_id must be a non-empty string"
        )
    return image_id


def _image_ids_from_dataset_metadata(source_dataset: object) -> list[str] | None:
    records = getattr(source_dataset, "records", None)
    if records is not None:
        image_ids: list[str] = []
        try:
            iterator = iter(records)
        except TypeError:
            return None
        for record in iterator:
            image_id = getattr(record, "image_id", None)
            if not isinstance(image_id, str) or not image_id:
                return None
            image_ids.append(image_id)
        return image_ids

    for attribute_name in ("source_dataset", "prepared_dataset"):
        nested_dataset = getattr(source_dataset, attribute_name, None)
        if nested_dataset is None:
            continue
        image_ids = _image_ids_from_dataset_metadata(nested_dataset)
        if image_ids is not None:
            return image_ids
    return None


def _split_group_counts(
    *,
    group_count: int,
    fractions: Mapping[str, float],
) -> dict[str, int]:
    raw_counts = {split: fractions[split] * group_count for split in FMD_SPLITS}
    counts = {split: int(np.floor(raw_counts[split])) for split in FMD_SPLITS}
    remaining = group_count - sum(counts.values())
    remainders = sorted(
        FMD_SPLITS,
        key=lambda split: (raw_counts[split] - counts[split], fractions[split]),
        reverse=True,
    )
    for split in remainders[:remaining]:
        counts[split] += 1

    positive_splits = [split for split in FMD_SPLITS if fractions[split] > 0]
    if group_count >= len(positive_splits):
        for split in positive_splits:
            if counts[split] > 0:
                continue
            donor = max(
                (candidate for candidate in positive_splits if counts[candidate] > 1),
                key=lambda candidate: counts[candidate],
            )
            counts[donor] -= 1
            counts[split] += 1
    return counts


def _build_split_summary(records: Sequence[SplitRecord]) -> dict[str, dict[str, object]]:
    summary: dict[str, dict[str, object]] = {}
    for split in FMD_SPLITS:
        split_records = [record for record in records if record["split"] == split]
        stratification_counts = Counter(
            record["stratification_key"] for record in split_records
        )
        summary[split] = {
            "group_count": len({record["group_key"] for record in split_records}),
            "image_count": len(split_records),
            "stratification_breakdown": dict(sorted(stratification_counts.items())),
        }
    return summary


def _validate_split_summary(
    split_summary_object: object,
    records: Sequence[object],
) -> None:
    if not isinstance(split_summary_object, Mapping):
        raise invalid_restoration_contract("split_summary must be a mapping")

    records_by_split = {
        split: [
            cast(Mapping[str, object], record)
            for record in records
            if isinstance(record, Mapping) and record.get("split") == split
        ]
        for split in FMD_SPLITS
    }
    for split in FMD_SPLITS:
        summary_object = split_summary_object.get(split)
        if not isinstance(summary_object, Mapping):
            raise invalid_restoration_contract(f"split_summary missing {split}")
        expected_group_count = len(
            {record["group_key"] for record in records_by_split[split]}
        )
        expected_image_count = len(records_by_split[split])
        if summary_object.get("group_count") != expected_group_count:
            raise invalid_restoration_contract(
                "split_summary mismatch for "
                f"{split} group_count: expected {expected_group_count}, "
                f"found {summary_object.get('group_count')}"
            )
        if summary_object.get("image_count") != expected_image_count:
            raise invalid_restoration_contract(
                "split_summary mismatch for "
                f"{split} image_count: expected {expected_image_count}, "
                f"found {summary_object.get('image_count')}"
            )

        expected_stratification = Counter(
            str(record["stratification_key"]) for record in records_by_split[split]
        )
        if summary_object.get("stratification_breakdown") != dict(
            sorted(expected_stratification.items())
        ):
            raise invalid_restoration_contract(
                "split_summary mismatch for "
                f"{split} stratification_breakdown"
            )
