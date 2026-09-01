from __future__ import annotations

import argparse
import csv
import math
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from torchvision.datasets import FashionMNIST, MNIST


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "filter_comparison"


@dataclass
class FilterResult:
    """
    滤波结果的数据容器，存储滤波器名称、延迟与图像质量指标
    """
    name: str
    latency_ms: float
    mse: float
    psnr: float
    ssim: float
    image: np.ndarray
    display_image: np.ndarray


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数并返回命名空间
    """
    parser = argparse.ArgumentParser(
        description="Compare frequency-domain filters on a degraded image sampled from the local dataset."
    )
    parser.add_argument("--dataset", choices=("mnist", "fashion_mnist"), default="mnist")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-index", type=int, default=7)
    parser.add_argument("--train", action="store_true", help="Use the training split instead of the test split.")
    parser.add_argument("--canvas-size", type=int, default=128)
    parser.add_argument("--content-size", type=int, default=96)
    parser.add_argument("--noise-sigma", type=float, default=0.08)
    parser.add_argument("--blur-kernel-size", type=int, default=11)
    parser.add_argument("--blur-sigma", type=float, default=2.2)
    parser.add_argument("--lowpass-cutoff", type=float, default=16.0)
    parser.add_argument("--highpass-cutoff", type=float, default=10.0)
    parser.add_argument("--band-low", type=float, default=8.0)
    parser.add_argument("--band-high", type=float, default=24.0)
    parser.add_argument("--butterworth-order", type=int, default=2)
    parser.add_argument(
        "--wiener-k",
        type=float,
        default=None,
        help="Wiener constant. If omitted, it is estimated from the degradation process.",
    )
    parser.add_argument("--timing-repeats", type=int, default=20)
    parser.add_argument("--grid-columns", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """
    校验命令行参数的合法性，不合法时抛出 ValueError
    """
    if args.canvas_size < 28:
        raise ValueError(f"canvas_size must be at least 28, got {args.canvas_size}")
    if args.content_size < 28:
        raise ValueError(f"content_size must be at least 28, got {args.content_size}")
    if args.content_size > args.canvas_size:
        raise ValueError(
            f"content_size must not exceed canvas_size, got {args.content_size} > {args.canvas_size}"
        )
    if args.blur_kernel_size <= 0 or args.blur_kernel_size % 2 == 0:
        raise ValueError(
            f"blur_kernel_size must be a positive odd integer, got {args.blur_kernel_size}"
        )
    if args.blur_sigma <= 0:
        raise ValueError(f"blur_sigma must be positive, got {args.blur_sigma}")
    if args.noise_sigma < 0:
        raise ValueError(f"noise_sigma must be non-negative, got {args.noise_sigma}")
    if args.lowpass_cutoff <= 0:
        raise ValueError(f"lowpass_cutoff must be positive, got {args.lowpass_cutoff}")
    if args.highpass_cutoff <= 0:
        raise ValueError(f"highpass_cutoff must be positive, got {args.highpass_cutoff}")
    if args.band_low <= 0 or args.band_high <= 0:
        raise ValueError(
            f"band_low and band_high must be positive, got {args.band_low}, {args.band_high}"
        )
    if args.band_low >= args.band_high:
        raise ValueError(
            f"band_low must be smaller than band_high, got {args.band_low} >= {args.band_high}"
        )
    if args.butterworth_order <= 0:
        raise ValueError(
            f"butterworth_order must be a positive integer, got {args.butterworth_order}"
        )
    if args.timing_repeats <= 0:
        raise ValueError(f"timing_repeats must be positive, got {args.timing_repeats}")
    if args.grid_columns <= 0:
        raise ValueError(f"grid_columns must be positive, got {args.grid_columns}")
    if args.wiener_k is not None and args.wiener_k <= 0:
        raise ValueError(f"wiener_k must be positive when set, got {args.wiener_k}")


def load_image_from_dataset(
    dataset_name: str,
    data_root: Path,
    sample_index: int,
    use_train_split: bool,
    canvas_size: int,
    content_size: int,
) -> tuple[np.ndarray, int, str]:
    """
    从 MNIST 或 FashionMNIST 数据集加载指定索引的图像并居中填充
    """
    if dataset_name == "mnist":
        dataset = MNIST(root=str(data_root), train=use_train_split, download=False)
        class_names = [str(index) for index in range(10)]
    elif dataset_name == "fashion_mnist":
        dataset = FashionMNIST(root=str(data_root), train=use_train_split, download=False)
        class_names = [
            "T-shirt/top",
            "Trouser",
            "Pullover",
            "Dress",
            "Coat",
            "Sandal",
            "Shirt",
            "Sneaker",
            "Bag",
            "Ankle boot",
        ]
    else:
        raise ValueError(f"Unsupported dataset: {dataset_name}")

    if sample_index < 0 or sample_index >= len(dataset):
        raise IndexError(
            f"sample_index must be in [0, {len(dataset) - 1}], got {sample_index}"
        )

    raw_image, raw_label = dataset[sample_index]
    image_array = np.array(raw_image, dtype=np.float32) / 255.0
    resized = cv2.resize(
        image_array,
        (content_size, content_size),
        interpolation=cv2.INTER_NEAREST,
    )

    padded = np.zeros((canvas_size, canvas_size), dtype=np.float32)
    start_y = (canvas_size - content_size) // 2
    start_x = (canvas_size - content_size) // 2
    padded[start_y:start_y + content_size, start_x:start_x + content_size] = resized

    return padded, int(raw_label), class_names[int(raw_label)]


def build_gaussian_kernel(kernel_size: int, sigma: float) -> np.ndarray:
    """
    构建指定尺寸和标准差的高斯模糊核并归一化
    """
    axis = np.arange(kernel_size, dtype=np.float32) - kernel_size // 2
    xx, yy = np.meshgrid(axis, axis)
    kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    kernel_sum = float(kernel.sum())
    if kernel_sum == 0.0:
        raise ValueError("Gaussian kernel sum unexpectedly equals zero.")
    return kernel / kernel_sum


def psf_to_otf(psf: np.ndarray, image_shape: tuple[int, int]) -> np.ndarray:
    """
    将点扩散函数（PSF）转换为光学传递函数（OTF）
    """
    psf_height, psf_width = psf.shape
    padded = np.zeros(image_shape, dtype=np.float32)
    padded[:psf_height, :psf_width] = psf
    padded = np.roll(padded, shift=-(psf_height // 2), axis=0)
    padded = np.roll(padded, shift=-(psf_width // 2), axis=1)
    return np.fft.fft2(padded)


def degrade_image(
    clean_image: np.ndarray,
    blur_kernel_size: int,
    blur_sigma: float,
    noise_sigma: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    对清晰图像施加高斯模糊并叠加高斯噪声，返回退化图像、模糊图像和 OTF
    """
    kernel = build_gaussian_kernel(blur_kernel_size, blur_sigma)
    otf = psf_to_otf(kernel, clean_image.shape)

    clean_fft = np.fft.fft2(clean_image)
    blurred = np.fft.ifft2(clean_fft * otf).real.astype(np.float32)

    random_number_generator = np.random.default_rng(seed)
    noise = random_number_generator.normal(
        loc=0.0,
        scale=noise_sigma,
        size=clean_image.shape,
    ).astype(np.float32)
    degraded = np.clip(blurred + noise, 0.0, 1.0)
    return degraded, blurred, otf


def frequency_radius(image_shape: tuple[int, int]) -> np.ndarray:
    """
    计算频域中每个像素点到中心的径向距离
    """
    height, width = image_shape
    y_coordinates = np.arange(height, dtype=np.float32) - height / 2.0
    x_coordinates = np.arange(width, dtype=np.float32) - width / 2.0
    xx, yy = np.meshgrid(x_coordinates, y_coordinates)
    return np.sqrt(xx**2 + yy**2)


def apply_frequency_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    在频域中应用掩膜并返回实数结果图像
    """
    image_fft = np.fft.fftshift(np.fft.fft2(image))
    filtered = np.fft.ifft2(np.fft.ifftshift(image_fft * mask)).real
    return filtered.astype(np.float32)


def ideal_low_pass_filter(image: np.ndarray, cutoff: float) -> np.ndarray:
    """
    理想低通滤波器，保留截止半径以内的频率分量
    """
    mask = (frequency_radius(image.shape) <= cutoff).astype(np.float32)
    return apply_frequency_mask(image, mask)


def ideal_high_pass_filter(image: np.ndarray, cutoff: float) -> np.ndarray:
    """
    理想高通滤波器，保留截止半径以外的频率分量
    """
    mask = (frequency_radius(image.shape) >= cutoff).astype(np.float32)
    return apply_frequency_mask(image, mask)


def ideal_band_pass_filter(image: np.ndarray, low_cutoff: float, high_cutoff: float) -> np.ndarray:
    """
    理想带通滤波器，保留上下截止半径之间的频率分量
    """
    radius = frequency_radius(image.shape)
    mask = np.logical_and(radius >= low_cutoff, radius <= high_cutoff).astype(np.float32)
    return apply_frequency_mask(image, mask)


def butterworth_low_pass_filter(image: np.ndarray, cutoff: float, order: int) -> np.ndarray:
    """
    巴特沃斯低通滤波器，在截止频率处平滑过渡
    """
    radius = frequency_radius(image.shape)
    mask = 1.0 / (1.0 + (radius / cutoff) ** (2 * order))
    return apply_frequency_mask(image, mask.astype(np.float32))


def butterworth_high_pass_filter(image: np.ndarray, cutoff: float, order: int) -> np.ndarray:
    """
    巴特沃斯高通滤波器，在截止频率处平滑过渡
    """
    radius = frequency_radius(image.shape)
    safe_radius = np.maximum(radius, 1e-6)
    mask = 1.0 / (1.0 + (cutoff / safe_radius) ** (2 * order))
    return apply_frequency_mask(image, mask.astype(np.float32))


def gaussian_low_pass_filter(image: np.ndarray, cutoff: float) -> np.ndarray:
    """
    高斯低通滤波器，以高斯函数作为频率响应
    """
    radius = frequency_radius(image.shape)
    mask = np.exp(-(radius**2) / (2 * cutoff**2))
    return apply_frequency_mask(image, mask.astype(np.float32))


def inverse_filter(image: np.ndarray, otf: np.ndarray, epsilon: float = 1e-3) -> np.ndarray:
    """
    逆滤波器，在频域中除以 OTF 以恢复原始图像，对过小值进行阈值保护
    """
    image_fft = np.fft.fft2(image)
    magnitude = np.abs(otf)
    restored_fft = np.zeros_like(image_fft)
    valid_mask = magnitude >= epsilon
    restored_fft[valid_mask] = image_fft[valid_mask] / otf[valid_mask]
    restored = np.fft.ifft2(restored_fft).real
    return restored.astype(np.float32)


def estimate_wiener_constant(blurred_image: np.ndarray, noise_sigma: float) -> float:
    """
    根据模糊图像信号方差和噪声方差估计维纳滤波常数
    """
    signal_variance = float(np.var(blurred_image))
    noise_variance = float(noise_sigma**2)
    return max(noise_variance / max(signal_variance, 1e-6), 1e-6)


def wiener_filter(image: np.ndarray, otf: np.ndarray, constant: float) -> np.ndarray:
    """
    维纳滤波器，在最小均方误差意义下恢复原始图像
    """
    image_fft = np.fft.fft2(image)
    restored_fft = (np.conjugate(otf) / (np.abs(otf) ** 2 + constant)) * image_fft
    restored = np.fft.ifft2(restored_fft).real
    return restored.astype(np.float32)


def clip_image(image: np.ndarray) -> np.ndarray:
    """
    将图像像素值裁剪到 [0, 1] 区间
    """
    return np.clip(image, 0.0, 1.0).astype(np.float32)


def normalize_for_display(image: np.ndarray) -> np.ndarray:
    """
    将图像归一化至 [0, 1] 用于显示，处理全零图像的特殊情况
    """
    image_min = float(image.min())
    image_max = float(image.max())
    if math.isclose(image_max, image_min):
        return np.zeros_like(image, dtype=np.float32)
    return ((image - image_min) / (image_max - image_min)).astype(np.float32)


def compute_mse(reference: np.ndarray, target: np.ndarray) -> float:
    """
    计算参考图像与目标图像之间的均方误差（MSE）
    """
    return float(np.mean((reference - target) ** 2))


def compute_psnr(reference: np.ndarray, target: np.ndarray) -> float:
    """
    计算峰值信噪比（PSNR），MSE 为零时返回无穷大
    """
    mse = compute_mse(reference, target)
    if mse <= 1e-12:
        return float("inf")
    return float(20.0 * math.log10(1.0 / math.sqrt(mse)))


def compute_ssim(reference: np.ndarray, target: np.ndarray) -> float:
    """
    计算结构相似性指数（SSIM）
    """
    reference = reference.astype(np.float32)
    target = target.astype(np.float32)

    c1 = (0.01 * 1.0) ** 2
    c2 = (0.03 * 1.0) ** 2

    mu_reference = cv2.GaussianBlur(reference, (11, 11), 1.5)
    mu_target = cv2.GaussianBlur(target, (11, 11), 1.5)

    mu_reference_sq = mu_reference * mu_reference
    mu_target_sq = mu_target * mu_target
    mu_reference_target = mu_reference * mu_target

    sigma_reference_sq = cv2.GaussianBlur(reference * reference, (11, 11), 1.5) - mu_reference_sq
    sigma_target_sq = cv2.GaussianBlur(target * target, (11, 11), 1.5) - mu_target_sq
    sigma_reference_target = cv2.GaussianBlur(reference * target, (11, 11), 1.5) - mu_reference_target

    numerator = (2.0 * mu_reference_target + c1) * (2.0 * sigma_reference_target + c2)
    denominator = (mu_reference_sq + mu_target_sq + c1) * (
        sigma_reference_sq + sigma_target_sq + c2
    )
    ssim_map = numerator / np.maximum(denominator, 1e-12)
    return float(np.mean(ssim_map))


def measure_latency(function, repeats: int) -> tuple[np.ndarray, float]:
    """
    多次执行函数并测量平均延迟（毫秒），同时返回函数结果
    """
    result = function()
    start_time = time.perf_counter()
    for _ in range(repeats):
        result = function()
    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000.0 / repeats
    return result, float(latency_ms)


def evaluate_filter(
    name: str,
    reference_image: np.ndarray,
    function,
    repeats: int,
) -> FilterResult:
    """
    执行滤波函数并收集延迟与图像质量指标
    """
    filtered_image, latency_ms = measure_latency(function, repeats)
    clipped_image = clip_image(filtered_image)

    return FilterResult(
        name=name,
        latency_ms=latency_ms,
        mse=compute_mse(reference_image, clipped_image),
        psnr=compute_psnr(reference_image, clipped_image),
        ssim=compute_ssim(reference_image, clipped_image),
        image=clipped_image,
        display_image=normalize_for_display(filtered_image),
    )


def make_panel(
    title: str,
    image: np.ndarray,
    subtitle_lines: list[str] | None = None,
    panel_size: int = 256,
    text_band_height: int = 82,
) -> np.ndarray:
    """
    将图像制作成带标题和副标题的展示面板
    """
    image_uint8 = np.uint8(np.round(np.clip(image, 0.0, 1.0) * 255.0))
    image_bgr = cv2.cvtColor(image_uint8, cv2.COLOR_GRAY2BGR)
    resized = cv2.resize(image_bgr, (panel_size, panel_size), interpolation=cv2.INTER_NEAREST)

    canvas = np.full(
        (panel_size + text_band_height, panel_size, 3),
        245,
        dtype=np.uint8,
    )
    canvas[:panel_size] = resized
    cv2.rectangle(canvas, (0, panel_size), (panel_size - 1, panel_size + text_band_height - 1), (230, 230, 230), -1)

    cv2.putText(
        canvas,
        title,
        (10, panel_size + 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.56,
        (20, 20, 20),
        1,
        cv2.LINE_AA,
    )

    if subtitle_lines:
        for line_index, line in enumerate(subtitle_lines, start=1):
            cv2.putText(
                canvas,
                line,
                (10, panel_size + 24 + 20 * line_index),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.47,
                (60, 60, 60),
                1,
                cv2.LINE_AA,
            )
    return canvas


def assemble_grid(panels: list[np.ndarray], columns: int) -> np.ndarray:
    """
    将多个面板按指定列数排列成网格图像
    """
    if not panels:
        raise ValueError("At least one panel is required to assemble a grid.")

    panel_height, panel_width = panels[0].shape[:2]
    rows = math.ceil(len(panels) / columns)
    filler = np.full((panel_height, panel_width, 3), 255, dtype=np.uint8)

    grid_rows = []
    for row_index in range(rows):
        start = row_index * columns
        end = start + columns
        row_panels = panels[start:end]
        if len(row_panels) < columns:
            row_panels = row_panels + [filler] * (columns - len(row_panels))
        grid_rows.append(np.concatenate(row_panels, axis=1))
    return np.concatenate(grid_rows, axis=0)


def save_grayscale_image(path: Path, image: np.ndarray) -> None:
    """
    将 [0, 1] 浮点图像保存为灰度 PNG 文件
    """
    image_uint8 = np.uint8(np.round(np.clip(image, 0.0, 1.0) * 255.0))
    cv2.imwrite(str(path), image_uint8)


def write_metrics_csv(path: Path, results: list[FilterResult]) -> None:
    """
    将滤波器指标写入 CSV 文件
    """
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["filter", "latency_ms", "mse", "psnr_db", "ssim"])
        for result in results:
            writer.writerow(
                [
                    result.name,
                    f"{result.latency_ms:.6f}",
                    f"{result.mse:.8f}",
                    f"{result.psnr:.4f}",
                    f"{result.ssim:.6f}",
                ]
            )


def write_summary(
    path: Path,
    dataset_name: str,
    label: int,
    class_name: str,
    clean_image: np.ndarray,
    degraded_image: np.ndarray,
    results: list[FilterResult],
    wiener_constant: float,
) -> None:
    """
    将滤波对比结果摘要写入文本文件
    """
    best_psnr = max(results, key=lambda result: result.psnr)
    best_ssim = max(results, key=lambda result: result.ssim)
    fastest = min(results, key=lambda result: result.latency_ms)
    degraded_metrics = {
        "mse": compute_mse(clean_image, degraded_image),
        "psnr": compute_psnr(clean_image, degraded_image),
        "ssim": compute_ssim(clean_image, degraded_image),
    }

    lines = [
        "Frequency-domain filter comparison",
        f"dataset: {dataset_name}",
        f"label: {label}",
        f"class_name: {class_name}",
        "",
        "Degraded image baseline",
        f"mse: {degraded_metrics['mse']:.8f}",
        f"psnr_db: {degraded_metrics['psnr']:.4f}",
        f"ssim: {degraded_metrics['ssim']:.6f}",
        "",
        f"Best PSNR: {best_psnr.name} ({best_psnr.psnr:.4f} dB)",
        f"Best SSIM: {best_ssim.name} ({best_ssim.ssim:.6f})",
        f"Fastest filter: {fastest.name} ({fastest.latency_ms:.6f} ms)",
        f"Wiener constant: {wiener_constant:.8f}",
        "",
        "Ranking by PSNR",
    ]

    for rank, result in enumerate(sorted(results, key=lambda item: item.psnr, reverse=True), start=1):
        lines.append(
            f"{rank}. {result.name}: psnr={result.psnr:.4f} dB, ssim={result.ssim:.6f}, latency={result.latency_ms:.6f} ms"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def run_comparison(args: argparse.Namespace) -> None:
    """
    执行完整的频域滤波对比流程并保存结果
    """
    clean_image, label, class_name = load_image_from_dataset(
        dataset_name=args.dataset,
        data_root=args.data_root,
        sample_index=args.sample_index,
        use_train_split=args.train,
        canvas_size=args.canvas_size,
        content_size=args.content_size,
    )
    degraded_image, blurred_image, blur_otf = degrade_image(
        clean_image=clean_image,
        blur_kernel_size=args.blur_kernel_size,
        blur_sigma=args.blur_sigma,
        noise_sigma=args.noise_sigma,
        seed=args.seed,
    )

    wiener_constant = (
        args.wiener_k
        if args.wiener_k is not None
        else estimate_wiener_constant(blurred_image=blurred_image, noise_sigma=args.noise_sigma)
    )

    filter_specs = [
        (
            "ideal_low_pass",
            lambda: ideal_low_pass_filter(degraded_image, cutoff=args.lowpass_cutoff),
        ),
        (
            "ideal_high_pass",
            lambda: ideal_high_pass_filter(degraded_image, cutoff=args.highpass_cutoff),
        ),
        (
            "ideal_band_pass",
            lambda: ideal_band_pass_filter(
                degraded_image,
                low_cutoff=args.band_low,
                high_cutoff=args.band_high,
            ),
        ),
        (
            "butterworth_low_pass",
            lambda: butterworth_low_pass_filter(
                degraded_image,
                cutoff=args.lowpass_cutoff,
                order=args.butterworth_order,
            ),
        ),
        (
            "butterworth_high_pass",
            lambda: butterworth_high_pass_filter(
                degraded_image,
                cutoff=args.highpass_cutoff,
                order=args.butterworth_order,
            ),
        ),
        (
            "gaussian_low_pass",
            lambda: gaussian_low_pass_filter(degraded_image, cutoff=args.lowpass_cutoff),
        ),
        (
            "inverse_filter",
            lambda: inverse_filter(degraded_image, blur_otf),
        ),
        (
            "wiener_filter",
            lambda: wiener_filter(degraded_image, blur_otf, constant=wiener_constant),
        ),
    ]

    results = [
        evaluate_filter(
            name=name,
            reference_image=clean_image,
            function=function,
            repeats=args.timing_repeats,
        )
        for name, function in filter_specs
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)

    save_grayscale_image(args.output_dir / "clean_image.png", clean_image)
    save_grayscale_image(args.output_dir / "degraded_image.png", degraded_image)
    save_grayscale_image(args.output_dir / "blurred_only_image.png", blurred_image)

    panels = [
        make_panel(
            title="clean_image",
            image=clean_image,
            subtitle_lines=[f"dataset={args.dataset}", f"label={label} ({class_name})"],
        ),
        make_panel(
            title="degraded_image",
            image=degraded_image,
            subtitle_lines=[
                f"noise_sigma={args.noise_sigma:.3f}",
                f"blur_sigma={args.blur_sigma:.3f}",
            ],
        ),
    ]

    for result in results:
        save_grayscale_image(args.output_dir / f"{result.name}.png", result.image)
        panels.append(
            make_panel(
                title=result.name,
                image=result.display_image,
                subtitle_lines=[
                    f"PSNR={result.psnr:.2f} dB",
                    f"SSIM={result.ssim:.4f}",
                    f"time={result.latency_ms:.4f} ms",
                ],
            )
        )

    grid = assemble_grid(panels, columns=args.grid_columns)
    cv2.imwrite(str(args.output_dir / "comparison_grid.png"), grid)

    write_metrics_csv(args.output_dir / "metrics.csv", results)
    write_summary(
        path=args.output_dir / "summary.txt",
        dataset_name=args.dataset,
        label=label,
        class_name=class_name,
        clean_image=clean_image,
        degraded_image=degraded_image,
        results=results,
        wiener_constant=wiener_constant,
    )

    print(f"Saved comparison outputs to: {args.output_dir}")
    print("Top filters by PSNR:")
    for result in sorted(results, key=lambda item: item.psnr, reverse=True)[:3]:
        print(
            f"  {result.name}: PSNR={result.psnr:.4f} dB, SSIM={result.ssim:.6f}, latency={result.latency_ms:.6f} ms"
        )


def main() -> None:
    """
    脚本入口，解析参数后运行频域滤波对比
    """
    args = parse_args()
    validate_args(args)
    run_comparison(args)


if __name__ == "__main__":
    main()
