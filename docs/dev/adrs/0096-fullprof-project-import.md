# 0096. Import and export FullProf projects

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

1. Load project > Import FullProf... reads a PCR file through the shared import base
   ([ADR-0098](0098-project-import-from-other-programs.md)), which also names the project after the
   PCR file and checks its parameter metadata. The result is a new, unsaved project with its
   measured data embedded; the user chooses where to save it. The browser has no import yet,
   because it needs a way to pick the companion files.
2. A legacy single-pattern project uses a same-stem companion or FullProf's recorded data filename.
   The multi-pattern format uses its declared filenames in pattern order. Companions reside beside
   the selected PCR. EDI uses its ordinary FullProf reflection reader for single-crystal INT data.
   The twin-capable layout uses the same native observations when every row is independent and
   uses the same scale. Grouped or multi-domain observations require a twin model.
3. Preserve the calculation range, exclusion intervals, background basis, calibration, diffraction
   model and phase links. Use the native space-group and Wyckoff resolver to convert normalized
   FullProf occupancies to chemical fractions. Keep the source scale with the conversion required
   by the radiation and geometry. An independently corroborated legacy occupancy factor is
   removed from atomic occupancies and its square is applied to intensity scales and applicable
   Larson parameters. For an out-of-order interpolation block, retain the source order's
   segment coverage and represent a jump with adjacent single-precision positions. Rebase
   the active coefficients when native knots move. Emit each pattern's interpolation points
   and exclusions consecutively, which is the positional order read by FullProf. Resolve each
   contributing phase's profile selector against its pattern's default. Use a shared profile
   when the effective profiles agree. Keep the explicit FullProf `:R` axes as the native
   rhombohedral setting with a factor of nine on the nuclear powder scale. For substitutional
   occupancies, check the normalization plateau across the co-occupants of each
   crystallographic orbit. Two equal filled orbits and an ATZ matching the unnormalized atom
   table establish a common factor while retaining partially occupied sites.
4. A nonzero FullProf codeword identifies a signed shift within a refinement group. Retain the
   starting value and use native parameter aliases and affine constraints for shared shifts.
   Transform the refinement directions when equivalent profile coefficients change basis.
   A declared zero refined-parameter count imports a fixed model.
5. Compatible polynomial CW and TOF instrument resolution files supply values for the native
   instrument calibration and peak shape. Their effective values are exported inline. GSAS RALF
   ALT and ISIS FXYE observations use forward bin widths and keep uncertainty scaled with intensity.
6. Convert compatible commensurate magnetic descriptions through native signed symmetry
   operators and magnetic moments. The combined FullProf magnetic phase form can carry magnetic
   centering vectors and BNS setting information. Classical `SYMM`/`MSYM` pairs convert when
   the moment operation is a signed axial copy of the spatial operation. The legacy body-centered
   form supplies an additional spatial centering. Sites in a recognized magnetic table setting
   can carry beta tensors and moments in the same phase. For the archived rare-earth ion labels, keep the
   FullProf radial coefficients in the native magnetic table and recognize them on export. Preserve
   difference-pattern phases with zero nuclear scattering and export them with the FullProf
   `mag_only` phase qualifier.
7. Report unsupported source terms and missing data before adopting the project. Verification uses
   FullProf's fixed-input calculated intensities on matched observations, with excluded rows
   removed from the metric. An active maximum-likelihood or unit-weight objective requires a
   corresponding residual. A nonzero or actively refined single-crystal `x-Lambda/2` term
   requires a harmonic-contamination correction. The bundled assistant skill also describes
   manual export to FullProf.

## Export

Desktop Export to FullProf and `export-fullprof` use the same core writer. The writer takes a
snapshot, evaluates the native relation graph, and publishes a new directory through the same
fresh-path primitive as a native project copy. It emits a PCR and one measured companion per
experiment. It writes FullProf XYDATA for measured powder patterns, a declared regular grid for
powder simulations, and INT for compatible single-crystal datasets. In XYDATA the final
unmeasured boundary record is outside the calculation range. FullProf uses it to evaluate the
last measured channel without truncating the peak profile. The observation code selects
a scale slot in the INT group. The reader and writer use the native single-crystal calculation for
CW and TOF data and the verified FullProf Larson isotropic and anisotropic models. Profile,
background, phase scales, masks and geometry are mapped into the corresponding FullProf fields.
Instrument parameters (zero, wavelengths, calibration, profile widths, asymmetry) are written with
their current, fitted values, so FullProf starts where the fit ended. A PCR has no place for
standard uncertainties or agreement factors, so when the project holds a fit the writer adds
`fit_results.txt` beside it: the fit's reduced chi-square, its R factors overall and per
experiment, and every free parameter's value with its s.u. rounded by the project's rule. FullProf
does not read it, and the importer never looks for it.

The fixed-input option emits zero active codewords for reproducible forward calculation.
Refinement export covers independent directions and native affine relations with one free source.
Use the native relation graph to identify these directions, including chains, before allocating
shared signed FullProf codewords in the target units. A nonlinear transfer or a dependent moved
by several independent variables needs a fixed export or a manual translation. The browser requires a separate multi-file output flow.

## Other conventions

Translate the observation mask using the actual grid and data dialect. Legacy D20
(`Ins=3`) rounds bounds to the nearest channel. Measured CW XYDATA uses the channel
before each lower-bound lookup. Write XYDATA limits between consecutive grid coordinates
to address the same channels. An excluded channel can still appear in FullProf's
profile output with background-only intensity.

Use FullProf's inversion-centred setting for bare origin-choice space-group symbols.
Preserve its explicit `:1` where supported. Project a rounded magnetic special-site
coordinate onto the same stabilizer used for FullProf's occupancy multiplicity. This
keeps the converted site's occupancy normalization and expanded orbit consistent.
Map source names to valid native datablock keys before building links or parameter
identities. Native saves fill the inactive second-wavelength slots of a single-wavelength
X-ray project with the same defaults used by the ordinary EDI reader.

## What EasyDiffraction does not have

The import maps FullProf's model onto crysta's existing one (ADR-0098, point 6). The list
below is everything FullProf can describe that the import refuses, approximates or drops.
Each item is future work for crysta as a general feature, never a FullProf-only option.

### Calculated differently (the project imports, results differ)

- **FCJ asymmetry.** crysta uses its own FCJ quadrature and profile window. FullProf's
  quadrature and its `AsyLim` angle above which asymmetry is switched off are not kept, so
  low-angle peaks differ slightly.
- **Bérar–Baldinozzi asymmetry.** crysta evaluates the width and angle of the correction
  at each reflection's 2θ, which keeps every reflection's integrated intensity. FullProf
  evaluates them at the pattern points and, judging from its output, uses the opposite sign
  of z and a different F_b. The import keeps P1 to P4 as crysta's A0, B0, A1, B1 with pseudo-Voigt (`Npr=5`);
  low-angle peak shapes differ.
- **Instrumental resolution file (`Res=1`, CW).** Its width terms are added to the PCR's
  U, V, W, X, Y and only the sums are kept. FullProf's split between instrument and sample
  is lost, and an export writes the sums inline with no IRF. FullProf's profile window,
  which depends on that split, can then differ (the YVO₃ case shows it).
- **Scattering lengths.** crysta uses its Sears neutron table; FullProf's built-in values
  can differ in the last digits.

### Refused (the import stops and names the item)

- Profiles: CW `Npr` other than the supported Gaussian, Lorentzian, pseudo-Voigt and TCH
  forms, TOF `Npr` other than the supported back-to-back forms, the FCJ profile `Npr=7`
  with FCJ terms written in the PCR, Bérar–Baldinozzi asymmetry with a profile other than
  pseudo-Voigt or together with FCJ, anisotropic size models, size terms on non-TCH
  profiles, per-phase profiles or profile families within one pattern.
- Instrument: resolution models other than `Res=1` CW polynomial and the TOF polynomial
  with `NPROF 9`, the IRF directives and records it does not know, extra CW instrument
  terms (secondary absorption, wavelength terms), X-ray doublet or polarization
  coefficients outside the supported set, X-ray polarization geometry `Ilo`, data formats
  `Ins` it does not read, `Job`/`Uni` axes it does not support.
- Sample: preferred orientation, TOF absorption (`ABSCOR2` and other models), X-ray
  absorption geometry, TOF extinction, single-crystal extinction laws other than the
  supported Larson forms, the single-crystal `lambda/2` contamination term.
- Background: `Nba=-4` and other background forms with no crysta counterpart, a decreasing
  terminal interpolated background.
- Atoms and symmetry: tabulated or X-ray scattering factors given in the PCR, anomalous
  scattering terms, atom models `N_t` other than the supported ones, space groups and
  phase types it cannot resolve to a crysta setting, incommensurate or non-collinear
  magnetic propagation vectors, magnetic operator layouts, centrings, phases or form
  factors it cannot convert, `MAG_ONLY` without a combined magnetic phase, turbostratic
  layers, an overall B together with anisotropic displacements.
- Refinement: parameter limits (`Nre`), restrained phases, refinement weighting `Iwg`
  other than the plain chi-squared, chi-squared weighting of single-crystal datasets,
  joint powder and integrated-intensity refinement, clustered powder reflections,
  external reflection models (`Irf`), the refinement geometry or search algorithm `Cry`
  other than profile or integrated intensities, a single-crystal dataset linked to
  several structures, nonpositive F amplitudes.

### Dropped or converted with loss

- Codewords become free flags and native constraints. A codeword relation that is not
  affine with one free source cannot be written back on export (see Export).
- FullProf's output-only settings (print flags, Fourier maps, reflection lists) are not
  imported.
- A `COMM` title becomes the project title; other comment lines are not kept.

## References

- [FullProf PCR documentation](https://fpsuite-doc.readthedocs.io/en/latest/pages/pcr/pcr_main.html)
- [FullProf manual](https://www.ill.eu/sites/fullprof/downloads/Docs/FullProf_Manual.pdf)
