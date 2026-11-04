# pd-xray-cwl_pbso4-lab_round-robin — provenance

**Built, not copied**, by `tools/cli_projects/build_pbso4_round_robin_project.py` from the vendored FullProf reference
`knowledge/verification/fullprof/pd-xray-cwl_pbso4-lab_round-robin/` (diffraction-lib `0d9f10e4`, set `pbsox`,
FullProf.2k 7.95 output; its own `PROVENANCE.md`). The data are the round robin's measured laboratory pattern
(`pbsox.dat`, FullProf's free format, `Ins` = 0: 10° to 160° in steps of 0.025°), each uncertainty the square root
of its count. The model keeps the `.pcr`'s zero, its 6-term polynomial background (origin 50°, fixed), its Cu Kα
doublet and its excluded regions (the lower one stops at 9.99° because FullProf fits the 10.00° point, which edi's
inclusive bound would drop).

**The profile is not FullProf's.** FullProf's reference is a TCH pseudo-Voigt with Bérar-Baldinozzi asymmetry, a pair
edi does not carry. The project uses the pseudo-Voigt with Bérar-Baldinozzi (FullProf's Npr 5). Its starts are the
Caglioti widths and mixing that best match FullProf's TCH full width and mixing over the fitted range (the
verification page's), FullProf's Asy1..Asy4 carried to the paper's coefficients through the map diffraction-lib
issue 166 inferred, `(−P1 − 3·P2, −P2, −P3 − 3·P4, −P4)`, and twice FullProf's scale. The widths, mixing,
coefficients and scale are free (10 parameters).

**One conversion.** The polarization is FullProf's characteristic-radiation factor `1 + Cthm cos²(2θ)` (`Cthm` 0.8),
which is twice edi's `P = 1 − K + K cos²(2θ_m) cos²(2θ)` at `K = 0.5`, `2θ_m` = `acos(√0.8)`; the scale starts at
twice FullProf's to carry the factor 2.

| quantity | kind | value | source |
| --- | --- | --- | --- |
| `n_points_fitted` | reference | 5760 | FullProf's `pbsox.sum`: `N-P+C = 5760` with no refined parameter |
| `n_free` | reference | 10 | this project's declaration |
| `iterations`, `reduced_chi_square`, `rwp` | regression pin | 7, 3.303859941, 0.08931857465 | edi `python -m edi fit --dry`, measured 2026-10-13 |

FullProf's own fixed model, with its TCH profile, gives reduced χ² 6.27 and Rwp 17.0 % on these data (its `.sum`).
The pins gate drift only.
