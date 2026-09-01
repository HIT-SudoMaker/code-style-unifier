from pathlib import Path


def test_data_surface_matches_stage_architecture() -> None:
    data_root = Path("data")
    legacy_root = data_root / "preprocess"
    legacy_preprocessing_root = data_root / "preprocessing"

    assert (data_root / "__init__.py").exists()
    assert not (data_root / "create_dataset.py").exists()
    assert not (data_root / "factory" / "pipeline_factory.py").exists()
    assert not (data_root / "factory" / "__init__.py").exists()
    assert (data_root / "configs" / "stages.py").exists()
    assert not (data_root / "configs" / "pipeline.py").exists()
    assert (data_root / "data_source" / "dataset_root.py").exists()
    assert (data_root / "data_source" / "indexing" / "idx_reader.py").exists()
    assert not (data_root / "data_source" / "indexing" / "idx_format_reader.py").exists()
    assert (data_root / "data_source" / "indexing" / "sampling.py").exists()
    assert (data_root / "data_source" / "indexing" / "file_index.py").exists()
    assert (data_root / "data_source" / "datasets" / "source_dataset.py").exists()
    assert (data_root / "data_source" / "datasets" / "image_file_dataset.py").exists()
    assert (data_root / "data_source" / "adapters" / "biosr.py").exists()
    assert (data_root / "data_source" / "adapters" / "fmd.py").exists()
    assert (data_root / "data_source" / "adapters" / "bbbc.py").exists()
    assert (data_root / "data_source" / "adapters" / "targets.py").exists()
    assert (data_root / "data_source" / "adapters" / "mnist.py").exists()
    assert (data_root / "data_source" / "adapters" / "fashion_mnist.py").exists()
    assert (data_root / "preparation" / "normalize.py").exists()
    assert (data_root / "preparation" / "resize.py").exists()
    assert (data_root / "preparation" / "dataset.py").exists()
    assert (data_root / "perturbation" / "noise" / "additive_gaussian_noise.py").exists()
    assert (data_root / "perturbation" / "noise" / "poisson_gaussian_noise.py").exists()
    assert (data_root / "perturbation" / "blur" / "defocus_blur.py").exists()
    assert (data_root / "perturbation" / "blur" / "gaussian_blur.py").exists()
    assert (data_root / "perturbation" / "edges" / "canny_edges.py").exists()
    assert (data_root / "perturbation" / "edges" / "sobel_edges.py").exists()
    assert (data_root / "perturbation" / "edges" / "laplacian_of_gaussian_edges.py").exists()
    assert (data_root / "perturbation" / "optics" / "circular_pupil_functions.py").exists()
    assert (data_root / "perturbation" / "optics" / "coherent_imaging.py").exists()
    assert (data_root / "perturbation" / "optics" / "low_pass_filters.py").exists()
    assert (data_root / "perturbation" / "dataset.py").exists()
    assert (data_root / "encoding" / "optical_encode.py").exists()
    assert (data_root / "encoding" / "dataset.py").exists()
    assert not (data_root / "contracts.py").exists()
    assert not (data_root / "scenarios.py").exists()
    assert not legacy_root.exists()
    assert not (legacy_root / "__init__.py").exists()
    assert not (legacy_root / "pipeline.py").exists()
    assert not (legacy_root / "normalize.py").exists()
    assert not (legacy_root / "resize.py").exists()
    assert not (legacy_root / "encode.py").exists()
    assert not (legacy_root / "noise.py").exists()
    assert not (legacy_root / "degradation.py").exists()
    assert not (legacy_root / "edge_detection.py").exists()
    assert not (legacy_preprocessing_root / "preprocessing.py").exists()
    assert not (legacy_preprocessing_root / "optical_encoding.py").exists()


def test_data_package_exports_only_stage_functions() -> None:
    import data

    assert data.__all__ == ("load", "prepare", "perturb", "encode")
    assert not hasattr(data, "create_dataset")


def test_stage_packages_export_dataset_wrappers() -> None:
    from data.encoding import EncodedDataset
    from data.preparation import PreparedDataset
    from data.perturbation import PerturbedDataset

    assert PreparedDataset.__name__ == "PreparedDataset"
    assert PerturbedDataset.__name__ == "PerturbedDataset"
    assert EncodedDataset.__name__ == "EncodedDataset"


def test_data_source_exports_single_registry_surface() -> None:
    import data.data_source as data_source

    assert hasattr(data_source, "DATASET_REGISTRY")
    assert hasattr(data_source, "resolve_dataset_entry")
    assert not hasattr(data_source, "DATASET_BUILDERS")
