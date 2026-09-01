# Data Source Layer

The data-source layer turns raw dataset assets into the shared `RawSample`
contract. It owns dataset identity, raw asset preparation, file indexing, and
source provenance. It does not own experiment-specific task composition.

The file-backed source flow is:

```text
raw asset -> organizer -> manifest -> file source spec -> file index -> dataset adapter -> RawSample
```

## File Responsibilities

`registry.py`
: Maps public dataset names to builder classes and default keyword arguments.

`assets/specs.py`
: Defines raw asset facts such as expected paths, source URLs, archive names,
and readiness metadata.

`assets/organizers.py`
: Downloads, extracts, converts, or generates raw assets into readable source
trees. It also writes manifests.

`assets/manifests.py`
: Defines the manifest schema and read/write helpers for raw asset audit
records.

`indexing/file_sources.py`
: Defines file-backed source scanning rules for BioSR, FMD, BBBC038, BBBC039,
and targets.

`indexing/file_index.py`
: Builds deterministic file records, image identifiers, split names, and
max-sample selections.

`datasets/image_file_dataset.py`
: Implements the common file-backed dataset that returns `RawSample`
dictionaries.

`datasets/source_dataset.py`
: Wraps MNIST-like indexed vision datasets behind the same `RawSample`
contract.

`indexing/sampling.py`
: Owns deterministic class-balanced sampling for indexed classification
sources.

`indexing/idx_reader.py`
: Reads IDX files used by MNIST-style datasets.

`adapters/mnist.py`
: Defines the MNIST source adapter.

`adapters/fashion_mnist.py`
: Defines the FashionMNIST source adapter.

`adapters/bbbc.py`
: Defines BBBC038 and BBBC039 source adapters.

`adapters/biosr.py`
: Defines the BioSR source adapter.

`adapters/fmd.py`
: Defines the FMD source adapter.

`adapters/targets.py`
: Defines generated optical target source adapters.

## Public Surface

Normal callers should construct datasets through:

```python
from data import load
from data.configs import SourceConfig

dataset = load(SourceConfig(dataset_name="mnist"))
```

Raw asset preparation and readiness inspection should be accessed through:

```python
from data.data_source.assets.organizers import prepare_generated_target_assets
from data.data_source.assets.specs import inspect_raw_dataset_assets
```

Other modules are source-level building blocks. Tests and new dataset adapters
may import them directly, but experiment code should prefer the public
entrypoints above.

## Raw Asset Boundary

`data/raw/** is data, not source code`.

The data-source layer may read files under `data/raw`, but project source code
must not import Python modules from that tree. Dataset-provided helper scripts
under `data/raw` are treated as raw payloads.

## Dataset Adapter Contract

Every public source adapter should return `RawSample` dictionaries with:

- single-channel image tensor;
- integer label;
- string category;
- provenance containing dataset identity, split name, source index, sampled
  index, raw resolution, source path, image id, source URL or provenance URL,
  license, and source metadata where available.

Adapters should keep experiment semantics out of source loading.
