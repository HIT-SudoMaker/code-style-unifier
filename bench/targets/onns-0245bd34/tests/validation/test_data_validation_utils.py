from __future__ import annotations

import numpy as np
import torch

from experiments.validation.data import data_validation_utils as utils


def test_core_source_names_match_design_spec() -> None:
    """
    验证核心数据源常量与设计spec一致
    """
    assert utils.CORE_SOURCE_NAMES == (
        "mnist",
        "fashion_mnist",
        "fmd",
        "biosr",
        "bbbc038",
        "bbbc039",
        "target_usaf",
        "target_siemens",
        "target_slanted_edge",
        "target_line_pairs",
    )
    assert utils.MICROSCOPY_SOURCE_NAMES == (
        "fmd",
        "biosr",
        "bbbc038",
        "bbbc039",
    )
    assert utils.TARGET_SOURCE_NAMES == (
        "target_usaf",
        "target_siemens",
        "target_slanted_edge",
        "target_line_pairs",
    )
    assert utils.CLASSIFICATION_SOURCE_NAMES == ("mnist", "fashion_mnist")


def test_data_check_uses_pass_fail_status() -> None:
    """
    验证data check helper生成统一PASS/FAIL记录
    """
    passed = utils.data_check("sample_contract", True, detail="ok")
    failed = utils.data_check("sample_contract", False, detail="bad")

    assert passed == {
        "name": "sample_contract",
        "status": "PASS",
        "detail": "ok",
    }
    assert failed == {
        "name": "sample_contract",
        "status": "FAIL",
        "detail": "bad",
    }


def test_data_validation_utils_reexports_validation_aesthetic_helpers() -> None:
    """
    楠岃瘉data validation鍙互浣跨敤缁熶竴validation瀹＄編helper
    """
    assert utils.VALIDATION_PALETTE["primary"] == "#587184"
    assert callable(utils.apply_validation_figure_style)
    assert callable(utils.style_validation_colorbar)


def test_title_from_figure_name_drops_numeric_prefix_and_underscores() -> None:
    """
    验证图文件名转换为无下划线可读图题
    """
    assert (
        utils.title_from_figure_name("01_raw_source_gallery_mnist")
        == "Raw Source Gallery MNIST"
    )
    assert (
        utils.title_from_figure_name("05_psf_convolution_trace")
        == "PSF Convolution Trace"
    )


def test_tensor_image_to_numpy_accepts_chw_tensor() -> None:
    """
    验证CHW tensor会转换为二维float32数组
    """
    image = torch.tensor([[[0.0, 1.0], [0.5, 0.25]]], dtype=torch.float32)

    values = utils.tensor_image_to_numpy(image)

    assert values.shape == (2, 2)
    assert values.dtype == np.float32
    assert np.isclose(values.max(), 1.0)


def test_image_contract_reports_shape_dtype_range_and_finiteness() -> None:
    """
    验证图像契约记录包含shape、dtype、范围和有限性
    """
    image = torch.tensor([[[0.0, 1.0], [0.5, 0.25]]], dtype=torch.float32)

    record = utils.image_contract_record("mnist", image)

    assert record["source"] == "mnist"
    assert record["image_shape"] == "1x2x2"
    assert record["dtype"] == "torch.float32"
    assert record["is_finite"] is True
    assert record["min"] == 0.0
    assert record["max"] == 1.0
