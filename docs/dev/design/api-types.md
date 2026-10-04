# edi — the user-facing API types

edi's reason for existing: it is the **home of all user-facing API types** (ADR-0001). This doc
sketches that API — the classes a scientist touches — and how it maps to `diffraction-lib` (the
shape/ergonomics source) and the crysta engine. It is a **design sketch to firm up in E02**, not a
frozen spec; the binding constraints are in the ADRs.

**Implementation home (ADR-0009):** the types below are implemented **once, in the C++ product core
(`core/`, Qt-free)**. `import edi` exposes them via **thin nanobind bindings + a small pythonic
sugar layer**; the app and CLI consume the same core directly. `diffraction-lib` defines the Python
surface's **shape and notebook ergonomics** to mirror — it is not ported as Python product code.

## The object model (the shape from `diffraction-lib`, carried into `import edi`)

```
Project                              # the top-level user object == an .edi project
├── sample_models / structures       # StructureFactory: cell, space group, atom sites, ADP/occ
├── experiments                       # ExperimentFactory: instrument, peak profile, background,
│                                     #   excluded regions, the measured pattern
└── analysis                          # free set (CIF SU brackets), bounds, fitting mode, results
```

- **`Project`** (core; bound as `edi.Project`) — create/load/save an `.edi` project; owns the
  structures, experiments, and analysis. The user's entry point (`import edi; p = edi.Project(...)`).
- **`StructureFactory` / structures** (core datablocks) — the crystal model as CIF-like categories
  (`_cell`, `_space_group`, `_atom_site`).
- **`ExperimentFactory` / experiments** (core datablocks) — per-experiment
  instrument/peak/scale/background/excluded-regions + the measured data.
- **analysis** (core) — the *user-facing* refinement config: which parameters are free (the **CIF
  standard-uncertainty bracket** convention `10.25(5)` = free, per crysta), bounds, fitting mode;
  results after a fit. The **numerics are crysta's** (ADR-0003) — this layer is configuration +
  presentation, not a minimizer.
- **io** (core) — read/write the `.edi`/CIF format. **edi owns the format.**

## The `.edi` project format (edi owns it; crysta reads it)

A directory, authored/saved by edi and read by crysta:

```
<project>/
  project.edi              # project display/metadata
  structures/*.edi         # the shared crystal structure(s)
  experiments/*.edi        # one per experiment/bank: instrument + peak + scale + background +
                           #   excluded regions + embedded measured _data
  analysis/analysis.edi    # fitting mode + minimizer + free-param bounds (in) + results (out)
```

- **Free flags via the bracket convention** — `_cell.length_a 10.25(5)` is *free*; a plain value is
  *fixed*. edi's editor sets brackets; crysta's `free_from_model` reads them. Same convention, both
  sides.
- **Parameter addressing** — the beta `IDEAS.md` shortcut form (`model(lbco) _cell.length_a`,
  `_atom_site.fract_x(Co)`) is a candidate for edi's user-facing parameter identifiers.
- **Parity is a tested invariant** — edi writes → crysta reads → agree (ADR-0003 pt 3). The format is
  specified on the edi side; crysta is a second reader that must not diverge. Whether the core reuses
  crysta's I/O module for reads or owns both directions is an E02 design question.

## The engine boundary (where compute happens)

edi never computes physics. The core's **engine adapter** is the **only** place edi touches crysta,
via its **public API** (ADR-0003): build the model → hand it to crysta → get a pattern / refinement
result, with progress/cancel and a residual-only path (for the app's live fit plot).
`analysis/calculators` and `analysis/minimizers` from `diffraction-lib` are **replaced by this
adapter**, not ported.

## One implementation, four surfaces (ADR-0002/0009)

The core is Qt-free; nothing in it or in `lib` imports Qt/PySide. The **Python surface** (`lib`) is
bindings + labelled presentation sugar (notebook/plot helpers) — mirroring `diffraction-lib`'s
exports (`Project`, `StructureFactory`, `ExperimentFactory`, io helpers, logging utils). The **CLI**
is a C++ `main()` over the core (ADR-0007). The **app** renders core state through thin QObject
adapters (app-layer) and QtGraphs — `display/` ideas from diffraction-lib become QML views; a
headless/text path stays available through the core for lib/CLI use.

## Open questions (to resolve in E02 / decisions)

- Exact public names/signatures (mirror `diffraction-lib`'s exports vs. refine them) —.
- **Binding ergonomics** (ADR-0009 consequence): which core types bind 1:1 vs get pythonic wrappers,
  so the notebook feel of diffraction-lib is preserved —.
- The parameter-identifier scheme (the `model(id) _category.item(site)` form) —.
- How much of `analysis` config surfaces vs. is derived from the brackets — follows crysta.
- Reuse of crysta's `.edi` reader vs. an edi-owned read+write pair (parity holds either way) —.
