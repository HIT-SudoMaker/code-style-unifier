# Project orientation and Authority preparation

Use when the selected Authority file is absent. This is first-onboarding warm-up
or preparation after loss of the file, not a CSU source verdict.

Tell the user before inspection: "Authority was not found at <resolved path>.
Formal CSU review has not started. I will inspect the requested project read-only
and prepare the facts and open questions needed for Authority. Missing facts and
unsupported checks are not evidence of source defects."

1. Confirm project root, review scope and selected Authority path. Use the caller's
   explicit path when given; otherwise use `.csu/authority/authority.json` under
   the project root. Keep this distinct from `.csu/runs/`, which stores runs.
   If a supplied path appears mistaken, report that uncertainty; do not silently
   choose another file or infer project history from directory existence.
2. Read the relevant project instructions, directory structure, language/build
   declarations, entry points and dependency declarations within the requested
   scope. Follow supporting project documents as needed. Record inspected scope
   and evidence limits; directory inspection alone is not global understanding.
3. Return a compact project overview and candidate-fact table: Authority field,
   proposed value, source path/location, evidence status and unresolved question.
   Separate directly observed facts, owner/document declarations and inference.
   Inference remains a candidate. Use only supported Authority fields; consult
   the field purposes in [remediation.md](remediation.md#draft-project-facts).
   Import roots and build declarations can support candidates, but installed
   packages do not prove dependency classification or safe import reordering.
   Language-specific uncertainty stays explicit across Python, Rust, C and C++.
4. State the exact intended file location and next step: confirm material facts,
   then create Authority and run a fresh review. Do not create or overwrite it
   under review-only authorization. If writing confirmed facts is already
   authorized, proceed within that authorization; ask only unresolved questions
   that affect truth. Use paths relative to the eventual review scope for fields
   that identify source files. Never copy CSU's self Authority into another project.

Finish when the overview, evidence-backed candidates, unresolved facts and closing
path are delivered. Return them in chat unless an artifact was requested. The
formal review remains blocked on missing Authority; do not create a synthetic
CSU terminal or seal for this preparation. Preparation does not repair source.

For later valid-Authority reviews, preserve observed Findings and distinguish
missing facts from unsupported tool capabilities. Count Blocked entries as
file/check-family pairs, not design defects. Only propose facts for fields the
current version accepts. Static Python imports in local blocks are observed; their location alone is not
a defect. Missing classifications can coexist
with unsupported mixed-class statement layout or native target analysis. Explain
each located cause without counting it as an additional file/check-family pair.
Preserve known Findings alongside Blocked; do not move imports to reduce counts.
