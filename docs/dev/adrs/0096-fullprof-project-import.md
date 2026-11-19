# 0096. Open and export FullProf projects

- **Status:** Proposed
- **Date:** 2026-11-19
- **Implementation:** 🟡 Partial
- **Priority:** High

## Context

A FullProf control file describes phases, diffraction experiments and refinement directions. The
control file and observations are separate inputs. EDI already has project, structure, experiment
and reflection loaders (ADR-0052, ADR-0057 and ADR-0095), and the bundled FullProf intake skill
describes the equivalent manual construction through normal project actions.

## Decision

1. Desktop Open Project accepts a labelled FullProf PCR file through the core's ordinary project
   loader. It constructs a detached native project with measured data embedded. The user chooses
   the native destination when saving. The browser chooser needs a companion-file selection flow.
2. A legacy single-pattern project uses a same-stem companion or FullProf's recorded data filename.
   The multi-pattern format uses its declared filenames in pattern order. Companions reside beside
   the selected PCR. EDI uses its ordinary FullProf reflection reader for single-crystal INT data.
3. Preserve the calculation range, exclusion intervals, background basis, calibration, diffraction
   model and phase links. Use the native space-group and Wyckoff resolver to convert normalized
   FullProf occupancies to chemical fractions. Keep the source scale with the conversion required
   by the radiation and geometry. An independently corroborated legacy occupancy factor is
   removed from atomic occupancies and its square is applied to intensity scales and applicable
   Larson parameters. Use a shared profile when the phases' PCR profiles agree.
4. A nonzero FullProf codeword identifies a signed shift within a refinement group. Retain the
   starting value and use native parameter aliases and affine constraints for shared shifts. A
   declared zero refined-parameter count imports a fixed model.
5. Report unsupported source terms and missing data before adopting the project. Verification uses
   FullProf's fixed-input calculated intensities on matched observations, with excluded rows
   removed from the metric. The bundled assistant skill also describes manual export to FullProf.

## Export

Desktop Export to FullProf and `export-fullprof` use the same core writer. The writer takes a
snapshot, evaluates the native relation graph, and publishes a new directory through the same
fresh-path primitive as a native project copy. It emits a PCR and one measured companion per
experiment. It writes FullProf XYDATA for measured powder patterns, a declared regular grid for
powder simulations, and INT for compatible single-crystal datasets. The observation code selects
a scale slot in the INT group. The reader and writer use the native single-crystal calculation for
CW and TOF data and the verified FullProf Larson isotropic and anisotropic models. Profile,
background, phase scales, masks and geometry are mapped into the corresponding FullProf fields.

The fixed-input option emits zero active codewords for reproducible forward calculation.
Refinement export covers independent directions and native affine relations with one free source.
Use the native relation graph to identify these directions, including chains, before allocating
shared signed FullProf codewords in the target units. A nonlinear transfer or a dependent moved
by several independent variables needs a fixed export or a manual translation. The browser requires a separate multi-file output flow.

## References

- [FullProf PCR documentation](https://fpsuite-doc.readthedocs.io/en/latest/pages/pcr/pcr_main.html)
- [FullProf manual](https://www.ill.eu/sites/fullprof/downloads/Docs/FullProf_Manual.pdf)
