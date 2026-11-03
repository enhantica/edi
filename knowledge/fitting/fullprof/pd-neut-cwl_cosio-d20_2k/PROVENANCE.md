# FullProf reference: Co₂SiO₄ at 2.344 K

FullProf.2k 8.40 (Feb2026, ILL) fitted the D20 pattern `002p3440_all594631.dat` of the Co₂SiO₄ temperature scan
at authoring time. Tests read these committed files and never run FullProf.

The model is the magnetic structure in Pnma.1 (irrep mGM1+): Co1 on 4a with all three moment components free, Co2
on 4c with My free. The cell, the free coordinates, the zero shift and the profile are fitted too: the
Thompson-Cox-Hastings pseudo-Voigt (U, V, W, Y) with Finger-Cox-Jephcoat axial-divergence asymmetry, its S/L 0.08393
and D/L 0.03529 held at the values crysta fits for the project, which FullProf cannot refine together. Co1 and Co2
share one Biso, held at 0.269 Å² from the 56.8 K pattern. The background has the project's sixteen points, none
between 7.6° and 12.6° so that none sits under the first magnetic peak, and only 0–6° and the dead detector cell are
excluded, as in `docs/user/cli/pd-neut-cwl_cosio-d20_2k`.

FullProf's result: Rwp 4.75 % (`cosio.sum`); Co1 moment (1.00(4), 3.08(2), −0.15(37)) μB, |M| 3.24(8) μB; Co2 My
2.73(4) μB. Co1's Mz is poorly determined by powder data.

Rerun from this directory with the data file `cosio.dat` (the pattern above in FullProf's XY format):

    printf 'cosio\n\n' | FULLPROF=<fullprof install> OMP_NUM_THREADS=1 fp2k

Files: `cosio.pcr` (input), `cosio.out` and `cosio.sum` (output), `cosio_1.prf` (profile), `cosio1.mcif`
(FullProf's magnetic CIF of the result). SHA-256:

    50429c4ca42d94db0273972d37737116c6b85dbce7480395a4c2f8490bbe84f6  cosio.pcr
    339f0cb008186995060ecac29d96c42ebfaaf815a02145f8ddd23c2350ca2321  cosio.out
    eaf1f7bdbc1d51fd74be3d35bfb3fd8855998700c2f607240839cd8f934fbae9  cosio.sum
    ecbf97a72434db543c879cbbff85ca73a3ce88133a1626c0a6b3fd34a7867d0c  cosio_1.prf
    4d38603134f6fe9fbae90b706a86fbe6626fc6f869cd5031c186ba90098ad75e  cosio1.mcif
