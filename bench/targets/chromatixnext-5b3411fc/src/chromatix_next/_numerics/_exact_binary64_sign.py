from __future__ import annotations

import math

import torch

_BINARY64_FRACTION_BITS = 52
_BINARY64_FRACTION_MASK = (1 << _BINARY64_FRACTION_BITS) - 1
_BINARY64_HIDDEN_BIT = 1 << _BINARY64_FRACTION_BITS
_BINARY64_EXPONENT_MASK = 0x7FF
_BINARY64_SUBNORMAL_EXPONENT = -1074
_BINARY64_SIGNIFICAND_EXPONENT_BIAS = 1075

_ACCUMULATOR_LIMB_BITS = 15
_ACCUMULATOR_LIMB_BASE = 1 << _ACCUMULATOR_LIMB_BITS
_ACCUMULATOR_LIMB_MASK = _ACCUMULATOR_LIMB_BASE - 1
_ACCUMULATOR_LIMB_COUNT = 424
_MINIMUM_MONOMIAL_EXPONENT = -3222
_MAXIMUM_EXTENDED_MONOMIAL_DEGREE = 7
_SIGNIFICAND_LIMB_SHIFTS = (0, 15, 30, 45)
_EXACT_LANE_CHUNK_SIZE = 512
_ALLOWED_COEFFICIENTS = frozenset((-4, -1, 1))
_META_ACCUMULATOR_EQUIVALENT_COUNT = 8

_ExactMonomial = tuple[int, tuple[torch.Tensor, ...]]


def _meta_exact_sign_with_conservative_workspace(
    *,
    lane_count: int,
    batch_shape: tuple[int, ...],
    maximum_monomial_degree: int,
    accumulator_limb_count: int,
    device: torch.device,
) -> torch.Tensor:
    # Meta 不求值，但按真实核心的同时存活上界建立结构工作集，供 Workstation 保守计量
    if lane_count == 0:
        empty_batch_workspace = torch.empty(
            (1,),
            dtype=torch.int64,
            device=device,
        )
        structural_sign = torch.empty(
            batch_shape,
            dtype=torch.int8,
            device=device,
        )
        del empty_batch_workspace
        return structural_sign
    chunk_lane_count = min(lane_count, _EXACT_LANE_CHUNK_SIZE)
    accumulator_equivalents = tuple(
        torch.empty(
            (chunk_lane_count, accumulator_limb_count),
            dtype=torch.int64,
            device=device,
        )
        for _ in range(_META_ACCUMULATOR_EQUIVALENT_COUNT)
    )
    expanded_factor_envelopes = tuple(
        torch.empty(
            (lane_count,),
            dtype=torch.int64,
            device=device,
        )
        for _ in range(maximum_monomial_degree)
    )
    chunk_count = math.ceil(lane_count / _EXACT_LANE_CHUNK_SIZE)
    retained_chunk_signs = torch.empty(
        (chunk_count, _EXACT_LANE_CHUNK_SIZE),
        dtype=torch.int8,
        device=device,
    )
    structural_sign = torch.empty(
        batch_shape,
        dtype=torch.int8,
        device=device,
    )
    del accumulator_equivalents, expanded_factor_envelopes, retained_chunk_signs
    return structural_sign


def _decode_binary64(
    values: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    bit_patterns = values.contiguous().view(torch.int64)
    encoded_exponents = (
        bit_patterns >> _BINARY64_FRACTION_BITS
    ) & _BINARY64_EXPONENT_MASK
    fraction_bits = bit_patterns & _BINARY64_FRACTION_MASK
    significands = torch.where(
        encoded_exponents == 0,
        fraction_bits,
        fraction_bits | _BINARY64_HIDDEN_BIT,
    )
    binary_exponents = torch.where(
        encoded_exponents == 0,
        torch.full_like(
            encoded_exponents,
            _BINARY64_SUBNORMAL_EXPONENT,
        ),
        encoded_exponents - _BINARY64_SIGNIFICAND_EXPONENT_BIAS,
    )
    positive_signs = torch.ones_like(bit_patterns)
    value_signs = torch.where(
        bit_patterns < 0,
        -positive_signs,
        positive_signs,
    )
    value_signs = torch.where(
        significands == 0,
        torch.zeros_like(value_signs),
        value_signs,
    )
    significand_limbs = torch.stack(
        tuple(
            (significands >> shift) & _ACCUMULATOR_LIMB_MASK
            for shift in _SIGNIFICAND_LIMB_SHIFTS
        ),
        dim=-1,
    )
    return value_signs, binary_exponents, significand_limbs


def _normalize_base_limbs(limbs: torch.Tensor) -> torch.Tensor:
    normalized_limbs = limbs.clone()
    for limb_index in range(normalized_limbs.shape[-1] - 1):
        carries = torch.div(
            normalized_limbs[:, limb_index],
            _ACCUMULATOR_LIMB_BASE,
            rounding_mode="floor",
        )
        normalized_limbs[:, limb_index] = torch.remainder(
            normalized_limbs[:, limb_index],
            _ACCUMULATOR_LIMB_BASE,
        )
        normalized_limbs[:, limb_index + 1] += carries
    return normalized_limbs


def _multiply_significand_limbs(
    factor_limbs: tuple[torch.Tensor, ...],
) -> torch.Tensor:
    if not factor_limbs:
        raise AssertionError("exact binary64 monomial contract", "empty factors")
    reference_factor_limbs = factor_limbs[0]
    if len(factor_limbs) > 3:
        return _multiply_extended_significand_limbs(factor_limbs)
    lane_count = reference_factor_limbs.shape[0]
    product_limbs = torch.ones(
        (lane_count, 1),
        dtype=torch.int64,
        device=reference_factor_limbs.device,
    )
    for current_factor_limbs in factor_limbs:
        convolved_limbs = torch.zeros(
            (lane_count, product_limbs.shape[-1] + 3),
            dtype=torch.int64,
            device=product_limbs.device,
        )
        for product_index in range(product_limbs.shape[-1]):
            for factor_index in range(len(_SIGNIFICAND_LIMB_SHIFTS)):
                convolved_limbs[:, product_index + factor_index] += (
                    product_limbs[:, product_index]
                    * current_factor_limbs[:, factor_index]
                )
        product_limbs = convolved_limbs
    carry_padding = torch.zeros(
        (lane_count, 2),
        dtype=torch.int64,
        device=product_limbs.device,
    )
    return _normalize_base_limbs(
        torch.cat((product_limbs, carry_padding), dim=-1)
    )


def _multiply_extended_significand_limbs(
    factor_limbs: tuple[torch.Tensor, ...],
) -> torch.Tensor:
    lane_count = factor_limbs[0].shape[0]
    product_limbs = torch.ones(
        (lane_count, 1),
        dtype=torch.int64,
        device=factor_limbs[0].device,
    )
    for factor_count, current_factor_limbs in enumerate(factor_limbs, start=1):
        product_limb_count = math.ceil(
            factor_count * (_BINARY64_FRACTION_BITS + 1)
            / _ACCUMULATOR_LIMB_BITS
        ) + 2
        convolved_limbs = torch.zeros(
            (lane_count, product_limb_count),
            dtype=torch.int64,
            device=product_limbs.device,
        )
        for product_index in range(product_limbs.shape[-1]):
            for factor_index in range(len(_SIGNIFICAND_LIMB_SHIFTS)):
                destination_index = product_index + factor_index
                if destination_index >= product_limb_count:
                    continue
                convolved_limbs[:, destination_index] += (
                    product_limbs[:, product_index]
                    * current_factor_limbs[:, factor_index]
                )
        product_limbs = _normalize_base_limbs(convolved_limbs)
    return product_limbs


def _exact_accumulator_layout(maximum_monomial_degree: int) -> tuple[int, int]:
    if maximum_monomial_degree <= 3:
        return _MINIMUM_MONOMIAL_EXPONENT, _ACCUMULATOR_LIMB_COUNT
    minimum_monomial_exponent = (
        _BINARY64_SUBNORMAL_EXPONENT * maximum_monomial_degree
    )
    accumulator_limb_count = math.ceil(
        (
            maximum_monomial_degree
            * (971 - _BINARY64_SUBNORMAL_EXPONENT)
        )
        / _ACCUMULATOR_LIMB_BITS
    ) + 32
    return minimum_monomial_exponent, accumulator_limb_count


def _accumulate_monomial(
    *,
    coefficient: int,
    factors: tuple[torch.Tensor, ...],
    positive_accumulator: torch.Tensor,
    negative_accumulator: torch.Tensor,
    minimum_monomial_exponent: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    lane_count = positive_accumulator.shape[0]
    device = positive_accumulator.device
    coefficient_sign = 1 if coefficient > 0 else -1
    coefficient_exponent_shift = 2 if abs(coefficient) == 4 else 0
    monomial_signs = torch.full(
        (lane_count,),
        coefficient_sign,
        dtype=torch.int64,
        device=device,
    )
    monomial_exponents = torch.full(
        (lane_count,),
        coefficient_exponent_shift,
        dtype=torch.int64,
        device=device,
    )
    decoded_factor_limbs: list[torch.Tensor] = []
    for factor in factors:
        factor_signs, factor_exponents, factor_limbs = _decode_binary64(factor)
        monomial_signs *= factor_signs
        monomial_exponents += factor_exponents
        decoded_factor_limbs.append(factor_limbs)

    product_limbs = _multiply_significand_limbs(tuple(decoded_factor_limbs))
    exponent_offsets = monomial_exponents - minimum_monomial_exponent
    starting_limb_indices = torch.div(
        exponent_offsets,
        _ACCUMULATOR_LIMB_BITS,
        rounding_mode="floor",
    )
    intra_limb_shifts = torch.remainder(
        exponent_offsets,
        _ACCUMULATOR_LIMB_BITS,
    )
    shifted_product_limbs = _normalize_base_limbs(
        product_limbs << intra_limb_shifts.unsqueeze(-1)
    )
    destination_indices = starting_limb_indices.unsqueeze(-1) + torch.arange(
        shifted_product_limbs.shape[-1],
        dtype=torch.int64,
        device=device,
    )
    zero_product_limbs = torch.zeros_like(shifted_product_limbs)
    positive_accumulator.scatter_add_(
        -1,
        destination_indices,
        torch.where(
            monomial_signs.unsqueeze(-1) > 0,
            shifted_product_limbs,
            zero_product_limbs,
        ),
    )
    negative_accumulator.scatter_add_(
        -1,
        destination_indices,
        torch.where(
            monomial_signs.unsqueeze(-1) < 0,
            shifted_product_limbs,
            zero_product_limbs,
        ),
    )
    return (
        _normalize_base_limbs(positive_accumulator),
        _normalize_base_limbs(negative_accumulator),
    )


def _compare_accumulators(
    positive_accumulator: torch.Tensor,
    negative_accumulator: torch.Tensor,
) -> torch.Tensor:
    limb_differences = positive_accumulator - negative_accumulator
    has_difference = limb_differences != 0
    reversed_first_indices = torch.argmax(
        has_difference.flip(-1).to(torch.int64),
        dim=-1,
    )
    highest_different_indices = (
        limb_differences.shape[-1] - 1 - reversed_first_indices
    )
    highest_differences = torch.gather(
        limb_differences,
        -1,
        highest_different_indices.unsqueeze(-1),
    ).squeeze(-1)
    return torch.where(
        has_difference.any(dim=-1),
        torch.sign(highest_differences),
        torch.zeros_like(highest_differences),
    ).to(torch.int8)


def _exact_binary64_monomial_sum_sign(
    monomials: tuple[_ExactMonomial, ...],
    batch_shape: tuple[int, ...],
) -> torch.Tensor:
    if not monomials:
        raise AssertionError("exact binary64 monomial contract", "empty monomials")
    if any(type(dimension) is not int or dimension < 0 for dimension in batch_shape):
        raise AssertionError("exact binary64 monomial contract", "invalid batch shape")
    validated_factors: list[torch.Tensor] = []
    maximum_monomial_degree = 0
    for coefficient, factors in monomials:
        if coefficient not in _ALLOWED_COEFFICIENTS:
            raise AssertionError(
                "exact binary64 monomial contract",
                "invalid coefficient",
            )
        if not 2 <= len(factors) <= _MAXIMUM_EXTENDED_MONOMIAL_DEGREE:
            raise AssertionError(
                "exact binary64 monomial contract",
                "invalid degree",
            )
        maximum_monomial_degree = max(maximum_monomial_degree, len(factors))
        validated_factors.extend(factors)
    reference_device = validated_factors[0].device
    for factor in validated_factors:
        if factor.device != reference_device:
            raise AssertionError(
                "exact binary64 monomial contract",
                "mixed devices",
            )
        try:
            expanded_shape = torch.broadcast_shapes(tuple(factor.shape), batch_shape)
        except RuntimeError as error:
            raise AssertionError(
                "exact binary64 monomial contract",
                "incompatible shape",
            ) from error
        if expanded_shape != batch_shape:
            raise AssertionError(
                "exact binary64 monomial contract",
                "unexpected broadcast shape",
            )
    lane_count = math.prod(batch_shape) if batch_shape else 1
    minimum_monomial_exponent, accumulator_limb_count = (
        _exact_accumulator_layout(maximum_monomial_degree)
    )
    if reference_device.type == "meta":
        return _meta_exact_sign_with_conservative_workspace(
            lane_count=lane_count,
            batch_shape=batch_shape,
            maximum_monomial_degree=maximum_monomial_degree,
            accumulator_limb_count=accumulator_limb_count,
            device=reference_device,
        )
    if any(factor.dtype is not torch.float64 for factor in validated_factors):
        raise AssertionError("exact binary64 monomial contract", "non-binary64 factor")
    if lane_count == 0:
        return torch.empty(batch_shape, dtype=torch.int8, device=reference_device)
    chunk_signs: list[torch.Tensor] = []
    for chunk_start in range(0, lane_count, _EXACT_LANE_CHUNK_SIZE):
        chunk_stop = min(chunk_start + _EXACT_LANE_CHUNK_SIZE, lane_count)
        chunk_lane_count = chunk_stop - chunk_start
        positive_accumulator = torch.zeros(
            (chunk_lane_count, accumulator_limb_count),
            dtype=torch.int64,
            device=reference_device,
        )
        negative_accumulator = torch.zeros_like(positive_accumulator)
        for coefficient, factors in monomials:
            chunk_factors = tuple(
                factor.expand(batch_shape).reshape(-1)[chunk_start:chunk_stop]
                for factor in factors
            )
            positive_accumulator, negative_accumulator = _accumulate_monomial(
                coefficient=coefficient,
                factors=chunk_factors,
                positive_accumulator=positive_accumulator,
                negative_accumulator=negative_accumulator,
                minimum_monomial_exponent=minimum_monomial_exponent,
            )
        chunk_signs.append(
            _compare_accumulators(positive_accumulator, negative_accumulator)
        )
    return torch.cat(chunk_signs).reshape(batch_shape)
