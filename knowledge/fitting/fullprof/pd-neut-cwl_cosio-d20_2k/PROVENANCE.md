# FullProf reference: Co₂SiO₄ at 2.344 K

FullProf.2k 8.40 (Feb2026, ILL) fitted the D20 pattern `002p3440_all594631.dat` of the Co₂SiO₄ temperature scan
at authoring time. Tests read these committed files and never run FullProf.

The model is the magnetic structure in Pnma.1 (irrep mGM1+): Co1 on 4a with all three moment components free, Co2
on 4c with My free. The cell, the free coordinates, the zero shift and the profile are fitted too: the
Thompson-Cox-Hastings pseudo-Voigt (U, V, W, Y) with Finger-Cox-Jephcoat axial-divergence asymmetry, its S/L and
D/L both held at 0.0619, the shared value the project fits (FullProf cannot refine them together). Co1 and Co2
share one Biso, held at 0.269 Å² from the 56.8 K pattern. The background has the project's sixteen points, none
between 7.6° and 12.6° so that none sits under the first magnetic peak, and only 0–6° and the dead detector cell are
excluded, as in `docs/user/cli/pd-neut-cwl_cosio-d20_2k`.

FullProf's result: Rwp 4.91 % (`cosio.sum`); cell 10.31593(14), 6.00680(9), 4.79115(7) Å, zero shift 0.3992(20)°;
Co1 moment (0.98(4), 3.07(2), −0.05(88)) μB, |M| 3.23(18) μB; Co2 My 2.75(4) μB. Co1's Mz is poorly determined by
powder data. The FCJ quadratures of FullProf and crysta differ, so the zero shift and the cell can differ by a few
standard deviations.

Rerun from this directory with the data file `cosio.dat` (the pattern above in FullProf's XY format):

    printf 'cosio\n\n' | FULLPROF=<fullprof install> OMP_NUM_THREADS=1 fp2k

Files: `cosio.pcr` (input), `cosio.out` and `cosio.sum` (output), `cosio_1.prf` (profile), `cosio1.mcif`
(FullProf's magnetic CIF of the result). SHA-256:

    5dab58e2d0606feb180e32a9ec6eb5fee1f20f33c2fefb176341ce9e082bc72f  cosio.pcr
    42dc2b6698ec194498cec241bd42152c1dccb5e28f73bccb455a70f9dc9f390e  cosio.out
    de625674862887388ccb6955f266ddd654167ae640e785b56838ac9d7bec2565  cosio.sum
    b4b7c73f5b5b34e79d6833473287b99e49418cfe6f140e2e9c24a4c6717e73f4  cosio_1.prf
    4029da011d015b7a63a0eb6aab32fab9121743b739b4f9433fde097c351cc438  cosio1.mcif
