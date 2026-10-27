# 0052. Each experiment describes itself

- **Status:** Accepted
- **Date:** 2026-10-26
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

A project record described the measurement with five `_metadata` tags: dimensionality, polarisation, instrument,
facility and purpose. The first four describe an experiment, so a joint fit of two instruments could not state both,
and the purpose follows from the data and from the CLI registry. crysta now holds the four on each experiment
and converts the retired tags in one place, `legacy_project_metadata`.

## Decision

1. **The model.** `ExperimentType` holds `dimensionality` and `polarisation`, the instrument its `name` and `facility`,
   each as declared and empty until declared. Read, an omitted one is its effective value: `1d`; `unpolarised` for
   neutron and `.` for X-ray; an unknown instrument and facility. The reader refuses any other dimensionality, or a
   polarisation that does not fit the probe, naming the item. A save writes them through crysta's writer.
2. **The retired tags.** A project record that still carries them is converted at load by crysta's
   `legacy_project_metadata`: an item an experiment declares stands, one it leaves out takes the converted value. Each
   retired tag warns once and is never written back. The committed records were migrated with crysta's
   `tools/dev/migrate_project_metadata.py`, its ledger in `tests/fixtures/metadata_migration.tsv`.
3. **Python.** `ExperimentType.dimensionality` and `.polarisation`, and the instrument's `name` and `facility`, read the
   effective values and set a declared one (deviation D90).
4. **The app.** The experiment-type group shows the dimensionality and the polarisation, each with its one admitted
   value. The instrument group starts with two selectors, Facility and Instrument, each listing "Not specified" first,
   then the facilities of edi's and diffraction-lib's examples and a Laboratory entry, and the instruments of the chosen
   facility for the experiment's sample form. For an experiment made from a data file they can be chosen, and "Not
   specified" is written `?`; for one read from a `.edi` or `.cif` file they show what the file states and cannot be
   changed. A name the file states that the lists lack is shown as written. The example facets are read from the
   experiments: the instruments and facilities are the list over a project's experiments, the dimensionality and
   polarisation are mapped as the conversion maps them (`1D` to `1d`, shown as "1D"; `none` to `unpolarised`), and the
   purpose is "refinement" when any experiment has measured data, else "simulation".
5. **Verification projects.** A CLI project the registry marks `verification: true` stays a CLI project, and the app
   bundle leaves it out; no record states a purpose any more.

## Consequences

- Amends ADR-0031: the descriptive tags no longer live in the project record, and the purpose is derived.
- Amends ADR-0048: the bundle leaves out the registry's verification projects by its flag.
- The app sets the instrument and facility only for an experiment made from a data file; a script sets them for any
  experiment through Python.
