from __future__ import annotations

from collections.abc import Callable
import copy
from typing import Any, NamedTuple, TypeVar, cast

import torch

import chromatix_next.errors as _errors

from .field import _SourceLineage
from .polarization import Polarization, PolarizationRepresentation
from .spectrum import Spectrum

_SourceT = TypeVar("_SourceT", bound="_LifecycleSource")

_ENVELOPE_CACHE_BUFFER_NAME = "_unit_envelope_cache"

_ENVELOPE_CACHE_KEY_ATTR = "_unit_envelope_cache_key"

_PHYSICAL_BUFFER_MISMATCH_MESSAGE = (
    "载入的物理缓冲数值与附加状态记录的不一致，状态字典已经损坏"
)



class _SourceStatePlan(NamedTuple):

    """
    描述源状态安装的物理值与缓存失效计划

    """

    spectrum: Spectrum
    polarization: Polarization
    buffer_shapes: tuple[tuple[str, torch.Size], ...]
    invalidate_envelope_cache: bool


def _commit_source_state_plan(
    module: "_LifecycleSource",
    plan: _SourceStatePlan,
) -> None:
    module.__dict__["_spectrum_value"] = plan.spectrum
    module.__dict__["_polarization_value"] = plan.polarization
    if plan.invalidate_envelope_cache:
        _clear_envelope_cache(module)


def _register_named_physical_state(
    module: torch.nn.Module,
    *,
    spectrum: Spectrum,
    polarization: Polarization,
) -> None:
    module.register_buffer(
        "wavelengths",
        torch.tensor(spectrum.wavelengths, dtype=torch.float64),
    )
    module.register_buffer(
        "spectral_weights",
        torch.tensor(spectrum.weights, dtype=torch.float64),
    )
    module.register_buffer(
        "polarization_state",
        torch.tensor(polarization.components, dtype=torch.complex128),
    )


def _read_named_parameter_or_buffer(
    module: torch.nn.Module,
    *,
    name: str,
) -> torch.Tensor:
    candidate = module._parameters.get(name)
    if candidate is None:
        candidate = module._buffers.get(name)
    assert candidate is not None
    return candidate


def _encode_spectrum_block(spectrum: Spectrum) -> dict[str, object]:
    return {
        "wavelengths": spectrum.wavelengths,
        "weights": spectrum.weights,
    }


def _encode_polarization_block(polarization: Polarization) -> dict[str, object]:
    return {
        "representation": polarization.representation.value,
        "components": tuple(
            (float(component.real), float(component.imag))
            for component in polarization.components
        ),
    }


def _encode_source_identity_fields(
    *,
    spectrum: Spectrum,
    polarization: Polarization,
    medium_identity: tuple[Any, ...],
) -> dict[str, object]:
    return {
        "spectrum": _encode_spectrum_block(spectrum),
        "polarization": _encode_polarization_block(polarization),
        "medium_identity": medium_identity,
    }


def _decode_spectrum_block(payload: dict[str, object]) -> Spectrum:
    return Spectrum(
        wavelengths=cast(tuple[float, ...], payload["wavelengths"]),
        weights=cast(tuple[float, ...], payload["weights"]),
    )


def _decode_polarization_block(payload: dict[str, object]) -> Polarization:
    representation = PolarizationRepresentation(
        cast(str, payload["representation"]),
    )
    components = tuple(
        complex(float(real), float(imaginary))
        for real, imaginary in cast(
            tuple[tuple[float, float], ...],
            payload["components"],
        )
    )
    return Polarization._restore_normalized_state(
        representation=representation,
        components=components,
    )


def _decode_wave_extra_state_fields(
    payload: dict[str, object],
) -> tuple[Spectrum, Polarization, tuple[Any, ...], str]:
    spectrum = _decode_spectrum_block(cast(dict[str, object], payload["spectrum"]))
    polarization = _decode_polarization_block(
        cast(dict[str, object], payload["polarization"]),
    )
    medium_identity = cast(tuple[Any, ...], payload["medium_identity"])
    normalization = cast(str, payload["normalization"])
    return spectrum, polarization, medium_identity, normalization


def _validate_source_physical_buffer_projection(
    *,
    spectrum: Spectrum,
    polarization: Polarization,
    wavelengths: torch.Tensor,
    spectral_weights: torch.Tensor,
    polarization_state: torch.Tensor,
    error_identity: str,
) -> None:
    expected_wavelengths = torch.tensor(
        spectrum.wavelengths,
        dtype=wavelengths.dtype,
        device=wavelengths.device,
    )
    expected_weights = torch.tensor(
        spectrum.weights,
        dtype=spectral_weights.dtype,
        device=spectral_weights.device,
    )
    expected_polarization_state = torch.tensor(
        polarization.components,
        dtype=polarization_state.dtype,
        device=polarization_state.device,
    )
    tolerance = 8.0 * torch.finfo(torch.float64).eps
    if (
        not torch.equal(wavelengths, expected_wavelengths)
        or not torch.equal(spectral_weights, expected_weights)
        or tuple(polarization_state.shape)
        != tuple(expected_polarization_state.shape)
        or not torch.allclose(
            polarization_state,
            expected_polarization_state,
            rtol=tolerance,
            atol=tolerance,
        )
    ):
        raise _errors.OpticalRuntimeError(
            error_identity,
            _PHYSICAL_BUFFER_MISMATCH_MESSAGE,
        )


def _read_envelope_cache(module: torch.nn.Module) -> torch.Tensor | None:
    # 派生偏振单位包络缓存张量（可能尚未计算）。非持久化 Buffer
    return module._buffers.get(_ENVELOPE_CACHE_BUFFER_NAME)


def _envelope_via_cache(
    module: torch.nn.Module,
    *,
    cache_key: tuple[Any, ...],
    compute: Callable[[], torch.Tensor],
) -> torch.Tensor:
    cache = _read_envelope_cache(module)
    existing_key: tuple[Any, ...] | None = getattr(
        module,
        _ENVELOPE_CACHE_KEY_ATTR,
        None,
    )
    if cache is not None and existing_key == cache_key:
        return cache
    envelope = compute()
    module._buffers[_ENVELOPE_CACHE_BUFFER_NAME] = envelope
    setattr(module, _ENVELOPE_CACHE_KEY_ATTR, cache_key)
    return envelope


def _clear_envelope_cache(module: torch.nn.Module) -> None:
    # 状态恢复后清除派生单位包络缓存
    module._buffers[_ENVELOPE_CACHE_BUFFER_NAME] = None
    setattr(module, _ENVELOPE_CACHE_KEY_ATTR, None)


def _shallow_copy_with_fresh_lineage(source: _SourceT) -> _SourceT:
    result = type(source).__new__(type(source))
    result.__dict__ = source.__dict__.copy()
    result.__dict__["_source_lineage"] = _SourceLineage()
    return result


def _deep_copy_with_fresh_lineage(
    source: _SourceT,
    memo: dict[int, object],
) -> _SourceT:
    # 深复制使用独立 Source Lineage
    result = type(source).__new__(type(source))
    memo[id(source)] = result
    result.__dict__ = {
        name: copy.deepcopy(value, memo)
        for name, value in source.__dict__.items()
    }
    result.__dict__["_source_lineage"] = _SourceLineage()
    return result


class _LifecycleSource(torch.nn.Module):

    """
    声明参与源状态生命周期的最小内部协议

    """

    def get_extra_state(self) -> dict[str, object]:
        """
        返回由 Source capsule 编码的完整命名物理载荷

        """
        encoder: Callable[["_LifecycleSource"], dict[str, object]] = getattr(
            type(self),
            "_encode_extra_state_payload",
        )
        return encoder(self)

    def set_extra_state(self, state: object) -> None:
        """
        经 Source capsule 的纯规划函数校验附加状态后，由通用机制 commit

        """
        planner: Callable[..., _SourceStatePlan] = getattr(
            type(self),
            "_plan_state_installation",
        )
        plan = planner(self, state)
        _commit_source_state_plan(self, plan)

    def __copy__(self) -> "_LifecycleSource":

        return _shallow_copy_with_fresh_lineage(self)

    def __deepcopy__(
        self,
        memo: dict[int, object],
    ) -> "_LifecycleSource":

        return _deep_copy_with_fresh_lineage(self, memo)
