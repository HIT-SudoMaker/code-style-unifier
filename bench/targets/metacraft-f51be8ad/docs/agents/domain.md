# Domain Docs

MetaCraft uses a single domain context.

## Before exploring

- Read the root `CONTEXT.md` and use its canonical language.
- Read relevant decisions under `docs/adr/`.
- Use `docs/agents/decision-traceability.md` to locate related Research Records, active concerns, implementation tickets, and verification evidence; never treat that index as normative authority.
- If either location is absent, proceed without inventing a replacement vocabulary.

## Consumer rules

- Do not use an avoided synonym when the glossary defines a canonical term.
- Surface an ADR conflict instead of silently overriding it.
- Keep implementation details out of `CONTEXT.md`.
- Add glossary terms and ADRs lazily through the domain-modeling workflow when a decision is actually resolved.
- For consequential work, preserve the chain Research Record -> ADR -> related active Canonical Specification concern -> implementation spec/ticket -> verification evidence. Record an explicit not-applicable reason for any omitted stage.
