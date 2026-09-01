import numpy as np
import pytest
import torch

from data.encoding.optical_encode import encode_image_to_field
from data.preparation.normalize import normalize_image
from data.preparation.resize import resize_image
from data.perturbation.blur.gaussian_blur import apply_gaussian_blur
from data.perturbation.blur.defocus_blur import apply_defocus_blur
from data.perturbation.edges.canny_edges import build_canny_edge_map
from data.perturbation.edges.laplacian_of_gaussian_edges import build_laplacian_of_gaussian_edge_map
from data.perturbation.edges.sobel_edges import build_sobel_edge_map
from data.perturbation.noise.additive_gaussian_noise import add_additive_gaussian_noise


def test_normalize_and_resize_image_centers_foreground():
    """Verify resize_image centers the foreground and pads correctly."""
    image = np.zeros((28, 28), dtype=np.uint8)
    image[10:18, 10:18] = 255

    padded = resize_image(
        image=normalize_image(image=image, normalization_method="auto"),
        image_resolution=(64, 64),
        array_resolution=(128, 128),
    )

    assert padded.shape == (128, 128)
    assert np.isclose(padded.max(), 1.0)
    assert padded[32:96, 32:96].sum() > 0.0
    assert np.isclose(padded[:16].sum() + padded[-16:].sum(), 0.0)


def test_encode_image_to_field_intensity_mode_uses_sqrt_amplitude():
    """Verify intensity encoding uses square-root amplitude and zero phase."""
    image = np.array([[0.0, 0.25], [1.0, 0.0]], dtype=np.float32)
    field = encode_image_to_field(image=image, encoding_method="intensity")

    assert field.dtype == torch.complex64
    assert field.shape == (1, 2, 2)
    assert torch.allclose(
        torch.abs(field),
        torch.tensor([[[0.0, 0.5], [1.0, 0.0]]]),
    )
    assert torch.allclose(torch.angle(field), torch.zeros((1, 2, 2)))


def test_encode_image_to_field_phase_mode_encodes_unit_amplitude_phase_rotation():
    image = np.array([[0.0, 0.25], [0.5, 1.0]], dtype=np.float32)
    field = encode_image_to_field(image=image, encoding_method="phase")

    assert field.dtype == torch.complex64
    assert field.shape == (1, 2, 2)
    assert torch.allclose(torch.abs(field), torch.ones((1, 2, 2)))
    assert torch.allclose(
        torch.angle(field),
        torch.tensor([[[0.0, np.pi / 2.0], [-np.pi, 0.0]]], dtype=torch.float32),
        atol=1e-6,
    )


def test_encode_image_to_field_rejects_unknown_mode():
    """
    楠岃瘉 encode_image_to_field 瀵规湭鐭ョ紪鐮佹柟寮忔姏鍑?ValueError
    """
    image = np.zeros((2, 2), dtype=np.float32)

    try:
        encode_image_to_field(image=image, encoding_method="bogus")
    except ValueError as exc:
        assert "bogus" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown encoding method")


@pytest.mark.parametrize(
    "image",
    [
        np.array([[0.0, -0.1]], dtype=np.float32),
        np.array([[0.0, np.nan]], dtype=np.float32),
        np.array([[0.0, np.inf]], dtype=np.float32),
    ],
)
def test_encode_image_to_field_rejects_non_physical_input_values(
    image: np.ndarray,
) -> None:
    with pytest.raises(ValueError) as exc_info:
        encode_image_to_field(image=image, encoding_method="intensity")
    assert "image" in str(exc_info.value)
    assert "must" not in str(exc_info.value)


def test_normalize_image_auto_scales_uint16_range():
    image = np.array([[0, 32768, 65535]], dtype=np.uint16)

    normalized = normalize_image(image=image, normalization_method="auto")

    assert normalized.dtype == np.float32
    assert normalized[0, 0] == pytest.approx(0.0)
    assert normalized[0, 1] == pytest.approx(32768.0 / 65535.0)
    assert normalized[0, 2] == pytest.approx(1.0)


def test_normalize_image_percentile_clips_outliers():
    image = np.array([[0.0, 10.0, 20.0, 1000.0]], dtype=np.float32)

    normalized = normalize_image(
        image=image,
        normalization_method="percentile",
        percentile_range=(0.0, 50.0),
    )

    assert normalized.dtype == np.float32
    assert normalized[0, 0] == pytest.approx(0.0)
    assert normalized[0, 2] == pytest.approx(1.0)
    assert normalized[0, 3] == pytest.approx(1.0)


def test_normalize_image_rejects_unknown_method():
    with pytest.raises(ValueError, match="normalization_method"):
        normalize_image(
            image=np.ones((2, 2), dtype=np.float32),
            normalization_method="unknown",
        )


def test_resize_image_center_padding_contract():
    image = np.ones((28, 28), dtype=np.float32)
    resized = resize_image(
        image=image,
        image_resolution=(28, 28),
        array_resolution=(32, 32),
    )
    assert resized.shape == (32, 32)
    assert resized.dtype == np.float32


def test_resize_image_defaults_to_center_padding():
    image = np.ones((2, 2), dtype=np.float32)

    resized = resize_image(
        image=image,
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )

    assert resized.shape == (4, 4)
    assert np.array_equal(resized[1:3, 1:3], np.ones((2, 2), dtype=np.float32))
    assert resized.sum() == pytest.approx(4.0)


@pytest.mark.parametrize(
    "interpolation_method",
    [
        "nearest",
        "bilinear",
        "bicubic",
    ],
)
def test_resize_image_accepts_supported_interpolation_methods(interpolation_method):
    image = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32)

    resized = resize_image(
        image=image,
        image_resolution=(4, 4),
        array_resolution=(4, 4),
        interpolation_method=interpolation_method,
    )

    assert resized.dtype == np.float32
    assert resized.shape == (4, 4)


def test_resize_image_rejects_unknown_interpolation_method():
    with pytest.raises(ValueError, match="interpolation_method"):
        resize_image(
            image=np.ones((2, 2), dtype=np.float32),
            image_resolution=(2, 2),
            array_resolution=(2, 2),
            interpolation_method="area",
        )


def test_resize_image_edge_taper_smooths_support_boundary():
    image = np.ones((5, 5), dtype=np.float32)

    resized = resize_image(
        image=image,
        image_resolution=(5, 5),
        array_resolution=(7, 7),
        edge_taper_width=1,
    )

    support = resized[1:6, 1:6]
    assert support[0, :].sum() == pytest.approx(0.0)
    assert support[:, 0].sum() == pytest.approx(0.0)
    assert support[-1, :].sum() == pytest.approx(0.0)
    assert support[:, -1].sum() == pytest.approx(0.0)
    assert support[2, 2] == pytest.approx(1.0)


def test_encode_image_to_field_keeps_complex_output_contract():
    image = np.ones((8, 8), dtype=np.float32)
    field = encode_image_to_field(image=image, encoding_method="intensity")
    assert field.shape == (1, 8, 8)
    assert field.dtype == torch.complex64


def test_add_additive_gaussian_noise_applies_seeded_stage_operator_and_clips_output():
    image = np.array([[0.0, 0.5], [1.0, 0.25]], dtype=np.float32)
    noisy = add_additive_gaussian_noise(
        image,
        sigma=0.3,
        random_generator=np.random.default_rng(123),
    )

    assert noisy.dtype == np.float32
    assert noisy.shape == image.shape
    assert np.all(noisy >= 0.0)
    assert np.all(noisy <= 1.0)
    assert np.allclose(
        noisy,
        np.array([[0.0, 0.389664], [1.0, 0.3081923]], dtype=np.float32),
    )


def test_apply_gaussian_blur_matches_expected_gaussian_kernel_response():
    image = np.zeros((5, 5), dtype=np.float32)
    image[2, 2] = 1.0

    degraded = apply_gaussian_blur(image, kernel_size=3)

    assert degraded.dtype == np.float32
    assert np.allclose(
        degraded,
        np.array(
            [
                [0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0625, 0.125, 0.0625, 0.0],
                [0.0, 0.125, 0.25, 0.125, 0.0],
                [0.0, 0.0625, 0.125, 0.0625, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0],
            ],
            dtype=np.float32,
        ),
    )


def test_apply_defocus_blur_matches_expected_disk_psf_response():
    image = np.zeros((5, 5), dtype=np.float32)
    image[2, 2] = 1.0

    degraded = apply_defocus_blur(image, radius=1)

    assert degraded.dtype == np.float32
    assert degraded.shape == image.shape
    assert np.allclose(
        degraded,
        np.array(
            [
                [0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.2, 0.0, 0.0],
                [0.0, 0.2, 0.2, 0.2, 0.0],
                [0.0, 0.0, 0.2, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0],
            ],
            dtype=np.float32,
        ),
    )


def test_apply_defocus_blur_rejects_invalid_radius():
    with pytest.raises(ValueError, match="radius"):
        apply_defocus_blur(np.ones((3, 3), dtype=np.float32), radius=0)


def test_build_canny_edge_map_returns_normalized_stage_edges():
    image = np.zeros((8, 8), dtype=np.float32)
    image[2:6, 4:] = 1.0

    edges = build_canny_edge_map(image, threshold1=10, threshold2=20)

    assert edges.dtype == np.float32
    assert np.all((edges == 0.0) | (edges == 1.0))
    assert np.array_equal(
        edges,
        np.array(
            [
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ],
            dtype=np.float32,
        ),
    )


def test_build_sobel_edge_map_returns_normalized_gradient_magnitude():
    image = np.zeros((8, 8), dtype=np.float32)
    image[:, 4:] = 1.0

    edges = build_sobel_edge_map(image, kernel_size=3)

    assert edges.dtype == np.float32
    assert edges.shape == image.shape
    assert edges.min() == pytest.approx(0.0)
    assert edges.max() == pytest.approx(1.0)
    assert edges[:, 3:5].sum() > 0.0
    assert np.count_nonzero(edges[:, :2]) == 0


def test_build_laplacian_of_gaussian_edge_map_returns_normalized_response():
    image = np.zeros((9, 9), dtype=np.float32)
    image[3:6, 3:6] = 1.0

    edges = build_laplacian_of_gaussian_edge_map(
        image,
        kernel_size=3,
        sigma=0.0,
    )

    assert edges.dtype == np.float32
    assert edges.shape == image.shape
    assert edges.min() == pytest.approx(0.0)
    assert edges.max() == pytest.approx(1.0)
    assert edges.sum() > 0.0


@pytest.mark.parametrize(
    "builder",
    [
        build_sobel_edge_map,
        build_laplacian_of_gaussian_edge_map,
    ],
)
def test_gradient_edge_maps_return_zero_for_constant_images(builder):
    edges = builder(np.ones((6, 6), dtype=np.float32), kernel_size=3)

    assert edges.dtype == np.float32
    assert np.array_equal(edges, np.zeros((6, 6), dtype=np.float32))


def test_resize_image_does_not_normalize_input_values():
    """Verify resize_image does not normalize input values."""
    image = np.array([[0.0, 255.0]], dtype=np.float32)

    padded = resize_image(
        image=image,
        image_resolution=(1, 2),
        array_resolution=(1, 2),
    )

    assert padded.dtype == np.float32
    assert padded.shape == (1, 2)
    assert padded.max() == pytest.approx(255.0)


@pytest.mark.parametrize(
    ("image_resolution", "array_resolution", "match"),
    [
        ((4, 4), (2, 2), "image_resolution <= array_resolution"),
        ((0, 2), (4, 4), "image_resolution"),
        ((2, 2), (4, 0), "array_resolution"),
        ((True, 2), (4, 4), "image_resolution"),
    ],
)
def test_resize_image_rejects_invalid_geometry(
    image_resolution,
    array_resolution,
    match,
):
    """Verify resize_image rejects invalid geometry."""
    with pytest.raises(ValueError, match=match):
        resize_image(
            image=np.ones((2, 2), dtype=np.float32),
            image_resolution=image_resolution,
            array_resolution=array_resolution,
        )
