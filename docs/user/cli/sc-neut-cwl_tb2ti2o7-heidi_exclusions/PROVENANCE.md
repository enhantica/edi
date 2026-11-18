# sc-neut-cwl_tb2ti2o7-heidi_exclusions: provenance

The structure, extinction, starting scale and measured reflections are those of `sc-neut-cwl_tb2ti2o7-heidi_basic`
(FullProf's files for the matching diffraction-lib verification page). The experiment adds the admission items by hand:
`_reflns.merge none`, `_reflns.absences exclude`, an `_excluded_reflection` loop with (1 1 1) and (4 0 0), and an
`_excluded_region` from 0.85 to 0.90 Å in d.

## Which values are references

Both values are counted from the project's files, never from edi or crysta.

| quantity | kind | value | tolerance |
| --- | --- | --- | --- |
| `n_free` | reference | 1 | tol_abs 0 |
| `n_points_fitted` | reference | 210 | tol_abs 0 |

How 210 is counted:

- The `_refln` loop holds 220 reflections, each with its own indices.
- d of a cubic cell is a / √(h² + k² + l²) with a = 10.13 Å (`structures/tb2ti2o7.edi`). Eight reflections fall in
  0.85 ≤ d ≤ 0.90 Å: (8 8 0), (11 3 1), (9 7 1), (9 5 5), (10 6 0), (9 7 3), (11 3 3), (10 6 2).
- (1 1 1) and (4 0 0) are listed by their indices; with merging off only those exact indices are left out. Neither is
  in the d range.
- Fd-3m (International Tables A, No. 227, origin choice 2) allows hkl with h + k, h + l, k + l even, 0kl with
  k + l = 4n and h00 with h = 4n; every listed reflection meets them, so no absence is left out.
- The analysis declares no fit cutoff (`_refine_ls.threshold_sigma`), so every remaining reflection is fitted:
  220 − 8 − 2 = 210.
