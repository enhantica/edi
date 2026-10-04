# 0008. Minimized external deps + permissive (BSD-3) licence

- **Status:** Accepted
- **Date:** 2026-07-04
- **Implementation:** 🟡 Partially implemented — the BSD-3 licence is set (`pyproject.toml`) and E01 added no new runtime dependency (Qt gated off); the dep-minimization constraint stays enforced as code lands.
- **Priority:** High
- **Forward constraint (binding on new features):** A new **runtime dependency** requires
  justification against the minimized-deps goal (prefer Qt / the standard library / crysta; vendor a
  small permissive shim over adding a heavy dependency). Record the dependency + rationale in the
  task packet; the reviewer checks it.

## Context

A stated product goal is **improved versions of the migrated components with a minimized set of
external dependencies**. The migration sources carry avoidable weight the audit flagged — e.g.
gui-components has a NumPy **runtime** dependency, a vendored `eval`-based JSONPath, and
font/asset bloat. edi should not inherit that. Dependency choices are also
**licence-constrained**: edi is meant to be embedded in Qt apps and published on PyPI, and it
borrows ideas from copyleft sources (gui-components/slate where GPL/LGPL applies, kirigami-gallery
LGPL) that must **not** be linked into a permissive product.

**Amended 2026-10-02 (owner decision 2026-09-29, [ADR-0015](0015-edi-app-stack.md) §6):** the **app** links Qt
Graphs (GPL-3.0-only), and with Qt Quick 3D, so the distributed app is a GPLv3 work. edi's source stays
BSD-3-Clause, and decision 2's "do not link against GPL" still binds the core, the Python package and the CLI. The
new runtime dependency (`qt6-graphs`, app environment only) is the justified one of decision 3: the pattern chart
needs a GPU chart that also builds for the web, and Qt ships it. **:** the app links Qt Quick 3D (`qt6-quick3d`,
GPL-3.0-only, app environment only), the second justified runtime dependency of decision 3: the structure view
needs instanced GPU drawing of thousands of spheres and cylinders that also builds for the web, and Qt ships it
(it was already in the environment as a dependency of Qt Graphs). `DEPENDENCIES.md` and the About dialog name it.

## Decision

1. **edi is permissive: BSD-3-Clause.** Chosen for continuity with crysta (BSD-3) and to allow
   embedding + PyPI distribution.
2. **Study-only vs borrowable, per source.** Reference projects in `knowledge/libraries/` are study
   material: extract **ideas, design, and patterns in our own words**; **never copy code**,
   especially from copyleft sources. Do not **link** the product against GPL/LGPL. The
   study corpus's licence table, kept with the corpus, is consulted before borrowing.
3. **Minimized runtime dependency set.** Prefer Qt + the Python standard library + crysta over new
   third-party dependencies. A new runtime dep is justified in the task packet against this goal;
   prefer vendoring a **small permissive shim** to pulling a heavy library (e.g. replace the
   `eval`-JSONPath and the NumPy-at-runtime patterns rather than porting them). Dev/test/build tools
   are exempt (they don't ship).
4. **Reviewer gate.** Adding or bumping a runtime dependency is a review checkpoint: the reviewer
   confirms the justification and the licence compatibility.

## Consequences

- Smaller install/bundle (important for the WASM target), fewer security/maintenance liabilities,
  and a clean permissive licence story for embedding + PyPI.
- Some convenience libraries are off-limits at runtime; occasionally we vendor a small shim instead
  — a deliberate trade of a little code for a lot less dependency surface.
- The licence table must be kept current as reference projects are added to `knowledge/libraries/`.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Port dependencies as-is from the migration sources | Inherits exactly the bloat/licence issues the audit flagged (NumPy-at-runtime, eval-JSONPath, fonts). Rejected — improve, don't transcribe. |
| Copyleft (GPL/LGPL) licence to freely reuse copyleft sources | Blocks embedding in permissive Qt apps and PyPI distribution; the ecosystem is permissive (crysta BSD-3). Rejected. |
| No dependency policy (add what's convenient) | Dependency creep silently defeats the minimized-deps product goal, especially on WASM. Rejected — packet justification + reviewer gate. |
