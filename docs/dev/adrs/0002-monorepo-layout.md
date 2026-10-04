# 0002. Monorepo layout `lib/ app/ shared/ cli/ docs/`

- **Status:** Accepted
- **Date:** 2026-07-04
- **Implementation:** 🟡 Partially implemented — E01 scaffolded the surface tree (`core/ lib/ app/ shared/ cli/ docs/ tests/`) + the CMake baseline (ADR-0009); product/API code is E02+.
- **Priority:** Highest
- **Forward constraint (binding on new features):** Keep the surface split. Product logic is
  implemented **once in `core`** ([ADR-0009](0009-cpp-product-core-thin-bindings.md)); the Python
  API surface lives in `lib` and is Qt-free; `app`/`cli` consume the core and never redefine product
  types. A new surface is a new top-level directory, not code smeared across existing ones.

**Amended 2026-08-27:** the documentation adopted the org-standard two-audience layout —
`docs/user/` + `docs/dev/` replace the `docs/`-vs-`knowledge/` split sketched below. The former
`knowledge/book` spec corpus (ADRs, feature catalog) lives at `docs/dev/`; `knowledge/` now holds
only the git-ignored reference-library clones and the FullProf verification data that stays beside
its notebooks and tests. The tree sketch below is preserved as decided in 2026-07.

**Amended 2026-07-04 (D2/D6 → ADR-0009):** a `core/` directory (the C++ product core) is added to
the layout; `lib/` becomes the thin Python binding surface over it; `cli/` is fixed as C++,
Python-free (ADR-0007); the app uses one C++/CMake host for desktop **and** WASM.

## Context

edi delivers one user-facing API (ADR-0001) across four surfaces. crysta's roadmap decision 20
already names the shape (`pip install easydiffraction` → `import edi`, in `edi/lib`; CLI in
`edi/cli`; desktop+WASM app in `edi/app` + `edi/shared`), and the edi seed
proposed adopting it. We need a fixed, ratified top-level
layout so every task packet, CI path filter, and lane-ownership row can reference stable paths.

## Decision

The edi monorepo top level is:

```
edi/
├── core/      C++ product core — the user-facing model, .edi/CIF I/O, the crysta adapter (ADR-0009). Qt-free.
├── lib/       Python library — thin bindings (+ pythonic sugar) over the core; import edi; dist easydiffraction. Qt-free.
├── app/       QML application — ONE C++/CMake host; desktop + WASM build targets, on the gui-components base.
├── shared/    shared session layer injected into the GUI base (theme/settings/page-model/undo…).
├── cli/       the C++ command-line surface, Python-free (ADR-0007).
├── docs/      product documentation (user-facing; distinct from knowledge/ the dev corpus).
├── tests/     cross-surface tests — tests/hidden/ (hidden spec) + tests/fixtures/ (golden projects).
└── knowledge/ the developer corpus (book, ADRs, design, roadmap, libraries, reviews).
```

- **`core` is the single implementation home; `lib` is the Python API surface** (thin bindings,
  Qt-free — no `PySide`/QML imports). `app` and `cli` consume the **core** directly (ADR-0009);
  nothing depends back on a host.
- **Package/dist names:** the import package is `edi`; the PyPI/dist name is `easydiffraction`
  (continuity with the ecosystem; matches crysta decision 20 and the diffraction-lib
  `lib_package_name`).
- **Path-filtered CI:** each surface's gates run only when its subtree changes (a `lib`-only change
  does not rebuild the WASM app), established in E01.
- **Build model:** one C++/CMake `qt_add_qml_module` host builds **both** desktop and WASM targets
  from one QML source tree (ADR-0006 as amended by ADR-0009); the `lib` bindings ship as a Python
  wheel. The GUI base's PySide-wheel path is not consumed by edi's app.

## Consequences

- Every task, CI filter, and lane-ownership row references stable top-level paths; the
  `COORDINATION.md` lane table is written against this layout.
- One repo builds three toolchains (Python wheel, Qt/QML desktop, Qt/WASM) — more CI surface than a
  single-language repo, accepted for one synced API and one answers file (vs the historical 3-repo
  split).
- `docs/` (user-facing product docs) and `knowledge/` (developer corpus) are deliberately separate
  trees with different audiences and build configs.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Separate repos per surface (lib/app/cli) | The historical split; triples release/sync overhead for one product. Rejected (ADR-0001). |
| Put shared session code inside `app` | `shared/` is injected into the GUI **base** and is reused by desktop+WASM; keeping it separate from `app` screens keeps the injection seam clean (ADR-0005). Rejected. |
| `src/edi/` single-package layout | Doesn't express the multi-surface product; the four surfaces need distinct build/test/CI treatment. Rejected. |
