# 08 - Let Field export only shared language

Type: implementation

Status: resolved (2026-08-01)

Blocked by:

- [Let one brief compile, conduct, and conclude](07-let-one-brief-compile-conduct-and-conclude.md)

## Outcome

Make `metacraft.field` a small shared-vocabulary interface. Importing the
package root exposes only values every field method may exchange and does not
load Torch, Lumerical, or a numerical realization.

Numerical methods remain available from their explicit owning modules. This
ticket narrows an interface; it does not move physics, duplicate a value, or
split files by size.

## Scope

Set `src/metacraft/field/__init__.py` to export exactly:

```python
[
    "ComponentBasis",
    "CoordinateFrame",
    "Field",
    "FieldComponent",
    "Medium",
    "PlaneSurface",
]
```

These six values remain owned by the shared field vocabulary.

Remove every root re-export of:

- realization identities;
- propagation outcomes;
- qualification values;
- capacity or memory outcomes;
- Debye values;
- pupil and focal-coordinate values;
- observation values;
- realization classes;
- qualification operations;
- propagation and evaluation operations;
- binding codecs.

Update all remaining production imports after Ticket 07. In particular,
`science/metalens/focus.py` may import the six shared values from
`metacraft.field`, but must import componentwise and electromagnetic
propagation values from their explicit numerical modules.

Update callers and tests that currently import specialized names from the
field root, including the applicable files under:

- `tests/field/`;
- `tests/science/test_propagation_delivery.py`;
- shared field and propagation fixtures;
- architecture import-surface tests.

Specialized callers must use their exact owners:

- `metacraft.field.angular_spectrum`;
- `metacraft.field.vector_angular_spectrum`;
- `metacraft.field.debye`;
- `metacraft.field.direct_debye`;
- `metacraft.field.fast_debye`;
- `metacraft.field.debye_qualification`;
- `metacraft.field.evidence`;
- `metacraft.field.reference_surface`.

Do not add lazy root forwarding for a removed name.

### Private device-memory interface

Add exactly one private owner:

```python
# src/metacraft/field/_device_memory.py

@dataclass(frozen=True, slots=True)
class AvailableDeviceMemory:
    device: str
    available_bytes: int

def observe_available_device_memory(
    device: str,
) -> AvailableDeviceMemory: ...
```

`AvailableDeviceMemory` requires a non-empty exact device name and a
non-negative exact integer byte count; `bool` is not an integer here. Zero is
a valid observation. The scalar or vector caller, not this value, decides
whether zero can satisfy its working-memory policy.

The private implementation owns only available-memory observation:

- for a selected CUDA device, call `torch.cuda.mem_get_info` for that exact
  device and return its free bytes;
- on Windows CPU, own the sole `GlobalMemoryStatusEx` structure and translate
  a false return into `OSError("memory_observation_failed")`;
- on POSIX CPU, multiply `SC_PAGE_SIZE` by `SC_AVPHYS_PAGES`.

Device selection and CUDA ordinal validation remain in each realization.
After CUDA is selected, observation or qualification failure propagates and
must not trigger a CPU retry. Platform and Torch exceptions other than the
defined Windows false-return translation propagate with their original
causes.

Scalar angular spectrum retains `_safe_working_memory`, including the greater
of 512 MiB and 20 percent reserve. Vector angular spectrum retains its
80-percent usable-memory rule. Both retain their own batching, one-plane fit,
applicability, and waiting behavior. Each caller reads only
`observation.available_bytes` and neither caller imports `ctypes` or `os` for
memory observation after the cutover.

Delete both `_available_memory_bytes` implementations and both duplicated
Windows memory-status structures. The private module passes the deletion test:
removing it would force the same CUDA/Windows/POSIX policy back into both real
callers. Do not accept a widened architecture-test allowlist as a substitute
for moving the ownership.

## TDD seam

Write failing tests first for:

1. `metacraft.field.__all__` equals the exact six-name list in the stated
   order.
2. Each of the six names imports and constructs through the field root.
3. A clean subprocess importing `metacraft.field` does not load `torch`,
   Lumerical, angular-spectrum, vector-angular-spectrum, direct-Debye, or
   accelerated-Debye modules.
4. Every specialized realization and qualification remains importable through
   its explicit owner.
5. Production has no root import of a removed field name.
6. Runtime dependency direction and the import DAG remain acyclic.
7. Direct private-interface tests cover CUDA, Windows success, Windows
   false-return failure, and POSIX observation.
8. Integration tests cross scalar and vector realization interfaces and prove
   that their distinct reserve policies are unchanged.
9. A selected CUDA observation failure propagates without a CPU fallback.
10. Source ratchets find one platform implementation, no caller-local
    `_available_memory_bytes`, and no duplicate memory-status structure.

Tests should verify the public import surface and representative behavior. They
must not inspect the implementation of `__getattr__`, because this ticket must
not add such a forwarding mechanism.

## Acceptance

- `metacraft.field` exports exactly the six shared values.
- Root field import does not load Torch or any numerical field realization.
- No removed name remains reachable through a root alias or re-export.
- All production and test callers use an explicit owner for specialized field
  behavior.
- Field, evidence, and result document shapes are unchanged by this ticket.
- No implementation is copied or moved merely to satisfy import paths.
- `_device_memory.py` is the sole owner of CUDA, Windows, and POSIX
  available-memory observation and has both numerical realizations as real
  callers.
- Scalar and vector reserve, batching, applicability, and failure policies are
  byte-for-behavior unchanged.
- A selected CUDA failure never falls back to CPU.
- No widened import allowlist is used to conceal ownership or dependency
  drift.
- Runtime imports remain acyclic.
- Focused field and architecture tests pass.
- Pyright reports no error or warning.
- Rust source remains unchanged.

## Verification

Use only:

```text
C:\Users\Administrator\miniforge3\envs\research_env\python.exe
```

Run:

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest -q -p no:cacheprovider `
  tests/field `
  tests/field/test_device_memory.py `
  tests/architecture/test_field_interface.py `
  tests/architecture/test_scientific_boundary.py `
  tests/architecture/test_runtime_import_dag.py

C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pyright
```

Run one isolated import assertion:

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -I -c "import sys; sys.path.insert(0, 'src'); import metacraft.field as field; assert field.__all__ == ['ComponentBasis', 'CoordinateFrame', 'Field', 'FieldComponent', 'Medium', 'PlaneSurface']; forbidden = ('torch', 'metacraft.field.angular_spectrum', 'metacraft.field.vector_angular_spectrum', 'metacraft.field.direct_debye', 'metacraft.field.fast_debye'); assert not any(name == item or name.startswith(item + '.') for name in sys.modules for item in forbidden)"
```

Audit remaining root imports:

```powershell
rg -n "from .*field import" src/metacraft tests examples
rg -n "def _available_memory_bytes|class _MemoryStatus|GlobalMemoryStatusEx|SC_AVPHYS_PAGES|mem_get_info" src/metacraft/field
git diff --check
git diff --exit-code 40f2127 -- rust
```

Every name found by the import search must belong to the exact six-name
interface. The resource search must show platform observation only in
`field/_device_memory.py` and calls through the frozen private function in the
two realization modules. No live availability is required.

## Stop and report

Stop and report if:

- one of the six shared values depends on Torch, Lumerical, or a numerical
  realization at import time;
- narrowing the root would require copying a type into a second module;
- a circular import appears;
- a caller cannot name the specialized module it actually uses;
- a field or evidence document would change;
- Rust source would need to change;
- any verification requires a live external process.

## Do not add

- root aliases for removed names;
- a lazy compatibility `__getattr__`;
- a second shared-field package;
- a generic realization registry;
- `utils`, `helpers`, or numbered modules;
- duplicated field values;
- physics, sampling, or threshold changes;
- import-cost tests that depend on machine timing instead of loaded-module
  facts.

## Comments

### 2026-08-01 - Reopened for private resource locality

The six-name root interface remains correct and frozen. The scalar and vector
angular-spectrum implementations nevertheless duplicate CUDA, Windows, and
POSIX available-memory observation, including the Windows structure and error
contract. The owner accepted one private Field module that owns this resource
observation for both real callers.

The shared private interface returns only an immutable available-memory
observation for one exact device. Scalar and vector realizations retain their
distinct working-memory reserve, batch sizing, applicability, and numerical
policies. Delete both duplicated platform implementations after tests cross
the shared private interface through each realization.

Do not change the six root exports, import cost, field documents, physics,
Torch loading behavior, device selection, CUDA ordinal validation, fallback
rules, or Rust. Do not add `utils`, `helpers`, a device registry, an algorithm
selector, or a public resource interface.

### 2026-08-01 - Exact deepening contract approved

The owner approved this ticket revision, not implementation. The private file,
two-name interface, platform semantics, caller-owned reserve policies,
failure behavior, deletion test, and verification commands above replace the
underspecified reopening note. Ticket 08 owns no current CSU blocking finding.

### 2026-08-01 - Private device-memory owner implemented

The owner subsequently authorized dependency-ordered implementation through
the accepted agent protocol. One writing agent implemented the deepening and
two independent read-only agents passed ADR/spec and standards review. Root
verification found one import-order finding after the first review; the writer
fixed only that ordering, both reviewers passed the targeted recheck, and the
root repeated the gate successfully.

`field/_device_memory.py` now solely observes available memory for one selected
device through the frozen two-name private interface. Scalar and vector
angular-spectrum realizations consume only `available_bytes` while retaining
their distinct reserve, batching, applicability, device-selection, and
selected-CUDA failure policies. The duplicate platform observers and Windows
structures are deleted. The exact six-name Field root remains cheap, and the
former widened importer allowlist is replaced by a dependency invariant that
protects underscore-private Field implementations.

Root verification passed the 147-test affected matrix before the final
import-only repair, then 52 targeted tests afterward; Pyright reported zero
findings, the full CSU scan reported zero blocking finding, isolated Field
import stayed Torch-free, and the Rust fixed-point and diff checks passed. No
Native execution or commit occurred in this ticket.
