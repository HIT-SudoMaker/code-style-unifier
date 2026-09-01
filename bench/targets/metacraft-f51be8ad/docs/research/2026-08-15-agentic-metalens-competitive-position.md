---
record_type: research_record
date: 2026-08-15
status: research_finding
authority_level: none
current_capability: false
scope: primary-source competitive audit for an agentic metalens paper
---

# Agentic metalens competitive position: MetaCraft vs. Self-Evolving, MetaChat, and adjacent systems

## Research question and source boundary

This note answers four questions:

1. What did *A Self-Evolving Agentic Framework for Metasurface Inverse Design* actually establish?
2. How direct a competitor is MetaChat?
3. What are the closest recent agentic or LLM-based competitors?
4. Can a paper limited to metalenses be publishable, and what evidence would make it defensible?

Only primary sources were used: the papers/preprints, publisher pages, authors' official repositories and datasets, plus this repository's source-of-truth documents and code. The local final PDF of the Self-Evolving paper and the local clone of the official MetaChat repository were inspected as well. No claim below relies on press coverage, review articles, citation aggregators, or vendor summaries.

## Executive decision

**Yes, a metalens-only paper is publishable.** Device breadth is not the blocking variable. A strong paper can be organized around one device family if it establishes a new, falsifiable method and closes the chain from target to physical device behavior. Metalens-specific precedents include a data-free optimization method demonstrated on and experimentally validated with a 1-mm cylindrical metalens, and a large-scale aperiodic inverse-design method validated with fabricated centimetre-scale/high-NA/polychromatic meta-optics ([Zhelyeznyakov et al., 2023](https://doi.org/10.1038/s44172-023-00107-x); [Chung et al., 2022](https://doi.org/10.1038/s41467-022-29973-3)).

**MetaCraft is not yet ready to claim “agentic metalens inverse design.”** Its current implemented strength is an unusually strict evidence-governed metalens research/compiler architecture: immutable scientific state, content-addressed advice and evidence, exact external-work receipts, resumability, typed absence/refusal, and distinct low/high-NA and propagation/PB proof routes ([DESIGN.md](../../DESIGN.md); [SCIENCE.md](../../SCIENCE.md)). Its current science nevertheless uses deterministic finite-library or pointwise selection; the repository explicitly says there is no optimizer implementation, and complete native execution of all four benchmark cases remains future work ([SCIENCE.md](../../SCIENCE.md#selection-and-optimization); [ROADMAP.md](../../ROADMAP.md)). The continuous-compensation proof tail is now implemented, but the Native evidence remains a reference-wavelength feasibility screen rather than a completed achromatic lens ([experiment record](2026-08-14-achromatic-experiment-result.md)).

**The publishable position is not “more agents” or “a better chatbot.”** Self-Evolving already owns learned skill evolution for parameterized unit-cell code generation; MetaChat owns very fast prompt-to-freeform, multiwavelength metalens generation in its learned 2-D surrogate domain; MetaDesigner already shows a Solver–Verifier–Researcher–Optimizer–Programmer system designing an RGB metalens. MetaCraft's credible open territory is **evidence-governed agentic metalens design**: an agent may propose work, but cannot turn advice, solver execution, or an unbracketed focus into a scientific result; every successful or refused conclusion must be replayable from exact evidence.

That is a meaningful scientific claim only if experiments show that the evidence contract prevents false success, survives interruption and stale/corrupt evidence, and still produces competitive physical lenses. Architecture and test count alone are not publication evidence.

## Competitor map

| System | What is genuinely demonstrated | Device/physics scope | Strongest result | Main boundary relevant to MetaCraft |
|---|---|---|---|---|
| **Self-Evolving** (Huang et al., 2026) | Coding agent + human-readable skill + meta-agent revision + deterministic TorchRDIT evaluator | Seven parameterized unit-cell task families; mostly reflective gratings plus two pillar transmission/phase families | Same-type success 38%→74%; physical-criteria fraction 0.51→0.87; new-type-B success 20%→90% | Measures executable inverse-design code and unit-cell criteria, not a metalens aperture-to-focus closure; one solver, one benchmark design, one base model; public repo excludes full paper experiment suite |
| **MetaChat** (Lupoiu et al., 2025) | AIM multi-agent orchestration + material/API tools + FiLM WaveY-Net Maxwell surrogate + freeform optimizer | 2-D dielectric freeform metasurfaces, demonstrated for lenses and deflectors over 400–700 nm | 270k-example surrogate; dual-wavelength 180-µm metalens; 300k surrogate simulations on 8 GPUs in 10 min; 57.1%/49.7% far-field peak-lobe energy | Strongest direct speed/freeform competitor; evidence is bounded by learned 2-D surrogate domain, and the reported metalens result is propagated from surrogate-generated fields rather than fabricated device validation |
| **MetaDesigner** (Wu et al., 2026 preprint) | Solver, Verifier, Researcher, Optimizer and Programmer agents with CST, retrieval and memory | RGB metalens, multiplane hologram and optoelectronic style transfer | 512×512-cell RGB metalens in 16 min 14 s; average focusing efficiency 20%; verifier catches physics/report errors | Direct system-level competitor, but authors themselves call for higher-fidelity simulation, experiment/fabrication constraints and field-specific standards; no public code/data found in the preprint audit |
| **Lu–Malof–Padilla** (2025) | Agent builds a forward surrogate and uses Neural Adjoint for inverse design | One 14-parameter all-dielectric metamaterial unit cell | Autonomous model/optimizer workflow on existing simulation subsets | Existing subsets stand in for simulations that could take months; agent inverse-design MSE is worse than the two human benchmarks; not a full device |
| **MCP-enabled LLM** (Huang et al., 2025) | LLM invokes TorchRDIT through two MCP servers, five APIs and 16 templates | Huygens meta-atom/code-generation tasks | 94%/100% execution success under two prompt conditions; 23%/76% satisfaction | Useful tool-interface baseline, not metalens-level design; hallucinated APIs remained a major error source |
| **Chat-to-Chip** (Zhang et al., 2025) | Fine-tuned open LLM maps tokenized geometry and spectral descriptions | 4×4 control-grid unit cell and 31-point spectrum | Test MSE 3.4×10⁻³; about 2 s inference | Adjacent LLM inverse model, not agentic and not an aperture/device proof |
| **AutoPhotonicDesign** (Kharel et al., 2026 preprint) | General coding agent in a deterministic propose–simulate–evaluate loop with acceptance criteria and journals | Photonic integrated circuits, not metasurfaces | Public code and append-only run journals; DRC/evaluator-driven closed loops | Architecturally close evidence-based competitor outside metasurfaces; also documents a case where expert intervention was required before the loop could proceed |

Sources: [Self-Evolving paper](https://arxiv.org/html/2604.01480) and [official code](https://github.com/yi-huang-1/evo-metaoptics); [MetaChat paper](https://arxiv.org/html/2503.20479) and [official code](https://github.com/jonfanlab/metachat); [MetaDesigner preprint](https://arxiv.org/abs/2605.22647); [Lu et al. paper](https://arxiv.org/html/2506.06935); [MCP-enabled LLM paper](https://doi.org/10.1515/nanoph-2025-0507); [Chat-to-Chip paper](https://doi.org/10.1515/nanoph-2025-0343); [AutoPhotonicDesign preprint](https://arxiv.org/abs/2606.00915) and [official code](https://github.com/flexcompute/autophotonicdesign).

## 1. Audit of *A Self-Evolving Agentic Framework for Metasurface Inverse Design*

### What it contributes

Huang et al. couple a coding agent to a fixed differentiable RCWA solver, TorchRDIT. A deterministic evaluator scores generated code against physical criteria, while a meta-agent uses rollout feedback to rewrite explicit human-readable skill/context files; model weights and the physics solver remain fixed. In four evolution iterations with Claude Sonnet 4.6, the learned skill improves same-type task success from 38% to 74%, criteria pass fraction from 0.51 to 0.87, and mean attempts from 4.10 to 2.30. One unseen family stays near ceiling (92%→90%); another rises from 20% to 90% ([paper](https://arxiv.org/html/2604.01480); [final publication DOI](https://doi.org/10.1002/lpor.71739)).

This is a real and reasonably controlled result: a fixed solver, a deterministic evaluator, explicit train/validation/test splits, per-criterion outcomes, attempts, and before/after skill comparisons. Calling it simply “rough” would be unfair.

### What it does not establish

The benchmark contains 50 training, 15 validation and 50 test prompts drawn from seven abstract parameterized unit-cell families. G1–G5 are reflective grating-style tasks; G6 and the auxiliary family use rectangular pillars with transmission/phase objectives. The benchmark intentionally chooses attainable parameterizations to isolate agent learning from impossible physics. It therefore tests **whether an agent can generate working inverse-design code for bounded unit-cell tasks**, not whether an autonomous system can realize a full metalens, predict its aperture field, find a bracketed focus, survive fabrication tolerance, or match experiment ([paper, benchmark section](https://arxiv.org/html/2604.01480)).

The “new-type” result also needs careful reading. New-type-A is a genuinely different device class and remains roughly flat overall, with one rescued task and two regressions. For new-type-B, validation and test belong to the same broader reflective class, so the paper describes the gain as within-class learning from validation rather than proof of unrestricted cross-class generalization. The authors explicitly limit the study to one solver stack, one benchmark design and one base model ([paper, discussion](https://arxiv.org/html/2604.01480)).

The official repository exposes the core runtime, deterministic evaluator, one IID 50/15/50 split and one example configuration. Its README explicitly excludes plotting, publication-report generation, the complete paper experiment suite, private run traces and dataset-generation tooling; only the IID split is public ([official repository](https://github.com/yi-huang-1/evo-metaoptics)). Thus the algorithmic core is inspectable, but the headline OOD tables are not currently end-to-end reproducible solely from the public package.

### Competitive implication

Self-Evolving owns a strong claim that MetaCraft should not imitate weakly: **solver-feedback-driven evolution of an agent's procedural skill**. MetaCraft can instead test a different hypothesis: whether immutable authority and evidence gating lower the rate of scientifically false completion while maintaining physical performance. The clean head-to-head is not “which prompt is smarter,” but:

- raw coding agent;
- coding agent + static skill;
- Self-Evolving-style skill revision;
- MetaCraft evidence-governed execution, with and without its authority/evidence gates.

All variants should receive identical briefs, solver access, budgets and deterministic evaluators. Agent success must be separated from physical success and from **false-positive success**—a run that reports success without complete admissible evidence.

## 2. Audit of MetaChat

### What it contributes

MetaChat is the strongest direct competitor for rapid freeform metalens synthesis. Its Agentic Iterative Monologue coordinates specialist agents and APIs; a FiLM-conditioned WaveY-Net serves as a wavelength-conditioned 2-D Maxwell surrogate. The surrogate was trained on 270,000 finite-difference frequency-domain examples and tested on 30,000 examples over 400–700 nm. The paper reports mean normalized MAE around 0.06 and inverse-design wavelength error improving from 0.098 to 0.043 across the band ([paper](https://arxiv.org/html/2503.20479)).

For a dual-wavelength lens, MetaChat constructs a 180-µm aperture with 100 1.8-µm superpixels and a 40-nm minimum feature. It reports 300,000 surrogate simulations on eight GPUs in ten minutes and 57.1%/49.7% of total far-field energy in the two target peak lobes. An RGB demonstration uses a 200-µm aperture and 111 superpixels. The design API in the paper is intentionally limited to transmitted parabolic lens and linear deflector phase profiles, even though the underlying freeform cell representation is general ([paper](https://arxiv.org/html/2503.20479)).

The openness is substantial: the official repository includes AIM source, FiLM WaveY-Net training/inference and a web app; the pretrained model is published on [Zenodo](https://doi.org/10.5281/zenodo.15802727), and the authors link the full training/validation dataset through the [Stanford Digital Repository](https://purl.stanford.edu/dq123fg9049) ([official repository](https://github.com/jonfanlab/metachat)). This is much stronger public reproducibility than a paper with only screenshots or prompts.

### Where the evidence boundary lies

The paper's physical engine is a learned **two-dimensional dielectric** surrogate. It independently compares stitched deflector near fields with FDFD, which is an important check. In the reviewed paper sections, however, the whole-metalens results are obtained by propagating surrogate-generated complex fields; an equivalent independent whole-metalens full-wave or fabricated-device validation is not reported. This is an audit observation, not proof that the design would fail. The paper's future-work discussion itself proposes coupling the framework to robotic experimental validation ([paper](https://arxiv.org/html/2503.20479)).

The agent-quality experiment also uses an LLM grader in the released evaluation framework; that should not be conflated with the paper's quantitative FDFD/surrogate validation. MetaCraft should avoid making its strongest agent claim depend only on another model's judgment ([released grader](https://github.com/jonfanlab/metachat/blob/main/metachat-aim/experiments/eval_framework/grader.py)).

### Competitive implication

MetaCraft should not promise to beat MetaChat on 300,000-evaluation throughput unless it develops a comparably trained surrogate. Its stronger differentiator can be **validity-domain-aware refusal and exact device-level evidence**:

- a surrogate prediction is advice/forecast until separately admitted validation closes it;
- ideal phase, realized complex aperture response and propagated focus remain distinct artifacts;
- low-NA scalar/component and high-NA vector routes cannot silently substitute for one another;
- PB converted focus and retained leakage are separately measured;
- interrupted, stale, mismatched or partially observed solver work cannot become a result.

This is complementary to MetaChat's speed. A compelling paper could use MetaChat-like or other optimizers as proposal generators and show that MetaCraft detects when their results cross an evidence boundary.

## 3. Closest additional competitors

### MetaDesigner

Wu et al.'s May 2026 preprint is the closest system-level competitor. It coordinates Solver, Verifier, Researcher, Optimizer and Programmer agents through CST, retrieval and persistent memory. Demonstrations include an RGB metalens, a six-plane hologram with reported SSIM 0.97 and optoelectronic style transfer ([preprint](https://arxiv.org/abs/2605.22647)).

The RGB metalens uses a 512×512 grid with 160-nm period, fixed 50-nm TiO₂ radius on SiO₂ and heights from 200 to 800 nm. It targets 480, 560 and 640 THz at three focal positions on an 80-µm plane. The system uses CST phase response at 480 THz and empirical linear relationships to estimate the other frequencies. It reports 16 min 14 s, 1.89 million tokens and 20% average focusing efficiency. Its verifier catches frequency–colour mapping, numerical-aperture and diffraction-limit overclaims as well as report inconsistencies ([preprint PDF linked from arXiv](https://arxiv.org/abs/2605.22647)).

This work makes “we have multiple specialist agents and a verifier” insufficient novelty. It also makes a useful case for MetaCraft's stricter verifier semantics: MetaDesigner's verifier reasons and corrects, whereas MetaCraft can require exact typed evidence and refuse a conclusion. The MetaDesigner authors themselves identify high-fidelity simulation, experimental feedback, fabrication constraints and field-specific standards as future requirements and say the framework is not a final answer. No official code/data link was found on the arXiv record or in the inspected preprint as of 2026-08-15; that absence should be rechecked before submission.

### Unit-cell agentic and LLM systems

Lu, Malof and Padilla let an agent construct a forward surrogate and then invoke Neural Adjoint for a 14-parameter, four-ellipse all-dielectric metamaterial unit cell. Existing dataset subsets stand in for simulations that the authors note could require months to generate. Their agent's inverse-design MSE (about 1.4–1.8×10⁻³) is worse than the two human benchmarks (0.94×10⁻³ and 0.30×10⁻³). This is evidence of workflow autonomy, not superior inverse-design physics or full-device closure ([ACS Photonics paper](https://doi.org/10.1021/acsphotonics.5c01514); [arXiv full text](https://arxiv.org/html/2506.06935)).

Huang et al.'s MCP-enabled system exposes TorchRDIT through two MCP servers, five APIs and 16 structure templates. Across 50 trials per prompt condition it reports code-execution success of 94% and 100%, task satisfaction of 23% and 76%, and substantial API hallucinations in the weaker condition. It is an appropriate baseline for tool-use reliability, but its Huygens meta-atom target is not a metalens proof ([Nanophotonics article](https://doi.org/10.1515/nanoph-2025-0507)).

Chat-to-Chip fine-tunes open LLMs to map between tokenized 4×4 geometry grids and 31-point spectra for a silicon-on-glass unit cell. It reports 3.4×10⁻³ test MSE and approximately two-second inference, but it is a learned inverse model rather than an agentic research loop, and the source dataset is available only on request ([Nanophotonics article](https://doi.org/10.1515/nanoph-2025-0343)).

### Adjacent evidence-driven photonic agent

AutoPhotonicDesign is not a metasurface system, but it is strategically close. A coding agent proposes silicon-photonic designs, invokes deterministic simulation and rule checks, and records append-only journals. The authors release the framework and run records. One multiphysics modulator example also documents that the initial RF stage failed and required an expert reference design before the automated loop could continue ([preprint](https://arxiv.org/abs/2606.00915); [official repository](https://github.com/flexcompute/autophotonicdesign)). MetaCraft therefore should formulate evidence governance at the **metalens physics and scientific-result boundary**, not claim generic precedence for simulator-in-the-loop agents or run journals.

## 4. What MetaCraft actually has now

The following are implemented repository capabilities, not proposed marketing claims:

- The installed public API is deliberately limited to `Authority`, `compile_study` and `conduct`. Rust admits durable authority state, Python owns scientific meaning, and AI advice is untrusted ([DESIGN.md](../../DESIGN.md)).
- A canonical brief compiles to immutable study state. Advice and evidence are content-addressed and replayed against exact admitted bytes; external work has permits, receipts, checkpointed recovery and typed outcomes. Scientific refusals do not silently retry ([DESIGN.md](../../DESIGN.md)).
- Metalens physics distinguishes propagation phase from geometric/PB phase and low NA (`NA ≤ 0.5`) from high NA. Low-NA evidence uses 8/12/16-state finite sets and componentwise angular-spectrum propagation. High-NA evidence uses same-solve sampled reference surfaces, pointwise assignment, vector angular-spectrum propagation and matched FFT/CZT aplanatic-reference comparison ([SCIENCE.md](../../SCIENCE.md)).
- Completion requires the chain `unit-cell evidence → realized aperture → field → focal region → bracketed focus → result`. Focus is searched over 0.8f–1.2f; the result reports focal shift, separate x/y half-maximum widths, depth, transmission and focus efficiencies. PB additionally reports retained-channel leakage ([SCIENCE.md](../../SCIENCE.md)).
- Four external benchmark cases cover propagation/PB × low/high NA and bind to McClung, Yang, Arbabi and Khorasaninejad references in the fixed catalogue ([benchmark catalogue](../../examples/metalens_benchmark/catalogue.py)). A native Lumerical adapter and qualification evidence exist, but the roadmap states that native execution of all four cases is future work ([ROADMAP.md](../../ROADMAP.md)).
- The continuous-achromatic branch has real TiO₂/glass material observations at 470–590 nm and a five-geometry 530-nm screen. Two completed geometries passed a >5% converted-power gate and one geometry timed out after 412.9 s. The code can now assign an immutable aperture, form compensated and PB-only spectral field families, evaluate complete-band focus, and replay a result, but Native evidence has not yet reached those stages ([experiment record](2026-08-14-achromatic-experiment-result.md)).

Important non-capabilities:

- There is no optimizer module. Current design is deterministic selection, so **“inverse design” would overstate the present implementation** ([SCIENCE.md](../../SCIENCE.md#selection-and-optimization)).
- The four-case benchmark matrix has reviewed comparison truth, not four completed native solver demonstrations ([ROADMAP.md](../../ROADMAP.md)).
- No current evidence establishes a continuous-achromatic lens, a Chen et al. reproduction or a fabricated device ([experiment record](2026-08-14-achromatic-experiment-result.md)).
- The large automated test suite is engineering evidence, not independent validation of lens performance.

## 5. A defensible paper thesis

### Recommended core hypothesis

> An authority- and evidence-governed agentic system reduces scientifically false completion and enables deterministic replay of metalens design studies, while preserving competitive device performance across distinct optical control and numerical-aperture regimes.

This hypothesis is novel enough to test against Self-Evolving's procedural skill learning, MetaChat's surrogate-driven speed, and MetaDesigner's reasoning verifier. It is also falsifiable: the governance layer may add cost without improving false-positive rate, or the lenses may underperform simpler deterministic baselines.

Until an optimizer exists, a precise working title would use **“agentic metalens research”**, **“evidence-governed metalens design”** or **“a verifiable agentic framework for metalens design.”** Use **“inverse design”** only after MetaCraft contains and benchmarks a real objective-driven optimizer with recorded stopping evidence.

### What not to claim

- Do not claim the first agentic metasurface or metalens framework; MetaChat, MetaDesigner, Self-Evolving and Lu et al. preclude it.
- Do not call competitors “粗糙” in the manuscript. The defensible statement is that they optimize different endpoints and leave different evidence boundaries open.
- Do not sell architectural complexity, number of types, number of tests, number of agents or immutable storage as scientific novelty by itself.
- Do not compare execution speed with MetaChat without matching hardware, simulation fidelity and validity domain.
- Do not treat ideal phase-mask focusing, an LLM verifier's approval, a completed unit-cell solve or an unbracketed focal peak as a realized metalens result.

## 6. Minimum experiment package for publication

### A. Complete the physical benchmark matrix

Run all four fixed cases natively through the recorded Lumerical adapter:

1. propagation phase, low NA;
2. propagation phase, high NA;
3. geometric/PB phase, low NA;
4. geometric/PB phase, high NA.

For each, publish the exact brief, material binding, unit-cell evidence, aperture assignment, field, focal survey, focus result and comparison to the paper's compatible metrics. Report non-comparable metrics as such; never create fallback numbers. This closes the repository's already declared `2×2` scientific claim rather than adding another aim.

### B. Add one real inverse-design experiment—or narrow the language

Implement a bounded route-specific optimizer with an explicit objective, budget, stopping rule and stopping evidence. Compare it with current deterministic selection under the same candidate library and solver budget. A high-NA sitewise recovery task or continuous-achromatic spectral task is more differentiated than another monochromatic low-NA phase lookup.

If the optimizer is not implemented, publish the work as evidence-governed **design/research orchestration**, not inverse design.

### C. Close the achromatic branch

Complete a full design-wavelength plus blind-holdout chain:

- qualified spectral unit-cell library;
- phase/group-delay coverage and conversion/transmission gates;
- realized physical aperture;
- per-wavelength complex fields and bracketed foci;
- focal shift, Strehl or agreed image-quality measure, x/y FWHM, DOF, efficiency and PB leakage where applicable;
- tolerance sweeps for width, height, sidewall angle and refractive-index uncertainty.

A typed physical refusal is publishable evidence if the target exceeds the admitted library's delay/coverage envelope; silently choosing an easier target is not.

### D. Evaluate agents with blinded repeated trials

Use held-out metalens briefs spanning wavelength, material family, NA, focal length, aperture size and control strategy. Repeat each condition with fixed budgets and seeds where possible. If making a general agent claim, use more than one base model. Report confidence intervals rather than only best runs.

At minimum compare:

1. deterministic MetaCraft without an LLM;
2. raw coding agent + solver documentation;
3. coding agent + the static MetaCraft skill;
4. MetaCraft without authority/evidence gates;
5. full MetaCraft;
6. a Self-Evolving-style skill-update condition if feasible.

Agent metrics should include task success, physical success, **false-positive completion rate**, human interventions, solver calls, retries, wall time, token/API cost and work saved after interruption/resumption.

### E. Ablate the physics and evidence contracts

Required ablations:

- ideal phase mask versus realized complex unit-cell aperture;
- component/scalar low-NA route versus vector high-NA route on their overlap domain;
- PB converted channel with versus without retained-leakage accounting;
- authority/evidence admission on versus off;
- exact replay on complete, stale, corrupt, foreign and partial evidence;
- interrupted run resumed from receipts versus full rerun;
- deterministic evaluator versus LLM-only grading.

The central result should be a reduction in false scientific conclusions, not merely more gracefully formatted reports.

### F. Independent validation

Cross-check a representative subset with a second numerical method or device-scale full-wave model. Fabricating and measuring at least one lens would materially strengthen any claim aimed at a high-impact optics venue. Without fabrication, a strong methods/software paper remains plausible if the cross-solver/full-wave validation, benchmark breadth, raw evidence release and limitations are unusually rigorous. MetaChat and the Self-Evolving framework make simulation-only novelty possible, but their publication records do not remove the need for independent validation of MetaCraft's distinct physical claims ([MetaChat](https://doi.org/10.1126/sciadv.adx8006); [Self-Evolving](https://doi.org/10.1002/lpor.71739)).

### G. Release a reproducibility package

Release benchmark briefs, schemas, fixed evaluators, run configurations, raw solver artifacts, permits/receipts, append-only run journals, admitted evidence and scripts for every main table/figure. Include failed and refused runs. This is a direct opportunity: the Self-Evolving public repository excludes its complete experiment suite, while MetaChat's model and training data set a high openness bar ([Self-Evolving repository](https://github.com/yi-huang-1/evo-metaoptics); [MetaChat repository](https://github.com/jonfanlab/metachat)).

## 7. Suggested paper story

The strongest compact story is:

1. **Problem:** current agents can generate code or layouts, but a plausible answer, completed solve and valid device result are not the same scientific object.
2. **Method:** MetaCraft compiles an exact metalens brief into an immutable proof obligation; untrusted advice may propose work, while typed evidence and deterministic evaluators alone close claims.
3. **Physics demonstration:** one controlled device family, but four materially different routes—propagation/PB × low/high NA—with a completed achromatic or high-NA optimization extension.
4. **Agent experiment:** blinded repeated trials show false-positive reduction, deterministic replay and interruption recovery relative to raw/static/evolving-agent baselines.
5. **Independent validation:** cross-solver or fabrication confirms that governance did not merely produce internally consistent artifacts.

One device family is an advantage here: it keeps the physics deep enough that each claim can be audited. Expanding prematurely to holograms, quasi-BICs or frequency-selective surfaces would dilute the contribution and, according to the repository roadmap, would currently be a roadmap claim rather than an implemented capability ([ROADMAP.md](../../ROADMAP.md)).

## 8. Remaining uncertainties

- MetaDesigner is a very recent preprint. Its code/data availability and publication status may change before MetaCraft submission; re-run the search immediately before positioning the manuscript.
- No exact head-to-head evaluation can be inferred from published numbers because tasks, solvers, dimensions, hardware, budgets and success criteria differ. The competitor table is a scope comparison, not a ranking.
- The absence of reported whole-metalens full-wave/fabrication validation in MetaChat is based on the reviewed article and repository, not on private author work.
- The most appropriate venue depends on which evidence is completed. A simulation-only evidence-governance paper and a fabricated achromatic/high-NA metalens paper have different novelty thresholds.
- MetaCraft's current architecture appears substantially more rigorous than its completed optical dataset. Whether the governance improves scientific outcomes remains an experimental question, not a conclusion supported by the codebase alone.

## Primary-source register

### Direct competitors

- Huang, Y. et al. *A Self-Evolving Agentic Framework for Metasurface Inverse Design*. **Laser & Photonics Reviews** e71739 (2026). [DOI](https://doi.org/10.1002/lpor.71739), [arXiv full text](https://arxiv.org/html/2604.01480), [official repository](https://github.com/yi-huang-1/evo-metaoptics).
- Lupoiu, R. et al. *A multi-agentic framework for real-time, autonomous freeform metasurface design*. **Science Advances** 11, eadx8006 (2025). [DOI](https://doi.org/10.1126/sciadv.adx8006), [arXiv full text](https://arxiv.org/html/2503.20479), [official repository](https://github.com/jonfanlab/metachat), [weights](https://doi.org/10.5281/zenodo.15802727), [dataset](https://purl.stanford.edu/dq123fg9049).
- Wu, X. et al. *Agentic metasurface design with self-correcting language-model systems*. arXiv:2605.22647 (2026). [Preprint](https://arxiv.org/abs/2605.22647).
- Lu, J., Malof, J. M. & Padilla, W. J. *An Agentic Framework for Autonomous Metamaterial Modeling and Inverse Design*. **ACS Photonics** 12, 6071–6080 (2025). [DOI](https://doi.org/10.1021/acsphotonics.5c01514), [arXiv full text](https://arxiv.org/html/2506.06935).
- Huang, Y. et al. *MCP-enabled large language models for metasurface inverse design*. **Nanophotonics** 14, 5589–5602 (2025). [DOI](https://doi.org/10.1515/nanoph-2025-0507), [arXiv](https://arxiv.org/abs/2508.10277).
- Zhang, Z. et al. *Chat-to-Chip: translating human intent into metasurface design with large language models*. **Nanophotonics** 14, 3625–3633 (2025). [DOI](https://doi.org/10.1515/nanoph-2025-0343), [arXiv](https://arxiv.org/abs/2509.24196).
- Kharel, P. et al. *Autonomous agentic design for photonics*. arXiv:2606.00915 (2026). [Preprint](https://arxiv.org/abs/2606.00915), [official repository](https://github.com/flexcompute/autophotonicdesign).

### Metalens-only publishability precedents

- Zhelyeznyakov, M. V. et al. *Large area optimization of meta-lens via data-free machine learning*. **Communications Engineering** 2, 60 (2023). [Publisher full text](https://www.nature.com/articles/s44172-023-00107-x), [DOI](https://doi.org/10.1038/s44172-023-00107-x).
- Chung, H. et al. *Inverse design enables large-scale high-performance meta-optics reshaping virtual reality*. **Nature Communications** 13, 2409 (2022). [Publisher full text](https://www.nature.com/articles/s41467-022-29973-3), [DOI](https://doi.org/10.1038/s41467-022-29973-3).

### Local MetaCraft truth

- [DESIGN.md](../../DESIGN.md)
- [SCIENCE.md](../../SCIENCE.md)
- [ROADMAP.md](../../ROADMAP.md)
- [Continuous-achromatic experiment record](2026-08-14-achromatic-experiment-result.md)
- [Metalens benchmark catalogue](../../examples/metalens_benchmark/catalogue.py)
- [Repository-owned design skill](../../skills/metacraft-design/SKILL.md)
