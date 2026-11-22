# 0099. Import and export cryspy projects

- **Status:** Proposed
- **Date:** 2026-11-21
- **Implementation:** 🟡 Partial: import and export of unpolarised constant-wavelength neutron powder projects with
  isotropic atoms
- **Priority:** High

## Context

cryspy saves a project as one `.rcif` file. It is CIF-like text with a data block per crystal and a
data block per experiment, followed by cryspy's calculated output (`_pd_proc_*`, `_pd_peak_*`,
`_refln_*` and per-phase `loop_<phase>` loops, some with uneven rows). Load project > Import cryspy...
reads it through the shared import base ([ADR-0098](0098-project-import-from-other-programs.md)).
The conventions below come from cryspy's source at the snapshot recorded in
`tests/fixtures/project_imports/cryspy-pbso4.json`.

## Decision

1. **Reading.** The core reads the rcif text itself: data blocks, items, loops, quoted values and text
   fields. A quoted token is always a value, so a label such as `'data_Pb'` is not read as syntax. A
   loop whose every tag is one of cryspy's output categories (`_pd_proc_`, `_pd_peak_`, `_refln_`,
   `_inversed_hessian`) is skipped without its rows being checked; cryspy writes some of them per
   phase as named loops with ragged rows. Every other loop, named (`loop_<name>`) or not, is read,
   and one with an incomplete row is refused. Every item and loop column the import does not convert
   is refused by name, so nothing is lost silently. An unterminated quote or text field, an item
   without a value and `save_` frames are refused with their line.
2. **Numbers and refinement.** A value written with a bracket (`8.4793(1)` or `1.0()`) is refined in
   cryspy and becomes a free parameter. A plain value is fixed. A constraint mark after the bracket is
   refused.
3. **Crystal blocks** (those with `_cell_length_a`) become structures. The cell, the space group
   (`_space_group_name_H-M_alt` with `_space_group_IT_coordinate_system_code`, matched to a crysta
   setting), and the atom sites with isotropic `Biso` or `Uiso` displacements are converted. An ion
   label keeps only its element, as cryspy does for neutrons. The Wyckoff letter is recomputed.
4. **Experiment blocks** (those with `_setup_wavelength` and a `_pd_meas_2theta` loop) become
   constant-wavelength neutron powder experiments:
   - The wavelength and `_setup_offset_2theta` map directly. Both programs subtract the offset
     from the measured angle.
   - cryspy's peak is a Thompson–Cox–Hastings pseudo-Voigt. U, V, W (degrees squared) and X, Y (on
     tan θ and 1/cos θ) have the same meaning in crysta, so they map directly.
   - Bérar–Baldinozzi p1 to p4 use crysta's convention (A0, B0, A1, B1). crysta has this
     asymmetry only on the pseudo-Voigt with linear mixing. With X = Y = 0 that is the same
     peak (Gaussian, mixing fixed at zero), so the asymmetry is kept. Otherwise the import uses
     the TCH profile, leaves the asymmetry out and reports a warning.
   - `_phase_scale` becomes the linked scale unchanged. cryspy multiplies by the phase scale,
     the Lorentz factor, the multiplicity and |F|² in (10⁻¹² cm)², with no cell-volume factor.
   - Background points become crysta line segments with their refine flags.
   - `_range_2theta_min/max` become excluded regions outside the range, and the `_exclude` loop
     becomes excluded regions with its ids.
   - The profile window is the whole pattern (cut-off 0), as in cryspy.
5. **Export.** Save project as > As cryspy... writes a copy as `<project>-cryspy/project.rcif`
   through the shared export list (ADR-0098, point 7). It is the import in reverse, for the same
   model: crystals with isotropic `Biso` or `Uiso` sites, constant-wavelength neutron powder
   experiments with the TCH pseudo-Voigt or the Gaussian Bérar–Baldinozzi peak, line-segment
   background, phase scales, the excluded regions as the `_exclude` loop and the measured points.
   - Before anything is written, every active term outside that model is refused by name: magnetic
     order, custom scattering lengths, anisotropic sites, sample displacement or transparency, a
     second wavelength, polarization, absorption, preferred orientation, extinction, another peak
     profile or background, a Bérar–Baldinozzi angular limit below 180°, nonzero pseudo-Voigt
     mixing on that peak, unequal joint-fit weights, parameter constraints and a sequential fit
     setup. So are incomplete inputs: a structure without atoms, no enabled phase link, a link to
     a missing structure, no wavelength, and measured points that are not finite, ascending,
     below 180° and with positive sigmas. A failed export publishes nothing.
   - A parameter is spelled as the native save spells it, including the save's exact cell or
     all-exact spelling. A fixed value is plain, a free value without an s.u. is `v()`, and a free
     value with an s.u. is `v(n)` with `n` the s.u. in whole units of the value's last decimal,
     rounded up, because cryspy's reader keeps only digit brackets. A value that would need an
     exponent before its bracket is refused. Other numbers use their shortest exact spelling, so
     neighbouring grid points stay distinct.
   - Text values are quoted when they would read as CIF syntax (`data_Pb`, a leading `_`) or hold
     a space.
   - cryspy evaluates every peak over the whole pattern; EasyDiffraction's profile window is not
     written. This is the same convention difference the import records (cut-off 0).
6. **Verification.** An imported reference project's cell, sites, instrument and measurements are
   checked against the rcif values. Its calculated pattern is compared with cryspy's own output in
   the file (`_pd_proc_intensity_plus_net + _pd_proc_intensity_minus_net +
   _pd_proc_intensity_bkg_calc`), which cryspy prints to two decimals.

## What EasyDiffraction does not have

The import maps cryspy's model onto crysta's existing one (ADR-0098, point 6). This is everything
cryspy can describe that the import approximates, leaves out or refuses. Each item is future work
for crysta as a general feature, never a cryspy-only option.

### Calculated differently (the project imports, results differ)

- **Where the peak is evaluated.** cryspy evaluates the widths, the mixing, the asymmetry and the
  Lorentz factor at each measured point. crysta evaluates the widths and mixing at each
  reflection's 2θ, which keeps every reflection's integrated intensity. Broad peaks at low and
  high angle differ slightly.
- **Asymmetry with Lorentzian widths.** When X or Y is not zero, cryspy's Bérar–Baldinozzi
  asymmetry is left out (point 4).
- **Background outside its points.** cryspy extends the first and last segments linearly and
  evaluates the background at the measured angle before the zero shift.
- **Scattering lengths.** cryspy uses its own isotope table; crysta uses its Sears table.

### Refused (the import stops and names the item)

- Data: X-ray data, polarised neutron data and flipping ratios, a magnetic field
  (`_setup_field` not zero), time-of-flight, two-dimensional powder and single-crystal blocks,
  any other block type.
- Crystal: anisotropic displacements (`Uani`, `Bani`), magnetic moments and susceptibilities,
  any `_atom_site_*` or other item not listed in point 3.
- Experiment: the Gaussian size term `_phase_igsize`, phase-specific U, V, W, X, Y, texture,
  absorption, extinction, the cos 2θ and sin 2θ offset terms, any item not listed in point 4.
- Refinement: cryspy's constraint marks.

### Left out

- The `global_` block (cryspy's inverse Hessian) and all calculated output.
- `_chi2_*` flags. For unpolarised data cryspy always fits the sum, as crysta does.
- `_setup_K` and `_setup_cthm`, which have no effect for neutrons.
- `_atom_site_multiplicity` and `_atom_site_Wyckoff_symbol`, which crysta derives itself.

## Consequences

- cryspy powder projects with these features open in EasyDiffraction and save as ordinary
  projects. The refusals above show what is still missing.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Read the rcif with cryspy or Gemmi | Rejected: the desktop core has no Python, and the calculated-output loops are not valid CIF. |
| Keep the asymmetry by fitting crysta's mixed pseudo-Voigt to the TCH peak | Rejected: an approximation crysta would hide inside the import, against ADR-0098 point 6. |
