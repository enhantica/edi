# FullProf reference: Co₂SiO₄ at 2.344 K

FullProf.2k 8.40 (Feb2026, ILL) fitted the D20 pattern `002p3440_all594631.dat` of the Co₂SiO₄ temperature scan
at authoring time. Tests read these committed files and never run FullProf.

The model is the magnetic structure in Pnma.1 (irrep mGM1+): Co1 on 4a with all three moment components free, Co2
on 4c with My free. The cell, the free coordinates, the zero shift and the Thompson-Cox-Hastings profile are fitted
too; Co1 and Co2 share one Biso, held at 0.269 Å² from the 56.8 K pattern. The background has the project's sixteen
points, none between 7.6° and 12.6° so that none sits under the first magnetic peak, and 0–6° is excluded, as in
`docs/user/cli/pd-neut-cwl_cosio-d20_2k`.

FullProf's result: Rwp 5.47 % (`cosio.sum`); Co1 moment (0.76(4), 2.72(2), 0.43(14)) μB, |M| 2.86(3) μB; Co2 My
2.86(4) μB. Co1's Mz is poorly determined by powder data.

Rerun from this directory with the data file `cosio.dat` (the pattern above in FullProf's XY format):

    printf 'cosio\n\n' | FULLPROF=<fullprof install> OMP_NUM_THREADS=1 fp2k

Files: `cosio.pcr` (input), `cosio.out` and `cosio.sum` (output), `cosio_1.prf` (profile), `cosio1.mcif`
(FullProf's magnetic CIF of the result). SHA-256:

    ed6fa0a1781ab5019ac4a71ada0d86e02eb67deb8d23fa196280831c9dce4937  cosio.pcr
    71403619bb51b3da9cabef785e9e6b598562d2ef73c31ad0f7ca9def8e9ef94d  cosio.out
    0896c6ab84fc250581d8c6b9aed7a64b46ad952486b4a2c37086020c0c859013  cosio.sum
    59f5692c6f8bab4d2659241dcac5c82e33023f615df149aae3bc3bfb72008b09  cosio_1.prf
    e93a41d6c7204840ddaac5463050b111503c4332b05feed680cfac63c8dbd5a2  cosio1.mcif
