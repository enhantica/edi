# FullProf reference: Co₂SiO₄ at 2.344 K

FullProf.2k 8.40 (Feb2026, ILL) fitted the D20 pattern `002p3440_all594631.dat` of the Co₂SiO₄ temperature scan
at authoring time. Tests read these committed files and never run FullProf.

The model is the magnetic structure in Pnma.1 (irrep mGM1+): Co1 on 4a with all three moment components free, Co2
on 4c with My free. The cell, the free coordinates, the zero shift and the Thompson-Cox-Hastings profile are fitted
too; Co1 and Co2 share one Biso, held at 0.269 Å² from the 56.8 K pattern. The project
`docs/user/cli/pd-neut-cwl_cosio-d20_2k` starts from these moments and fits them again.

FullProf's result: Rwp 4.90 % (`cosio.sum`); Co1 moment (0.70(4), 2.60(2), 0.34(15)) μB, |M| 2.71(3) μB; Co2 My
2.97(4) μB. Co1's Mz is poorly determined by powder data.

Files: `cosio.pcr` (input), `cosio.out` and `cosio.sum` (output), `cosio_1.prf` (profile), `cosio1.mcif`
(FullProf's magnetic CIF of the result). SHA-256:

    621ab5f5fcb886f416f76f6a29c543074ec69b46689a36b52c86ac5b77312fa8  cosio.pcr
    3dab8a538652034fc145c88c6d3dfd5793ae7369c1a4695b54559ca606fe7970  cosio.out
    e5682d2416e9a6688b82c1e850fc68e7974c7186e4a6359f66aa4c55f80bff62  cosio.sum
    06f3cd5b6d7ba8a4161cecf2291a6a679037c1982f7cefac6d744108b4e2e19e  cosio_1.prf
    589180392ab40335444f1c35ed90f55349be3ea6909562d3452a738928546d8b  cosio1.mcif
