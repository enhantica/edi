# pd-neut-cwl_pbso4_beba-asymmetry — provenance

**Built, not copied**, by `tools/cli_projects/build_c11_t57_projects.py` from the vendored FullProf reference
`knowledge/verification/fullprof/pd-neut-cwl_pbso4_beba-asymmetry/` — the upstream `.pcr` with `AsyLim` 180. The
model keeps the `.pcr`'s eight background points and excluded regions (the lower one stops at 9.99° because FullProf
fits the 10.00° point, which edi's inclusive bound would drop). The data are the D1A-format `.dat` (`Ins` = 6): each
count is a mean over its counters, so its variance is count / counters, which reproduces FullProf's own Rexp (1.951
vs its 1.95).

**The profile is not FullProf's (2026-10-05).** FullProf's reference is a TCH pseudo-Voigt with Bérar-Baldinozzi
asymmetry, a pair edi no longer carries. The project uses the pseudo-Voigt with Bérar-Baldinozzi
(FullProf's Npr 5): FullProf's Gaussian widths U, V, W as starts, the mixing from `eta_0` 0.25 and `eta_1` 0, and
FullProf's P1..P4 carried to the paper's coefficients through the map diffraction-lib issue 166 inferred,
`(−P1 − 3·P2, −P2, −P3 − 3·P4, −P4)`, as starts. The widths, mixing, coefficients and scale are free (10
parameters); FullProf's scale is no longer a reference, because it belongs to the other profile.

| quantity | kind | value | source |
| --- | --- | --- | --- |
| `n_points_fitted` | reference | 2909 | `scale-fit.out` `N-P+C = 2908` with its one free parameter |
| `n_free` | reference | 10 | this project's declaration |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | 5, 3.482247696, 0.03634572357 | edi `python -m edi fit --dry`, measured 2026-10-05 against crysta's renamed profiles |

The old model's scale-only fit gave reduced χ² 3.527 and Rwp 3.664 %, and FullProf's own χ² 3.537 and Rwp 3.67 %.

The pins gate drift only. `fullprof/scale-fit.inp` is the reference `.pcr` with the scale as its one
free parameter (code 11), 100 cycles at full shifts and nothing else changed;
`fullprof/scale-fit.out` is FullProf.2k 8.40's output (`fp2k` sha256
`b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`, `printf 'pbso4\n\n' | fp2k` in a
copy of the reference folder), run once at authoring time; no gate runs FullProf.

## Files (sha256)

- `fullprof/scale-fit.inp` `f3eee92f51e94473673ad8e3c1592d0cefc3b48096f53ee889fb7ee39df681f3`
- `fullprof/scale-fit.out` `a0026f176f83076e678e7862b062535af2ddc725cedd0ee0636b63fa06edf039`
