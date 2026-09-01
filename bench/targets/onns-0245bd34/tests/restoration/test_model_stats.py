from __future__ import annotations

import math

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from experiments.restoration.fixed_measurement.learning.backend import BackendConfig, build_restoration_backend
from experiments.restoration.fixed_measurement.learning.model_stats import (
    count_conv2d_macs,
    count_model_macs,
    count_trainable_parameters,
    fft2_macs,
    measure_forward_seconds,
)


class _TinyModel(nn.Module):
    def __init__(self) -> None:
        """
        鏋勫缓鍗曞眰鍗风Н娴嬭瘯妯″瀷
        """
        super().__init__()
        self.layer = nn.Conv2d(1, 2, kernel_size=3, padding=1)

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        鎵ц寰瀷鍗风Н灞?        """
        return self.layer(image)


class _TwoLayerModel(nn.Module):
    def __init__(self) -> None:
        """
        鏋勫缓璁粌鐘舵€佺嫭绔嬬殑鍙屽眰妯″瀷
        """
        super().__init__()
        self.first = nn.Conv2d(1, 1, kernel_size=1)
        self.second = nn.Conv2d(1, 1, kernel_size=1)

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        渚濇鎵ц涓や釜鍗风Н灞?        """
        return self.second(self.first(image))


class _RaisingModel(nn.Module):
    def __init__(self) -> None:
        """
        鏋勫缓鍗风Н鍚庢姏鍑哄紓甯哥殑妯″瀷
        """
        super().__init__()
        self.layer = nn.Conv2d(1, 1, kernel_size=1)
        self.forward_calls = 0

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        璁板綍鍓嶅悜娆℃暟鍚庢姏鍑哄紓甯?        """
        self.forward_calls += 1
        self.layer(image)
        raise RuntimeError("boom")


def test_count_trainable_parameters() -> None:
    """
    楠岃瘉鍙缁冨弬鏁扮粺璁″寘鍚潈閲嶄笌鍋忕疆
    """
    model = _TinyModel()

    assert count_trainable_parameters(model) == 20


def test_count_conv2d_macs() -> None:
    """
    楠岃瘉鏍囧噯鍗风Н鐨勪箻鍔犳鏁?    """
    model = _TinyModel()
    image = torch.ones(1, 1, 16, 16)

    assert count_conv2d_macs(model, image) == 4608


def test_count_conv2d_macs_handles_depthwise_groups() -> None:
    """
    楠岃瘉涔樺姞缁熻鑰冭檻閫愰€氶亾鍒嗙粍
    """
    model = nn.Conv2d(4, 4, kernel_size=3, padding=1, groups=4)
    image = torch.ones(1, 4, 8, 8)

    assert count_conv2d_macs(model, image) == 2304


def test_count_conv2d_macs_restores_mixed_training_modes_after_success() -> None:
    """
    楠岃瘉涔樺姞缁熻鍚庢仮澶嶆贩鍚堣缁冪姸鎬?    """
    model = _TwoLayerModel()
    model.train()
    model.second.eval()

    count_conv2d_macs(model, torch.ones(1, 1, 4, 4))

    assert model.training is True
    assert model.first.training is True
    assert model.second.training is False


def test_count_conv2d_macs_restores_modes_and_hooks_after_forward_raises() -> None:
    """
    楠岃瘉涔樺姞缁熻寮傚父鍚庢仮澶嶇姸鎬佸苟娓呯悊閽╁瓙
    """
    model = _RaisingModel()
    model.train()
    model.layer.eval()

    with pytest.raises(RuntimeError, match="boom"):
        count_conv2d_macs(model, torch.ones(1, 1, 4, 4))
    with pytest.raises(RuntimeError, match="boom"):
        count_conv2d_macs(model, torch.ones(1, 1, 4, 4))

    assert model.training is True
    assert model.layer.training is False
    assert model.forward_calls == 2
    assert model.layer._forward_hooks == {}


def test_measure_forward_seconds_returns_nonnegative_value() -> None:
    """
    楠岃瘉鍓嶅悜鑰楁椂闈炶礋
    """
    model = _TinyModel()
    image = torch.ones(1, 1, 16, 16)

    seconds = measure_forward_seconds(model, image, warmup_steps=1, timed_steps=2)

    assert seconds >= 0.0


def test_measure_forward_seconds_rejects_invalid_step_counts() -> None:
    """
    楠岃瘉鍓嶅悜璁℃椂鎷掔粷闈炴硶姝ユ暟
    """
    model = _TinyModel()
    image = torch.ones(1, 1, 16, 16)

    with pytest.raises(ValueError, match="warmup_steps must be nonnegative"):
        measure_forward_seconds(model, image, warmup_steps=-1)
    with pytest.raises(ValueError, match="timed_steps must be positive"):
        measure_forward_seconds(model, image, timed_steps=0)


def test_measure_forward_seconds_restores_mixed_training_modes() -> None:
    """
    楠岃瘉鍓嶅悜璁℃椂鍚庢仮澶嶆贩鍚堣缁冪姸鎬?    """
    model = _TwoLayerModel()
    model.train()
    model.second.eval()

    measure_forward_seconds(model, torch.ones(1, 1, 4, 4), warmup_steps=0, timed_steps=1)

    assert model.training is True
    assert model.first.training is True
    assert model.second.training is False


def test_fft2_macs_matches_radix2_estimate() -> None:
    """
    楠岃瘉浜岀淮蹇€熷倕閲屽彾涔樺姞浼拌
    """
    height, width = 8, 8
    expected = (height * width // 2) * (int(math.log2(height)) + int(math.log2(width)))
    assert fft2_macs(height, width) == expected


class _SpectralStub(nn.Module):
    def __init__(self) -> None:
        """
        鏋勫缓甯﹂璋辨垚鏈帴鍙ｇ殑鍗风Н鏇胯韩
        """
        super().__init__()
        self.conv = nn.Conv2d(1, 1, kernel_size=1)

    def spectral_macs(self, input_shape: tuple[int, ...]) -> int:
        """
        杩斿洖杈撳叆褰㈢姸瀵瑰簲鐨勯璋变箻鍔犳鏁?        """
        _, _, height, width = input_shape
        return fft2_macs(height, width)

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        鎵ц鏇胯韩鍗风Н
        """
        return self.conv(image)


def test_count_model_macs_includes_spectral_and_conv() -> None:
    """
    楠岃瘉妯″瀷鎬绘垚鏈寘鍚嵎绉笌棰戣氨椤?    """
    model = _SpectralStub()
    example = torch.rand(1, 1, 8, 8)
    total = count_model_macs(model, example)
    conv_macs = 8 * 8  # 1x1 conv, 1->1, 64 output elements * 1 mac
    assert total == conv_macs + fft2_macs(8, 8)


class _NestedSpectral(nn.Module):
    def __init__(self) -> None:
        """
        鏋勫缓宓屽棰戣氨妯″潡
        """
        super().__init__()
        self.conv = nn.Conv2d(1, 1, kernel_size=1)

    def spectral_macs(self, input_shape: tuple[int, ...]) -> int:
        """
        杩斿洖瀹為檯瀛愭ā鍧楄緭鍏ョ殑棰戣氨鎴愭湰
        """
        _, _, height, width = input_shape
        return fft2_macs(height, width)

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        鎵ц宓屽鍗风Н
        """
        return self.conv(image)


class _DownsamplingOuter(nn.Module):
    def __init__(self) -> None:
        """
        鏋勫缓鍏堥檷閲囨牱鍐嶈绠楅璋辩殑澶栧眰妯″潡
        """
        super().__init__()
        self.spectral = _NestedSpectral()

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        灏嗙┖闂村昂瀵稿噺鍗婂悗鎵ц棰戣氨瀛愭ā鍧?        """
        downsampled = F.avg_pool2d(image, 2)
        return self.spectral(downsampled)


def test_count_model_macs_uses_hook_captured_shape_not_top_level() -> None:
    """
    楠岃瘉棰戣氨鎴愭湰閲囩敤閽╁瓙鎹曡幏鐨勫疄闄呰緭鍏ュ舰鐘?    """
    model = _DownsamplingOuter()
    example = torch.rand(1, 1, 16, 16)
    total = count_model_macs(model, example)
    conv_macs = 8 * 8  # 1x1 conv on the 8x8 downsampled feature map
    # The nested submodule sees an 8x8 tensor, so its spectral cost must reflect that.
    assert fft2_macs(16, 16) != fft2_macs(8, 8)
    assert total == conv_macs + fft2_macs(8, 8)
    assert total != conv_macs + fft2_macs(16, 16)


def _build_nafnet_fixture() -> nn.Module:
    """
    鏋勫缓鐪熷疄 NAFNet-S 鍚庣浣滀负鏁堢巼搴﹂噺澶瑰叿

    澶嶇敤椤圭洰鏃㈡湁鐨?NAFNet 鏋勫缓璺緞(build_restoration_backend),涓嶅彟璧峰す鍏?
    NAFNet 鏃?.spectral_macs() 妯″潡,鏁呭叾鎬绘垚鏈?== conv-only(鏁板€间笉鍙橀噺)銆?    """
    return build_restoration_backend(BackendConfig(model_name="nafnet_s"))


def _build_spectral_module_fixture() -> nn.Module:
    """
    鏋勫缓甯﹂璋辨垚鏈帴鍙ｇ殑妯″潡澶瑰叿

    澶嶇敤鏈枃浠跺凡瀹氫箟鐨?_SpectralStub(conv 1x1 + fft2 璋辨垚鏈?,
    鐢ㄤ簬鏂█鍚氨椤规椂鎬绘垚鏈弗鏍煎ぇ浜?conv-only銆?    """
    return _SpectralStub()


def _example_input_for(model: nn.Module) -> torch.Tensor:
    """
    杩斿洖鍖归厤妯″瀷鐨勫崟閫氶亾绀轰緥杈撳叆寮犻噺

    涓や釜澶瑰叿(NAFNet 鍚庣 / 璋辨ā鍧?鍧囦负鍗曢€氶亾,32x32 鍚屾椂婊¤冻:
    NAFNet 鐨?pad_factor 鏁撮櫎瑕佹眰 涓?fft2_macs 鐨?2 鐨勫箓瑕佹眰銆?    """
    return torch.rand(1, 1, 32, 32)


def test_count_model_macs_equals_conv_when_no_spectral() -> None:
    """
    楠岃瘉鏃犻璋辨ā鍧楁椂鎬绘垚鏈瓑浜庡嵎绉垚鏈?    """
    model = _build_nafnet_fixture()
    example = _example_input_for(model)

    assert count_model_macs(model, example) == count_conv2d_macs(model, example)


def test_count_model_macs_includes_spectral() -> None:
    """
    楠岃瘉棰戣氨妯″潡浣挎€绘垚鏈珮浜庡嵎绉垚鏈?    """
    model = _build_spectral_module_fixture()
    example = _example_input_for(model)

    assert count_model_macs(model, example) > count_conv2d_macs(model, example)
