# ADR 0025: Let geometry budget time and native decay close it

Status: accepted

Date: 2026-08-10

## Context

The periodic FDTD template used one fixed `2000 fs` maximum for every visible
and infrared cell. Native diagnostics then showed both failure modes of that
shortcut: ordinary visible cells often decayed much sooner, while one Arbabi
cell reached a shorter maximum with residual energy and reported normalized
transmission above one. A wave crossing the solver once is necessary but does
not prove that a finite source pulse or resonant energy has decayed.

The correction must preserve ADR 0017's sole layout owner, ADR 0013/0015's
response qualification, and ADR 0024's bounded work. It must not expose an
`fs` knob to callers or create an adaptive solve loop.

## Decision

The Lumerical periodic Adapter owns one immutable `PeriodicTimeBudget` beside
each `PeriodicConstruction`. Its ordinary maximum is the next `100 fs` step at
or above the greatest of:

1. the ordinary-profile floor of `1000 fs`;
2. `100 fs + 4 n_guard L / c`, where `L` is ADR 0017's complete FDTD span and
   `n_guard` is the greatest admitted atom, substrate, or air phase index;
3. `100 fs + Q_guard lambda ln(1/eta) / (2 pi c)`, with `Q_guard = 200` and
   native autoshutoff threshold `eta = 1e-5`.

The index applied across the complete span is deliberately conservative. The
`100 fs` injection guard and `Q_guard` are versioned ordinary-method policy,
not inferred source timing or a claim that a cell's physical Q equals 200.
The sole extended maximum is exactly twice the ordinary maximum.

Every solve records native status, actual simulated time, terminal
autoshutoff level, configured threshold, project, and execution. Status `2`
accepts the attempt after the existing physical response gates. Status `1`
consumes the sole extension. If the second attempt also has status `1`, it is
accepted only when the response changed by no more than `0.005` absolute power
and `0.01 rad` wrapped phase for propagation, or `0.005` Cartesian complex
amplitude for polarization. When reference-surface capability is admitted,
the complete Cartesian complex patch must additionally change by no more than
`0.005` in relative L2 norm and `0.005` transmitted power. Such acceptance
retains a residual-energy warning. Status `3`, an invalid physical response,
or an unstable second attempt closes as an explicit refusal. A third automatic
solve is forbidden.

Installation qualification uses the same two maxima but requires native
autoshutoff by the second attempt; response-to-response convergence cannot
substitute for a clean capability fixture. Accepted numerical closure is part
of the work construction record. Each attempt retains its own project,
execution, and termination evidence; a failed ladder additionally retains
`numerical-refusal.json` without fabricating a complete work record.

## Consequences

Visible and infrared constructions now receive explainable but different
caps, while cheap cells still finish early through native autoshutoff. Layout
plans the bound, native decay closes the run; planning stays pure, execution
stays product-specific, and science receives no solver-time control.

The ordinary profile remains intentionally bounded rather than universally
optimal. A future explicitly resonant, high-Q, broadband, dispersive-group-
delay, or microwave method must declare its own numerical contract instead of
silently enlarging this one. Changing any guard or tolerance is a method
change requiring new construction identity and fresh native evidence.
