---
status: accepted
---

# Adopt action-echo admission control

Adaptive Measurement uses two causally distinct decisions. Before an echo it
selects `probe`, `trial`, or `abstain`; after a physically delivered trial it
selects `admit` or `revert`. The robust protocol is four reference-on
quadrature observations, four reference-on echo observations, and one later
reference-on science observation. One optional uncertainty-resolving probe may
raise the bounded protocol to ten total observations. The older `4 + 1`
protocol remains a non-audited baseline, and a five-observation off-axis mode
is deferred until sideband separation is independently established.

The Action Echo tests whether the delivered field change conforms to a
prediction locked before the trial; it is not restoration truth and does not
alone prove prospective benefit. A rejected trial can be reverted before the
science observation but cannot be made physically nonexistent, so every trial,
echo, exposure, settling interval, and revert contributes to Episode Harm and
the complete budget.

This decision supersedes the single-stage `correct / probe / abstain` state
machine and `4 + 1` default in ADR-0020. It preserves ADR-0020's fixed
mechanical delay, reference-on science endpoint, truth-blind policy,
hardware-feasible action set, and prospective evidence requirements. Fixed
Measurement, its archived evidence identity, `data`, and `layers` remain
unchanged while the Adaptive implementation is replaced behind one episode
Interface.
