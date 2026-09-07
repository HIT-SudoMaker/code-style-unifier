from __future__ import annotations

import math
from numbers import Integral, Real

import torch

from experiments.restoration.errors import invalid_restoration_contract


_EPSILON = 1e-12
_INTENSITY_POLICIES_REQUIRING_SCALE = {
    "fixed_dataset_level",
    "characterization_calibrated_gain",
}


def _tensor(name: str, value: torch.Tensor) -> torch.Tensor:
    if not isinstance(value, torch.Tensor):
        raise invalid_restoration_contract(f"{name} must be a torch.Tensor")
    if value.numel() == 0:
        raise invalid_restoration_contract(f"{name} must not be empty")
    tensor = value.to(dtype=torch.float32)
    if not bool(torch.isfinite(tensor).all()):
        raise invalid_restoration_contract(f"{name} must contain only finite values")
    return tensor


def _compatible_tensors(**tensors: torch.Tensor) -> dict[str, torch.Tensor]:
    converted = {name: _tensor(name, value) for name, value in tensors.items()}
    shapes = {tuple(value.shape) for value in converted.values()}
    if len(shapes) != 1:
        raise invalid_restoration_contract("tensors must have compatible shapes")
    return converted


def _positive_data_range(data_range: float) -> float:
    if isinstance(data_range, bool) or not isinstance(data_range, Real):
        raise invalid_restoration_contract("data_range must be a positive real number")
    numeric_value = float(data_range)
    if not math.isfinite(numeric_value) or numeric_value <= 0:
        raise invalid_restoration_contract("data_range must be a positive real number")
    return numeric_value


def _positive_scale(scale: float | None) -> float:
    if scale is None or isinstance(scale, bool) or not isinstance(scale, Real):
        raise invalid_restoration_contract(
            "scale must be a positive finite real number"
        )
    numeric_value = float(scale)
    if not math.isfinite(numeric_value) or numeric_value <= 0.0:
        raise invalid_restoration_contract(
            "scale must be a positive finite real number"
        )
    return numeric_value


def normalize_intensity(
    image: torch.Tensor,
    *,
    policy: str,
    scale: float | None = None,
) -> torch.Tensor:
    """Apply the intensity normalization contract shared by all experiments."""
    image_tensor = _tensor("image", image)
    if policy in _INTENSITY_POLICIES_REQUIRING_SCALE:
        return torch.clamp(
            image_tensor / _positive_scale(scale),
            min=0.0,
            max=1.0,
        )
    if policy == "per_image_min_max":
        if image_tensor.ndim == 0:
            return image_tensor * 0.0
        dimensions = (0,) if image_tensor.ndim == 1 else (-2, -1)
        minimum = torch.amin(image_tensor, dim=dimensions, keepdim=True)
        maximum = torch.amax(image_tensor, dim=dimensions, keepdim=True)
        denominator = torch.clamp(maximum - minimum, min=_EPSILON)
        return (image_tensor - minimum) / denominator
    raise invalid_restoration_contract(
        f"unknown intensity normalization policy: {policy}"
    )


def _finite_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    return numeric_value


def _positive_real(name: str, value: object) -> float:
    numeric_value = _finite_real(name, value)
    if numeric_value <= 0.0:
        raise invalid_restoration_contract(f"{name} must be a positive real number")
    return numeric_value


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    numeric_value = int(value)
    if numeric_value <= 0:
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    return numeric_value


def _image_plane(name: str, value: torch.Tensor) -> torch.Tensor:
    tensor = _tensor(name, value)
    if tensor.ndim < 2:
        raise invalid_restoration_contract(f"{name} must have at least two dimensions")
    if tensor.ndim == 2:
        return tensor
    return tensor.reshape((-1, *tensor.shape[-2:]))[0]


def extract_center_image_region(
    image: torch.Tensor,
    *,
    region_resolution: tuple[int, int],
) -> torch.Tensor:
    """Return the centred active image region without changing leading axes."""
    if not isinstance(image, torch.Tensor):
        raise invalid_restoration_contract("image must be a torch.Tensor")
    if image.ndim < 2:
        raise invalid_restoration_contract("image must have at least two dimensions")
    if image.numel() == 0 or not bool(torch.isfinite(image).all()):
        raise invalid_restoration_contract("image must contain only finite values")
    if not isinstance(region_resolution, tuple) or len(region_resolution) != 2:
        raise invalid_restoration_contract(
            "region_resolution must be a height-width pair"
        )
    region_height = _positive_integer(
        "region_resolution height",
        region_resolution[0],
    )
    region_width = _positive_integer(
        "region_resolution width",
        region_resolution[1],
    )
    image_height, image_width = image.shape[-2:]
    if region_height > image_height or region_width > image_width:
        raise invalid_restoration_contract(
            "region_resolution must fit within the image plane"
        )
    row_start = (image_height - region_height) // 2
    column_start = (image_width - region_width) // 2
    return image[
        ...,
        row_start : row_start + region_height,
        column_start : column_start + region_width,
    ]


def _contiguous_width(mask: torch.Tensor, center_index: int) -> int:
    left = center_index
    while left > 0 and bool(mask[left - 1]):
        left -= 1
    right = center_index
    last_index = mask.numel() - 1
    while right < last_index and bool(mask[right + 1]):
        right += 1
    return right - left + 1


def point_response_fwhm(image: torch.Tensor) -> float:
    """
    实现评估指标辅助逻辑
    """
    response = _tensor("image", image)
    if response.ndim < 2:
        raise invalid_restoration_contract("image must have at least two dimensions")
    flattened_peak = int(torch.argmax(response).item())
    peak_indices = torch.unravel_index(
        torch.tensor(flattened_peak, device=response.device),
        response.shape,
    )
    peak_y = int(peak_indices[-2].item())
    peak_x = int(peak_indices[-1].item())
    peak_value = response[peak_indices].item()
    if peak_value <= 0.0:
        return 0.0

    half_maximum = peak_value * 0.5
    if response.ndim == 2:
        peak_plane = response
    else:
        peak_plane = response[tuple(int(index.item()) for index in peak_indices[:-2])]
    row = peak_plane[peak_y, :]
    column = peak_plane[:, peak_x]
    row_width = _contiguous_width(row >= half_maximum, peak_x)
    column_width = _contiguous_width(column >= half_maximum, peak_y)
    return float(max(row_width, column_width))


def point_response_peak_sidelobe_ratio(
    image: torch.Tensor,
    *,
    exclusion_radius: int = 1,
) -> float:
    """
    实现评估指标辅助逻辑
    """
    response = _image_plane("image", image)
    radius = _positive_integer("exclusion_radius", exclusion_radius)
    flattened_peak = int(torch.argmax(response).item())
    peak_y, peak_x = (
        int(index.item())
        for index in torch.unravel_index(
            torch.tensor(flattened_peak, device=response.device),
            response.shape,
        )
    )
    peak_value = float(response[peak_y, peak_x].item())
    if peak_value <= _EPSILON:
        return 0.0

    mask = torch.ones_like(response, dtype=torch.bool)
    y_min = max(0, peak_y - radius)
    y_max = min(response.shape[0], peak_y + radius + 1)
    x_min = max(0, peak_x - radius)
    x_max = min(response.shape[1], peak_x + radius + 1)
    mask[y_min:y_max, x_min:x_max] = False
    if not bool(mask.any()):
        return 0.0
    sidelobe = float(torch.max(response[mask]).item())
    return sidelobe / peak_value


def energy_throughput(
    input_intensity: torch.Tensor,
    output_intensity: torch.Tensor,
) -> float:
    """
    实现评估指标辅助逻辑
    """
    tensors = _compatible_tensors(
        input_intensity=input_intensity,
        output_intensity=output_intensity,
    )
    denominator = torch.sum(tensors["input_intensity"])
    if abs(float(denominator.item())) <= _EPSILON:
        return 0.0
    return float((torch.sum(tensors["output_intensity"]) / denominator).item())


def interference_reconstruction_error(
    full: torch.Tensor,
    reference: torch.Tensor,
    process: torch.Tensor,
    interference: torch.Tensor,
    *,
    atol: float = 1e-5,
    rtol: float = 1e-5,
) -> float:
    """
    实现评估指标辅助逻辑
    """
    tensors = _compatible_tensors(
        full=full,
        reference=reference,
        process=process,
        interference=interference,
    )
    residual = (
        tensors["full"]
        - tensors["reference"]
        - tensors["process"]
        - tensors["interference"]
    )
    scale = torch.abs(tensors["full"]) * rtol + atol
    normalized = torch.clamp(torch.abs(residual) - scale, min=0.0)
    return float(torch.mean(normalized).item())


def phase_intensity_ratio(
    *,
    full: torch.Tensor,
    reference: torch.Tensor,
    process: torch.Tensor,
) -> float:
    """
    实现评估指标辅助逻辑
    """
    tensors = _compatible_tensors(
        full=full,
        reference=reference,
        process=process,
    )
    numerator = torch.mean(tensors["full"])
    denominator = (
        torch.mean(tensors["reference"]) + torch.mean(tensors["process"]) + _EPSILON
    )
    return float((numerator / denominator).item())


def interference_visibility(
    *,
    reference: torch.Tensor,
    process: torch.Tensor,
    interference: torch.Tensor,
) -> float:
    """
    实现评估指标辅助逻辑
    """
    tensors = _compatible_tensors(
        reference=reference,
        process=process,
        interference=interference,
    )
    numerator = torch.mean(torch.abs(tensors["interference"]))
    denominator = (
        torch.mean(tensors["reference"]) + torch.mean(tensors["process"]) + _EPSILON
    )
    return float((numerator / denominator).item())


def ringing_index_from_edge(edge_profile: torch.Tensor) -> float:
    """
    实现评估指标辅助逻辑
    """
    profile = _tensor("edge_profile", edge_profile).flatten()
    lower_level = torch.minimum(profile[0], profile[-1])
    upper_level = torch.maximum(profile[0], profile[-1])
    overshoot = torch.clamp(profile.max() - upper_level, min=0.0)
    undershoot = torch.clamp(lower_level - profile.min(), min=0.0)
    step_height = torch.clamp(upper_level - lower_level, min=_EPSILON)
    return float(((overshoot + undershoot) / step_height).item())


def contrast_transfer(
    *,
    input_contrast: float,
    output_contrast: float,
) -> float:
    """
    实现评估指标辅助逻辑
    """
    input_value = _finite_real("input_contrast", input_contrast)
    output_value = _finite_real("output_contrast", output_contrast)
    if abs(input_value) <= _EPSILON:
        return 0.0
    return output_value / input_value


def michelson_contrast(image: torch.Tensor) -> float:
    """
    实现评估指标辅助逻辑
    """
    plane = _image_plane("image", image)
    maximum = float(torch.max(plane).item())
    minimum = float(torch.min(plane).item())
    denominator = maximum + minimum
    if abs(denominator) <= _EPSILON:
        return 0.0
    return (maximum - minimum) / denominator


def grating_contrast_transfer(
    input_image: torch.Tensor,
    output_image: torch.Tensor,
) -> float:
    """
    实现评估指标辅助逻辑
    """
    tensors = _compatible_tensors(input_image=input_image, output_image=output_image)
    return contrast_transfer(
        input_contrast=michelson_contrast(tensors["input_image"]),
        output_contrast=michelson_contrast(tensors["output_image"]),
    )


def slanted_edge_intensity_mtf(
    image: torch.Tensor,
    *,
    angle_degrees: float,
    pixel_size: float = 1.0,
    oversampling_factor: int = 4,
) -> dict[str, object]:
    """
    实现评估指标辅助逻辑
    """
    plane = _image_plane("image", image)
    angle = math.radians(_finite_real("angle_degrees", angle_degrees))
    pixel_size_value = _positive_real("pixel_size", pixel_size)
    oversampling = _positive_integer("oversampling_factor", oversampling_factor)

    height, width = plane.shape
    y_coordinates = (
        torch.arange(height, dtype=torch.float32, device=plane.device)
        - (height - 1) / 2.0
    )
    x_coordinates = (
        torch.arange(width, dtype=torch.float32, device=plane.device)
        - (width - 1) / 2.0
    )
    grid_y, grid_x = torch.meshgrid(y_coordinates, x_coordinates, indexing="ij")
    signed_distance = grid_x * math.cos(angle) + grid_y * math.sin(angle)
    bin_width = 1.0 / float(oversampling)
    distance_minimum = (
        math.floor(float(torch.min(signed_distance).item()) / bin_width) * bin_width
    )
    distance_maximum = (
        math.ceil(float(torch.max(signed_distance).item()) / bin_width) * bin_width
    )
    bin_count = int(round((distance_maximum - distance_minimum) / bin_width)) + 1
    if bin_count < 4:
        raise invalid_restoration_contract(
            "slanted edge profile is too short for MTF extraction"
        )

    flattened_distance = signed_distance.flatten()
    flattened_image = plane.flatten()
    bin_indices = torch.clamp(
        torch.floor((flattened_distance - distance_minimum) / bin_width).to(torch.long),
        min=0,
        max=bin_count - 1,
    )
    sums = torch.zeros(bin_count, dtype=torch.float32, device=plane.device)
    counts = torch.zeros(bin_count, dtype=torch.float32, device=plane.device)
    sums.scatter_add_(0, bin_indices, flattened_image)
    counts.scatter_add_(0, bin_indices, torch.ones_like(flattened_image))
    valid = counts > 0
    edge_spread = sums[valid] / counts[valid]
    if edge_spread.numel() < 4:
        raise invalid_restoration_contract(
            "slanted edge profile has too few populated bins"
        )

    edge_minimum = torch.min(edge_spread)
    edge_maximum = torch.max(edge_spread)
    edge_range = edge_maximum - edge_minimum
    if float(edge_range.item()) <= _EPSILON:
        return _empty_mtf_result(pixel_size_value)
    normalized_edge = (edge_spread - edge_minimum) / edge_range
    if float(normalized_edge[-1].item()) < float(normalized_edge[0].item()):
        normalized_edge = 1.0 - normalized_edge

    line_spread = torch.diff(normalized_edge)
    if line_spread.numel() < 4:
        raise invalid_restoration_contract(
            "line spread function is too short for MTF extraction"
        )
    window = torch.hann_window(line_spread.numel(), periodic=False, device=plane.device)
    spectrum = torch.abs(torch.fft.rfft(line_spread * window))
    if float(spectrum[0].item()) <= _EPSILON:
        return _empty_mtf_result(pixel_size_value)
    mtf = spectrum / spectrum[0]
    frequencies = torch.fft.rfftfreq(line_spread.numel(), d=bin_width).to(
        device=plane.device
    )
    passband = frequencies <= 0.5
    if not bool(passband.any()):
        return _empty_mtf_result(pixel_size_value)
    frequency_values = [float(value) for value in frequencies[passband].detach().cpu()]
    mtf_values = [
        float(torch.clamp(value, min=0.0, max=1.0).item()) for value in mtf[passband]
    ]
    if frequency_values[0] != 0.0:
        frequency_values.insert(0, 0.0)
        mtf_values.insert(0, 1.0)

    mtf50 = _first_frequency_at_or_below(frequency_values, mtf_values, 0.5)
    mtf10 = _first_frequency_at_or_below(frequency_values, mtf_values, 0.1)
    nyquist_response = _interpolate_curve(frequency_values, mtf_values, 0.5)
    mtf_auc = _normalized_auc(frequency_values, mtf_values, limit=0.5)
    return {
        "frequencies_cycles_per_pixel": frequency_values,
        "mtf": mtf_values,
        "mtf50_cycles_per_pixel": mtf50,
        "mtf10_cycles_per_pixel": mtf10,
        "mtf50_cycles_per_meter": mtf50 / pixel_size_value,
        "mtf10_cycles_per_meter": mtf10 / pixel_size_value,
        "nyquist_response": nyquist_response,
        "mtf_auc": mtf_auc,
    }


def _empty_mtf_result(pixel_size: float) -> dict[str, object]:
    return {
        "frequencies_cycles_per_pixel": [0.0, 0.5],
        "mtf": [0.0, 0.0],
        "mtf50_cycles_per_pixel": 0.0,
        "mtf10_cycles_per_pixel": 0.0,
        "mtf50_cycles_per_meter": 0.0 / pixel_size,
        "mtf10_cycles_per_meter": 0.0 / pixel_size,
        "nyquist_response": 0.0,
        "mtf_auc": 0.0,
    }


def _first_frequency_at_or_below(
    frequencies: list[float],
    values: list[float],
    level: float,
) -> float:
    for index in range(1, len(frequencies)):
        previous_value = values[index - 1]
        current_value = values[index]
        if current_value <= level:
            previous_frequency = frequencies[index - 1]
            current_frequency = frequencies[index]
            if previous_value == current_value:
                return min(0.5, current_frequency)
            fraction = (level - previous_value) / (current_value - previous_value)
            crossing = previous_frequency + fraction * (
                current_frequency - previous_frequency
            )
            return min(0.5, max(0.0, crossing))
    return 0.5


def _interpolate_curve(
    frequencies: list[float], values: list[float], x_value: float
) -> float:
    if x_value <= frequencies[0]:
        return values[0]
    for index in range(1, len(frequencies)):
        if frequencies[index] >= x_value:
            previous_frequency = frequencies[index - 1]
            current_frequency = frequencies[index]
            previous_value = values[index - 1]
            current_value = values[index]
            if current_frequency == previous_frequency:
                return current_value
            fraction = (x_value - previous_frequency) / (
                current_frequency - previous_frequency
            )
            return previous_value + fraction * (current_value - previous_value)
    return values[-1]


def _normalized_auc(
    frequencies: list[float], values: list[float], *, limit: float
) -> float:
    clipped_frequencies = [frequency for frequency in frequencies if frequency <= limit]
    clipped_values = values[: len(clipped_frequencies)]
    if not clipped_frequencies or clipped_frequencies[-1] < limit:
        clipped_frequencies.append(limit)
        clipped_values.append(_interpolate_curve(frequencies, values, limit))
    area = 0.0
    for index in range(1, len(clipped_frequencies)):
        delta = clipped_frequencies[index] - clipped_frequencies[index - 1]
        area += 0.5 * (clipped_values[index] + clipped_values[index - 1]) * delta
    if limit <= _EPSILON:
        return 0.0
    return max(0.0, min(1.0, area / limit))


def psnr(
    prediction: torch.Tensor,
    target: torch.Tensor,
    *,
    data_range: float = 1.0,
) -> float:
    """
    实现评估指标辅助逻辑
    """
    dynamic_range = _positive_data_range(data_range)
    tensors = _compatible_tensors(prediction=prediction, target=target)
    mean_square_error = torch.mean((tensors["prediction"] - tensors["target"]).square())
    if float(mean_square_error.item()) == 0.0:
        return math.inf
    return float(
        (20.0 * math.log10(dynamic_range))
        - (10.0 * torch.log10(mean_square_error)).item()
    )


def ssim_global(
    prediction: torch.Tensor,
    target: torch.Tensor,
    *,
    data_range: float = 1.0,
) -> float:
    """
    实现评估指标辅助逻辑
    """
    dynamic_range = _positive_data_range(data_range)
    tensors = _compatible_tensors(prediction=prediction, target=target)
    prediction_tensor = tensors["prediction"]
    target_tensor = tensors["target"]
    c1 = (0.01 * dynamic_range) ** 2
    c2 = (0.03 * dynamic_range) ** 2
    prediction_mean = torch.mean(prediction_tensor)
    target_mean = torch.mean(target_tensor)
    prediction_delta = prediction_tensor - prediction_mean
    target_delta = target_tensor - target_mean
    prediction_variance = torch.mean(prediction_delta.square())
    target_variance = torch.mean(target_delta.square())
    covariance = torch.mean(prediction_delta * target_delta)
    numerator = (2.0 * prediction_mean * target_mean + c1) * (2.0 * covariance + c2)
    denominator = (prediction_mean.square() + target_mean.square() + c1) * (
        prediction_variance + target_variance + c2
    )
    score = numerator / denominator
    return float(torch.clamp(score, min=-1.0, max=1.0).item())
