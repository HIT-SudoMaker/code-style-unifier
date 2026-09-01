# Harness-agent tooling reference for MetaCraft

Date: 2026-08-08

Status: research record; not an architectural decision

## Question

What should MetaCraft learn from two established agent-skill repositories when
it becomes a harness-native scientific tool for Codex, Claude Code, and future
agent runners, without copying either repository's methodology or embedding a
language-model HTTP client in MetaCraft?

## Current acceptance scope

MetaCraft currently has two locally available harnesses: Codex and Claude
Code. They are the only integration targets that may be called supported by
this work, and both require clean-session evidence through the same local
command contract.

The planning audit observed `codex-cli 0.146.0` and Claude Code `2.1.220` on
2026-08-08. These are environment facts for planning, not minimum supported
versions or proof that the future acceptance runs pass.

Reasonix and Pi are future compatibility candidates only. They are not
installed locally, receive no dedicated Adapter or copied prompt, and must not
appear in the acceptance matrix or supported-harness documentation until a
later clean-session check proves their behavior.

## Primary sources

The following upstream repositories were cloned as ignored local reference
material. The exact revisions used by this record are:

| Repository | Local checkout | Revision |
| --- | --- | --- |
| [mattpocock/skills](https://github.com/mattpocock/skills) | [`reference/mattpocock-skills`](../../reference/mattpocock-skills/) | [`84fdeffd12f2ee307994d1eb6feb48173b6e0502`](https://github.com/mattpocock/skills/commit/84fdeffd12f2ee307994d1eb6feb48173b6e0502) |
| [obra/superpowers](https://github.com/obra/superpowers) | [`reference/obra-superpowers`](../../reference/obra-superpowers/) | [`44c9b2d6e889982ac18c27d05a19fefe335194e1`](https://github.com/obra/superpowers/commit/44c9b2d6e889982ac18c27d05a19fefe335194e1) |

The local checkouts are excluded by the root `.gitignore`; they are references,
not vendored product dependencies or nested submodules.

Important source files are pinned to the reviewed revisions so this record does
not depend on the ignored local clones:

- [`mattpocock/skills` README](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/README.md)
- [its Claude plugin decision](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/.agents/adr/0002-ship-as-a-claude-code-plugin.md)
- [its invocation mechanics](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/productivity/writing-for-agents/SKILL-MECHANICS.md)
- [its Claude plugin manifest](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/.claude-plugin/plugin.json)
- [`superpowers` porting guide](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/docs/porting-to-a-new-harness.md)
- [its Codex plugin manifest](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/.codex-plugin/plugin.json)
- [its Claude plugin manifest](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/.claude-plugin/plugin.json)
- [its session-start hook](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/hooks/session-start)
- [its shared bootstrap skill](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/skills/using-superpowers/SKILL.md)
- [its Codex tool mapping](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/skills/using-superpowers/references/codex-tools.md)

Current product documentation was also checked because plugin and MCP behavior
changes independently of these pinned repositories:

- [Codex skills documentation](https://developers.openai.com/codex/skills)
- [Claude Code skills documentation](https://code.claude.com/docs/en/skills)

## What the two repositories actually demonstrate

### One behavior source, thin harness glue

`superpowers` keeps skill bodies harness-agnostic and maps abstract actions to
the tools of each harness. Its porting guide explicitly separates shared skill
content, per-harness tool mapping, and bootstrap delivery. Harness integration
files carry discovery and translation; they do not fork the skill's behavior.

`mattpocock/skills` reaches the same destination with a smaller distribution
model: normal `SKILL.md` sources remain authoritative, while Claude and OpenAI
metadata describe how those sources are discovered. Its plugin ADR records a
real incompatibility between Claude's explicit skill-path list and Codex's
single recursive skill path instead of pretending the manifests are identical.

The transferable invariant is therefore:

> Share the domain behavior, not the harness manifest.

MetaCraft should have one scientific consultation cadence and one set of
grounds semantics. Codex- and Claude-specific files may describe installation,
discovery, and tool names, but must not contain separate period, height, or
evidence policy.

### Skills and live tools have different responsibilities

Both ecosystems use skills for reusable behavior-shaping instructions. Current
OpenAI and Claude documentation also support MCP for typed live data and
actions. These roles are complementary:

- a skill tells the agent when and how to conduct a MetaCraft design;
- MetaCraft tools form exact grounds, validate structured answers, and advance
  immutable scientific state;
- the harness supplies reasoning, web research, file access, and user
  interaction.

Putting exact period ceilings or candidate validation rules into a skill would
duplicate production science. Putting the whole interaction cadence into MCP
tool descriptions would create a wide, fragile Interface. The skill should
orchestrate; the tools should enforce.

### Automatic bootstrap is purpose-dependent

`superpowers` injects a bootstrap at every session start because it intends to
govern almost every software-development task. Its porting guide treats that
injection as the integration's defining requirement.

MetaCraft has a narrower domain. A universal session-start injection would spend
context in unrelated coding sessions and would make the plugin feel invasive.
The more appropriate pattern is the model-invoked skill described by
`mattpocock/skills`: keep a precise discovery description resident and load the
full workflow only when a metasurface-design request matches, while preserving
explicit user invocation.

Therefore MetaCraft should not copy the `superpowers` global bootstrap or add a
session-start hook merely because the reference implementation has one.

### Native installation matters; user configuration is not the product

`superpowers` requires every port to ride the harness's own installation
mechanism and rejects hand-editing global user configuration. It also requires
real clean-session transcripts and tool-mapping verification. The
`mattpocock/skills` ADR similarly records manifest limitations rather than
working around them with fragile symlinks.

MetaCraft should consequently ship thin native install artifacts where useful,
but must not make `.claude`, `.codex`, or user home edits part of its scientific
implementation. A harness that can already load a compatible skill and connect
to the same MCP server may need only documentation, not another Adapter.

### Distribution is tested behavior

Both repositories test packaging details that are easy to dismiss as ceremony:
manifest versions, included skill paths, ignored sources, deterministic archive
contents, and installation behavior. `superpowers` additionally treats a clean
session transcript as the acceptance test for a harness integration.

MetaCraft should test the installed result, not merely validate JSON files in
the source checkout.

## Recommended MetaCraft architecture

### Destination

MetaCraft becomes a provider-free scientific tool used by an external harness.
It does not initiate model or web requests. It forms a content-addressed
consultation request and validates the consultation answer returned by the
harness.

```text
one MetaCraft design skill
            |
            v
Codex or Claude harness -- reasoning / web / user interaction
            |
            v
one narrow local command Adapter
            |
            v
brief -> grounds -> advice -> choice -> planner
```

The dependency direction remains one-way: the skill and command Adapter depend
on MetaCraft's public scientific Interface; production science never imports a
Codex, Claude, plugin, or command implementation.

### Shared skill

One focused, model-invoked skill should describe the complete opening cadence:

1. obtain or clarify the user's wording;
2. ask MetaCraft to form the next consultation request;
3. obey its research policy;
4. reason over exact grounds and legal candidates;
5. submit one structured answer;
6. surface `evidence_required` honestly;
7. continue only with MetaCraft-validated advice.

The skill must not duplicate numerical rules, material aliases, prompt bodies,
response schemas, or choice validation. Those remain inside MetaCraft. Its
description should name the user goal and trigger conditions; the body should
name actions rather than Codex- or Claude-specific tool calls.

### One narrow command Adapter

Codex and Claude Code can both load a skill and run a local command. MetaCraft
therefore does not initially need an MCP server, plugin runtime, or
harness-specific executable. One command Adapter mirrors the one public
application operation:

```text
metacraft conduct --brief BRIEF.json --application-root RUN \
    --material-library MATERIALS.toml \
    [--lumerical-environment LUMERICAL.env] [--answer ANSWER.json]
```

Without `--answer`, `conduct` starts or resumes the exact application and may
return a consultation request. With `--answer`, the same operation validates
that answer and advances to the next typed outcome. The Adapter exchanges
structured JSON and owns no scientific policy. An MCP Adapter should be added
only if a real caller cannot use this command Interface or if typed tool
discovery demonstrates a measured reliability gain.

### Thin skill artifact

The first deliverable needs one canonical behavior source and two byte-identical
native discovery routers:

```text
skills/metacraft-design/SKILL.md
.agents/skills/metacraft-design/SKILL.md
.claude/skills/metacraft-design/SKILL.md
```

Each router contains discovery metadata and one instruction to read the
canonical file at `../../../skills/metacraft-design/SKILL.md`; neither carries
scientific policy. Codex discovers repository skills through `.agents/skills`,
while Claude Code discovers project skills through `.claude/skills`. Native
plugin manifests become worthwhile only if later distribution evidence shows a
need; they are packaging choices, not part of the scientific architecture.

## Research and network policy

Network access raises the information ceiling but does not itself create
stability. External pages can contain stale facts, low-quality claims, or prompt
injection. A consultation request should declare one of two modes:

- `closed_book`: benchmark reasoning uses only supplied grounds and cannot
  search for the benchmark paper or its withheld design values;
- `source_grounded`: production consultation may research external sources and
  must map every consequential external claim to a source locator.

External content is reference material, never agent instruction. External
sources may inform an advice but remain distinct from Authority-admitted
evidence. If an external claim conflicts with the exact study grounds, the
answer must report the conflict rather than overwrite the brief or domain.

This split prevents web-enabled benchmark runs from finding and copying the
published period and height that the blind comparison intends to withhold.

## What MetaCraft should not copy

- Do not copy the complete `superpowers` software-development methodology.
- Do not inject a MetaCraft bootstrap into every unrelated session.
- Do not maintain separate scientific prompts for Codex and Claude Code.
- Do not expose model endpoint, API key, retry, or provider JSON concerns from
  the production science package.
- Do not put executable physical policy only in Markdown instructions.
- Do not hand-edit users' global harness configuration during normal use.
- Do not assume a manifest field or hook works because another harness uses a
  field with the same name; verify the installed artifact.
- Do not let web citations silently become scientific evidence.

## Verification implications

A future implementation should pass four kinds of checks:

1. **Science contract:** identical brief and admitted grounds form identical
   request bytes; invalid values and invented ground identifiers are refused.
2. **Adapter contract:** Codex and Claude Code run the same command and produce the
   same MetaCraft record for the same answer.
3. **Installed integration:** a clean session discovers the MetaCraft skill,
   calls the tool without pasted setup instructions, and returns a complete
   transcript.
4. **Behavior evaluation:** the four blind benchmark briefs test correct
   mechanism reasoning, legal period/height neighborhoods, route-aware order
   handling, source discipline, and honest evidence escalation.

The acceptance prompt should describe an ordinary metasurface-design goal, not
name the skill or tool. Success requires discovery before any solver sweep is
planned. A separate explicit-invocation test should also work for users who want
deterministic control.

## Conclusion

The two repositories support a small but strong design:

> One shared scientific skill and one narrow local command Adapter.

This preserves a single source of scientific truth while allowing the two
currently testable harnesses, Codex and Claude Code, to contribute their own
reasoning, web access, and interaction model. Future harnesses may attempt the
same contract only when they are actually available for verification. The
design is simpler than an embedded language-model client or an initial
MCP/plugin platform, and more reliable than a skill-only design because the
program, not the prompt, still owns legal candidates, state transitions, and
validation.
