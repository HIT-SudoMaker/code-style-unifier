# Research square-template PB compensation

Status: resolved (2026-08-13)

Assignee: Codex research agent

Label: `wayfinder:research`

Blocked by: none

Parent: [Find the continuous-achromatic metalens compilation road](../map.md)

## Question

What square-lattice and geometry capabilities does the current periodic
template actually establish, and what do primary Wang--Tsai sources require
when a wavelength-independent PB base phase is combined with a
geometry-controlled spectral compensation phase? Which facts belong to
Method, template/binding, bounded plan, and observed evidence rather than the
Brief?

## Resolution

[The research record](../../../docs/research/2026-08-13-square-template-pb-compensation-seams.md)
confirms that the current Lumerical realization already fixes a square
periodic cell from one scalar period, equal x/y spans, and periodic x/y
boundaries. Square lattice is consequently template, qualification, binding,
and plan truth rather than a required Brief field.

The current template remains single-wavelength, normal-incidence,
zeroth-order, and unrotated. Its rectangle/ellipse path observes both linear
input bases and supports the present analytic PB orientation law, but it does
not yet prove that law over a continuous band. The first adaptation should
therefore retain this square construction, extend the bounded plan to full
design and holdout Jones spectra, and add a small physical-rotation
qualification set.

For one selected geometry `g` and physical orientation `theta`, the converted
response is modeled as `t_cross(g, lambda, 0) exp(i s 2 theta)`. Geometry
supplies the spectral compensation and its reference-wavelength phase
intercept; orientation supplies the wavelength-independent PB offset.
Assignment must solve them jointly and keep one geometry plus one orientation
fixed at every site over the whole band.
