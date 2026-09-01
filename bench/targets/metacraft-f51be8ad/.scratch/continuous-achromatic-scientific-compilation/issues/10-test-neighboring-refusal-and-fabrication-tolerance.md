# 10 — Test neighboring refusal and fabrication tolerance

**What to build:** Stress the frozen continuous route with one predeclared higher-delay neighboring Brief and one frozen lateral-and-height fabrication perturbation protocol. The system must distinguish correct refusal from numerical failure and report nominal robustness without changing the selected device after seeing perturbation results.

**Blocked by:** 09 — Close the Native target, baseline, and full band.

**Status:** ready-for-human

- [ ] The neighboring Brief is fixed before execution and requires strictly more relative delay than the nominal target.
- [ ] Complete insufficient response produces the expected typed physical refusal and never a false Result.
- [ ] Missing capability, missing evidence, and numerical incompletion remain distinct from that refusal.
- [ ] Lateral dimensions and height are perturbed under one content-addressed tolerance protocol around the frozen nominal layout.
- [ ] Nominal and perturbed runs use the same wavelengths, propagation, normalization, and focus metrics.
- [ ] The nominal geometry and orientation maps are not redesigned in response to tolerance outcomes.
- [ ] Worst-case, distribution, and failed-perturbation observations are retained rather than reporting only favorable samples.
- [ ] Any robustness claim is bounded to the tested perturbation protocol.

## Comments

- 2026-08-15 readiness audit: the resolved route already distinguishes typed candidate, physical refusal, unavailable evidence, and numerical incompletion; the reviewed `NA = 0.24719` neighboring target exercises the higher-delay branch in deterministic tests; and the frozen aperture exposes immutable geometry, orientation, delay, and adjacency-transition diagnostics.
- Deterministic gap: retain a canonical neighboring Brief plus one content-addressed lateral-and-height perturbation protocol, bounded request projection, nominal-versus-perturbed comparison, and worst-case/distribution/failed-sample evidence without permitting redesign.
- Human gate: the owner must freeze the neighboring Brief identity, lateral and height perturbation values, sampling plan, failure handling, robustness metrics, and acceptance bounds before observations, then separately authorize any Native execution. Test or synthetic perturbations may validate the protocol but cannot satisfy the Native robustness claim; `DEVELOPMENT.md` separately gates Native execution, Rust changes, and publication on explicit owner authorization.
