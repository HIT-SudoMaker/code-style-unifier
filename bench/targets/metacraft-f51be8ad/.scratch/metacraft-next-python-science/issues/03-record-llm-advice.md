# 03 — Record LLM advice

**What to build:** A brief can receive structured advice from any configured OpenAI-compatible LLM endpoint, while every received, unavailable, or invalid outcome remains reviewable and compilation remains deterministic without the network.

**Blocked by:** 02 — Compile the standard studies.

**Status:** wontfix

**Superseded by:** [Four-brief delivery ticket 02](../../four-brief-metalens-delivery/issues/02-let-material-evidence-form-one-legal-height-domain.md).

- [x] Configuration uses base URL, API key, and model without a provider-specific public module.
- [x] Prompt, provider, endpoint identity, model, raw response, validation, and failure are retained.
- [x] Explicit user facts always outrank advice and ambiguous route advice does not decide for the user.
- [x] A deterministic adviser fixture covers the default suite; live consultation is opt-in.
- [x] Missing credentials, transport failure, invalid JSON, and invalid schema yield honest advice outcomes.
