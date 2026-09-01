from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_data_readme_documents_public_mainline() -> None:
    content = _read_text("data/README.md")

    required_phrases = (
        "from data import encode, load, perturb, prepare",
        "SourceConfig",
        "PerturbationConfig",
        "operation list",
        "There is deliberately no `create_dataset`",
        "load       -> image",
        "prepare    -> image",
        "perturb    -> image + reference_image",
        "encode     -> input_image + input_field + optional reference_image",
        "additive Gaussian noise",
        "photon shot noise plus",
        "Gaussian read-noise",
        "Canny binary edge maps",
        "Sobel gradient-magnitude edge maps",
        "Laplacian-of-Gaussian edge response maps",
        "Gaussian low-pass blur",
        "disk-PSF defocus blur",
        "ideal circular low-pass filters",
        "circular aperture pupil functions",
        "pupil-function to PSF and OTF",
        "data/raw/** is data, not source code",
        "Dataset-provided helper scripts should not be kept under `data/raw`",
        "Experiments own task composition",
        "data.data_source.assets.specs",
        "mnist/",
        "fashion_mnist/",
        "biosr/",
        "fmd/",
        "bbbc038/",
        "bbbc039/",
        "targets",
    )

    for phrase in required_phrases:
        assert phrase in content


def test_data_source_readme_documents_module_roles() -> None:
    content = _read_text("data/data_source/README.md")

    required_phrases = (
        "raw asset -> organizer -> manifest -> file source spec -> file index -> dataset adapter -> RawSample",
        "assets/specs.py",
        "assets/organizers.py",
        "assets/manifests.py",
        "indexing/file_sources.py",
        "indexing/file_index.py",
        "datasets/image_file_dataset.py",
        "datasets/source_dataset.py",
        "adapters/mnist.py",
        "adapters/fashion_mnist.py",
        "adapters/bbbc.py",
        "adapters/biosr.py",
        "adapters/fmd.py",
        "adapters/targets.py",
        "assets/organizers.py",
    )

    for phrase in required_phrases:
        assert phrase in content
