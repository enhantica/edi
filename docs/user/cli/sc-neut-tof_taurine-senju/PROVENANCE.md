# sc-neut-tof_taurine-senju — provenance

Fit the amino-sulfonic acid taurine to six time-of-flight neutron single-crystal datasets from SENJU at J-PARC together, each reflection measured at its own wavelength.

## Sources

- **Model:** diffraction-lib (develop `cb2cda7be6117199be8f8cac0a666a7bccd32d90`)'s verification page `sc-neut-tof_taurine_basic` (FullProf `taurine.pcr`): the P2₁/c structure and its 14 sites.
- **Data:** `data/taurine-senju.int`, FullProf's reflection file of the taurine project with its six SENJU datasets (the dataset in column 6), one experiment each. The project embeds the 1540 reflections with a positive su (286, 255, 276, 221, 242 and 260) unchanged (h, k, l, F², su, wavelength). Its sha256 is `bc1824a80d8c132f05219c6e89a1df050c94c97a6d3318f039b6bc3711145637`.

## Start

Built by `tools/cli_projects/build_sc_projects.py`: FullProf's positions with S1 x, O1 y, N1 z and C1 x moved by 0.005 (S1 x 0.20800 for 0.20300, O1 y 0.23701 for 0.24201, N1 z 0.33658 for 0.33158, C1 x 0.33574 for 0.34074), every beta tensor 0, its scales Sc1-Sc6 and its extinction model 4 (anisotropic Larson) with x11, x22 and x33 0, x12, x13 and x23 0 and fixed. Experiments 2-6 take experiment 1's extinction through constraints. Free: every position and beta, the six scales and the three extinction terms (135 parameters). As FullProf (Rmub 3.0), the fit uses only reflections with F² > 3 su(F²).

## Differences from the source

- FullProf leaves the reflections it marks forbidden out; they have no su here and are not in the project.
- FullProf multiplies each s.u. by its parameter's codeword coefficient (its manual, eq. 3.7), and this .pcr codes the six scales and the three extinction terms with 0.20, so FullProf prints their s.u. at a fifth: x11 0.000760 against edi's 0.0036. With the 0.20 undone the s.u. agree: edi's are 1.00 to 1.02 times FullProf's for the scales, 0.94 to 0.96 for the extinction, 1.04 to 1.10 for the positions and 1.02 to 1.08 for the betas.
- FullProf prints χ² 30.1; its own reflection list gives sum((F²obs - F²calc)/su)² = 24676 over the 947 reflections, which is 30.39 over N - P = 812 as edi and FullProf's manual (eq. 3.8) define it. Started from FullProf's values, edi finds 30.41 there and goes on in 4 iterations to 30.27, the minimum it reaches from this example's start: FullProf applies its scale and extinction shifts at 0.20 too (the same codewords) and stops just above the minimum.

## Result from this start (local diagnostic)

From this start edi converges in 8 iterations to reduced χ² 30.27, wR(F²) 12.2 %, over the same 947 reflections FullProf fits (FullProf, converged at its cycle 52 with Eps 0.01: χ² 30.1, RF2w 12.2 %). Every one of the 135 parameters is within 0.6 of edi's s.u. of FullProf's value (positions within 0.41, betas 0.38, scales 0.58, extinction 0.44): x11 0.0584(36), x22 0.0139(15) and x33 0.0076(15) against FullProf's 0.0568(38), 0.0135(16) and 0.0071(15) with its 0.20 undone, and scales 2.80(6), 3.87(9), 3.25(6), 2.84(7), 2.78(6) and 2.97(6) against FullProf's 2.78, 3.85, 3.23, 2.83, 2.74 and 2.96.
