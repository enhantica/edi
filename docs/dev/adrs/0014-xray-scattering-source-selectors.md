# ADR-0014 — The X-ray scattering-source selectors: edi carries crysta's category as written

- **Status:** Accepted (the design records 2026-09-26 (2026-09-26, "source-named X-ray scattering selectors") " folds in source-named X-ray
  scattering selectors…" and (2026-09-26, "Cromer–Liberman as the default") "OWNER DECISION: builds Cromer–Liberman as the default…")
- **Date:** 2026-09-26

**Amended 2026-09-27 (crysta
[ADR-0067]):**
the category gains `_scattering_source.neutron_scattering_length`, carried under the same five rules with the
radiation reversed: a neutron experiment (declared or omitted radiation) may declare it, an X-ray one refuses it.
crysta additionally refuses it together with the structure's
`_scattering_length` map (ADR-0067 §6). The edi FullProf verification pages declare `sears1992` in the
experiment's `.edi` text instead of a hand-copied `scattering_lengths_fm` map.

## Context

crysta owns the physics and the `.edi` format of the X-ray scattering sources: crysta
[ADR-0066]
decides the category, every admitted value (one table row each: publication, form, range, coverage,
engines, measured differences), the defaults and the wavelength lookup. edi delegates calculation to crysta
(ADR-0003) and round-trips projects, so it needs its own rule for carrying the category.

## Decision

1. **The category.** On an experiment whose `_experiment_type.radiation_probe` is `xray`, edi reads and writes
   `_scattering_source.xray_form_factor` (`wk1995`, `it1992`) and `_scattering_source.xray_dispersion`
   (`cromer-liberman`, `sasaki1989`, `it1992`, `none`) exactly as crysta defines them. The defaults are
   `wk1995` and `cromer-liberman` (owner decision, the design records (2026-09-26, "Cromer–Liberman as the default"), (2026-09-26, "three X-ray dispersion sources")); the value table itself is
   crysta's and is not restated here, so the two cannot drift. A test that pins numbers declares both items.
2. **Presence-faithful round trip.** A declared item is written back as written; an omitted item is not
   written (the typed-axis rule edi already applies to `_experiment_type`).
3. **Fail closed at load.** A neutron experiment declaring either item, or an unknown value, is a structured
   load error naming the admitted values — never a silent default.
4. **Delegation.** The adapter passes the declared values to crysta with the radiation on every calculate
   and fit path, so edi never chooses a table itself.
5. **Declared in the project file.** adds no Python member for the selectors: a page or script declares them
   in the experiment's `.edi` text, which reaches the loader rule above. A Python member follows when
   diffraction-lib defines the category, and the crysta-py ⊆ edi-py rule (ADR-0011) then applies to both
   products together.

## Consequences

A project saved by edi and one saved by crysta carry the same bytes for this category, and an edi page
comparing against FullProf declares `it1992` + `sasaki1989` in the file, not in edi code.
