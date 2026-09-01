import pytest
import numpy as np
from data.perturbation.noise.poisson_gaussian_noise import add_poisson_gaussian_noise
from data.perturbation.optics.coherent_imaging import optical_transfer_function_from_point_spread_function, point_spread_function_from_pupil_function
from data.perturbation.optics.low_pass_filters import build_ideal_low_pass_filter
from data.perturbation.optics.circular_pupil_functions import build_circular_pupil_function


def test_poisson_gaussian_noise_is_deterministic_with_seed() -> None:
    """
    Verify Poisson-Gaussian noise uses the provided random seed deterministically.
    """
    image = np.full((8, 8), 0.5, dtype=np.float32)

    first = add_poisson_gaussian_noise(image, peak_photons=100.0, read_noise_sigma=0.01, random_seed=7)
    second = add_poisson_gaussian_noise(image, peak_photons=100.0, read_noise_sigma=0.01, random_seed=7)

    assert np.allclose(first, second)
    assert first.shape == image.shape
    assert first.dtype == np.float32
    assert np.all(first >= 0.0)
    assert np.all(first <= 1.0)


def test_poisson_gaussian_noise_rejects_invalid_noise_parameters() -> None:
    """
    Verify Poisson-Gaussian noise rejects invalid photon and read-noise settings.
    """
    image = np.full((2, 2), 0.5, dtype=np.float32)

    with pytest.raises(ValueError, match="peak_photons"):
        add_poisson_gaussian_noise(image, peak_photons=0.0, read_noise_sigma=0.01)

    with pytest.raises(ValueError, match="read_noise_sigma"):
        add_poisson_gaussian_noise(image, peak_photons=100.0, read_noise_sigma=-0.01)


def test_pupil_psf_otf_shapes_and_energy() -> None:
    """
    Verify pupil, PSF, and OTF helpers preserve array shape and PSF normalization.
    """
    pupil = build_circular_pupil_function(shape=(16, 16), radius_fraction=0.5)
    point_spread_function = point_spread_function_from_pupil_function(pupil)
    optical_transfer_function = optical_transfer_function_from_point_spread_function(point_spread_function)

    assert pupil.shape == (16, 16)
    assert pupil.dtype == np.complex64
    assert point_spread_function.shape == (16, 16)
    assert point_spread_function.dtype == np.float32
    assert optical_transfer_function.shape == (16, 16)
    assert optical_transfer_function.dtype == np.complex64
    assert np.isclose(point_spread_function.sum(), 1.0)
    assert np.isclose(optical_transfer_function[8, 8], 1.0 + 0.0j)


def test_pupil_psf_reject_invalid_inputs() -> None:
    """
    Verify pupil and PSF helpers reject invalid optical inputs.
    """
    with pytest.raises(ValueError, match="radius_fraction"):
        build_circular_pupil_function(shape=(8, 8), radius_fraction=0.0)

    with pytest.raises(ValueError, match="PSF"):
        point_spread_function_from_pupil_function(np.zeros((8, 8), dtype=np.complex64))

    with pytest.raises(ValueError, match="DC"):
        optical_transfer_function_from_point_spread_function(np.zeros((8, 8), dtype=np.float32))


def test_low_pass_mask_is_centered() -> None:
    """
    Verify the low-pass mask keeps centered low frequencies and rejects corners.
    """
    mask = build_ideal_low_pass_filter(shape=(8, 8), cutoff_fraction=0.25)

    assert mask.shape == (8, 8)
    assert mask.dtype == np.float32
    assert mask[4, 4] == 1.0
    assert mask[0, 0] == 0.0


def test_low_pass_mask_rejects_invalid_cutoff() -> None:
    """
    Verify the low-pass mask rejects unsupported cutoff fractions.
    """
    with pytest.raises(ValueError, match="cutoff_fraction"):
        build_ideal_low_pass_filter(shape=(8, 8), cutoff_fraction=0.0)

    with pytest.raises(ValueError, match="cutoff_fraction"):
        build_ideal_low_pass_filter(shape=(8, 8), cutoff_fraction=0.75)
