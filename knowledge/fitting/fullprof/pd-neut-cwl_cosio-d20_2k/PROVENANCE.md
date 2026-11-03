# FullProf reference: Co₂SiO₄ at 2.344 K

FullProf.2k 8.40 (Feb2026, ILL) fitted the D20 pattern `002p3440_all594631.dat` of the Co₂SiO₄ temperature scan
at authoring time. Tests read these committed files and never run FullProf.

The model is the magnetic structure in Pnma.1 (irrep mGM1+): Co1 on 4a with all three moment components free, Co2
on 4c with My free. The cell, the free coordinates, the zero shift and the profile are fitted too: a pseudo-Voigt
whose mixing is linear in 2θ, with Bérar-Baldinozzi asymmetry, the profile the project uses. Co1 and Co2 share one
Biso, held at 0.269 Å² from the 56.8 K pattern. The background has the project's sixteen points, none between 7.6° and 12.6° so that none sits under the first magnetic peak, and 0–6° is excluded, as in
`docs/user/cli/pd-neut-cwl_cosio-d20_2k`.

FullProf's result: Rwp 5.15 % (`cosio.sum`); Co1 moment (0.82(4), 2.85(3), 0.12(47)) μB, |M| 2.97(10) μB; Co2 My
3.00(4) μB. Co1's Mz is poorly determined by powder data.

Rerun from this directory with the data file `cosio.dat` (the pattern above in FullProf's XY format):

    printf 'cosio\n\n' | FULLPROF=<fullprof install> OMP_NUM_THREADS=1 fp2k

Files: `cosio.pcr` (input), `cosio.out` and `cosio.sum` (output), `cosio_1.prf` (profile), `cosio1.mcif`
(FullProf's magnetic CIF of the result). SHA-256:

    ffdbe8ac7a16214b6c21f4696c9ba00963e21bf7f5e95d248de166113a565b8c  cosio.pcr
    14771d3fe4a8f3e1a0d3435806b57191bb85045b3d10d7d26b2074c5c61e6631  cosio.out
    e4ffe4fc567e8e27fc024a9a36ae086e949a387edaaedbcf8db5a41a512f5543  cosio.sum
    2b69329a4a6e657cf7cdf1b2384fbd2c9ca00e677438ac0952500d671279e8c6  cosio_1.prf
    e2271aab99e6856c66175904e16871d05e8f8e08126330b27c46586fe33a78a2  cosio1.mcif
