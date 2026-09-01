# 09 — Register portable materials

**What to build:** A researcher can register either a user optical-constant table or an immutable refractiveindex.info dataset and resolve deterministic in-band material samples without confusing portable data with solver-native identities.

**Blocked by:** 02 — Compile the standard studies.

**Status:** wontfix

**Superseded by:** [Four-brief delivery ticket 02](../../four-brief-metalens-delivery/issues/02-let-material-evidence-form-one-legal-height-domain.md).

- [x] Local `txt` and `csv` inputs require explicit columns and units and reject duplicate wavelengths or ambiguous values.
- [x] Refractiveindex.info inputs retain source bytes, source identity, attribution, and parsed canonical data.
- [x] Both sources produce one portable material-record contract with explicit interpolation and covered band.
- [x] Sampling is deterministic and never silently extrapolates.
- [x] Material records and samples round-trip through exact authority references.
- [x] No CST or COMSOL material implementation is introduced.
