# Context

MetaCraft uses one language for authority and science. These terms are normative.

## Authority

**authority** — The Rust core that owns workspace truth. It admits or rejects a proposed transition; it does not interpret scientific meaning.

**workspace** — One MetaCraft instance: an object store, an append-only ledger, and replayable projections under one writer boundary.

**application root** — One outer directory claimed fresh by the first conduct call and thereafter resumable only for its byte-identical brief. It contains exactly the Authority `authority/` workspace and product-owned `runs/` artifacts; foreign and partial roots are never repaired.

**object** — Immutable bytes with descriptive metadata and a content-addressed reference.

**reference** — The exact identity of an object: content hash, metadata hash, media type, and byte length.

**proposal** — A canonical request to store an object and relate it to authority state.

**decision** — The authority's immutable answer: `admitted` or `rejected`, with stable findings and revisions.

**revision** — The exact ledger head observed by a caller. `root` is the empty workspace.

**record** — An immutable object retained without becoming current.

**current** — The sole admitted object for a named key, optionally superseding the exact previous object.

**capacity** — A current, qualified upper bound for open permits in one scope.

**permit** — A bounded reservation for one proposed unit of work.

**receipt** — An admitted observation that consumes one open permit. It proves that permitted work left a valid fact, not that the scientific objective succeeded.

**close** — A revocation or expiry that ends one open permit when no valid observation was admitted.

## Science

**brief** — The user's immutable wording, declared aim and objectives, operating conditions, constraints, and honest omissions. Its canonical content is its identity; it carries no catalogue or display label. A missing field is malformed, while a required scientific fact that remains absent asks for user clarification. An interpretation or proposed material family is not a user fact until the user confirms it.

**advice** — An immutable, untrusted scientific conclusion derived from one exact consultation request and a validated external answer. MetaCraft never obtains it through an embedded model transport. Absence or malformed input is not advice. A document-bearing advice record has one exact reference derived from its canonical bytes. Derivation names the record but does not admit it: Rust admission establishes that the record exists, while a period or height choice alone records scientific adoption.

**consultation required** — A typed conduct pause carrying the exact request re-derived from the current Study frontier and that complete waiting frontier. It is not stored as workflow state.

**consultation answer rejection** — The narrow public input fault raised when a supplied answer is invalid, stale, duplicate, or not currently required. Storage, Authority, and implementation faults are not consultation-answer rejections.

**consultation request** — One content-addressed scientific question carrying an exact brief identity, request-owned grounds, legal candidates, exclusions, cautions, research mode, and closed answer contract. It names no provider, model, endpoint, harness, or benchmark truth.

**consultation ground** — One request-owned proposition with an identity, statement, source identity, and exact kind: fact, constraint, forecast, or caution. Its kind prevents a forecast or caution from becoming evidence or a verdict.

**consultation answer** — One closed external answer citing an exact request and returning either a recommendation over one legal candidate or an evidence requirement. External claims remain separate untrusted values with exact source locators.

**objective** — A desired scientific outcome declared within a brief, such as focus, field reconstruction, spectral response, or resonance quality. An objective becomes testable only after compilation into claims.

**period domain** — The metalens-specific physical and fabrication bounds within which one cell period may be chosen for an exact brief and material binding. It contains no selected period or device-response observation.

**period advice** — An untrusted provider-free scientific conclusion over one exact period consultation request. It retains the validated recommendation or evidence requirement and exact request grounds, chooses neither later cell dimensions nor shape, and never closes a claim.

**period basis** — The exclusive source of one period choice: either an explicit brief constraint or one exact period advice. A brief constraint is not represented by synthetic advice.

**period choice** — One deterministically validated cell period that cites its period domain and one period basis. Only an admitted period choice permits a height domain.

**height domain** — The finite metalens-specific heights, fabrication constraints, and lateral candidate counts derived from one exact brief, material binding, period choice, and dimension step. It contains no device-response observation.

**phase envelope** — A pure-Python, zero-solver forecast of the propagation-phase coverage a height can reach, computed from the height domain and the optical contrast. It may rule a height out by arithmetic or by a certified rigorous bound; it closes only its own narrow claim — never periodic transmission, cell library, or phase set — it never claims coverage, and its model estimates never produce a verdict.

**height reach** — One height's entry in the phase envelope, carrying its verdicts, bounds, forecasts, and applicability annotations.

**optical contrast** — The refractive-index relationship between the atom material and its surroundings that the phase envelope consumes, built from qualification-admitted solver-native samples.

**height advice** — An untrusted provider-free scientific conclusion over one exact height consultation request, formed only after an admitted period choice. It retains either one validated legal-height recommendation or an explicit evidence requirement, the exact request grounds, and, for propagation phase, the exact phase-envelope reference. It is consultation input, never evidence and never closes a claim.

**height basis** — The exclusive source of one height choice: either an explicit brief constraint or one exact height advice. A brief constraint is not represented by synthetic advice.

**height choice** — One deterministically validated height that cites its height domain and one height basis. Only an admitted height choice permits a detailed lateral cell library.

**cell study plan** — One immutable, bounded plan formed after an admitted period choice. It owns exact height, lateral geometries, response channels, work count, cautions, and provenance; periodic execution projects its work verbatim and never reconstructs a grid.

**PB phase** — The Pancharatnam–Berry polarization-conversion route. The unrotated cell is qualified from complete x/y Jones response first; one qualified cell then yields analytic 8/12/16 orientation sets without orientation solver work.

**response qualification profile** — A user-owned objective or versioned reviewed Method contract that states the numeric transmission, conversion, leakage, and optional retardance/cross-coupling gates. Forecasts cannot substitute for this profile.

**feasibility screen** — A zero-solver assessment that either excludes a design through a certified necessary condition or leaves it eligible for evidence gathering. It never establishes scientific success; forecasts and advice cannot create a refusal.

**phase set** — One immutable propagation-phase 8-, 12-, or 16-state realization of uniformly spaced target phases. Each state retains its realized response, fabrication cell, loss, tie-break, and exact source evidence; the three quantizations remain separate results.

**orientation set** — One immutable geometric-phase set of 8, 12, or 16 ordered physical rotations derived from one admitted anisotropic cell and one admitted continuous orientation relation. It is a fabrication comparison, not a phase set, and creates no orientation-specific solver work.

**cell geometry** — One typed lateral cross-section with its natural dimensions: circle by diameter, square by width, rectangle by long and short side, or ellipse by major and minor axis. A shape name and an unrelated dimension bag are not a geometry.

**substrate** — The continuous supporting medium beneath a periodic meta atom. Its top surface is the current metalens cell's declared `z = 0` interface.

**meta atom** — One patterned nanoscale optical element above the substrate. `Nano pillar` names only pillar-shaped meta atoms and is not the generic term.

**cell** — One admitted fabricable meta atom with exact geometry, height, period, material identities, and source evidence. A pre-evidence candidate and a solver-native construction are not cells.

**aperture** — The metalens focus-objective arrangement of admitted cells across occupied lattice sites to realize a target optical control. It retains its circular or square footprint and half span without calling a square span a radius. It is shared by current metalens control strategies, not presumed for another aim.

**incident polarization** — The polarization condition declared by the brief at incidence. It is an input condition, not a global label copied onto a propagated field.

**field** — One single-wavelength sampled electromagnetic fact with an explicit surface, coordinate frame, medium, component basis, electric components, optional magnetic components, and exact source references. Its components carry its vector meaning; scalar or vector approximation belongs to the establishing method and qualification.

**rectilinear reference surface** — One raw single-plane electromagnetic observation whose horizontal and vertical sample coordinates are retained explicitly with its complex components. Its axes are finite and strictly ordered but need not be uniform, square, equally spaced, or equal in sample count. It is an observation, not yet a field or evidence.

**uniform reference-surface formation** — One qualified scientific transformation that forms a complete compatible batch of rectilinear reference surfaces into uniformly sampled fields on one shared grid. It preserves the exact source observations, returns no partial batch, and is distinct from solver observation and field propagation.

**focal region** — The propagated field observation over the declared axial and transverse region. It is established from an exact field by one bound propagation realization and is evaluated without propagating again.

**aplanatic reference** — One ideal focal-field fact formed from an independently authored aplanatic pupil on exact focal coordinates. It is not a propagated plane field and cannot inherit a realized field's surface by relabelling.

**numerical agreement** — Qualification evidence that distinct exact realizations of one physical method agree on the same coordinates under one declared comparison rule. It qualifies implementations; it neither compares different physical methods nor declares a design successful.

**focus** — A bracketed evaluation of the realized aperture field over the axial interval from `0.8f` to `1.2f`. It reports the found focus, separate x/y half-maximum widths, depth, and distinct transmission and concentration ratios; one nominal focal plane is not completion. A pointwise high-aperture result retains the qualified vector field and aplanatic-reference comparison that ground the same evaluation.

**design** — A resolved scientific intent: aim, objectives, operating conditions, constraints, allowed control strategies, capabilities, and budget. Its canonical content is its identity; it contains no copied brief or benchmark label, compiled route, exact solver, or local execution fact.

**claim** — A typed scientific statement that must hold under exact conditions before a result may be concluded. Claims are compiler language, not authority state or workflow positions.

**method** — A registered scientific way to establish one claim from prerequisite claims and evidence under explicit applicability conditions. A method owns no end-to-end lifecycle and names no solver product.

**route** — The content-addressed compiled selection of claims and methods from one aim to a result. A route is a value inside a study, not a strategy label, executor, package-level workflow, or solver product.

**compiler** — The pure Python seam that resolves one brief, reviewable advice, registered claims and methods, admitted evidence, and qualified capabilities into one immutable study. It performs no authority mutation, filesystem access, network call, or scientific execution.

**scientific module** — A Python-owned body of types and pure rules that either declares terminal claims for one aim or establishes claims through methods. A scientific module contributes to compilation; it does not own an end-to-end lifecycle.

**proof** — The complete claim, method, prerequisite, and evidence topology that must close before a route can return a result.

**capability** — A scientifically typed ability required by a method under stated conditions. It is independent of any product, installation, or current capacity.

**realization** — One exact executable implementation of a method, such as a qualified Python numerical implementation or solver Adapter and template.

**binding** — The exact qualified implementation chosen for one ready proof need, including its method, realization, and applicable local facts. A product binding does not pre-assign scientific material roles.

**material binding** — The task-scoped relationship between canonical atom and substrate families, their exact source identities, the requested wavelength, and admitted optical samples. For solver-native materials it cites the qualified product binding, but it is not part of product installation qualification.

**qualification** — Immutable evidence that one exact implementation satisfies one capability under stated conditions. It is not a permanent or mutable solver status.

**study** — An immutable compiled snapshot containing one design, route, complete proof, satisfied claims, ready tasks, and unresolved facts. New admitted evidence produces a new study; it never advances a mutable workflow.

**finding** — One typed explanation of why a claim remains unresolved. A finding may cite immutable diagnostic records, but neither the finding nor those records close the claim.

**task** — One immutable, fully bound scientific operation with exact inputs, expected evidence, prerequisite references, and capacity scope. It has no mutable status.

**aim unavailable** — A compilation refusal stating that the declared aim has no implemented terminal proof. It does not fabricate a study or finding.

**method unavailable** — A compilation refusal stating that an implemented aim and objective have no applicable scientific method under the resolved design. It does not fabricate a proof merely to carry the refusal.

**observation** — Raw output gathered by Python from a task. It is not authority and closes no claim.

**evidence** — An immutable observation or artifact whose scientific form Python validated and whose proposal Rust admitted. Only evidence closes a proof claim.

**result** — An admitted scientific conclusion produced by pure evaluation of one complete proof and its exact evidence closure. Its irreducible case meaning is bound to the exact brief identity, so paper context cannot be attached to another brief's closure.

**benchmark case** — One externally labelled, immutable pairing of a blind brief, published reference, benchmark alignment, and comparison contract. Its paper-anchored catalogue label selects the example but is not the identity of the brief, Method, Design, or Result. It is not production science, a workflow, or a solver configuration.

**published reference** — The reviewed paper identity and facts owned by one benchmark case. Each fact is reported, derived, not reported, or unresolved and retains the primary-source basis for that state. It is comparison context, never a production constraint or acceptance threshold.

**benchmark alignment** — The complete case-owned account of how blind brief inputs and omissions relate to published facts. Each subject is matched, adapted, independent, withheld, or excluded; alignment grants no comparison permission and defines no acceptance threshold.

**comparison contract** — The sole case-owned permission for placing benchmark Result measures beside published facts. Every fixed-frame measure has one signed-difference, context, not-reported, or not-applicable rule; there is no implicit default.

**benchmark Result measures** — The complete fixed ordered frame of typed MetaCraft observations restored from one admitted Result for external comparison. They add no paper meaning to the Result.

**benchmark measure** — One typed design or field quantity used by every benchmark case. A paper value carries its reviewed definition and primary-source locator before it may be compared.

**comparison disposition** — Exactly one of `comparable`, `context only`, `not reported`, or `not applicable`. A comparable value contains compatible finite MetaCraft and reference quantities plus one finite signed MetaCraft-minus-reference difference.

**benchmark comparison** — One external record that restores an admitted Result's exact evidence and places its design and field endpoints beside reviewed published truth. It adds no meaning to the Result and no paper threshold to production science.

**conduct** — The brief-first application operation that repeatedly compiles immutable studies, gathers only ready evidence through Rust authority, and returns either one honest waiting study or separately admitted results.

**aim** — The device class. Canonical values are `metalens`, `frequency selective surface`, `holographic metasurface`, and `quasi-bic metasurface`.

**operating spectrum** — The wavelength condition declared by one aim-owned brief. A metalens operating spectrum is currently either monochromatic or a continuous band; compiler-selected design samples and holdout samples are planning facts, not parts of the operating spectrum.

**mechanism constraint** — A user's explicit requirement, prohibition, or omission of a physical control mechanism. It limits method applicability but is not a control strategy, compiled route, numerical realization, or solver choice.

**control strategy** — An aim-specific mechanism used to realize a desired control. Current metalens values are `propagation phase` and PB phase (the serialized historical value `geometric phase` remains a compatibility identity); other aims may require a different strategy or no phase control at all.

**continuous compensation phase** — The metalens Method that couples a geometry-controlled complex spectral response to a wavelength-independent PB orientation so one fixed geometry and orientation at every aperture site realize a fixed focus over a continuous band. It composes propagation/resonant dispersion and PB phase; it is not a third control strategy or a collection of independently redesigned monochromatic apertures.

**spectral field family** — One immutable index of exact single-wavelength aperture fields formed from the same frozen physical aperture at every design, interleaved-validation, and post-freeze blind-verification wavelength. It does not turn `Field` into a spectral tensor or permit a missing wavelength to disappear into an average.

**achromatic focus** — The continuous-band evaluation that retains every wavelength-specific focus and reports the deterministic summaries currently required by the compiled proof: maximum and mean absolute focal shift, maximum spot width, mean transmitted fraction, mean focus efficiency, and maximum leakage fraction, with separate summaries for every wavelength role. Device-level publication gates and any broader metric contract remain owner-frozen work. It cannot be formed from a reference wavelength, design wavelengths without interleaved and blind verification, or one nominal focal plane.

**low na** — The metalens applicability range at numerical aperture no greater than `0.5`. It uses finite 8-, 12-, or 16-state fabrication alternatives and componentwise angular-spectrum evaluation. The exact numerical aperture remains the design fact; `low na` is method applicability, not a stored classification.

**high na** — The metalens applicability range above numerical aperture `0.5` and below `1`. It uses pointwise fabrication assignment, an admitted sampled reference-surface response, qualified vector angular-spectrum propagation of the assembled plane field, and a separately authored aplanatic ideal-focus reference formed under one joint FFT/CZT contract. It is method applicability, not a stored classification.

**component propagation** — Independent propagation of the components already represented by a Field. It remains the current low-NA and PB realization because it preserves right/left channel and converted/retained power meaning and accepts the current 940 nm / 480 nm benchmark sampling.

**electromagnetic propagation** — Coupled vector angular-spectrum propagation of a transverse-linear Field sampled at no more than half the in-medium wavelength. It recovers cartesian longitudinal electric response and absolute longitudinal Poynting power. Strict common-domain parity does not make it a replacement for component propagation outside that applicability.

**order regime** — The propagating-order condition at the periodic cell's physical period. `zeroth order` means the selected period stays below the conservative order ceiling; `multi order` means nonzero orders may propagate. The regime classifies the proof required after a sampling-legal choice: coefficient-only field formation requires `zeroth order`, while a qualified sampled reference-surface response may retain `multi order` with an explicit caution (ADRs 0009 and 0022).

**sampling ceiling** — The Nyquist upper bound `lambda/(2*NA)` on the cell period, compiled from the brief alone.

**cell period** — The physical lattice spacing selected from an explicit brief constraint or validated period advice. It lies on the 10 nm grid strictly below the sampling ceiling. The selected value's relationship to the order ceiling classifies proof applicability without changing its legality; neither ceiling is a downstream substitute for the selected period (ADR 0022).

**square lattice** — A periodic placement whose two in-plane translation vectors are orthogonal and have one equal physical period. It is distinct from a square cell window, square aperture footprint, or square meta-atom cross-section.

**order ceiling** — The conservative diffraction threshold `lambda/(n_substrate+numerical_aperture)`, derived from the sampled substrate index. It classifies a selected period's order regime and the response evidence needed for a complete field; it is not a period-legality bound or a universal limit on order-resolved methods (ADR 0022).

**period limit** — The greatest 10 nm multiple strictly below the sampling ceiling for every current metalens response capability. It bounds an explicit period or period advice but is not itself the selected cell period (ADR 0022).

**caution** — A non-blocking, evidence-backed limitation that remains visible through the study, run record, and result. It never closes a claim, makes a task ready, or prevents an otherwise complete result.

**dimension step** — The fabrication increment declared by a brief for generated lateral dimensions. The current cell-library sweeps use that exact grid; advice never coarsens or rewrites it.

**aspect limit** — The fabrication bound holding both the pillar feature and the inter-pillar gap to `height / limit` — one limit, deliberately carrying both meanings.

**external solver** — Software outside MetaCraft that may run a task only after its path, version, license, qualification, and capacity are established.

**solver adapter** — A product-specific Python realization of an external solver. It owns product discovery, qualification, native construction, licensing, execution command, and observation parsing, while delegating local process placement to the workstation.

**periodic time budget** — The immutable two-tier maximum-time policy owned by one periodic FDTD construction. The complete solver span, admitted material indices, wavelength, and ordinary response profile determine one ordinary maximum and one doubled extension; callers never provide femtoseconds (ADR 0025).

**periodic numerical closure** — The recorded reason a periodic FDTD response may leave its time ladder: native autoshutoff, autoshutoff after the sole extension, convergence after that extension with a residual-energy warning, divergence, or exhausted time. It retains every attempt's native termination evidence and never authorizes a third automatic solve (ADR 0025).

**workstation** — The shared Python execution Module that observes one local host and places external solver process trees without interpreting their scientific or product meaning.

**lane** — One fresh local placement for a single external solver process tree: four distinct physical cores in one locality cell, no SMT siblings, and a 16-GiB memory limit.

**material family** — One canonical natural lowercase scientific name, such as `amorphous silicon` or `titanium dioxide`. It is distinct from a solver-native product string and from the boundary spelling of a configuration key.

**material intent** — One canonical material family and the material source that a brief permits for one scientific role. It contains no project selection, native product name, wavelength-specific sample, or Authority reference.

**material observation request** — The ordered canonical material families and wavelength for which science needs optical observations. It may repeat one family for distinct scientific roles, but contains no project selection, native product name, or Authority reference.

**material verification request** — One material observation request bound by the project material library to the exact solver binding and Authority-admitted solver-material registrations that a solver Adapter must verify. It contains no catalogue or substitution policy.

**material source** — One of `local table`, `refractiveindex.info dataset`, or `solver native`. A solver-material selection exists before execution, but its native identity becomes valid evidence only inside the named solver binding.

**material library** — The MetaCraft-held collection of reusable material sources available for explicit selection. It contains portable material records and solver materials; it is neither an external solver database nor a run's evidence store.

**solver material** — A MetaCraft-held registration that links one canonical material family to one exact native record in a named external solver. It is a reusable selection, not optical data or qualification; the solver Adapter must validate and sample it when used.

**material record** — Portable canonical optical data with immutable source bytes, provenance, units, and covered band. It is produced only from a local table or a refractiveindex.info dataset.

**material sample** — Optical values resolved from one material record for one requested wavelength or band under one explicit interpolation policy, or sampled for one task from a solver-native material through its qualified product binding, recorded with fit targets and the fit residual.

**selection** — A deterministic choice from a finite admitted candidate set under one explicit loss and tie-break rule.

**optimization** — An iterative search that generates or updates candidates under an objective, stopping rule, and convergence evidence. It is planned, not current capability.

## Avoided language

Do not use M1–M7, sequence numbers, activation numbers, fixed workflow, kernel for Python science, versioned module names, `Scalar*`/`Vector*` field type trees, or an `is_vector` field flag. Do not use `single order` (use `zeroth order`), `admissible period` (use `order ceiling`), or `n_eff`-style abbreviations in public names. Production identifiers use the domain term that states the responsibility; mathematical shorthand remains in equations and exact native product strings only.
