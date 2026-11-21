# 0097. Import GSAS-II projects

- **Status:** Proposed
- **Date:** 2026-11-19
- **Implementation:** 🟡 CW neutron and X-ray, TOF neutron, and paired magnetic CW powder projects
- **Priority:** High
- **Forward constraint:** The core owns both GPX decoding and model translation. An additional
  GSAS-II model must declare its admission rules, source units and independent numerical reference.

## Context

The [project loader](0052-project-folders-archives-and-opening.md) opens a complete Edi model.
The existing [FullProf text tool](../../../tools/fullprof/ralf_to_xydata.py) converts measurements
for the normal data loader. The assistant's [GSAS intake](../../../data/assistant/skills/gsas-intake/SKILL.md)
provides a text-evidence workflow. A GSAS-II GPX holds the observations and the model together.
It contains serialized Python records whose usual reader can invoke Python objects.

## Decision

- The Qt-free core admits a GPX through the normal project loader. Its reader interprets the
  primitive records and recognized NumPy numeric storage layouts as data. A file cannot resolve
  a Python object or request an import, callable or file lookup. The reader bounds bytes,
  objects, arrays and stack size and refuses unsupported record operations. The desktop
  Open project file picker uses the same loader. The converted project is unsaved and the
  existing Save As operation produces the standard Edi files.
- A developer-side GSAS-II exporter emits ASCII JSON using the `gsas-ii-pnc-v1` format.
  Use the exporter on trusted local inputs because it uses the upstream GPX reader. The core
  accepts this bundle with the `.gsas.json` suffix and uses the same model translation as for
  GPX. The development environment builds GSAS-II to generate independent reference profiles.
- The reader accepts Python 2 and 3 GPX layouts used in the tutorial corpus, including
  NumPy's C- and Fortran-ordered arrays and masked arrays. Recognized GSAS-II variable
  references and expression records are inert data. Their content is consumed only by a
  corresponding model mapping.
- The multi-bank powder bundle uses `gsas-ii-powder-v2`. An active model may contain one or
  more nuclear phases, joint powder datasets, and isotropic or anisotropic displacement.
  A GPX space-group symbol selects candidates and its expanded operators select the matching
  table setting. A phase without a matching setting is refused. A paired nuclear and
  magnetic CW neutron model uses one Edi structure when the two phase links, cells, sites,
  and applicable ties agree. The signed symmetry operators and moment components are
  retained.
- Each measured row carries two-theta in degrees or TOF in microseconds, intensity, and
  inverse variance. The Edi measurement uses sigma = 1/sqrt(weight). A zero-weight row
  remains on the grid and receives a reversible excluded region with positive placeholder
  sigma. Masked rows retain their weights and use a distinct exclusion identifier.
  The background domain is the observed range inside the active GPX fit limits. The
  legacy GSAS-II `chebyschev` power series is expanded in the Edi Chebyshev basis.
- CW Debye–Scherrer sample shifts map to the Edi cosine and sine terms through
  `-0.18 / (πR)` for sample displacements in micrometres and radius in millimetres.
  X-ray wavelengths and doublet ratios are transferred. GSAS-II X-ray polarization and
  azimuth are combined into the effective coefficient of cos² 2θ.
- The TOF mapping applies `difC`, `difA` and zero directly, and uses the absolute bank angle.
  The GSAS-II back-to-back exponential rates and Gaussian variances use the same bases
  as the Edi Jorgensen–Von Dreele model for the admitted terms. Fixed isotropic Lorentzian
  broadening maps to the TOF size term `1e-4 difC / size` and strain term
  `1e-6 difC microstrain`. Active reciprocal calibration, linear-in-d variance, and
  inverse-d² decay terms are refused.
- GSAS-II stores Gaussian variance in centidegrees squared. Edi stores squared Gaussian FWHM
  in degrees, so multiply U, V and W by 8 ln(2) / 10000. For each Lorentzian coefficient, add
  the matching fixed sample contribution before dividing by 100. GSAS-II's X is the secant
  term and Y the tangent term. Edi uses the opposite names. The secant contribution is
  1.8 wavelength / (π size in µm) in centidegrees. The tangent contribution is
  0.018 microstrain in ppm / π in centidegrees.
- The two Edi FCJ apertures are each half of GSAS-II's effective SH/L. A free SH/L uses a
  declared equality between the two Edi apertures. Edi uses its own
  FCJ quadrature and a finite profile window. The two engines also differ in how they apply
  zero shift to the angle at which intensity and widths are evaluated.
- Edi's linked scale is the histogram and phase scale product divided by 100 times the
  starting cell volume for CW and by cell volume for TOF. GSAS-II multiplies by reciprocal
  cell volume and evaluates its CW
  kernel in centidegrees. The single free scale, instrument/profile and background flags
  are preserved. Edi uses its Sears neutron table. Folding the fixed size and strain terms
  into the width discards their independent identity in the saved Edi model.
- The reverse developer workflow constructs a new GSAS-II project from the saved Edi file.
  It rebuilds datasets, phase links, single or joint structural models, atomic ADP
  equalities and supported paired magnetic models. It reparametrizes inseparable GSAS-II
  terms using the Edi model's effective values. The archived feature inventory records
  source workflows that cannot be preserved in the current Edi model.

These mappings use the upstream `GetSampleSigGam`, `GetReflPos`, `getPowderProfile`,
`getFCJVoigt3`, `PYPSVFCJO` and `getBackground` implementations at the pinned
[GSAS-II revision](https://github.com/AdvancedPhotonSource/GSAS-II/tree/46b3d7b541d344f9506848c37b35737b1a87ddac).
Profile differences are reported on the total and the background-subtracted Bragg signal.
The reference calculation uses zero refinement cycles and the comparison reapplies the Edi
calculation after reopening the saved project.

## Run the PbSO₄ verification

Create a trusted GPX in GSAS-II with one PbSO₄ phase and the PNC histogram from
[the scripting tutorial exercise files](https://advancedphotonsource.github.io/GSAS-II-tutorials/PythonScript/data/).
Use `PbSO4-Wyckoff.cif`, `PBSO4.CWN` and `inst_d1a.prm`, link the phase to the bank,
and save the starting project. Run these commands from the repository root after building Edi.

```bash
pixi run --locked -m tools/deps/gsas-ii/pixi.toml python -m tools.gsas_ii.export_project \
  pbso4.gpx pbso4.gsas.json --reference
pixi run --locked python -m tools.gsas_ii.import_project \
  pbso4.gpx pbso4-edi --comparison pbso4-comparison --reference-bundle pbso4.gsas.json
```

`edi.Project.load("pbso4.gpx")` opens the same model without GSAS-II installed.
The optional comparison writes a CSV on the observed grid and a JSON summary.

## Recheck the tutorial corpus

Use the revision of [software-examples](https://github.com/enhantica/software-examples) recorded
with the test run. The batch check visits the dedicated project folders and reference folders,
attempts to open each GPX, and reports the stage and error for each failure. It saves,
reopens and recalculates each case that opens. A matching independent reference bundle
also enables a numeric comparison.

```bash
pixi run --locked python -m tools.gsas_ii.check_corpus /path/to/software-examples/gsas-ii \
  --roundtrip-dir gpx-audit --report gpx-corpus-check.json
pixi run --locked -m tools/deps/gsas-ii/pixi.toml python -m tools.gsas_ii.compare_corpus \
  /path/to/software-examples/gsas-ii gpx-audit --report gpx-roundtrip-check.json
```

## Validate the reverse direction

The developer exporter reads the saved Edi data and produces the same exchange
format. It fixes the GSAS-II phase scale at one and assigns the scaled product
and its refine flag to the histogram. It chooses a fixed size of 1 µm and zero
microstrain and puts the remaining effective widths in the instrument's X and
Y. This reconstruction preserves the effective widths but cannot infer their
original decomposition from the Edi file. It requires the same phase, dataset,
FCJ and background subset.

GSAS-II's own writer makes the new GPX from the reconstructed CIF, observations
and settings. The comparison reads back that output and calculates its profile
with zero refinement cycles. For the original PbSO₄ reference, the commands
below take the saved Edi project as the reverse input and use the original
bundle only for comparison.

```bash
pixi run --locked python -m tools.gsas_ii.export_edi pbso4-edi reverse.gsas.json
pixi run --locked -m tools/deps/gsas-ii/pixi.toml python -m tools.gsas_ii.build_project \
  reverse.gsas.json roundtrip.gpx --compare-to pbso4.gsas.json --metrics roundtrip.json
```
