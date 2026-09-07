from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import torch

from chromatix_next._tensors import _COMPLEX_DTYPE, _REAL_DTYPE

from ._source_lifecycle import (
    _envelope_via_cache,
    _LifecycleSource,
    _read_named_parameter_or_buffer,
)
from .field import (
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    _own_field_value,
    _SourceLineage,
)
from .grid import SpatialGrid
from .medium import Medium
from .polarization import Polarization
from .spectrum import Spectrum


class _SampledWaveSource(_LifecycleSource, ABC):

    """
    收束采样波源共享的合成与缓存机制

    """

    _spectrum_value: Spectrum
    _polarization_value: Polarization
    _medium_value: Medium
    _normalization: FieldNormalization
    _source_lineage: _SourceLineage
    _unit_envelope_cache_key: tuple[Any, ...] | None

    def _register_unit_envelope_cache(self) -> None:
        self.register_buffer("_unit_envelope_cache", None, persistent=False)
        self._unit_envelope_cache_key = None

    def _synthesize_sampled_wave(self, grid: SpatialGrid) -> OpticalField:
        output_grid = grid.to(
            device=self._buffer("wavelengths").device,
            dtype=self._fixed_real_dtype(),
        )
        amplitude = self._amplitude_for(output_grid)
        unit_envelope = self._unit_envelope_for(output_grid)
        envelope = amplitude * unit_envelope
        path_reference = OpticalPathReference(
            lengths=(0.0,) * self._spectrum_value.count,
        )
        return _own_field_value(
            OpticalField(
                envelope=envelope,
                grid=output_grid,
                spectrum=self._spectrum_value,
                polarization_representation=(
                    self._polarization_value.representation
                ),
                medium=self._medium_value,
                normalization=self._normalization,
                path_reference=path_reference,
            ),
            self._source_lineage,
        )

    def _buffer(self, name: str) -> torch.Tensor:
        candidate = self._buffers.get(name)
        assert candidate is not None
        return candidate

    @property
    def _scale_value(self) -> torch.Tensor:
        name = (
            "total_power"
            if self._normalization is FieldNormalization.POWER
            else "relative_amplitude"
        )
        return _read_named_parameter_or_buffer(self, name=name)

    def _unit_envelope_for(self, grid: SpatialGrid) -> torch.Tensor:
        # 具体 Source 仍独占缓存键事实与单位包络方程
        return _envelope_via_cache(
            self,
            cache_key=self._unit_envelope_cache_key_for(grid),
            compute=lambda: self._compute_unit_envelope(grid),
        )

    def _amplitude_for(self, grid: SpatialGrid) -> torch.Tensor:
        self._validate_physical_state()
        if self._normalization is FieldNormalization.POWER:
            return self._power_amplitude(grid)
        return self._scale_value

    def _fixed_real_dtype(self) -> torch.dtype:
        return _REAL_DTYPE

    def _fixed_complex_dtype(self) -> torch.dtype:
        return _COMPLEX_DTYPE

    @abstractmethod
    def _validate_physical_state(self) -> None:
        ...

    @abstractmethod
    def _unit_envelope_cache_key_for(
        self,
        grid: SpatialGrid,
    ) -> tuple[Any, ...]:
        ...

    @abstractmethod
    def _compute_unit_envelope(self, grid: SpatialGrid) -> torch.Tensor:
        # 具体 Source 计算自己的单位包络方程
        ...

    @abstractmethod
    def _power_amplitude(self, grid: SpatialGrid) -> torch.Tensor:
        ...
