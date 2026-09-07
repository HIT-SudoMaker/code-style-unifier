from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import torch
from torch import nn
from torch.nn import functional as F

from experiments.restoration.fixed_measurement.learning.backends._validation import validate_single_channel_image
from experiments.restoration.errors import invalid_restoration_contract


NafNetModelName = Literal["nafnet_s", "nafnet_m"]
# 涓存椂琛ヨ竟鏃跺鍒惰竟缂樺儚绱犮€?
_SPATIAL_PADDING_MODE: str = "replicate"


@dataclass(frozen=True, slots=True)
class NafNetModelSpec:
    """
    鎻忚堪椤圭洰鍐呴儴鐨?NAFNet 瀹归噺瑙勬牸

    S銆丮銆丩 涓夋。鐢ㄤ簬鏈」鐩殑瀹归噺瀵圭収锛屾ā鍧楃粨鏋勪笌 NAFNet 瀵归綈锛?    浣嗕笉琛ㄧず鍘熻鏂囩殑瀹樻柟璁粌閰嶇疆
    """

    width: int
    encoder_blocks: tuple[int, ...]
    middle_blocks: int
    decoder_blocks: tuple[int, ...]


NAFNET_MODEL_SPECS: dict[str, NafNetModelSpec] = {
    "nafnet_s": NafNetModelSpec(
        width=16,
        encoder_blocks=(1, 1, 2, 2),
        middle_blocks=2,
        decoder_blocks=(1, 1, 1, 1),
    ),
    "nafnet_m": NafNetModelSpec(
        width=32,
        encoder_blocks=(1, 2, 2, 4),
        middle_blocks=4,
        decoder_blocks=(1, 1, 2, 2),
    ),
}


class _LayerNorm2d(nn.Module):
    """
    瀵逛簩缁寸壒寰佹墽琛岄€氶亾褰掍竴鍖?    """

    def __init__(self, channels: int, eps: float = 1e-6) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.ones(1, channels, 1, 1))
        self.bias = nn.Parameter(torch.zeros(1, channels, 1, 1))
        self.eps = eps

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        娌块€氶亾缁村綊涓€鍖栧浘鍍忕壒寰?        """
        mean = image.mean(dim=1, keepdim=True)
        variance = (image - mean).pow(2).mean(dim=1, keepdim=True)
        normalized = (image - mean) / torch.sqrt(variance + self.eps)
        return normalized * self.weight + self.bias


class _SimpleGate(nn.Module):
    """
    瀹炵幇 NAFNet 绠€鍗曢棬鎺?    """

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        灏嗘墿灞曠壒寰佺殑涓ょ粍閫氶亾閫愬厓绱犵浉涔?        """
        left, right = image.chunk(2, dim=1)
        return left * right


class _SimplifiedChannelAttention(nn.Module):
    """
    瀹炵幇 NAFNet 绠€鍖栭€氶亾娉ㄦ剰鍔?    """

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.proj = nn.Conv2d(channels, channels, kernel_size=1)

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        灏嗘睜鍖栧緱鍒扮殑閫氶亾鏉冮噸鏂藉姞鍒板浘鍍忕壒寰?        """
        return image * self.proj(self.pool(image))


class _NafBlock(nn.Module):
    """
    瀹炵幇鐢ㄤ簬鍗曞浘鍍忔仮澶嶇殑 NAFNet 瀵归綈妯″潡
    """

    def __init__(self, channels: int, expansion: int = 2, dropout: float = 0.0) -> None:
        super().__init__()
        hidden_channels = channels * expansion
        ffn_channels = channels * expansion
        self.norm1 = _LayerNorm2d(channels)
        self.conv1 = nn.Conv2d(channels, hidden_channels, kernel_size=1)
        self.depthwise = nn.Conv2d(
            hidden_channels,
            hidden_channels,
            kernel_size=3,
            padding=1,
            groups=hidden_channels,
        )
        self.gate = _SimpleGate()
        self.channel_attention = _SimplifiedChannelAttention(hidden_channels // 2)
        self.conv2 = nn.Conv2d(hidden_channels // 2, channels, kernel_size=1)
        self.dropout1 = nn.Dropout2d(dropout) if dropout > 0.0 else nn.Identity()
        self.beta = nn.Parameter(torch.zeros(1, channels, 1, 1))

        self.norm2 = _LayerNorm2d(channels)
        self.conv3 = nn.Conv2d(channels, ffn_channels, kernel_size=1)
        self.conv4 = nn.Conv2d(ffn_channels // 2, channels, kernel_size=1)
        self.dropout2 = nn.Dropout2d(dropout) if dropout > 0.0 else nn.Identity()
        self.gamma = nn.Parameter(torch.zeros(1, channels, 1, 1))

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        瀵瑰浘鍍忕壒寰佹墽琛屼竴涓畫宸?NAFNet 妯″潡
        """
        residual = image
        hidden = self.norm1(image)
        hidden = self.conv1(hidden)
        hidden = self.depthwise(hidden)
        hidden = self.gate(hidden)
        hidden = self.channel_attention(hidden)
        hidden = self.conv2(hidden)
        hidden = self.dropout1(hidden)
        image = residual + hidden * self.beta

        residual = image
        hidden = self.norm2(image)
        hidden = self.conv3(hidden)
        hidden = self.gate(hidden)
        hidden = self.conv4(hidden)
        hidden = self.dropout2(hidden)
        return residual + hidden * self.gamma


class NafNetRestorationBackend(nn.Module):
    """
    瀹炵幇椤圭洰鍘熺敓鐨勫崟閫氶亾 NAFNet 鎭㈠鍚庣
    """

    def __init__(
        self,
        model_name: NafNetModelName = "nafnet_s",
        residual_learning: bool = True,
    ) -> None:
        """
        鏋勫缓鎸囧畾瀹归噺鐨勯」鐩師鐢?NAFNet
        """
        super().__init__()
        if model_name not in NAFNET_MODEL_SPECS:
            allowed = ", ".join(NAFNET_MODEL_SPECS)
            raise invalid_restoration_contract(
                f"model_name must be one of: {allowed}"
            )
        spec = NAFNET_MODEL_SPECS[model_name]
        self.model_name = model_name
        self.spec = spec
        self.residual_learning = residual_learning
        self.intro = nn.Conv2d(1, spec.width, kernel_size=3, padding=1)
        self.ending = nn.Conv2d(spec.width, 1, kernel_size=3, padding=1)

        channels = spec.width
        self.encoders = nn.ModuleList()
        self.downs = nn.ModuleList()
        for block_count in spec.encoder_blocks:
            self.encoders.append(_make_blocks(channels, block_count))
            self.downs.append(nn.Conv2d(channels, channels * 2, kernel_size=2, stride=2))
            channels *= 2

        self.middle = _make_blocks(channels, spec.middle_blocks)

        self.ups = nn.ModuleList()
        self.decoders = nn.ModuleList()
        for block_count in spec.decoder_blocks:
            self.ups.append(
                nn.Sequential(
                    nn.Conv2d(channels, channels * 2, kernel_size=1),
                    nn.PixelShuffle(2),
                )
            )
            channels //= 2
            self.decoders.append(_make_blocks(channels, block_count))

    @property
    def pad_factor(self) -> int:
        """
        杩斿洖缂栫爜鍣ㄦ繁搴﹁姹傜殑绌洪棿鏁撮櫎鍥犲瓙
        """
        return 2 ** len(self.spec.encoder_blocks)

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        鎭㈠鎵归噺鍗曢€氶亾鍥惧儚
        """
        validate_single_channel_image(image)
        original_height, original_width = image.shape[-2:]
        padded = self._pad_to_factor(image)
        restored = self._forward_padded(padded)
        restored = restored[..., :original_height, :original_width]
        if self.residual_learning:
            restored = restored + image
        return torch.clamp(restored, 0.0, 1.0)

    def _forward_padded(self, image: torch.Tensor) -> torch.Tensor:
        hidden = self.intro(image)
        skips: list[torch.Tensor] = []
        for encoder, down in zip(self.encoders, self.downs, strict=True):
            hidden = encoder(hidden)
            skips.append(hidden)
            hidden = down(hidden)
        hidden = self.middle(hidden)
        for decoder, up, skip in zip(
            self.decoders,
            self.ups,
            reversed(skips),
            strict=True,
        ):
            hidden = up(hidden)
            hidden = hidden + skip
            hidden = decoder(hidden)
        return self.ending(hidden)

    def _pad_to_factor(self, image: torch.Tensor) -> torch.Tensor:
        height, width = image.shape[-2:]
        pad_height = (self.pad_factor - height % self.pad_factor) % self.pad_factor
        pad_width = (self.pad_factor - width % self.pad_factor) % self.pad_factor
        if pad_height == 0 and pad_width == 0:
            return image
        return F.pad(image, (0, pad_width, 0, pad_height), mode=_SPATIAL_PADDING_MODE)


def _make_blocks(channels: int, block_count: int) -> nn.Sequential:
    return nn.Sequential(*(_NafBlock(channels) for _ in range(block_count)))
