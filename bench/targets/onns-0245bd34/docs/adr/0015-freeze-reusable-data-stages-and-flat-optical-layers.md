---
status: accepted
---

# Freeze Reusable Data Stages and Flat Optical Layers

The project adopts two building-block architectures with different composition grammars. `data` is an ordered series of data blocks—`load -> prepare -> perturb -> encode`—because each block advances sample meaning in one direction. `layers` is a flat set of physical blocks—diffraction, lens, phase modulation, and detection—because their order, repetition, and connection define an experiment-specific optical system rather than a package-level sequence. Restoration and any future task experiment assemble both kinds of blocks inside their own directories.

This rejects a shared `create_dataset` factory, a prescribed layer pipeline, and a shared ONN assembler. They would initially shorten call sites, but their interfaces would have to absorb task-specific variation and would move scientific choices away from the experiment that justifies them. The accepted consequence is a small amount of explicit composition code in each experiment; the benefit is that serial data semantics and flat physical primitives remain clear while task variation retains locality.
