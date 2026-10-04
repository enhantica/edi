# pd-neut-cwl_pbso4_beba-asymmetry — provenance

**Built, not copied**, by `tools/cli_projects/build_c11_t57_projects.py` from the vendored FullProf reference
`knowledge/verification/fullprof/pd-neut-cwl_pbso4_beba-asymmetry/` — the upstream `.pcr` with `AsyLim` 180, the one limit angle every Bérar-Baldinozzi comparison uses. The
model is the `.pcr`'s, with its eight background points and excluded regions (the lower one stops at 9.99° because FullProf fits the 10.00° point, which edi's inclusive
bound would drop). The data are the D1A-format `.dat` (`Ins` = 6): each count is a mean over its counters, so its variance is count / counters, which reproduces FullProf's
own Rexp (1.951 vs its 1.95). The scale starts at the `.pcr` value and is the only free parameter.

**One translation.** FullProf's P1..P4 are not the paper's coefficients. The project carries them
through the map diffraction-lib issue 166 inferred from FullProf's calculated output,
`(−P1 − 3·P2, −P2, −P3 − 3·P4, −P4)`. The map is inexact (the two `F_b` differ in shape; the
verification page measures the remainder at 0.83 %), and the scale agreement below is what it buys.

| quantity | kind | value | source |
| --- | --- | --- | --- |
| `n_points_fitted` | reference | 2909 | `scale-fit.out` `N-P+C = 2908` plus the one free parameter |
| `param.scale.value` | reference | 1.4638115 ± 0.0018606 | `scale-fit.out`, the final parameter summary (`Scale_ph1_pat1`) — the tolerance is FullProf's own uncertainty |
| `n_free` | reference | 1 | this project's declaration |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | 2, 3.527032501, 0.03663543171 | edi `python -m edi fit`, measured 2026-09-26 with crysta at, merged as `55db2c3b` (#206) |

FullProf's own figures for the same fit — χ² 3.537, Rwp 3.67 % — agree with the pins to their
printed precision; they are not used as references because FullProf prints them to three digits.

The pins gate drift only. `fullprof/scale-fit.inp` is the reference `.pcr` with the scale as its one
free parameter (code 11), 100 cycles at full shifts and nothing else changed;
`fullprof/scale-fit.out` is FullProf.2k 8.40's output (`fp2k` sha256
`b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`, `printf 'pbso4\n\n' | fp2k` in a
copy of the reference folder), run once at authoring time; no gate runs FullProf.

## Files (sha256)

- `fullprof/scale-fit.inp` `f3eee92f51e94473673ad8e3c1592d0cefc3b48096f53ee889fb7ee39df681f3`
- `fullprof/scale-fit.out` `a0026f176f83076e678e7862b062535af2ddc725cedd0ee0636b63fa06edf039`
