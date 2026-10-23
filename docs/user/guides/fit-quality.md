# Fit quality against FullProf and diffraction-lib

Each example with measured data was fitted three times from the same start: by edi, by FullProf and by
diffraction-lib. All three fits use the same structure model, data, excluded regions, background points, peak
profile and free parameters. The tables below compare where each program ended.

## How the numbers are computed

The factors are not copied from the programs' own reports. `tools/comparison/fit_quality.py` recomputes them from
the observed and calculated curves each program saved. It uses one set of points per example: the points edi fits
that FullProf also kept. It also uses the measured σ of each point, with w = 1/σ². Sums run over all banks of an
example together; N is the number of points and P the program's number of free parameters:

- R<sub>p</sub> = Σ|y<sub>o</sub> − y<sub>c</sub>| / Σy<sub>o</sub>
- R<sub>wp</sub> = √(Σw(y<sub>o</sub> − y<sub>c</sub>)² / Σw·y<sub>o</sub>²)
- R<sub>exp</sub> = √((N − P) / Σw·y<sub>o</sub>²)
- reduced χ² = Σw(y<sub>o</sub> − y<sub>c</sub>)² / (N − P)

So the three rows of an example differ only in the calculated curve and in P. A scan is compared on its template
file alone, the file the scan starts from. Running `python tools/comparison/fit_quality.py --check` recomputes every
number from the committed curves and fails if this page differs.

## Where the curves come from

| program | version | curves |
| --- | --- | --- |
| edi | the commit named in each `edi/reference.json` | `knowledge/comparison/<example>/edi/`, written by `tools/comparison/run_edi.py` |
| FullProf | 8.40 (February 2026) | the fitting references in `knowledge/fitting/fullprof/<example>/`, `fit.prf` |
| diffraction-lib | 0.21.1+dev3, develop `cb2cda7b` | `knowledge/comparison/<example>/diffraction-lib/`, written by `tools/comparison/run_diffraction_lib.py` |

diffraction-lib reads the example's own project files, so its model is edi's. Its minimizer is lmfit's
Levenberg-Marquardt. When it cannot express a model, the row says so and shows no numbers.

FullProf's profile file gives x to three decimals and intensities to two, so for the LBCO-Si McStas data, whose
counts are below 1, its factors carry that rounding.

## What differs between the fits

- **PbSO₄, neutron and X-ray together:** edi also fits the D1A wavelength, which FullProf's reference keeps
  fixed. Its rows compare different free sets, and the list after the table names this example.
- **LATP:** the measured σ are small, so reduced χ² is of order 10⁸ and R<sub>exp</sub> rounds to 0.00 % in all
  programs.

## The comparison

<!-- fit-quality tables: written by tools/comparison/fit_quality.py -->

| example | program | N | P | R<sub>p</sub> (%) | R<sub>wp</sub> (%) | R<sub>exp</sub> (%) | reduced χ² |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [`pd-neut-cwl_lbco-hrpt`](../cli/pd-neut-cwl_lbco-hrpt/index.md) | edi | 3098 | 15 | 5.64 | 7.23 | 6.35 | 1.297 |
|  | FullProf | 3098 | 15 | 5.62 | 7.21 | 6.35 | 1.289 |
|  | diffraction-lib | 3098 | 15 | 5.63 | 7.20 | 6.35 | 1.288 |
| [`pd-neut-cwl_hs-hrpt`](../cli/pd-neut-cwl_hs-hrpt/index.md) | edi | 3220 | 32 | 4.23 | 5.30 | 3.61 | 2.152 |
|  | FullProf | 3220 | 32 | 4.23 | 5.30 | 3.61 | 2.148 |
|  | diffraction-lib | – | – | – | – | – | not compared¹ |
| [`pd-neut-cwl_cosio-d20`](../cli/pd-neut-cwl_cosio-d20/index.md) | edi | 1418 | 42 | 3.01 | 3.97 | 1.88 | 4.452 |
|  | FullProf | 1418 | 42 | 3.02 | 4.02 | 1.88 | 4.56 |
|  | diffraction-lib | 1418 | 42 | 5.57 | 7.87 | 1.88 | 17.52 |
| [`pd-neut-cwl_lmo-echidna`](../cli/pd-neut-cwl_lmo-echidna/index.md) | edi | 3002 | 24 | 3.91 | 5.00 | 3.23 | 2.394 |
|  | FullProf | 3002 | 24 | 4.00 | 5.07 | 3.23 | 2.457 |
|  | diffraction-lib | 3002 | 24 | 4.04 | 5.13 | 3.23 | 2.52 |
| [`pd-neut-cwl_y2o3-spodi`](../cli/pd-neut-cwl_y2o3-spodi/index.md) | edi | 2509 | 43 | 1.12 | 1.34 | 1.23 | 1.199 |
|  | FullProf | 2509 | 43 | 1.12 | 1.34 | 1.23 | 1.199 |
|  | diffraction-lib | 2509 | 43 | 1.12 | 1.34 | 1.23 | 1.193 |
| [`pd-neut-cwl_yalo3-al2o3-spodi`](../cli/pd-neut-cwl_yalo3-al2o3-spodi/index.md) | edi | 2959 | 56 | 3.20 | 4.05 | 1.30 | 9.731 |
|  | FullProf | 2959 | 56 | 3.22 | 4.10 | 1.30 | 9.941 |
|  | diffraction-lib | – | – | – | – | – | not compared¹ |
| [`pd-neut-tof_si-sepd`](../cli/pd-neut-tof_si-sepd/index.md) | edi | 5600 | 23 | 8.19 | 6.94 | 3.65 | 3.611 |
|  | FullProf | 5600 | 23 | 8.21 | 6.95 | 3.65 | 3.616 |
|  | diffraction-lib | 5600 | 23 | 8.79 | 7.34 | 3.65 | 4.041 |
| [`pd-neut-tof_cecoal-polaris`](../cli/pd-neut-tof_cecoal-polaris/index.md) | edi | 3692 | 32 | 3.28 | 2.08 | 1.23 | 2.853 |
|  | FullProf | 3692 | 32 | 3.30 | 2.09 | 1.23 | 2.868 |
|  | diffraction-lib | – | – | – | – | – | not compared¹ |
| [`pd-neut-tof_ceo2-pearl`](../cli/pd-neut-tof_ceo2-pearl/index.md) | edi | 2237 | 19 | 4.43 | 5.29 | 2.69 | 3.877 |
|  | FullProf | 2237 | 19 | 4.43 | 5.30 | 2.69 | 3.892 |
|  | diffraction-lib | – | – | – | – | – | not compared¹ |
| [`pd-neut-tof_lbco-si-mcstas`](../cli/pd-neut-tof_lbco-si-mcstas/index.md) | edi | 633 | 25 | 5.58 | 5.04 | 2.47 | 4.156 |
|  | FullProf | 633 | 25 | 5.64 | 5.10 | 2.47 | 4.246 |
|  | diffraction-lib | 633 | 25 | 5.57 | 5.05 | 2.47 | 4.17 |
| [`pd-neut-tof_ncaf-wish`](../cli/pd-neut-tof_ncaf-wish/index.md) | edi | 18973 | 193 | 8.69 | 7.69 | 2.50 | 9.497 |
|  | FullProf | 18973 | 193 | 8.70 | 7.70 | 2.50 | 9.504 |
|  | diffraction-lib | – | – | – | – | – | not compared¹ |
| [`pd-neut-tof_ferrite-austenite-beer`](../cli/pd-neut-tof_ferrite-austenite-beer/index.md) | edi | 5642 | 73 | 4.97 | 7.13 | 1.92 | 13.78 |
|  | FullProf | 5642 | 73 | 4.98 | 7.25 | 1.92 | 14.24 |
|  | diffraction-lib | 5642 | 73 | 4.98 | 7.13 | 1.92 | 13.77 |
| [`pd-xray-cwl_pbso4-lab`](../cli/pd-xray-cwl_pbso4-lab/index.md) | edi | 5799 | 33 | 6.39 | 8.40 | 4.87 | 2.976 |
|  | FullProf | 5799 | 33 | 6.41 | 8.42 | 4.87 | 2.986 |
|  | diffraction-lib | – | – | – | – | – | not compared¹ |
| [`pd-xray-cwl_lam7o3-p021`](../cli/pd-xray-cwl_lam7o3-p021/index.md) | edi | 1236 | 39 | 1.21 | 1.64 | 3.80 | 0.1867 |
|  | FullProf | 1236 | 39 | 1.24 | 1.70 | 3.80 | 0.1999 |
|  | diffraction-lib | 1236 | 39 | 1.18 | 1.61 | 3.80 | 0.1803 |
| [`pd-neut-xray-cwl_pbso4-d1a-lab`](../cli/pd-neut-xray-cwl_pbso4-d1a-lab/index.md) | edi | 8709 | 52 | 5.41 | 5.23 | 2.93 | 3.182 |
|  | FullProf | 8709 | 51 | 5.72 | 5.76 | 2.93 | 3.855 |
|  | diffraction-lib | – | – | – | – | – | not compared¹ |
| [`pd-neut-cwl_cosio-d20_scan`](../cli/pd-neut-cwl_cosio-d20_scan/index.md) | edi | 1419 | 39 | 3.25 | 4.62 | 2.11 | 4.801 |
|  | FullProf | 1419 | 39 | 3.29 | 4.66 | 2.11 | 4.885 |
|  | diffraction-lib | 1419 | 39 | 3.25 | 4.62 | 2.11 | 4.793 |
| [`pd-xray-cwl_latp-bm01_scan`](../cli/pd-xray-cwl_latp-bm01_scan/index.md) | edi | 3114 | 59 | 3.88 | 4.51 | 0.00 | 1.422e+08 |
|  | FullProf | 3114 | 59 | 3.83 | 4.57 | 0.00 | 1.459e+08 |
|  | diffraction-lib | – | – | – | – | – | not compared¹ |

¹ Not compared, and why:

- [`pd-neut-cwl_hs-hrpt`](../cli/pd-neut-cwl_hs-hrpt/index.md), diffraction-lib: Bérar-Baldinozzi asymmetry: diffraction-lib's profile carries the TCH widths X and Y beside it, edi's a pseudo-Voigt mixing eta, so the two programs fit different models and their minima are not compared.
- [`pd-neut-cwl_yalo3-al2o3-spodi`](../cli/pd-neut-cwl_yalo3-al2o3-spodi/index.md), diffraction-lib: Bérar-Baldinozzi asymmetry: diffraction-lib's profile carries the TCH widths X and Y beside it, edi's a pseudo-Voigt mixing eta, so the two programs fit different models and their minima are not compared.
- [`pd-neut-tof_cecoal-polaris`](../cli/pd-neut-tof_cecoal-polaris/index.md), diffraction-lib: Time-of-flight absorption: the fit frees the cylinder absorption ABSCOR1, and diffraction-lib has no time-of-flight absorption.
- [`pd-neut-tof_ceo2-pearl`](../cli/pd-neut-tof_ceo2-pearl/index.md), diffraction-lib: Polynomial background: diffraction-lib reads line-segment and Chebyshev backgrounds only.
- [`pd-neut-tof_ncaf-wish`](../cli/pd-neut-tof_ncaf-wish/index.md), diffraction-lib: Time-of-flight absorption: banks 1+10, 2+9 and 3+8 carry a cylinder absorption, and diffraction-lib has no time-of-flight absorption.
- [`pd-xray-cwl_pbso4-lab`](../cli/pd-xray-cwl_pbso4-lab/index.md), diffraction-lib: Bérar-Baldinozzi asymmetry: diffraction-lib's profile carries the TCH widths X and Y beside it, edi's a pseudo-Voigt mixing eta, so the two programs fit different models and their minima are not compared.
- [`pd-neut-xray-cwl_pbso4-d1a-lab`](../cli/pd-neut-xray-cwl_pbso4-d1a-lab/index.md), diffraction-lib: Bérar-Baldinozzi asymmetry: diffraction-lib's profile carries the TCH widths X and Y beside it, edi's a pseudo-Voigt mixing eta, so the two programs fit different models and their minima are not compared.
- [`pd-xray-cwl_latp-bm01_scan`](../cli/pd-xray-cwl_latp-bm01_scan/index.md), diffraction-lib: Bérar-Baldinozzi asymmetry: diffraction-lib's profile carries the TCH widths X and Y beside it, edi's a pseudo-Voigt mixing eta, so the two programs fit different models and their minima are not compared.

Examples where edi's R<sub>wp</sub> exceeds FullProf's by more than 5 %:

- none

Examples whose programs free different numbers of parameters:

- `pd-neut-xray-cwl_pbso4-d1a-lab`: edi 52, FullProf 51

### Cell lengths

| example | phase | edi (Å) | FullProf (Å) | diffraction-lib (Å) |
| --- | --- | --- | --- | --- |
| `pd-neut-cwl_lbco-hrpt` | lbco | 3.890791(38) | 3.89079 | 3.890868(38) |
| `pd-neut-cwl_hs-hrpt` | hs | 6.86399(47), 14.1417(11) | 6.86245, 14.13864 | – |
| `pd-neut-cwl_cosio-d20` | cosio | 10.30873(25), 6.00379(15), 4.78665(12) | 10.30872, 6.00378, 4.78665 | 10.30844, 6.00358, 4.78671 |
| `pd-neut-cwl_lmo-echidna` | lmo | 2.875137(62), 14.18322(37) | 2.87516, 14.18333 | 2.875718(17), 14.18651(15) |
| `pd-neut-cwl_y2o3-spodi` | y2o3 | 10.604451(72) | 10.60445 | 10.604524(71) |
| `pd-neut-cwl_yalo3-al2o3-spodi` | Al2O3 | 4.75840(43), 12.9668(22) | 4.75674, 12.97262 | – |
| `pd-neut-cwl_yalo3-al2o3-spodi` | YAlO3 | 5.172477(72), 5.326738(74), 7.36083(10) | 5.17241, 5.32658, 7.36084 | – |
| `pd-neut-tof_si-sepd` | si | 5.430881(60) | 5.43088 | 5.432100(59) |
| `pd-neut-tof_cecoal-polaris` | cecoal | 7.65132(65), 4.05150(35), 6.90557(59) | 7.65133, 4.05148, 6.90561 | – |
| `pd-neut-tof_ceo2-pearl` | ceo2 | 5.41050 | 5.41050 | – |
| `pd-neut-tof_lbco-si-mcstas` | lbco | 3.89027(14) | 3.89027 | 3.89044(14) |
| `pd-neut-tof_lbco-si-mcstas` | si | 5.43249(64) | 5.43245 | 5.43271(64) |
| `pd-neut-tof_ncaf-wish` | ncaf | 10.25026 | 10.25026 | – |
| `pd-neut-tof_ferrite-austenite-beer` | austenite | 3.64680 | 3.64680 | 3.64680 |
| `pd-neut-tof_ferrite-austenite-beer` | ferrite | 2.88600 | 2.88600 | 2.88600 |
| `pd-xray-cwl_pbso4-lab` | pbso4 | 8.480763(89), 5.398867(58), 6.960385(75) | 8.48066, 5.39888, 6.96026 | – |
| `pd-xray-cwl_lam7o3-p021` | lam7o3 | 5.46218(11), 7.73302(16), 5.49022(11) | 5.46218, 7.73294, 5.49018 | 5.46225(10), 7.73308(16), 5.49026(11) |
| `pd-neut-xray-cwl_pbso4-d1a-lab` | pbso4 | 8.481021(82), 5.398724(53), 6.960392(70) | 8.48004, 5.39848, 6.95972 | – |
| `pd-neut-cwl_cosio-d20_scan` | cosio | 10.33593(30), 6.02972(17), 4.79759(14) | 10.33590, 6.02965, 4.79758 | 10.33614(30), 6.02985(17), 4.79767(14) |
| `pd-xray-cwl_latp-bm01_scan` | alpo4_c2221 | 6.968(21), 7.111(21), 7.003(19) | 6.96964, 7.11593, 7.00370 | – |
| `pd-xray-cwl_latp-bm01_scan` | alpo4_p63mc | 4.9828(68), 9.504(19) | 4.98695, 9.50427 | – |
| `pd-xray-cwl_latp-bm01_scan` | latp | 8.49519(25), 20.82674(87) | 8.49690, 20.83213 | – |

<!-- end of the fit-quality tables -->
