from __future__ import annotations

from layers import DetectionLayer
import pytest
import torch


def test_detection_layer_returns_raw_intensity_by_default() -> None:
    """
    验证默认返回未归一化光强
    """
    layer = DetectionLayer((2, 2))
    field = torch.tensor(
        [[[[1 + 0j, 2 + 0j], [3 + 0j, 4 + 0j]]]],
        dtype=torch.complex64,
    )

    output = layer(field)
    expected = torch.tensor([[[[1.0, 4.0], [9.0, 16.0]]]])

    assert torch.allclose(output, expected)


def test_detection_layer_defaults_to_single_precision_contract() -> None:
    layer = DetectionLayer((2, 2))
    field = torch.ones(1, 1, 2, 2, dtype=torch.complex64)

    output = layer(field)

    assert output.dtype == torch.float32


def test_detection_layer_rejects_non_contract_complex_dtype() -> None:
    layer = DetectionLayer((2, 2))
    field = torch.ones(1, 1, 2, 2, dtype=torch.complex128)

    with pytest.raises(ValueError, match="complex64"):
        layer(field)


def test_detection_layer_supports_optional_normalization() -> None:
    """
    验证启用归一化时光强按样本最大值缩放
    """
    layer = DetectionLayer((2, 2), is_normalization_enabled=True)
    field = torch.tensor(
        [[[[1 + 0j, 2 + 0j], [3 + 0j, 4 + 0j]]]],
        dtype=torch.complex64,
    )

    output = layer(field)

    assert torch.isclose(output.max(), torch.tensor(1.0))
    assert torch.allclose(output, torch.tensor([[[[0.0625, 0.25], [0.5625, 1.0]]]]))


def test_detection_layer_normalization_handles_zero_intensity_without_nan() -> None:
    """
    验证全零输入归一化后保持有限零值
    """
    layer = DetectionLayer((2, 2), is_normalization_enabled=True)
    field = torch.zeros(1, 1, 2, 2, dtype=torch.complex64)

    output = layer(field)

    assert torch.allclose(output, torch.zeros_like(output))
    assert torch.isfinite(output).all()


def test_detection_layer_extra_repr_reports_configuration() -> None:
    """
    验证 repr 暴露固定探测合同
    """
    layer = DetectionLayer((2, 2))

    assert repr(layer) == (
        "DetectionLayer(array_resolution=(2, 2), "
        "is_normalization_enabled=False)"
    )


def test_detection_layer_rejects_non_complex_input() -> None:
    """
    验证拒绝实数输入张量
    """
    layer = DetectionLayer((2, 2))
    field = torch.ones(1, 1, 2, 2, dtype=torch.float32)

    with pytest.raises(ValueError, match="复数"):
        layer(field)


def test_detection_layer_rejects_non_boolean_normalization_flag() -> None:
    """
    验证拒绝非布尔归一化开关
    """
    with pytest.raises(ValueError, match="is_normalization_enabled"):
        DetectionLayer((2, 2), is_normalization_enabled="yes")


def test_detection_layer_peak_normalization_preserves_weak_signal_scale() -> None:
    layer = DetectionLayer((2, 2), is_normalization_enabled=True)
    field = torch.full((1, 1, 2, 2), 1e-6 + 0j, dtype=torch.complex64)

    output = layer(field)

    assert torch.allclose(output, torch.ones_like(output))


def test_detection_layer_rejects_resolution_mismatch() -> None:
    """
    验证拒绝空间分辨率不匹配的输入
    """
    layer = DetectionLayer((2, 2))
    field = torch.ones(1, 1, 4, 2, dtype=torch.complex64)

    with pytest.raises(ValueError, match="分辨率"):
        layer(field)


def test_detection_layer_rejects_device_mismatch() -> None:
    """
    验证拒绝设备不一致的输入张量
    """
    layer = DetectionLayer((2, 2))
    field = torch.ones(1, 1, 2, 2, dtype=torch.complex64, device="meta")

    with pytest.raises(ValueError, match="同一设备"):
        layer(field)


def test_detection_layer_rejects_invalid_resolution_type() -> None:
    """
    验证拒绝非法分辨率容器类型
    """
    with pytest.raises(ValueError, match="分辨率"):
        DetectionLayer(8)


def test_detection_layer_rejects_non_integer_resolution_values() -> None:
    """
    验证拒绝非整数分辨率取值
    """
    with pytest.raises(ValueError, match="整数"):
        DetectionLayer((8.9, 8.1))


def test_detection_layer_rejects_boolean_resolution_values() -> None:
    """
    验证拒绝布尔分辨率取值
    """
    with pytest.raises(ValueError, match="布尔"):
        DetectionLayer((True, 8))
