# 0010. One parameter vocabulary, with metadata on the parameter

- **Status:** Accepted
- **Date:** 2026-08-21
- **Implementation:** ✅ implemented
- **Amended 2026-08-30:** the flattened metadata stays on the C++
  `ParameterSpec` and in the reports, but the six Python properties that mirrored it
  (`display_name`, `display_units`, `latex_name`, `latex_units`, `edi_names`, `cif_names`) had no
  consumer among edi's CLI, notebooks, pages and tools and left the Python surface; `units` stays as
  the `GenericNumericDescriptor.units` counterpart. The vocabulary rule above is unchanged.
- **Priority:** High
- **Forward constraint (binding on new features):** every public parameter name appears **once**
  across edi's surfaces — Python attribute, identity path, `.edi` item and crysta seam label agree
  leaf-for-leaf — and every `Parameter` a model carries points at a committed `ParameterSpec`
  declaring `units`, `validator`, `display` and `tags`. A new parameter lands by adding its spec
  row and category field together; a name that exists on one surface only is a defect.

## Context

(owner-requested) found edi **inconsistent with itself**: the `.edi` format was fully categorised
and already matched diffraction-lib category-for-category, while the Python objects and identity
paths were categorised for `Structure` but flat for `ExperimentBase` (38 fields) — two vocabularies
for the same quantity, three counting crysta's seam labels. The owner ruled the target shape be
built now (A/B/C, all 2026-08-16), with diffraction-lib parity as the top priority and every
remaining divergence argued in
[`docs/dev/design/diffraction-lib-parity.md`](../design/diffraction-lib-parity.md).

## Decision

1. **One vocabulary, leaf-identical across four surfaces.** The categorised object tree
   (`experiment.peak.broad_gauss_sigma_0`, `structure.cell.length_a`, …) is the identity-path
   grammar verbatim; `.edi` items are the specs' canonical `edi_names[0]`; crysta's free-label
   leaves match edi's field leaves (crysta keeps its own namespacing — bank and site prefixes).
   The schema-2 `.edi` epoch carries the format half.
2. **Metadata rides the parameter.** `ParameterSpec` (`edi/parameter_spec.hpp`) is a hand-written
   inline table — the crysta dictionary columns without the YAML+codegen pipeline (≈40 rows do
   not pay for build machinery; revisit if the table triples). Specs are static constants; model
   constructors attach them; readers and the writer consume the ordered
   `edi_names`/`cif_names` (first canonical for writing, every listed name accepted on read).
3. **Validation is staged exactly three ways** — Python attribute set, `.edi`/CIF load, factory dicts — and the adapter's refined-value write-back deliberately
   bypasses it (minimizer trial values may leave physical ranges; diffraction-lib's `_set_value_from_minimizer` does the same). **Amended (the owner's option B,
   2026-10-02):** what the fit keeps, a load must reopen. A fit leaves a value outside its admissible range where the minimizer put it and every save writes it,
   so the `.edi`/CIF readers no longer refuse a finite value outside its spec's range: it loads, `load_project` names each such value in one warning, and the app
   shows it in red (ADR-0017 §17). A malformed or non-finite number is still refused. The Python attribute set and the app's typed values keep the range: it
   describes what a user may enter, not what a fit may return. crysta's loader follows the same rule (`crysta.schema.parameter_outside_range`, a warning). **The
   rule covers editing ranges only (2026-10-04):** a physical-domain limit the engine enforces when it calculates, fits or saves is refused at load, in both
   products, with a domain error, so load, use and save agree — the March–Dollase ratio (> 0) and random fraction ([0, 1]) and the X-ray monochromator
   polarization coefficient ([0, 1]) and 2θ ([0, 180]°), a line-shift pair whose |SyCos| + |SySin| overflows, a nonpositive wavelength and a cell crysta's metric
   refuses (review-9 F13: positive lengths, angles in (0, 180)°, a positive determinant, a finite positive volume and a finite reciprocal tensor — crysta's own
   `cell_domain_message`, reached through the adapter, never a copy). Every reading entrance applies them: `load_project`, both structure readers and the
   `from_cif_*` factories built on them. The solver keeps a trial inside them, so a fit never leaves one; the bond-cutoff settings keep their own refusal.
4. **The path grammar is the object grammar.** Plural spellings (`structures[<id>]`,
   `experiments[<id>]`) are always valid; the singular prefixes are the ruled shortcuts, valid
   exactly as the object accessors are. Produced keys stay canonical per producer.

## Consequences

- The crysta seam's translation tables shrank toward identity: the TOF/CW label collision died
  with the rename, killing the kind dispatch it forced; the mapping stays total and fail-closed.
- Every `.edi` file is schema 2; v1 files refuse with one clear message. Pre-1.0, atomic, ruled.
- Adding a fifth experiment-type axis is a new field on `ExperimentType`, never a new enum
  product; no combined discriminator exists (`ExperimentKind` is retired).
- Metadata exposure (`units`, display strings, tags, bounds) is uniform on every bound Parameter,
  and `parameter_specs()` enumerates the committed table for gates and documentation.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| YAML dictionary + codegen | Right at crysta's scale; edi's ~40 rows do not pay for the build machinery. Column shape adopted, pipeline not. Revisit if the table grows severalfold. |
| Metadata in a path-keyed registry, `Parameter` stays `{value, esd, free}` | Makes metadata unreachable from a bound Parameter object (parity breaks: `param.units` etc.); registry lookups leak into every consumer. Rejected. |
| Aliases for renamed attributes | Owner-ruled out (hard rename, criterion 3): two spellings in docs and code is the worse cost pre-1.0. |
| Object tree now, identity paths later | Leaves a third vocabulary standing and guarantees a second migration — rejected by the owner across every decision in the packet. |
