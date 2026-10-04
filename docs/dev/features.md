# Feature catalog

The **user-facing capability catalog** of edi, each feature carrying a status per **surface** —
the diffraction-lib `docs/features` layout, extended with the milestone that delivers it. This is
the product-side complement of crysta's engine-facing
[feature catalog]
(Math · Need · Impl · Libraries): compute physics is checked off **there**; what a *user* can do,
on which surface, is checked off **here**.

**Surfaces** (one C++ product core underneath — ADR-0009): **LIB** = `import edi` (Python
bindings) · **CLI** = the `easydiffraction` binary · **APP** = desktop QML app · **WEB** = the same
app's WASM target.

**Legend:** ☑ shipped (gate green) · 🚧 in progress · ☐ planned (milestone linked) · ➖ not
applicable to this surface by design. Tick a box in the same change that lands the gate; the
roadmap stays authoritative for milestone status.

## 1. Project & data I/O

| Feature | LIB | CLI | APP | WEB | Milestone |
|---|:--:|:--:|:--:|:--:|---|
| Create / open / save an `.edi` project (directory format) | ☐ | ☐ | ☐ | ☐ | E02 · E05 · E07 |
| crysta-loader **parity** (edi writes → crysta reads, tested) | ☐ | ➖ | ➖ | ➖ | |
| CIF import/export (structures) | ☐ | ☐ | ☐ | ☐ | E02 |
| Measured-data intake (`.xye`/ascii; embedded `_data` loops) | ☐ | ☐ | ☐ | ☐ | E02 |
| Format zoo (`.gss`, …) normalizing to `.edi` | ☐ | ☐ | ☐ | ☐ | post-v1 (crysta C27 records ownership: here) |
| Golden example projects (beta `Examples/`, NCAF first) | ☐ | ☐ | ☐ | ☐ | |

## 2. Sample model

| Feature | LIB | CLI | APP | WEB | Milestone |
|---|:--:|:--:|:--:|:--:|---|
| Cell / space group / atom sites (CIF-like categories) | ☐ | ☐ | ☐ | ☐ | E02 · |
| ADPs (Biso) & occupancies | ☐ | ☐ | ☐ | ☐ | E02 |
| Parameter addressing (`model(id) _category.item(site)` form) | ☐ | ☐ | ☐ | ☐ | |
| Structure view (app) | ➖ | ➖ | ☐ | ☐ | E05 |

## 3. ExperimentBase

| Feature | LIB | CLI | APP | WEB | Milestone |
|---|:--:|:--:|:--:|:--:|---|
| InstrumentBase / peak-profile / background configuration | ☐ | ☐ | ☐ | ☐ | E02 · |
| Excluded regions | ☐ | ☐ | ☐ | ☐ | E02 |
| Multi-experiment (multi-bank) projects | ☐ | ☐ | ☐ | ☐ | E02 |

## 4. Analysis & refinement

| Feature | LIB | CLI | APP | WEB | Milestone |
|---|:--:|:--:|:--:|:--:|---|
| Pattern calculation via crysta (public API) | ☐ | ☐ | ☐ | ☐ | |
| Free-set via CIF SU brackets (`10.25(5)` = free) | ☐ | ☐ | ☐ | ☐ | |
| Refinement drive (bounds · fitting mode · run/cancel) | ☐ | ☐ | ☐ | ☐ | · |
| **Live fit plot** (residual-only stream, per-iteration) | ➖ | ➖ | ☐ | ☐ | (engine: crysta C09 callbacks) |
| Progress + cancellation on every surface | ☐ | ☐ | ☐ | ☐ | · |
| Joint multi-bank refinement (arrowhead, engine-side) | ☐ | ☐ | ☐ | ☐ | E02 |

## 5. Results & reporting

| Feature | LIB | CLI | APP | WEB | Milestone |
|---|:--:|:--:|:--:|:--:|---|
| Fit summary (Rwp/χ², parameters + e.s.d.s) | ☐ | ☐ | ☐ | ☐ | · |
| Report generation (headless/text path in the core) | ☐ | ☐ | ☐ | ☐ | |
| `--format human/plain/json` structured output | ➖ | ☐ | ➖ | ➖ | E03 (with crysta C10's CLI kit) |
| Undo/redo (crysta EditCommand; file-journal on the CLI) | ☐ | ☐ | ☐ | ☐ | · C10/E03 joint |

## 6. Application shell & platform

| Feature | LIB | CLI | APP | WEB | Milestone |
|---|:--:|:--:|:--:|:--:|---|
| Desktop shell on the decoupled GUI base (pages · `ApplicationInfo` · Style tokens) | ➖ | ➖ | ☐ | ☐ | E04 (needs guibase G03·G04) |
| QtGraphs plots via the base's charting façade | ➖ | ➖ | ☐ | ☐ | |
| Theme (light/dark) + WASM-safe settings persistence | ➖ | ➖ | ☐ | ☐ | E06 |
| QtIFW installer (app + CLI component — D8) | ➖ | ☐ | ☐ | ➖ | |
| Browser (WASM) target of the same host | ➖ | ➖ | ➖ | ☐ | E07 (needs guibase G01·G02 + crysta C28) |
| Feature-gated desktop↔web parity record | ➖ | ➖ | ☐ | ☐ | (ADR-0006) |
| i18n (`qsTr` coverage) | ➖ | ➖ | ☐ | ☐ | with E04+ (modern-Qt [MUST]) |

## 7. Distribution

| Feature | LIB | CLI | APP | WEB | Milestone |
|---|:--:|:--:|:--:|:--:|---|
| `pip install easydiffraction` → `import edi` (wheel with real bindings) | ☐ | ➖ | ➖ | ➖ | E02 |
| Tag-driven versions (versioningit — D10) | ☑ | ☑ | ☑ | ☑ | done 2026-07-04 (templates v0.1.7) |
| Optional `python -m edi` shim | ☐ | ➖ | ➖ | ➖ | post-v1 (ADR-0007 pt 4) |
| Lean CLI-only archive for clusters | ➖ | ☐ | ➖ | ➖ | post-v1 (D8) |

---

*Update discipline: a feature's box flips only with its acceptance gate (never by intention);
new user-facing features get a row here in the same change that adds them to a milestone.*
