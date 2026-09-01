# 02 — Let Study carry complete science

Status: resolved (2026-07-31)

**Blocked by:** 01 — Let one Python name describe one system.

## Outcome

`Study` becomes the one complete immutable scientific state for a compiled
branch. It carries the brief, design, advice, proof, evidence, capabilities,
bindings, ready tasks, and findings required to understand and resume that
branch. It owns canonical encoding and strict restoration.

Checkpoint and result restoration consume the Study codec instead of
independently interpreting fragments of its shape. Ticket 07 remains the
owner of the public compile/conduct outcome cutover, final `StudyFrontier`,
scientific Result bytes, and deletion of the replaced lifecycle.

## Scope

- Deepen `src/metacraft/science/study.py` so `Study` owns:
  - complete immutable scientific state;
  - one canonical `Document` representation;
  - strict `from_document` restoration;
  - validation of brief identity, route/proof agreement, task bindings,
    evidence closure, capabilities, bindings, and findings.
- Update `src/metacraft/science/compiler.py` and
  `src/metacraft/science/compile.py` to construct the complete Study directly.
- Make current conduct, checkpoint, and result restoration use the Study
  codec while preserving their current public entry points until Ticket 07.
- Replace duplicate Study-shape decoding in:
  - `src/metacraft/science/result.py`;
  - `src/metacraft/_local/replay.py`.
- Update the current local scientific operations only as far as required to
  carry complete Study values without maintaining a second durable
  scientific-state projection.
- Keep the production runtime import graph acyclic. Generic Study code must
  not import metalens or another aim consumer.
- Accept only the final Python Study document shape. A fresh workspace is the
  supported start.

The codec may preserve aim-owned canonical subtrees, but explicit metalens
composition remains the sole place that validates or narrows metalens
language. Do not introduce a registry, reflection, or dynamic aim discovery.

## TDD seam

The public test seam is:

```python
document = study.document()
restored = Study.from_document(document)
```

Write tests first for:

- initial, waiting, ready, and complete Studies round-tripping exactly;
- evidence-bearing and advice-bearing Studies retaining exact References;
- capabilities and bindings surviving restoration;
- route and proof disagreement being rejected;
- brief identity mismatch being rejected;
- evidence for another task being rejected;
- a task citing an absent binding being rejected;
- duplicate evidence, capabilities, bindings, tasks, or findings being
  rejected where uniqueness is required;
- missing, extra, malformed, or non-canonical nested values being rejected;
- result and checkpoint restoration using this codec;
- generic Study modules importing no metalens consumer.

Tests assert through `Study.document`, `Study.from_document`,
`compile_study`, and the current public replay seam. They must not construct or
assert a private decoder shape.

## Acceptance

- [ ] `Study` contains every scientific fact required to explain and resume
      one branch.
- [ ] `Study.document()` is the sole canonical Study encoder.
- [ ] `Study.from_document()` is the sole strict Study decoder.
- [ ] Compile produces a complete Study without a sidecar scientific-state
      object.
- [ ] Checkpoint and result restoration call the Study codec.
- [ ] Duplicate Study decoding and proof/evidence shape validation are
      deleted from Result and replay implementation.
- [ ] Generic Study code imports no metalens module.
- [ ] The runtime import graph remains acyclic.
- [ ] Python records in the replaced Study/checkpoint shape are unsupported;
      no compatibility reader exists.
- [ ] Rust protocol values and Rust source remain unchanged.
- [ ] Public compile and conduct outcome shapes remain reserved for Ticket 07.

Study, checkpoint, result-closure, and downstream Python References may change
because the Python scientific body changes. Rust Reference structure and
admission semantics do not.

## Verification

```powershell
$projectPython = 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe'

& $projectPython -m pytest -q --tb=short -p no:cacheprovider `
  tests/science/test_standard_studies.py `
  tests/science/test_scientific_identity.py `
  tests/science/test_branch_checkpoint.py `
  tests/science/test_conduct_frontier.py `
  tests/science/test_result_closure.py `
  tests/science/test_result_replay.py `
  tests/architecture/test_runtime_import_dag.py `
  tests/architecture/test_scientific_boundary.py `
  tests/authority/test_public_contract.py `
  tests/authority/test_strict_decoding.py

& $projectPython -m pyright

rg -n "_decode_stored_study|_validate_restored_study" src tests
git diff --check
git diff -- rust
```

The duplicate-decoder search and Rust diff must be empty. The complete
non-live suite is reserved for Ticket 10.

## Stop and report

Stop without adding another abstraction if:

- strict restoration requires generic Study code to import metalens;
- two modules must independently decode the complete Study shape;
- preserving current public conduct requires a second durable state codec;
- a required scientific fact has no clear owner in Study or an exact
  referenced document;
- a Rust protocol or source change appears necessary;
- the change cannot remain compatible with Ticket 07's atomic lifecycle
  cutover.

Report the exact dependency edge, duplicated meaning, failing document, and
focused test that exposed it.

## Do not add

- A Study registry, plugin, reflection mechanism, or dynamic decoder lookup.
- A compatibility reader or schema migration.
- A mutable Study or mutable progress database.
- A second lifecycle or public frontier mutation interface.
- Public compile/conduct outcomes owned by Ticket 07.
- Scientific Result meaning or Result-schema changes owned by Ticket 07.
- Rust source or protocol changes.

## Comments

Resolved with `Study.document()` and `Study.from_document()` as the sole
complete scientific-state codec. Checkpoints and result closure now consume
that codec; their duplicate proof, evidence, binding, finding, and advice
decoders were removed. `AvailableScience` remains transient only and owns no
durable shape pending Ticket 07.

Verification passed 355 science and architecture tests in the implementing
agent, followed by independent focused runs of 65 and 50 tests. Pyright
reported zero findings, the runtime dependency graph stayed acyclic, and Rust
had no diff. The canonical metalens design key was also reduced to the single
name `capabilities`; no alternate decoder remains.
