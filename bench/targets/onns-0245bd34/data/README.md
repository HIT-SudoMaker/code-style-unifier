# Data

`data` provides four small, composable stages:

```python
from data import encode, load, perturb, prepare
from data.configs import (
    EncodingConfig,
    GaussianBlurConfig,
    PerturbationConfig,
    PreparationConfig,
    SourceConfig,
)

raw = load(SourceConfig(dataset_name="fmd", dataset_root="data/raw"))
prepared = prepare(
    raw,
    PreparationConfig(
        image_resolution=(64, 64),
        array_resolution=(128, 128),
    ),
)
perturbed = perturb(
    prepared,
    PerturbationConfig(
        operations=(GaussianBlurConfig(kernel_size=3),),
    ),
)
encoded = encode(
    perturbed,
    EncodingConfig(encoding_method="intensity"),
)
```

There is deliberately no `create_dataset`, pipeline factory, or output-stage
switch. Classification, restoration, and validation code choose which stages
to call and in what order.

## Contracts

```text
load       -> image
prepare    -> image
perturb    -> image + reference_image
encode     -> input_image + input_field + optional reference_image
```

- `load` returns a `RawSample` with an image, label, category, and provenance.
- `prepare` normalizes, resizes, pads, and optionally tapers the image.
- `perturb` applies an ordered operation list and keeps the prepared image as
  `reference_image`.
- `encode` produces a float32 `input_image` and complex64 `input_field`.

The generic module uses neutral names. A restoration experiment may map
`reference_image` to `clean_image` and `input_image` to `degraded_image`; a
classification experiment may add detector targets. Those task meanings stay
outside `data`.

Perturbation modules include:

- additive Gaussian noise and photon shot noise plus Gaussian read-noise;
- Gaussian low-pass blur and disk-PSF defocus blur;
- Canny binary edge maps, Sobel gradient-magnitude edge maps, and
  Laplacian-of-Gaussian edge response maps;
- ideal circular low-pass filters, circular aperture pupil functions, and
  pupil-function to PSF and OTF conversions.

`PerturbationConfig.operations` is ordered. Random operations are reproducible
when a degradation or sampling seed is supplied.

## Raw assets

`data/raw/** is data, not source code`.

Raw assets may include archives, extracted images, generated targets, and
manifests. They are read by source adapters but never imported as Python code.
Dataset-provided helper scripts should not be kept under `data/raw`.

Expected roots include:

```text
data/raw/
  mnist/
  fashion_mnist/
  biosr/
  fmd/
  bbbc038/
  bbbc039/
  targets/
```

Asset inspection and organization live in
`data.data_source.assets.specs` and `data.data_source.assets.organizers`.

## Experiment boundary

Experiments own task composition. They select sources and stage configs, then
wrap the generic result in their own task contract. Hardware effects, metrics,
baselines, split policies, and training recipes do not belong in `data`.

## Adding a source

A new file-backed source usually needs:

1. Asset facts in `data/data_source/assets/specs.py`.
2. Download or extraction logic in `data/data_source/assets/organizers.py`.
3. Scanning rules in `data/data_source/indexing/file_sources.py`.
4. An adapter under `data/data_source/adapters/`.
5. A registry entry in `data/data_source/registry.py`.
6. Tests for loading and provenance.
