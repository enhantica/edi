# RWG requirements — the edi (front-end) coverage

The [RWG stakeholder requirements] were analysed in the **crysta** knowledge base
(`docs/dev/requirements/rwg-requirements.md` there), which splits every requirement at the **engine ↔
product** boundary. Many requirements are **engine-scope** (crysta owns them); the requirements graded
**⚪ front-end / facility** there are **edi's** — the engine exposes a *hook*, and edi builds the
surface. This page tracks that edi-scoped half and where it lands in the edi roadmap.

> **How to read.** Each row: the RWG item, the **crysta hook** the engine exposes (so edi never
> re-implements engine logic — ADR-0003 boundary), and the **edi milestone** that builds the surface.
> The three new milestones **E10/E11/E12** (added 2026-07-10) were created for the RWG-driven surfaces
> that had no home; the rest map onto existing milestones.

## Coverage map

| RWG § | Requirement (edi surface) | crysta hook (engine exposes) | edi milestone |
|---|---|---|---|
| 06.1 | Fit quality across many histograms | per-bank Rwp/GoF (computed) | |
| 06.2 | Per-histogram inspector (data/fit/residual/metadata) | `y_calc`+residual on grid; `DatasetMetadata` | |
| 06.3 | Parameter trajectories, correlations, sensitivities | trajectory record; correlation `(JᵀWJ)⁻¹`; AD columns | |
| 06.4 | Compare competing models side by side | per-model result objects + AIC/BIC | |
| 01.4 / 06 | Sequential/parametric series view (`a(T)`) | `SeriesResult` table (crysta C32) | |
| 08.4 | LLM support (setup/troubleshoot/strategy) | LLM-assist surface contract: state snapshot, diagnostics→action, what-if | E11 T1–T3 |
| 08.3 | Guidance for novices / full-service pipelines | declarative strategies/presets | |
| 08.1 | A coherent UI (data/models/params/progress) | QObject adapter + thread-safe access + live-fit (crysta C07/C09) | E04 / E05 |
| 08.2 | Expert workflows without a UI-only path | headless CLI + Python API (crysta) | E03 |
| 09.2 | Neutron formats (NeXus/HDF5; `.gss`/`.xye`) | **engine-native NeXus reader** (crysta C27) + format-ownership decision | |
| 09.3 | Centralized facility data systems + remote | (out of engine core, ADR-0002) | |
| 09.4 | IPTS-style records / provenance | provenance record schema | |
| 10.4 | WASM (browser execution) | crysta WASM engine (crysta C28) | E07 |

## What this added to the edi roadmap

- **3 new milestones** — E10 advanced analysis/comparison/series views,
  E11 LLM-assist & guided workflows,
  E12 facility data-system integration (pages +
  `status.yml` + index rows + draft tasks).
- Each new milestone **gates on the crysta hook** it consumes (crysta C07/C09/C27/C32 +
  ADR-0052/0053/0054) — the cross-repo dependency is explicit in `status.yml` `gate:`.

## Boundary — why these are edi's, not crysta's

Per crysta [ADR-0002] (no Qt / no product logic in the C++ engine core) and edi
[ADR-0003](../adrs/0003-crysta-engine-boundary.md) (edi drives the engine only through its public
API): the **views, the assistant, the facility plumbing, and the coherent UI** are product concerns
edi owns; crysta's obligation is the **named hook** each surface reads. So the crysta KB is not
incomplete for lacking them — they are correctly tracked *here*.
