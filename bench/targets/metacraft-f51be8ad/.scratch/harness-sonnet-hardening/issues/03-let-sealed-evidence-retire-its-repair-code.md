# Let sealed evidence retire its repair code

**Parent map:** [Harness-native Sonnet hardening](../map.md)

**Label:** `wayfinder:grilling`

**Status:** resolved (2026-08-09)

**Blocked by:** none

## Question

After the two zero-rerun correction chains have been sealed as immutable
artifacts, which executable correction paths can be deleted from the active
acceptance runner while preserving provenance, independent verification, and
the ability to understand every old/new identity?

Apply the deletion test to the correction flags, functions, helpers, and tests.
Separate reproducible verification from forbidden re-editing, and define the
smallest surviving fresh-run Interface. Existing transcripts, manifests,
correction records, and their hashes must not change.

## Resolution

Delete both one-time correction writers from the active acceptance runner.
Their work is complete and their durable meaning now lives in the immutable
artifact chain, not in an executable maintenance Interface.

The smallest surviving runner Interface is:

```text
tests/harness_acceptance_runner.py --preflight
tests/harness_acceptance_runner.py --run --evidence-root <absent-directory>
```

`--run` continues to perform preflight first. Its evidence root must be absent;
`run_matrix` already claims it with `mkdir(..., exist_ok=False)`. A later
bounded retest therefore produces one fresh evidence root and never edits the
sealed `acceptance/07` root. No `--verify`, amendment, migration, repair, or
compatibility mode is added to this runner.

### Deletion inventory

Remove from `tests/harness_acceptance_runner.py`:

- the `--correct-audits` and `--correct-retained-evidence` flags, their
  exactly-one-mode accounting, and both dispatch branches;
- `correct_retained_audits` (106 lines) and `correct_retained_evidence`
  (207 lines);
- the correction-only `_retained_codex_capsule` (12 lines) and
  `_retained_claude_capsule` (10 lines) helpers;
- the now-unused `re` import.

Those four functions alone are 335 lines. Repository-wide reference search
finds no caller beyond the two flags and the functions themselves. Deleting
them makes their mutation, temporary-directory, old-path recovery, amendment,
and second post-hoc generation complexity vanish; it does not move that
complexity to another caller. They therefore fail the deletion test and are
historical execution paths, not a deep Module.

Retain the fresh-run implementation: `preflight`, `run_matrix`, `_run_once`,
`_generate_post_hoc`, `classify_acceptance`, the explanation/encoding/hash
helpers, and the audit/redaction/capsule dependencies they use. These still
hide real clean-session, confinement, sealing, and reporting behavior behind
the two-command Interface.

### Immutable provenance

Do not change, regenerate, normalize, or reserialize any tracked artifact
under `.scratch/harness-native-consultation/acceptance/07/`. In particular,
retain byte-for-byte:

- `sealed-manifest.original.json`;
- `audit-correction.json`;
- `sealed-manifest.audit-corrected.json`;
- `retained-evidence-correction.json`;
- `sealed-manifest.json`;
- all retained transcripts, stderr records, audits, outcomes, and post-hoc
  reports.

The two correction records already name why the projection changed, every
available old/new identity, and `session_rerun_count: 0`. The three manifests
retain the original, audit-corrected, and sanitized projections. Executable
re-editing is neither provenance nor reproducibility; after sealing it is an
additional mutation authority.

### Verification replacement

Keep verification read-only in
`tests/acceptance/test_retained_harness_evidence.py`. Deepen that test rather
than preserving or relocating either writer:

1. Verify the original manifest digest and each original run identity against
   `audit-correction.json`, including unchanged transcript identities and the
   old audit/outcome identities.
2. Verify the audit-corrected manifest digest, its amendment references, and
   each corrected audit/outcome identity against the first correction record.
3. Verify the second correction's original-manifest, previous-manifest, and
   previous-correction digests; match every `run_changes` old identity to the
   prior projection and every new identity to the current manifest and current
   artifact bytes.
4. Verify the current manifest's correction digest, all eight current
   transcript/stderr/audit/outcome hashes, the five current post-hoc hashes,
   and both zero-rerun declarations.
5. Preserve the current semantic assertions: eight confined records, no
   forbidden retained machine paths or session identifiers, no accepted
   answers, no advice or selections, honest Codex/Claude failure positions,
   and no comparison/delta/threshold/Result claim in post-hoc reports.
6. Add one runner Interface regression proving the two retired correction
   flags are rejected and only `--preflight` or `--run` is accepted. Test the
   command behavior, not private parser placement.

This verifier may compute hashes and parse records but must open no harness,
write no artifact, regenerate no projection, and depend on no recovered
temporary capsule path. It is independent verification of retained facts, not
an alternate repair seam.

### Rejected alternatives

- Do not move the correction functions into an archive or helper Module; that
  retains the same mutation authority behind a different name.
- Do not generalize them into an amendment registry or migration framework;
  there is no second live amendment use case.
- Do not delete correction records after copying their gist into prose; the
  exact records and hashes are the provenance.
- Do not make the sealed root writable through a force or overwrite flag.
- Do not regenerate old projections with today's audit/redaction code; that
  would test current implementation, not verify retained identities.

## Comments

The repository evidence is sufficient to resolve this decision without a new
human policy choice. The parent map already freezes the artifact bytes and
requires a later live retest to be exact-once in a fresh lane. The closure and
Ticket 07 state that the two correction chains are complete, chained, and
zero-rerun; all correction symbols are otherwise unreachable. Focused retained
acceptance verification passed on 2026-08-09:

```text
10 passed in 9.54s
```

Implementation should snapshot the hashes of the whole retained root before
editing the runner, apply only the deletion and read-only test deepening above,
then prove the post-change snapshot is identical. It must also run the focused
acceptance tests and `git diff --check`.

**Map gist:** Retire both sealed correction writers and keep only fresh
`preflight -> run -> audit -> seal`, while a read-only verifier proves the
unchanged two-amendment identity chain.
