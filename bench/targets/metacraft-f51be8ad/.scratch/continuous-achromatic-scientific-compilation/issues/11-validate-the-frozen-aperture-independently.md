# 11 — Validate the frozen aperture independently

**What to build:** Test the analytical PB rotation on a bounded set of directly simulated rotated cells, then evaluate the already frozen nominal aperture with one independent device-scale or cross-method realization under a predeclared transfer contract. These checks validate rotational covariance, local-periodic transfer, and device behavior; they do not redesign the aperture or reuse the same approximation under another label.

**Blocked by:** 09 — Close the Native target, baseline, and full band; 10 — Test neighboring refusal and fabrication tolerance.

**Status:** ready-for-human

- [ ] The validation method, approximations, mesh or convergence protocol, coordinates, metrics, and tolerances are declared before observing agreement.
- [ ] Representative geometries, angles, and wavelengths for direct rotated-cell Native spot checks are declared before execution and include nominal, high-leakage or resonant-risk cases.
- [ ] Direct rotated-cell observations compare converted PB phase, converted power, and retained-channel leakage with the analytical rotation law without feeding results back into assignment.
- [ ] The exact nominal geometry and orientation maps are transferred without optimization or correction.
- [ ] Independent validation includes predeclared high-jump neighbor transition classes from the frozen aperture diagnostics.
- [ ] Nominal and independent results are compared on compatible coordinates and quantities.
- [ ] Agreement, disagreement, numerical uncertainty, and known model differences are all retained.
- [ ] A narrower cross-method validation is named honestly and does not claim whole-device Maxwell validation.
- [ ] An unexplained rotated-cell, neighbor-transfer, or device-scale disagreement blocks the publication-success gate.
- [ ] Independent artifacts and receipts carry exact environment, implementation, and source identities.

## Comments

- 2026-08-15 readiness audit: Tickets 01--05 provide the exact frozen geometry/orientation maps, handed analytical PB law, used-geometry set, adjacency transition classes, complete Field/focus quantities, and content-addressed evidence needed as validation inputs.
- Deterministic gap: the current periodic-work Interface represents unrotated cross sections and has no post-freeze rotated-cell request/receipt contract. A bounded rotated-cell protocol and one honest independent transfer/comparison Evidence record are still required; they should reuse the existing Native Adapter where applicable and must not become an optimizer or second lifecycle.
- Human gate: before observing agreement, the owner must choose the genuinely independent method, approximation scope, representative geometries/angles/wavelengths and high-jump transitions, coordinates, mesh or convergence protocol, metrics, tolerances, and disagreement rule, and authorize the external validation. Recorded or synthetic evidence may exercise the protocol but cannot satisfy independent Native validation; `DEVELOPMENT.md` separately gates Native execution, Rust changes, and publication on explicit owner authorization.
