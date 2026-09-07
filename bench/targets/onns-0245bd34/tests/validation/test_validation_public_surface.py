from __future__ import annotations

from pathlib import Path


def test_validation_public_surface_names_validation_packages_only() -> None:
    """
    验证 validation 包只公开新架构入口
    """

    import experiments.validation as validation

    assert sorted(validation.__all__) == [
        "ValidationBasicConfig",
        "ValidationRunConfig",
        "data",
        "layers",
        "run_all",
    ]
    assert validation.ValidationBasicConfig.__module__.endswith(".config")
    assert validation.ValidationRunConfig.__module__.endswith(".config")


def test_validation_basic_config_normalized_and_validates(tmp_path: Path) -> None:
    """
    验证基础配置可规范化并接受三类 suite
    """
    from experiments.validation.config import ValidationBasicConfig, ValidationRunConfig

    basic = ValidationBasicConfig(
        output_root=tmp_path,
        device="cpu",
        seed=7,
        size="tiny",
    ).normalized()
    run_config = ValidationRunConfig(
        basic=basic,
        suites=["layers", "data"],
    ).normalized()

    assert basic.output_root == tmp_path
    assert basic.device == "cpu"
    assert basic.seed == 7
    assert basic.size == "tiny"
    assert run_config.suites == ("layers", "data")


def test_validation_config_rejects_invalid_values(tmp_path: Path) -> None:
    """
    验证配置拒绝非法设备、尺寸和 suite
    """
    import pytest

    from experiments.validation.config import ValidationBasicConfig, ValidationRunConfig

    with pytest.raises(ValueError, match="device"):
        ValidationBasicConfig(output_root=tmp_path, device="gpu").validate()
    with pytest.raises(ValueError, match="seed"):
        ValidationBasicConfig(output_root=tmp_path, seed=-1).validate()
    with pytest.raises(ValueError, match="size"):
        ValidationBasicConfig(output_root=tmp_path, size="small").validate()
    with pytest.raises(ValueError, match="suites"):
        ValidationRunConfig(basic=ValidationBasicConfig(output_root=tmp_path), suites=[]).validate()
    with pytest.raises(ValueError, match="suites"):
        ValidationRunConfig(
            basic=ValidationBasicConfig(output_root=tmp_path),
            suites=["layers", "unknown"],
        ).validate()

