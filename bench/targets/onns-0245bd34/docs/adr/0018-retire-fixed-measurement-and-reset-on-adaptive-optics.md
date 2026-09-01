---
status: accepted
---

# Retire fixed measurement and reset on adaptive optics

The fixed-measurement serial restoration route is retired as an active
research architecture because completed matched studies did not establish an
advantage over credible digital neural-network baselines. The next research
line starts from a falsifiable pre-detection adaptive-optics hypothesis:
independently read calibration probes support a correction, continuation, or
abstention decision; a deployable correction is held for separate science
observations; and every comparison includes acquisition and timing cost. The
proposed method ends at the physically corrected detector output rather than a
post-detection restoration network.

The fixed-measurement implementation and canonical evidence remain read-only
history rather than dependencies of the new experiment. `data` and `layers`
remain frozen reusable foundations; adaptive episode composition belongs to
the experiment. This supersedes ADR-0008's fixed eight-step framing and its
positive characterization of fixed measurement, while retaining the useful
idea of active identification under an upper measurement budget.
