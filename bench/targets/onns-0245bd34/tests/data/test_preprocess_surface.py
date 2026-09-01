import importlib
import sys
from pathlib import Path

import pytest


def test_legacy_preprocess_package_is_removed() -> None:
    legacy_package = ".".join(("data", "preprocess"))
    legacy_root = Path("data") / "preprocess"

    assert not legacy_root.exists()
    assert not (legacy_root / "__init__.py").exists()
    assert not (legacy_root / "normalize.py").exists()
    assert not (legacy_root / "resize.py").exists()
    assert not (legacy_root / "encode.py").exists()
    assert not (legacy_root / "edge_detection.py").exists()
    assert not (legacy_root / "noise.py").exists()
    assert not (legacy_root / "degradation.py").exists()
    assert not (legacy_root / "pipeline.py").exists()

    for name in list(sys.modules):
        if name == legacy_package or name.startswith(f"{legacy_package}."):
            sys.modules.pop(name, None)
    importlib.invalidate_caches()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(legacy_package)


def test_stage_packages_expose_current_operator_modules() -> None:
    from data.preparation.normalize import normalize_image
    from data.preparation.resize import resize_image
    from data.perturbation.blur.gaussian_blur import apply_gaussian_blur
    from data.perturbation.blur.defocus_blur import apply_defocus_blur
    from data.perturbation.edges.canny_edges import build_canny_edge_map
    from data.perturbation.edges.sobel_edges import build_sobel_edge_map
    from data.perturbation.edges.laplacian_of_gaussian_edges import build_laplacian_of_gaussian_edge_map
    from data.perturbation.noise.additive_gaussian_noise import add_additive_gaussian_noise
    from data.perturbation.optics.coherent_imaging import optical_transfer_function_from_point_spread_function, point_spread_function_from_pupil_function
    from data.perturbation.optics.low_pass_filters import build_ideal_low_pass_filter
    from data.perturbation.optics.circular_pupil_functions import build_circular_pupil_function
    from data.encoding.optical_encode import encode_image_to_field

    assert callable(normalize_image)
    assert callable(resize_image)
    assert callable(add_additive_gaussian_noise)
    assert callable(apply_gaussian_blur)
    assert callable(apply_defocus_blur)
    assert callable(build_canny_edge_map)
    assert callable(build_sobel_edge_map)
    assert callable(build_laplacian_of_gaussian_edge_map)
    assert callable(build_circular_pupil_function)
    assert callable(build_ideal_low_pass_filter)
    assert callable(optical_transfer_function_from_point_spread_function)
    assert callable(point_spread_function_from_pupil_function)
    assert callable(encode_image_to_field)


def test_stage_package_roots_re_export_current_operators() -> None:
    from data.encoding import encode_image_to_field
    from data.encoding.optical_encode import encode_image_to_field as encode_image_to_field_impl
    from data.perturbation import add_additive_gaussian_noise, apply_defocus_blur, apply_gaussian_blur, build_canny_edge_map, build_circular_pupil_function, build_ideal_low_pass_filter, build_sobel_edge_map, build_laplacian_of_gaussian_edge_map, optical_transfer_function_from_point_spread_function, point_spread_function_from_pupil_function
    from data.perturbation.blur.defocus_blur import apply_defocus_blur as apply_defocus_blur_impl
    from data.perturbation.blur.gaussian_blur import apply_gaussian_blur as apply_gaussian_blur_impl
    from data.perturbation.edges.canny_edges import build_canny_edge_map as build_canny_edge_map_impl
    from data.perturbation.edges.sobel_edges import build_sobel_edge_map as build_sobel_edge_map_impl
    from data.perturbation.edges.laplacian_of_gaussian_edges import build_laplacian_of_gaussian_edge_map as build_laplacian_of_gaussian_edge_map_impl
    from data.perturbation.noise.additive_gaussian_noise import add_additive_gaussian_noise as add_additive_gaussian_noise_impl
    from data.perturbation.optics.coherent_imaging import optical_transfer_function_from_point_spread_function as optical_transfer_function_from_point_spread_function_impl
    from data.perturbation.optics.coherent_imaging import point_spread_function_from_pupil_function as point_spread_function_from_pupil_function_impl
    from data.perturbation.optics.low_pass_filters import build_ideal_low_pass_filter as build_ideal_low_pass_filter_impl
    from data.perturbation.optics.circular_pupil_functions import build_circular_pupil_function as build_circular_pupil_function_impl
    from data.preparation import normalize_image, resize_image
    from data.preparation.normalize import normalize_image as normalize_image_impl
    from data.preparation.resize import resize_image as resize_image_impl

    assert normalize_image is normalize_image_impl
    assert resize_image is resize_image_impl
    assert add_additive_gaussian_noise is add_additive_gaussian_noise_impl
    assert apply_defocus_blur is apply_defocus_blur_impl
    assert apply_gaussian_blur is apply_gaussian_blur_impl
    assert build_canny_edge_map is build_canny_edge_map_impl
    assert build_sobel_edge_map is build_sobel_edge_map_impl
    assert build_laplacian_of_gaussian_edge_map is build_laplacian_of_gaussian_edge_map_impl
    assert build_circular_pupil_function is build_circular_pupil_function_impl
    assert build_ideal_low_pass_filter is build_ideal_low_pass_filter_impl
    assert optical_transfer_function_from_point_spread_function is optical_transfer_function_from_point_spread_function_impl
    assert point_spread_function_from_pupil_function is point_spread_function_from_pupil_function_impl
    assert encode_image_to_field is encode_image_to_field_impl
