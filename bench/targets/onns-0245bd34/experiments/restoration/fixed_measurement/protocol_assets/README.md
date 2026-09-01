# Fixed-Measurement Protocol Assets

This directory contains the version-controlled inputs that define formal
fixed-measurement restoration training:

- `fmd_split_manifest.json` freezes canonical FMD `avg50` images, group-disjoint
  train/validation/test membership, and every clean-image SHA-256 hash.
- `characterization/` freezes the 638 nm, 0.1 m, 512-sample optical operating
  point together with its source configuration, metrics, checks, and resolution
  budget.

Regenerate both assets with:

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe `
  -m scripts.restoration.freeze_fixed_measurement_protocol --device cuda
```

Formal training verifies these assets and the underlying image files before it
builds any model or writes any run directory.
