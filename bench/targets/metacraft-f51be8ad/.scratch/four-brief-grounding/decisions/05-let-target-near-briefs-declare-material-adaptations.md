# Let target-near briefs declare material adaptations

Label: `wayfinder:grilling`

Status: resolved (2026-08-08)

## Question

When an installed solver has no exact default record for a paper material,
should a benchmark brief remain blocked on that paper material, silently map
it to a different family, or state a realistic target-near material while
preserving the paper fact separately?

## Resolution

The Yun and Arbabi blind briefs use the canonical family `silicon`, selected
explicitly as `Si (Silicon) - Palik`. Their published references continue to
state `hydrogenated amorphous silicon`. Each case records the relationship as
an `adapted` atom-material alignment with a rationale; it never claims that
the two families are equivalent.

The Khorasaninejad brief retains `amorphous titanium dioxide` and explicitly
selects `TiO2 (Titanium Dioxide) - Siefke`, the reviewed installed record that
best matches its low-temperature ALD thin-film context and covers 532 nm.

Wording advice may ask a material clarification such as “Did you mean
silicon?” when the user's term is ambiguous. The suggestion remains untrusted:
it cannot rewrite the wording, create an alias, or make a solver selection.

After wording and material binding are resolved, the existing scientific
sequence remains unchanged: choose one period, derive the resulting height
domain, then choose one height. Paper period and height stay outside the blind
brief as post-design comparison context.

## Consequences

- Blind cases can exercise the installed solver without falsifying published
  material truth.
- Case/reference differences remain visible in canonical identity and review.
- A future exact a-Si:H dataset can be registered as its own family without
  changing or aliasing the silicon registration.
- No production alias table, fuzzy matcher, or material substitution service
  is introduced.
