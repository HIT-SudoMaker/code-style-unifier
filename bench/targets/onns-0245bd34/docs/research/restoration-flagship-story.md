# Restoration Flagship Story: from learned re-encoding to self-verifying optical measurement

> **Superseded narrative provenance (2026-08-12).** ADR-0020 replaces the
> reference-off primary endpoint and `self-verifying` method name with a
> fixed-reference, reference-on, correctability-aware intelligent optical front
> end. Retain this document for the Fixed-to-Adaptive story development and
> figure reasoning only. Follow
> [`../restoration/intelligent-front-end.md`](../restoration/intelligent-front-end.md)
> for current claims and terminology.

- Status: accepted experiment narrative; not a scientific contract
- Direction accepted: 2026-08-11
- Scope: fixed-measurement evidence, adaptive/dynamic measurement hypothesis, main-text story and Figure logic
- Target readership: PhotoniX / Light: Science & Applications and adjacent high-impact optics venues
- Evidence discipline: Established = already supported; Inference = reasoned from evidence; Hypothesis = requires new experiment
- Canonical scientific authority: [restoration-research-design.md](../restoration-research-design.md)
- Positioning evidence: [restoration paper positioning](2026-08-11-restoration-paper-positioning.md)

This document records the current story so that experiments, figures and code architecture can be designed against one argument. It must evolve when decisive experiments fail or narrow the claim. It must not be used to promote an untested adaptive result into a conclusion.

The project has accepted this narrative as the prioritization guide for subsequent restoration experiments. The authority order is:

1. the canonical scientific design sets physical scope, hard gates and kill criteria;
2. this narrative determines which surviving claims and experiments receive priority;
3. the experiment protocol freezes budgets, endpoints, comparators and stopping rules;
4. the implementation architecture realizes that protocol without widening the claim.

Top-tier positioning is therefore a design target, not a promised publication outcome. Experiments remain authorized to narrow or kill any part of the story.

## 1. Executive decision

The paper should not be framed as a stronger image-restoration network, a failed attempt to beat NAFNet, or a generic SLM adaptive-optics system.

The strongest current story is:

> Static optical learning can reshape a measurement, but it cannot determine whether a scene-specific physical correction is supported. By moving learning from post-detection re-encoding to pre-detection spatiotemporal probing, a phase-only optical system may acquire just enough evidence to continue, correct or abstain, and let a later independent raw science observation decide whether the action was beneficial.

The memorable conceptual pair is:

> Static optical restoration learns a transform; adaptive optical measurement learns an experiment.

The protagonist is the measurement decision, not the neural network. The physical SLM is the instrument, temporal probing is the source of new evidence, learning allocates the observation budget, and the later raw science frame is the judge.

## 2. Provisional title strategy

### 2.1 Recommended working title

**Spatiotemporal optical probing enables self-verifying wavefront correction**

Why this is the best current title:

- it leads with the physical move rather than deep learning;
- it names the new capability rather than a model architecture;
- it does not depend on an unverified numerical speed claim;
- it leaves room for fixed measurement to serve as the discovered boundary;
- it remains bounded to wavefront correction rather than claiming universal image restoration.

### 2.2 Title variants and their evidence gates

1. **Sub-200-ms self-verifying wavefront correction by adaptive optical probing**
   - Use only if end-to-end delivered correction is measured below 200 ms at a preregistered percentile, including exposure, readout, inference, SLM settling and correction loading.

2. **Learning when and how to correct with adaptive optical measurements**
   - More accessible and concept-led, but it makes learning visually central and may sound less like an optical-principle paper.

3. **Self-verifying adaptive optical measurements for prospective wavefront correction**
   - Most precise about causal validation, but prospective is less immediately readable in a title.

4. **From optical re-encoding to self-verifying adaptive measurement**
   - Useful as a talk title or Discussion heading. It is not preferred as the article title because it foregrounds the laboratory chronology.

5. **Self-verifying adaptive optics for [native microscopy consequence]**
   - Preferred only if a strong native scientific endpoint becomes the decisive evidence. The bracket must be replaced by the actual demonstrated consequence, not a generic promise.

The words restoration, deep learning and dynamic should not be forced into the title. Restoration suggests post-processing; deep learning describes an implementation; dynamic is ambiguous unless the paper establishes time-varying aberration tracking.

## 3. One-sentence manuscript argument

Target argument, not yet an earned result:

> In local quasi-static coherent microscopy, we test whether a phase-only optical system can use at most a small number of adaptively selected spatiotemporal calibration observations to choose, withhold or continue a hardware-feasible correction, supported by a sub-200-ms decision loop and judged only on a causally later reference-free raw science observation.

The stronger future sentence, permitted only after all main gates pass, is:

> We show that post-detection optical re-encoding is learnable yet information-bound, whereas pre-detection spatiotemporal probing enables a phase-only microscope to decide within a fraction of a second when and how to correct, or when correction should be withheld, with every decision verified on a subsequent raw science frame.

Boundary:

- local, quasi-static, narrowband coherent transmission or phase microscopy;
- phase-dominant, hardware-correctable aberrations;
- reference-assisted calibration and reference-free science acquisition;
- no claim-facing post-detection restoration network;
- no general claim of superiority to MEMS deformable mirrors, fluorescence AO, nonlinear microscopy or fast atmospheric AO.

## 4. The narrative engine

### 4.1 Character and conflict

| Narrative role | Scientific identity |
|---|---|
| Protagonist | a physical measurement decision that must improve a future observation |
| Initial ability | a trainable phase-only optical transform |
| Conflict | post-detection re-encoding acts after the measurement has already closed |
| Discovery | learnability does not imply new measurement information or advantage over a strong digital observer |
| New move | move programmable phase modulation before the claim-facing observation and distribute it across time |
| Tension | each additional observation costs photons, reads, SLM states and time; an unsupported correction can be harmful |
| Resolution | actively choose the next probe, stop when action evidence is sufficient, and abstain when it is not |
| Verdict | a later independent reference-free raw science frame |
| Meaning | learning is most valuable when it designs evidence, not when it only reshapes an already formed image |

### 4.2 What makes the story non-obvious

The novelty cannot be merely SLM, phase diversity, a small neural network, uncertainty or eight to ten frames. Each exists in adjacent literature.

The non-obvious combination is conditional on demonstrating all of the following:

1. fixed learned optics is physically/algorithmically expressive but empirically bounded when it only re-encodes an existing detection;
2. a short temporal sequence is affordable at the device cadence and creates action-relevant identifiability;
3. the next probe depends on the observation history rather than following a fixed codebook;
4. uncertainty is translated into a physical continue/correct/abstain decision;
5. the selected correction is held in hardware;
6. benefit and harm are evaluated on a later independent raw science observation;
7. the full gain survives matched photons, reads, SLM states, settling, compute and wall time.

If these conditions are not jointly supported, the paper becomes a conventional learned AO method rather than a new measurement principle.

## 5. How Fixed Measurement becomes indispensable

Fixed Measurement is not an embarrassing prehistory and should not be narrated as a failure. It supplies the paradox that makes the adaptive design necessary.

### 5.1 Established evidence

- The formal fixed-measurement programme completed 36/36 frozen study units.
- Across light, medium and heavy conditions, the trained optical phase improved over zero phase by approximately 12.58, 12.33 and 12.29 dB.
- Frozen and joint optical-digital cascades nevertheless did not exceed the matched digital NAFNet-S baseline.
- The formal evidence is based on a frozen computational/digital-twin operating point; it is not yet a native microscopy hardware result.

See the [formal experiment report](../../results/restoration/fixed_measurement/reports/fixed_measurement_core_formal_v1/experiment_report.json).

### 5.2 Scientific interpretation

The fixed result supports two statements together:

1. **Optical expressivity:** a constrained phase-only transform can be learned and can materially change the optical output.
2. **Intervention boundary:** learning a post-detection transform does not by itself create an information advantage over a strong digital method that already observes the degraded image.

At inference, the historical replay path has the form

\[
X\rightarrow D\rightarrow Z_\theta\rightarrow \widehat X.
\]

When the learned parameters are fixed and the replay observation depends only on the already detected image D, data processing gives

\[
I(X;Z_\theta)\leq I(X;D).
\]

This does not prove that every digital implementation is faster, cheaper or more energy efficient. It establishes why post-detection optical re-encoding has no automatic measurement-information advantage.

### 5.3 Its role in the main paper

Fixed Measurement should do four jobs:

- provide the trained-phase-versus-zero-phase evidence that the optical degree of freedom is learnable;
- provide the matched digital comparison that exposes the late-intervention ceiling;
- define the strongest fixed optical baseline for the adaptive experiments;
- motivate the central move from learning a transform to learning what to measure.

It should not do the following:

- occupy half the paper as an independent restoration programme;
- be presented as proof that digital restoration cannot work;
- transfer its trained phase mask to native microscopy without a bridge experiment;
- force the adaptive episode to inherit the replay-specific data contract;
- turn the paper into a chronology of failure followed by a pivot.

### 5.4 Required bridge experiment

To keep fixed and adaptive evidence in one flagship paper, the bridge must compare, as far as physically possible:

- the same phase-only hardware degree of freedom;
- the same controlled aberration family;
- the same target or specimen class;
- the same raw science metric;
- fixed learned phase;
- optimized fixed temporal codebook;
- adaptive history-dependent probing;
- classical phase diversity or digital holography;
- a complete resource budget.

Without this bridge, the fixed result should remain a compact boundary panel and supporting evidence rather than a co-equal experimental branch.

## 6. Five-act paper story

### Act I — Reveal the capability

Open with the complete optical system, not its historical derivation. A programmable phase-only microscope applies a short sequence of probes, reads calibration observations, automatically chooses continue/correct/abstain, holds a physical correction, blocks the reference and acquires a later raw science frame.

Reader reaction sought: this is not a restoration network and not a static phase mask; the optical instrument is deciding what evidence it needs.

Evidence required:

- a real optical-path schematic;
- one representative complete episode;
- delivered phase states and timing;
- raw science before/after;
- at least one headline quantitative result.

### Act II — Expose the fixed-measurement paradox

Show that a learned phase transform strongly improves over zero phase while the hybrid chain still does not outperform the matched digital observer. Connect this empirical result to the post-detection information chain.

Reader reaction sought: light can learn, but late light cannot ask a new question.

Evidence required:

- fixed replay optical path;
- trained phase and zero-phase output;
- formal paired performance;
- matched digital comparison;
- explicit assumptions behind the information boundary.

### Act III — Turn time into an optical evidence dimension

Show why distinct aberration/hardware states can be ambiguous under one observation yet lead to different useful correction actions. Demonstrate how successive probes contract the set of plausible actions, not merely the coefficient error.

Reader reaction sought: the extra frames are not redundant images; they are selected physical questions.

Evidence required:

- ambiguity pairs;
- prefix curves for action agreement, regret or posterior contraction;
- fixed-codebook and Fisher-optimal controls;
- expected probe-count and early-stop distribution;
- measured correction-selection latency.

### Act IV — Make correction a risk-aware decision

The system must demonstrate that evidence can be insufficient. Compare continue/correct/abstain against always-correct, never-correct, last-trusted and simple-threshold policies. Show that abstention reduces harmful correction without collapsing coverage.

Reader reaction sought: the method is credible because it knows when not to act.

Evidence required:

- calibrated prospective benefit or harm risk;
- risk-coverage curves;
- harmful-correction rate;
- OOD and hardware-drift stress tests;
- complete matched-budget frontier.

### Act V — Let the future frame decide

Acquire the claim-facing science observation only after the decision, correction loading and settling. The calibration frames cannot become the headline result. The ending must be a native specimen or scientifically meaningful imaging endpoint, correction lifetime and a clear operating boundary.

Reader reaction sought: the improvement is physically prospective and scientifically useful, not digitally reconstructed after the fact.

Evidence required:

- reference-free raw science frames;
- safe, sham, opposite-sign and equal-RMS actions;
- multiple sessions, fields or depths;
- correction lifetime and amortized cost;
- a native scientific endpoint;
- explicit failure cases.

## 7. Main Figure architecture

This is a working architecture, not a frozen panel layout.

### Figure 1 — A self-verifying optical system learns when and how to correct

Archetype: schematic-led composite with one dominant hero panel.

- complete optical path and adaptive decision loop;
- temporal strip from first probe to correction decision;
- pupil residual phase, PSF or empirically valid spatial-frequency response across the episode;
- raw science before/after;
- compact latency, benefit and harm headline.

Figure 1 must show both capability and evidence. A concept-only optical cartoon is insufficient.

### Figure 2 — Static optical learning is expressive but information-bound

- historical fixed replay path;
- trained phase versus zero phase;
- learned physical response rather than a large training-loss panel;
- matched digital/frozen/joint comparison;
- information-chain interpretation.

Routine loss curves and optimizer diagnostics belong in Extended Data unless they answer a physical question.

### Figure 3 — Temporal probing resolves correction-relevant ambiguity

- single-observation ambiguity;
- successive probe histories;
- action-equivalence contraction;
- fixed versus adaptive probe choice;
- early stopping and observation-count distribution.

### Figure 4 — Adaptive decisions improve the benefit-risk-latency frontier

- no AO, fixed learned phase, optimized fixed codebook, Fisher probes, classical phase diversity/digital holography, single-shot learned sensing and adaptive probing;
- raw science gain versus wall time;
- raw science gain versus photon/read/state budget;
- harmful correction versus coverage;
- method ablations only where they test a main claim.

### Figure 5 — Prospective correction improves later raw science observations

- native microscopy image plate;
- independent raw science endpoints;
- specimen/session/field robustness;
- OOD abstention;
- correction lifetime and event-triggered recalibration;
- the clearest native scientific consequence.

The intended rhythm is:

> Figure 1 surprises; Figure 2 explains the necessity; Figure 3 reveals the mechanism; Figure 4 earns trust; Figure 5 establishes consequence and boundary.

## 8. Physics-language guardrail

The paper must not use modulation transfer function as a generic name for every frequency-domain change.

For the coherent branch, the phase-only pupil may be written as

\[
H_t(\mathbf k)
=
P(\mathbf k)
\exp\left\{i[\phi_{\mathrm{ab}}(\mathbf k)+u_t(\mathbf k)]\right\}.
\]

Phase correction can flatten the residual pupil phase and improve PSF, focus, interferometric contrast or an empirically defined spatial-frequency response even when the pupil magnitude P is unchanged. Use MTF only when the relevant intensity imaging model is linear and shift invariant and the reported MTF is experimentally defined and measured.

Recommended visual quantities:

- residual pupil phase;
- delivered correction phase;
- PSF/focal response and Strehl where valid;
- empirical contrast or two-dimensional transfer response;
- FRC or task-relevant raw science metric;
- coherent transfer function when the complex-field model is explicit.

## 9. Introduction architecture

Use a technical-challenge, observation-driven introduction rather than a chronological literature review.

### Paragraph 1 — The scientific stake

High-resolution imaging depends not only on reconstruction after detection but on whether the optical system acquires a trustworthy measurement before information is lost or confounded.

### Paragraph 2 — The existing trade-off

Digital restoration is powerful after detection; adaptive optics changes the physical measurement before detection. Static learned optics and single-shot learned sensing can be fast, but a fixed observation may remain ambiguous under unknown specimens, hardware mismatch and distribution shift.

### Paragraph 3 — The unresolved capability

Existing few-frame, learned and sequential AO methods do not by those properties alone establish a system that knows whether the evidence supports a beneficial future physical correction, or whether the action should be deferred or withheld.

### Paragraph 4 — The observation that motivates the method

Our fixed-measurement programme showed that a phase-only optical transform was strongly learnable yet did not outperform a matched digital observer when it only re-encoded an already detected image. This suggested that the critical design variable was not model size, but the point at which learning intervened.

### Paragraph 5 — Present study

Introduce the spatiotemporal probe-decision-correction-science sequence, the small observation budget, the continue/correct/abstain decision and the later independent raw science endpoint. State the coherent/quasi-static boundary explicitly.

## 10. Abstract skeleton

Do not draft final prose until the main experiments are available. The abstract should eventually follow:

1. Imaging systems need trustworthy physical correction before the claim-facing observation is formed.
2. Post-detection restoration and static/single-shot optical strategies face different information and reliability limits.
3. Here we introduce a phase-only spatiotemporal optical measurement strategy that decides whether to continue, correct or abstain.
4. Fixed Measurement establishes learnability and the late-intervention boundary.
5. Adaptive probing establishes the measured observation count, latency, prospective raw science gain and harm reduction relative to strong matched baselines.
6. Native microscopy establishes the scientific consequence and operating boundary.
7. The implication is a shift from learning image representations to learning trustworthy physical measurements.

No placeholder number should be silently replaced by an estimate. The final abstract must lead with the strongest preregistered physical result, not the best-looking sample.

## 11. Claim-evidence map

| Claim | Required evidence | Current status |
|---|---|---|
| A phase-only fixed transform is learnable | formal trained-phase versus zero-phase results | Established in frozen computational protocol |
| Fixed hybrid restoration does not outperform matched digital NAFNet-S | formal three-seed matched comparison | Established in frozen computational protocol |
| The fixed replay path has a post-detection information boundary | explicit Markov assumptions plus data-processing argument | Supported inference |
| Eight to ten device states fit within roughly 133-167 ms at 60 Hz | nominal device cadence | Supported lower-bound calculation; end-to-end timing unmeasured |
| Delivered correction is selected/applied below 200 ms | triggered hardware timing including settling, camera and compute | Hypothesis |
| A small number of probes identifies a useful correction action | oracle and action-identifiability experiments | Hypothesis |
| History-dependent probing beats the best fixed/Fisher codebook | complete matched-budget comparison | Hypothesis |
| Continue/correct/abstain reduces harmful physical correction | calibrated prospective risk and risk-coverage evidence | Hypothesis |
| Calibration transfers to a later reference-free science frame | randomized prospective acquisition | Hypothesis |
| The correction improves a native scientific endpoint and lasts long enough to amortize calibration | native specimens, sessions and lifetime study | Hypothesis |

## 12. Terminology ledger

| Canonical term | Definition | Avoid or restrict |
|---|---|---|
| Fixed Measurement | historical post-detection replay and fixed learned optical transform | fixed restoration as an unqualified synonym |
| adaptive optical measurement | next probe or decision depends on the observation history | dynamic measurement when adaptivity is intended |
| dynamic aberration | aberration changes across time or between episodes | using dynamic merely because several fixed frames exist |
| spatiotemporal probe | delivered phase state used to acquire action-relevant evidence | code, frame or mask when the physical action matters |
| calibration observation C_t | independently read reference-assisted observation before the decision | training image |
| phase action u_t | delivered hardware-feasible SLM phase command | predicted phase when not delivered |
| correction decision | continue, correct or abstain | classification without physical consequence |
| science observation Y_sci | later reference-free raw detector observation | reconstruction, output image or result image |
| prospective benefit Delta | raw science utility difference relative to the safe action | improvement without comparator |
| harmful correction | correction whose prospective benefit crosses the preregistered negative margin | failure without a quantitative definition |
| self-verifying | risk-aware action is evaluated on a later independent science observation | uncertainty-aware alone |
| correction-selection latency | time through evidence collection and decision | correction time when loading is excluded |
| end-to-end verification latency | time through later raw science acquisition | 1/6 s until measured |
| coherent transfer function / pupil response | frequency-domain quantity under the coherent model | MTF unless its imaging assumptions are satisfied |

The eventual method name is intentionally left open. Do not coin an acronym until the optical contract and native application are stable.

## 13. What the paper must not become

- a large network presented as the central novelty;
- an eight-to-ten-frame speed claim without end-to-end timing;
- a comparison against MEMS actuator bandwidth;
- a replayed-image experiment relabelled as native microscopy;
- a fixed sequence called adaptive because it varies in time;
- a calibration image reused as the science endpoint;
- an MTF story that violates the coherent phase-only model;
- a paper in which fixed and adaptive sections use unrelated systems and metrics;
- a collection of strong figures without one manuscript argument.

## 14. Experimental and architecture consequences

The narrative imposes the following implementation order:

1. measure the hardware timing chain and define correction-selection and end-to-end verification latency;
2. establish the delivered phase-only oracle and calibration-to-science transfer;
3. test action identifiability before training a large policy;
4. freeze fixed, Fisher and classical baselines before adaptive optimization;
5. implement a variable-length episode with continue/correct/abstain and a complete budget ledger;
6. acquire later raw science observations without post-detection restoration in the claim-facing path;
7. add dynamic tracking or event-triggered recalibration only after correction lifetime is measured.

The adaptive data model must not inherit the replay invariant of the historical RestorationScene/RestorationBatch contract. Fixed Measurement remains sealed; adaptive measurement receives its own episode, observation, action, decision, budget and science-result contracts. The detailed code architecture belongs in a separate ADR derived from this narrative and the canonical research design.

The maximum probe count should be a protocol field, not a hard-coded architectural assumption. The current scientific design uses T <= 8; a move to T <= 10 requires timing/oracle evidence and an explicit protocol decision.

## 15. Publication-positioning gate

This story has PhotoniX/LSA-level potential only if the paper establishes a new optical measurement/control capability rather than a modest algorithmic improvement.

Proceed with the flagship framing if:

- delivered phase-only oracle headroom is robust;
- the bridge links fixed and adaptive evidence coherently;
- adaptive probing beats strong fixed/classical baselines under a complete budget;
- the system reduces harmful corrections at useful coverage;
- benefit appears in later independent raw science observations;
- a native microscopy endpoint is strong and reproducible.

Narrow the paper if:

- adaptive probing matches but does not beat the best fixed codebook;
- classical phase diversity or digital holography matches the learned policy;
- abstention contributes no measurable harm reduction;
- only synthetic or replayed targets show benefit;
- timing is materially slower than the nominal cadence suggests.

Kill the central claim if:

- the delivered phase-only oracle has no stable prospective headroom;
- reference-assisted calibration does not transfer to reference-free science acquisition;
- the correction action is not identifiable within a practical observation budget;
- the apparent gain depends on post-detection restoration or circular science-frame selection.

## 16. Current conclusion

The paper should tell one story:

> A static optical transform can be learned, but trustworthy physical correction requires the instrument to acquire evidence about its own action. A short sequence of phase-only measurements may make that evidence affordable, allow the system to decide when not to act, and convert optical restoration from representation processing into prospective measurement control.

The emotional and logical arc is:

> surprise with the complete capability; reveal the fixed paradox; explain time as evidence; prove the decision is safer and better; close with a future raw science observation.

This narrative is provisional. Experiments decide which title, verbs and claims survive.
