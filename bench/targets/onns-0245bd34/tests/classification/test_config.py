from __future__ import annotations

from pathlib import Path

import pytest

from experiments.classification import config
from experiments.classification import train
from experiments.classification.config import (
    BasicConfig,
    ModelConfig,
    SearchConfig,
    TrainingConfig,
    build_default_training_config,
    resolve_default_epochs,
)
from experiments.classification.model import (
    CLASSIFICATION_FOCAL_LENGTH,
    CLASSIFICATION_PROPAGATION_DISTANCE,
)


def test_build_default_training_config_preserves_training_defaults(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    training_config = build_default_training_config(
        topology="without_lens",
        project_root=tmp_path,
    )

    assert isinstance(training_config, TrainingConfig)
    assert training_config.topology == "without_lens"
    assert training_config.batch_size == 128
    assert training_config.learning_rate == pytest.approx(0.0037)
    assert training_config.weight_decay == pytest.approx(0.0)
    assert training_config.epochs == 50
    assert training_config.device == "cpu"
    assert training_config.seed == 42
    assert training_config.run_name == "default"
    assert training_config.project_root == tmp_path
    assert training_config.resize_mode == "bilinear"
    assert training_config.phase_parameterization == "direct"
    assert training_config.phase_initialization == "uniform"
    assert training_config.propagation_distance == pytest.approx(
        CLASSIFICATION_PROPAGATION_DISTANCE
    )
    assert training_config.focal_length == pytest.approx(CLASSIFICATION_FOCAL_LENGTH)
    assert training_config.samples_per_class is None
    assert training_config.is_scheduler_enabled is False


def test_standard_config_surface_matches_training_defaults(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    basic = BasicConfig(project_root=tmp_path, run_name="standard")
    model = ModelConfig(topology="with_lens")
    training_config = TrainingConfig(
        basic=basic,
        model=model,
        epochs=3,
    ).normalized()

    assert isinstance(training_config, TrainingConfig)
    assert training_config.basic.project_root == tmp_path
    assert training_config.basic.run_name == "standard"
    assert training_config.model.topology == "with_lens"
    assert training_config.topology == "with_lens"
    assert training_config.project_root == tmp_path
    assert training_config.run_name == "standard"
    assert training_config.batch_size == 128
    assert training_config.learning_rate == pytest.approx(0.0037)
    assert training_config.epochs == 3
    assert training_config.to_flat_dict()["topology"] == "with_lens"
    assert training_config.to_flat_dict()["run_name"] == "standard"


def test_search_config_defaults_match_current_optuna_space() -> None:
    """
    验证分类测试契约保持稳定
    """
    search_config = SearchConfig().normalized()

    assert search_config.trials == 10
    assert search_config.trial_epochs == 3
    assert search_config.is_best_retraining_enabled is False
    assert search_config.seed == 42
    assert search_config.samples_per_class is None
    assert search_config.topology_candidates == ("without_lens", "with_lens")
    assert search_config.batch_size_candidates == (128, 200)
    assert search_config.resize_mode_candidates == ("bilinear",)
    assert search_config.learning_rate_range == pytest.approx((5e-4, 5e-3))
    assert search_config.propagation_distance_range == pytest.approx((2e-3, 8e-3))


def test_search_config_normalizes_sequence_fields() -> None:
    """
    验证分类测试契约保持稳定
    """
    search_config = SearchConfig(
        topology_candidates=["without_lens", "with_lens"],
        batch_size_candidates=[128, 200],
        resize_mode_candidates=["nearest", "bilinear"],
        learning_rate_range=[5e-4, 5e-3],
        propagation_distance_range=[2e-3, 8e-3],
    ).normalized()

    assert search_config.topology_candidates == ("without_lens", "with_lens")
    assert search_config.batch_size_candidates == (128, 200)
    assert search_config.resize_mode_candidates == ("nearest", "bilinear")
    assert search_config.learning_rate_range == pytest.approx((5e-4, 5e-3))
    assert search_config.propagation_distance_range == pytest.approx((2e-3, 8e-3))


@pytest.mark.parametrize(
    ("field_name", "value", "match"),
    [
        ("trials", 0, "trials"),
        ("trial_epochs", 0, "trial_epochs"),
        ("seed", -1, "seed"),
        ("samples_per_class", 0, "samples_per_class"),
        ("is_best_retraining_enabled", 1, "is_best_retraining_enabled"),
        ("topology_candidates", [], "topology_candidates"),
        ("topology_candidates", ["nope"], "Unsupported topology"),
        ("topology_candidates", "without_lens", "topology_candidates"),
        ("batch_size_candidates", [], "batch_size_candidates"),
        ("batch_size_candidates", [128, 0], "batch_size_candidates"),
        ("batch_size_candidates", "128", "batch_size_candidates"),
        ("resize_mode_candidates", [], "resize_mode_candidates"),
        ("resize_mode_candidates", ["bicubic"], "resize_mode_candidates"),
        ("resize_mode_candidates", b"bilinear", "resize_mode_candidates"),
        ("learning_rate_range", [5e-4], "learning_rate_range"),
        ("learning_rate_range", [5e-3, 5e-4], "learning_rate_range"),
        ("learning_rate_range", [0.0, 5e-3], "learning_rate_range"),
        ("propagation_distance_range", [2e-3, float("inf")], "propagation_distance_range"),
        ("propagation_distance_range", "2e-3,8e-3", "propagation_distance_range"),
    ],
)
def test_search_config_validate_rejects_invalid_values(
    field_name: str,
    value: object,
    match: str,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    search_config = SearchConfig(**{field_name: value})

    with pytest.raises(ValueError, match=match):
        search_config.validate()


def test_training_config_flat_constructor_builds_composed_config(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    training_config = TrainingConfig(
        topology="with_lens",
        project_root=tmp_path,
        run_name="flat",
        epochs=2,
    ).normalized()

    assert isinstance(training_config.basic, BasicConfig)
    assert isinstance(training_config.model, ModelConfig)
    assert training_config.basic.project_root == tmp_path
    assert training_config.model.topology == "with_lens"
    assert training_config.topology == "with_lens"
    assert training_config.epochs == 2


def test_train_config_normalized_rejects_unsupported_topology(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    with pytest.raises(ValueError, match="Unsupported topology"):
        TrainingConfig(topology="no_lens", project_root=tmp_path).normalized()


@pytest.mark.parametrize(
    "run_name",
    ["", ".", "..", "../victim", r"..\victim"],
)
def test_train_config_validate_rejects_unsafe_run_name(
    tmp_path: Path,
    run_name: str,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    with pytest.raises(ValueError, match="run_name"):
        TrainingConfig(project_root=tmp_path, run_name=run_name).validate()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("batch_size", 0),
        ("epochs", 0),
        ("learning_rate", -1.0),
        ("weight_decay", -1.0),
        ("samples_per_class", 0),
    ],
)
def test_train_config_validate_rejects_invalid_numeric_values(
    tmp_path: Path,
    field_name: str,
    value: object,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    training_config = TrainingConfig(project_root=tmp_path, **{field_name: value})

    with pytest.raises(ValueError, match=field_name):
        training_config.validate()


def test_train_reexports_config_public_surface() -> None:
    """
    验证分类测试契约保持稳定
    """
    assert train.TrainingConfig is config.TrainingConfig
    assert train.BasicConfig is config.BasicConfig
    assert train.ModelConfig is config.ModelConfig
    assert train.SearchConfig is config.SearchConfig
    assert train.resolve_default_epochs is config.resolve_default_epochs
    assert resolve_default_epochs("with_lens") == 50
    assert train.build_default_training_config("with_lens").topology == "with_lens"
    assert not hasattr(train, "build_default_train_config")
    assert not hasattr(train, "TrainConfig")
    assert not hasattr(train, "ClassificationBasicConfig")
    assert not hasattr(train, "ClassificationModelConfig")
    assert not hasattr(train, "ClassificationTrainingConfig")
