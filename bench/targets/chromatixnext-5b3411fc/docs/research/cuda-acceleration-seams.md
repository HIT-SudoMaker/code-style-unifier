# CUDA acceleration seams for ChromatixNext

Status: design analysis; no native CUDA strategy accepted yet

## Objective

Identify where a family-local native CUDA Execution Strategy can materially improve a PyTorch optical simulator without creating a second scientific implementation, weakening Windows/Linux portability, or replacing cuFFT with an unqualified in-house transform.

## Observed workstation and baseline

The inspected Windows workstation provides Python 3.12.13, PyTorch `2.12.0+cu130`, CUDA runtime and compiler 13.0, one CUDA device with compute capability 12.0 and approximately 32 GiB of memory. The retained acceleration observations already show that, for the existing 1024 by 1024 radiative angular-spectrum tracer, Prepared PyTorch execution is approximately two to five times faster than Eager PyTorch execution across the recorded precision and exterior cases while often reducing allocated or reserved memory. The first engineering gain therefore comes from resource lifetime and preparation, not native code.

`torch.compile` is presently unavailable in those observations because a working Triton installation is absent. The current `_acceleration_decision` rejects every native prototype whenever compiled execution is unavailable. That policy confuses an evaluated platform/toolchain limitation with a missing prerequisite and would prevent a Windows native strategy precisely where compiled PyTorch may not be deployable.

## Required acceleration ladder

Every hotspot should pass through four ordered, paired strategies:

1. **Eager PyTorch Execution** establishes the readable equation and portable reference.
2. **Prepared PyTorch Execution** freezes reusable coordinates, supports, phases, transforms, and workspaces under the Execution Plan.
3. **Compiled PyTorch Execution** evaluates `torch.compile` and CUDA Graph capture where the platform and static-shape contract permit them.
4. **Native CUDA Execution** is prototyped only for a measured remaining hotspot and retained only after the CUDA Acceleration Gate.

PyTorch documents that compositions of existing operators should ordinarily remain ordinary PyTorch code so that compilation, autograd, and other subsystems can see them. A custom operator is justified when a genuinely opaque or fused native calculation is required. [PyTorch custom-operator guidance](https://docs.pytorch.org/tutorials/advanced/python_custom_ops.html)

The gate should require a documented **Compiled Execution Assessment**, not successful compiler availability. If compiled execution is available, native CUDA competes against the fastest qualified Prepared or Compiled PyTorch strategy. If it is unavailable for the qualified platform/toolchain, the report retains the exact reason and native CUDA competes against Prepared PyTorch. An unattempted or scientifically failing compiler path still blocks promotion until resolved.

## Keep cuFFT authoritative

The dominant transforms should remain `torch.fft`, which dispatches to the vendor transform library on CUDA. cuFFT already owns transform planning, batched and strided transforms, JIT-loaded device kernels, and substantial temporary workspace. NVIDIA documents that plan creation fixes internal steps and may allocate large buffers; batched plans support strided layouts. [cuFFT documentation](https://docs.nvidia.com/cuda/cufft/)

ChromatixNext should not write an FFT implementation. Direct cuFFT plan ownership is considered only if profiling proves that PyTorch cannot expose required deterministic workspace bounds, plan reuse, or a safe fused callback and the direct adapter passes the same gate. Even then, the scientific transfer relation remains in the family operation and the cuFFT adapter remains one Execution Strategy.

## High-value native candidates

### Fused spectral transfer preparation

For repeatedly changing qualified parameters, one native kernel can derive discrete frequencies, longitudinal wave number, Physical Longitudinal Support, Alias-Safe Numerical Support, shift phase, evanescent decay where admitted, and the final complex transfer value without materializing every intermediate two-dimensional tensor.

This is primarily a memory and preparation-latency candidate. For a fully frozen propagation reused many times, storing the final transfer resource remains appropriate; native preparation does not eliminate its unavoidable memory.

### Fused Fourier-domain multiplication

After cuFFT, a memory-bandwidth-bound kernel may combine the transfer multiplication with every mathematically inseparable support or normalization factor. It must not absorb independent pupils, physical apertures, or other graph operations merely to reduce launch count. Native fusion follows Scientific Seams rather than crossing them.

### Fused detector accumulation

When no intermediate Spectral Intensity is published, a native strategy can compute magnitude squared, spectral weighting, detector response, pixel integration, and deterministic accumulation without retaining every intermediate spectral image. This is a promising memory-reduction seam because the owning scientific operation is already Ideal Detection and the fused equation does not hide reorderable optical effects.

### Controlled multislice stepping

Multislice workloads repeat FFT propagation and local modulation for many slices. CUDA Graph replay or a family-local native pointwise kernel may reduce launch and intermediate-memory overhead while cuFFT remains responsible for transforms. Full-loop fusion is admitted only when forward values, saved tensors, checkpointing, and the selected Gradient Contract remain explicit.

### Scaled-transform pointwise stages

Fresnel, scalable angular-spectrum, and CZT-based paths contain chirp generation, phase multiplication, modulation, and normalization stages that may be bandwidth-bound. They become candidates only after their destination-grid and normalization contracts are qualified.

## Rejected native targets

- a handwritten FFT;
- one generic optical CUDA kernel selected by mode flags;
- runtime compilation or downloading on an ordinary user workstation;
- kernels that silently downcast `complex128`;
- approximate fast mathematics outside one shared Scientific Tolerance;
- atomic spectral reductions whose ordering violates determinism or the Gradient Contract;
- fusion across independent Scientific Operations merely to improve a microbenchmark;
- a CUDA-only scientific capability with no authoritative PyTorch implementation.

## PyTorch integration contract

Native operators should be ahead-of-time built, family-local, functional by default, and registered under a stable project namespace through the PyTorch dispatcher. PyTorch requires an exact schema and mutation/aliasing declaration; compiler integration requires a matching fake kernel, and training requires an explicit autograd registration. `torch.library.opcheck` checks dispatcher and subsystem registration, while `torch.autograd.gradcheck` or independent finite differences are still required for mathematical gradient correctness. [PyTorch `torch.library`](https://docs.pytorch.org/docs/stable/library.html), [C++/CUDA custom-operator tutorial](https://docs.pytorch.org/tutorials/advanced/cpp_custom_ops.html), [autograd registration guidance](https://docs.pytorch.org/tutorials/advanced/python_custom_ops_registrations.html)

The initial native seam should return fresh storage and never mutate an Optical Field input. It needs representative `opcheck`, forward, adjoint, finite-difference, non-contiguous-layout, empty/odd/rectangular-shape, both-precision, Windows, Linux, eager, compiled, packed, grouped, and sequential cases. If packed execution treats the native operator as opaque, it also needs an explicit batching rule.

Prebuilt extension identity includes source closure, compiler, CUDA toolkit, PyTorch ABI/API, target compute capabilities, build flags, binary hash, and platform. PyTorch now documents a limited Stable ABI suitable for many production custom-extension cases, but it does not remove CUDA architecture, toolchain, and scientific qualification obligations. [PyTorch Stable ABI](https://docs.pytorch.org/docs/stable/notes/libtorch_stable_abi.html)

## Packaging and platform boundary

Normal installation and execution must not require NVCC, Visual Studio, Ninja, a network connection, or a writable compiler cache. Development builds may use the local CUDA toolchain. Releases either ship a qualified native binary for an exact supported envelope or omit that strategy while retaining PyTorch execution.

Windows and Linux native binaries are separately built and qualified. Windows remains single CUDA; Linux may partition independent Ensemble Axes or spectral groups across local GPUs, but every individual FFT stays device-local unless a later multi-device transform strategy is independently justified. Native availability is resolved before the Frozen Execution Plan and never becomes a runtime fallback.

## Benchmark correction

The current gate uses one 1024 by 1024 shape per precision and legacy periodic/zero-padded names. A production gate must use representative workload classes rather than one favourable point:

- small launch-bound, medium, and workstation-scale grids;
- odd, even, rectangular, anisotropic, and padded shapes;
- `complex64` and `complex128`;
- one and multiple Spectral Components under packed, grouped, and sequential plans;
- radiative aligned, shifted, isolated, and later outgoing near-field support where applicable;
- forward and every claimed gradient;
- repeated optimization and one-shot simulation lifetimes;
- Windows and Linux single CUDA.

Promotion remains capability- and strategy-specific. A native detector kernel cannot justify a native propagation kernel, and one RTX 5090 result cannot define the CUDA Qualification Envelope.

## Recommended first prototype

Do not start with the FFT. After the new propagation contracts are implemented and the Prepared PyTorch baseline is re-profiled, prototype one **Fused Spectral Transfer Preparation** kernel if its intermediate tensors materially affect peak memory, or one **Fused Detector Accumulation** kernel if detector-only polychromatic scenarios dominate memory. Choose between them using measured end-to-end scenarios, not intuition. Remove the prototype if it fails the existing material speed or memory threshold.
