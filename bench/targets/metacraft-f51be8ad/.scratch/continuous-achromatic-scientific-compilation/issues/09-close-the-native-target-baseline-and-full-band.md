# 09 — Close the Native target, baseline, and full band

**What to build:** When the Native spectral campaign yields a candidate, assign and freeze the exact continuous aperture, execute its post-freeze blind-verification work, and evaluate the compensated target and same-contract PB-only chromatic baseline over the full dense grid through complete Fields, focal regions, and focus. If the candidate campaign refused, retain that publication-blocking branch without fabricating this closure.

**Blocked by:** 05 — Close, replay, and inspect one continuous Result; 08 — Run the Native spectral candidate campaign.

**Status:** ready-for-human

- [ ] The nominal target uses the new publication Brief, its resolved 63-site central-diameter Lattice, and one immutable geometry/orientation layout.
- [ ] The 16 additional blind-verification wavelengths execute only after the nominal geometry and orientation maps freeze and only for the union of assigned and PB-only baseline geometries.
- [ ] Candidate plus post-freeze work never exceeds the campaign's frozen 6800-work global ceiling.
- [ ] All five design, four interleaved-validation, and 16 post-freeze blind-verification wavelengths have complete converted and retained Fields and focal regions.
- [ ] The PB-only baseline reuses byte-equal aperture coordinates and the identical propagation, normalization, and focus contracts.
- [ ] Design, validation, and blind-verification metrics are reported separately before dense complete-band summaries.
- [ ] Blind-verification failure blocks publication success without altering eligibility, thresholds, assignment, or the aperture.
- [ ] Device-level transmission, focus efficiency, focal shift, spot width, and leakage gates are frozen independently of unit-cell eligibility floors.
- [ ] Missing or incomplete focus at any wavelength produces an exact typed stop and no Result.
- [ ] A complete Result replays byte-exactly without Native or numerical work.
- [ ] The retained comparison establishes achromatic improvement only from comparable compensated and baseline summaries.
- [ ] A refused candidate leaves this ticket scientifically blocked rather than triggering silent redesign.

## Comments

- 2026-08-15 readiness audit: Tickets 01--05 already freeze the 63-site authoritative Lattice and one aperture, project blind work only for `used_geometries`, enforce the 6800-work ceiling, form the same-contract compensated/PB-only 2-by-25 Field and focus matrix with role-separated summaries, and restore the complete Result without numerical work.
- Deterministic gap: add one content-addressed device-publication gate over transmission, focus efficiency, focal shift, spot width, leakage, complete-band comparison, and the existing band-verification evidence. The current engineering cell profile and dense phase/curvature verdict intentionally do not own these device gates.
- Human gate: the owner must first accept a positive Ticket 08 Native candidate, freeze the device-level metric definitions and numerical thresholds before examining device outcomes, and authorize the Native/post-freeze evidence action. Synthetic closure cannot satisfy this ticket's Native publication evidence; `DEVELOPMENT.md` separately gates Native execution, Rust changes, and publication on explicit owner authorization.
