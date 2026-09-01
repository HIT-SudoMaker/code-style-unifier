from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
import re

from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash


_SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*\Z")
_IDENTITY_SEGMENT_LIMITS = {
    "study_id": 48,
    "method_id": 48,
    "profile_name": 24,
}
_PLAN_ID_LIMIT = 64
_MAX_REPRODUCIBLE_SEED = 2**32 - 1
_MAX_REPLICATE_ID = 9999
_SLUG_REQUIRED = (
    "{field_name} must be a lowercase ASCII slug with single underscores"
)
_SLUG_LENGTH_REQUIRED = "{field_name} must contain at most {limit} characters"
_SEED_REQUIRED = "seed must be an integer between 0 and 4294967295"
_REPLICATE_REQUIRED = "replicate_id must be an integer between 1 and 9999"
_UPSTREAM_ID_REQUIRED = "upstream_run_ids must contain non-empty strings"
_UNIQUE_UPSTREAM_REQUIRED = "upstream_run_ids must not contain duplicates"
_PLAN_SLUG_REQUIRED = "plan_id must be a lowercase ASCII slug with single underscores"
_PLAN_STUDY_REQUIRED = "experiment plan must include at least one study"
_PLAN_STUDY_TYPE_REQUIRED = "experiment plan studies must be StudyConfig values"
_UNIQUE_RUN_REQUIRED = "experiment plan study run_ids must be unique"
_SHARED_ROOT_REQUIRED = "experiment plan studies must share one project_root"
_CONFIGURATION_MUTATED = "configuration mutated after StudyConfig creation"


@dataclass(frozen=True, slots=True)
class StudyConfig:
    """
    鎻忚堪鍗曟鍥哄畾娴嬮噺鍘熷瓙鐮旂┒杩愯
    """

    study_id: str
    method_id: str
    profile_name: str
    seed: int
    configuration: object
    replicate_id: int = 1
    project_root: Path | str = Path.cwd()
    upstream_run_ids: tuple[str, ...] = ()
    _config_fingerprint: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """
        鏍￠獙鐮旂┒韬唤涓殑鍙瀛楁
        """
        for field_name in ("study_id", "method_id", "profile_name"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or _SLUG_PATTERN.fullmatch(value) is None:
                message = _SLUG_REQUIRED.format(field_name=field_name)
                raise ValueError(message)
            limit = _IDENTITY_SEGMENT_LIMITS[field_name]
            if len(value) > limit:
                message = _SLUG_LENGTH_REQUIRED.format(
                    field_name=field_name,
                    limit=limit,
                )
                raise ValueError(message)
        if (
            not isinstance(self.seed, int)
            or isinstance(self.seed, bool)
            or not 0 <= self.seed <= _MAX_REPRODUCIBLE_SEED
        ):
            raise ValueError(_SEED_REQUIRED)
        if (
            not isinstance(self.replicate_id, int)
            or isinstance(self.replicate_id, bool)
            or not 1 <= self.replicate_id <= _MAX_REPLICATE_ID
        ):
            raise ValueError(_REPLICATE_REQUIRED)
        object.__setattr__(self, "project_root", Path(self.project_root))
        object.__setattr__(self, "upstream_run_ids", tuple(self.upstream_run_ids))
        if any(
            not isinstance(run_id, str) or not run_id
            for run_id in self.upstream_run_ids
        ):
            raise ValueError(_UPSTREAM_ID_REQUIRED)
        if len(set(self.upstream_run_ids)) != len(self.upstream_run_ids):
            raise ValueError(_UNIQUE_UPSTREAM_REQUIRED)
        object.__setattr__(
            self,
            "_config_fingerprint",
            self._compute_config_fingerprint(),
        )

    @property
    def config_fingerprint(self) -> str:
        """
        杩斿洖鍘熷瓙杩愯瀹屾暣閰嶇疆鎸囩汗
        """
        return self._config_fingerprint

    def validate_configuration_unchanged(self) -> None:
        """
        鏍￠獙鐮旂┒閰嶇疆鏈彂鐢熸紓绉?        """
        if self._compute_config_fingerprint() != self._config_fingerprint:
            raise ValueError(_CONFIGURATION_MUTATED)

    def _compute_config_fingerprint(self) -> str:
        return compute_config_hash(
            {
                "study_id": self.study_id,
                "method_id": self.method_id,
                "profile_name": self.profile_name,
                "seed": self.seed,
                "replicate_id": self.replicate_id,
                "upstream_run_ids": self.upstream_run_ids,
                "configuration": self.configuration,
            }
        )

    @property
    def run_id(self) -> str:
        """
        杩斿洖绱у噾涓斿吋瀹?Windows 鐨勮繍琛岃韩浠?        """
        return (
            f"{self.profile_name}_s{self.seed}_r{self.replicate_id}_"
            f"c{self.config_fingerprint[:8]}"
        )


@dataclass(frozen=True, slots=True)
class StudyResult:
    """
    鎻忚堪鍗曟鍘熷瓙鐮旂┒鐨勫彲瑙傚療缁撴灉
    """

    study_id: str
    status: str
    run_id: str
    run_dir: Path
    metrics: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ExperimentPlan:
    """
    姹囬泦鍚屼竴鍙鐜板疄楠屼腑鐨勫師瀛愮爺绌?    """

    plan_id: str
    studies: tuple[StudyConfig, ...]

    def __post_init__(self) -> None:
        """
        鏍￠獙璁″垝韬唤鍜屽師瀛愯繍琛屽敮涓€鎬?        """
        if (
            not isinstance(self.plan_id, str)
            or _SLUG_PATTERN.fullmatch(self.plan_id) is None
        ):
            raise ValueError(_PLAN_SLUG_REQUIRED)
        if len(self.plan_id) > _PLAN_ID_LIMIT:
            message = _SLUG_LENGTH_REQUIRED.format(
                field_name="plan_id",
                limit=_PLAN_ID_LIMIT,
            )
            raise ValueError(message)
        object.__setattr__(self, "studies", tuple(self.studies))
        if not self.studies:
            raise ValueError(_PLAN_STUDY_REQUIRED)
        if any(not isinstance(study, StudyConfig) for study in self.studies):
            raise TypeError(_PLAN_STUDY_TYPE_REQUIRED)
        run_ids = [study.run_id for study in self.studies]
        if len(set(run_ids)) != len(run_ids):
            raise ValueError(_UNIQUE_RUN_REQUIRED)
        project_roots = {study.project_root for study in self.studies}
        if len(project_roots) != 1:
            raise ValueError(_SHARED_ROOT_REQUIRED)


@dataclass(frozen=True, slots=True)
class ExperimentReport:
    """
    姹囬泦鍥哄畾娴嬮噺璁″垝鐨勭被鍨嬪寲鐮旂┒缁撴灉
    """

    plan_id: str
    status: str
    studies: tuple[StudyResult, ...]
    report_dir: Path
    report_json: Path
    summary_md: Path
    skipped_run_ids: tuple[str, ...] = ()
