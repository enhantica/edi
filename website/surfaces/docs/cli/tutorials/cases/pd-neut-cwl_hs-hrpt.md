# Rietveld fit: herbertsmithite, HRPT

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit herbertsmithite, ZnCu₃(OD)₆Cl₂, a deuterated kagome antiferromagnet, to constant-wavelength
neutron powder data from HRPT at PSI, with a pseudo-Voigt profile and Bérar-Baldinozzi
asymmetry.

It builds the catalogue case `pd-neut-cwl_hs-hrpt` step by step: the same project the command
line fits and the app's Examples open.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p pd-neut-cwl_hs-hrpt/structures pd-neut-cwl_hs-hrpt/experiments pd-neut-cwl_hs-hrpt/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name pd-neut-cwl_hs-hrpt
_metadata.title "ZnCu₃(OD)₆Cl₂ [R-3m] · HRPT @ PSI"
_metadata.description "Herbertsmithite · Deuterated kagome antiferromagnet · Bérar-Baldinozzi asymmetry"
_metadata.authors .
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_hs-hrpt-hs
    mv data/pd-neut-cwl_hs-hrpt-hs.edi pd-neut-cwl_hs-hrpt/structures/hs.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_hs-hrpt-hs
    mv data/pd-neut-cwl_hs-hrpt-hs.edi pd-neut-cwl_hs-hrpt/structures/hs.edi
    ```

## Define the experiment

Download the experiment into `experiments`: the file declares the instrument, the peak profile, the background, the structures it links and the measured data.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_hs-hrpt-hrpt
    mv data/pd-neut-cwl_hs-hrpt-hrpt.edi pd-neut-cwl_hs-hrpt/experiments/hrpt.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_hs-hrpt-hrpt
    mv data/pd-neut-cwl_hs-hrpt-hrpt.edi pd-neut-cwl_hs-hrpt/experiments/hrpt.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_minimizer.type crysta
_minimizer.max_iterations 1000

_fitting_mode.type single

_edi.schema_version 3
```

## Cell, scale and 2θ zero

The cell lengths, the scale and the zero shift put the peaks in place and at the right height.

In `experiments/hrpt.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
hs 0.5() 1.0
```

In `structures/hs.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 6.85()
_cell.length_c 14.1()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_hs-hrpt, 3220 pts fitted / 3220 loaded, 4 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       39.94       121.13
      1      0.045     25.02        47.54   60.8% ↓
      2      0.049     24.70        46.30   2.6% ↓
      3      0.053     24.51        45.59   1.5% ↓
      4      0.057     24.40        45.19   0.9% ↓
      5      0.060     24.34        44.97   0.5% ↓
      6      0.064     24.30        44.84   0.3% ↓
      7      0.068     24.28        44.77   0.2% ↓
      8      0.072     24.27        44.73   0.1% ↓
      9      0.076     24.27        44.71   
     10      0.080     24.26        44.70   
     11      0.084     24.26        44.69   
     12      0.088     24.26        44.69   
     13      0.092     24.26        44.69   
     14      0.095     24.26        44.68   
     15      0.099     24.26        44.68   
     16      0.103     24.26        44.68   
     17      0.111     24.26        44.68   
  done · converged · 17 iters · reduced χ² 44.68 · Rwp 24.26 % · 0.12 s

  refined parameters (4 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0000       0.1191    0.0049   
  scale           experiment.linked_structures[hs].scale                    0.5       0.3209    0.0033   35.8% ↓
  a, Å            structure.cell.length_a                                6.8500      6.86180   0.00028   0.2% ↑
  c, Å            structure.cell.length_c                               14.1000     14.13493   0.00080   0.2% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

The estimated points are a starting point; fit them now that the peaks are in place.

In `experiments/hrpt.edi`, add `()` after the values the stage frees:

```edi
1 4 460()
2 20 460()
```

The same for every other row (8 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_hs-hrpt, 3220 pts fitted / 3220 loaded, 14 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       24.26        44.82
      1      0.053     21.75        36.02   19.6% ↓
      2      0.064     21.75        36.02   
  done · converged · 2 iters · reduced χ² 36.02 · Rwp 21.75 % · 0.07 s

  refined parameters (14 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                       460          514        33   11.8% ↑
  intensity       experiment.background[1].intensity                        460          550        15   19.6% ↑
  intensity       experiment.background[2].intensity                        460        402.9       9.6   12.4% ↓
  intensity       experiment.background[3].intensity                        460          563        11   22.3% ↑
  intensity       experiment.background[4].intensity                        460          528        11   14.9% ↑
  intensity       experiment.background[5].intensity                        460          579        11   26.0% ↑
  intensity       experiment.background[6].intensity                        460        521.3       9.8   13.3% ↑
  intensity       experiment.background[7].intensity                        460          462        11   0.4% ↑
  intensity       experiment.background[8].intensity                        460          616        11   33.9% ↑
  intensity       experiment.background[9].intensity                        460          545        13   18.4% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.1191       0.1203    0.0049   1.0% ↑
  scale           experiment.linked_structures[hs].scale                 0.3209       0.2898    0.0032   9.7% ↓
  a, Å            structure.cell.length_a                                6.8618      6.86188   0.00028   
  c, Å            structure.cell.length_c                               14.1349     14.13547   0.00080   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

The Gaussian widths and the mixing η₀, with the background staying free. diffraction-lib frees
the Lorentzian Y where this profile has η₀.

In `experiments/hrpt.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.1()
_peak.broad_gauss_v -0.2()
_peak.broad_gauss_w 0.2()
_peak.mixing_eta_0 0.5()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_hs-hrpt, 3220 pts fitted / 3220 loaded, 18 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       21.75        36.07
      1      0.054     13.45        13.79   61.8% ↓
      2      0.059     13.44        13.77   0.1% ↓
      3      0.064     13.44        13.77   
      4      0.069     13.44        13.77   
      5      0.074     13.44        13.77   
      6      0.078     13.44        13.77   
      7      0.090     13.44        13.77   
  done · converged · 7 iters · reduced χ² 13.77 · Rwp 13.44 % · 0.10 s

  refined parameters (18 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                       514          513        21   0.2% ↓
  intensity       experiment.background[1].intensity                        550        549.9       9.2   
  intensity       experiment.background[2].intensity                      402.9        403.2       5.9   0.1% ↑
  intensity       experiment.background[3].intensity                        563        509.3       6.9   9.5% ↓
  intensity       experiment.background[4].intensity                        528        447.1       6.9   15.3% ↓
  intensity       experiment.background[5].intensity                        579        500.6       6.8   13.5% ↓
  intensity       experiment.background[6].intensity                      521.3        450.8       6.3   13.5% ↓
  intensity       experiment.background[7].intensity                        462        350.9       6.8   24.1% ↓
  intensity       experiment.background[8].intensity                        616        484.7       7.4   21.3% ↓
  intensity       experiment.background[9].intensity                        545        501.8       7.8   7.9% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.1203       0.1216    0.0042   1.1% ↑
  scale           experiment.linked_structures[hs].scale                 0.2898       0.4261    0.0040   47.0% ↑
  U, deg²         experiment.peak.broad_gauss_u                             0.1        0.487     0.032   387.4% ↑
  V, deg²         experiment.peak.broad_gauss_v                            -0.2       -0.305     0.058 ! 52.5% ↓
  W, deg²         experiment.peak.broad_gauss_w                             0.2        0.288     0.023 ! 44.2% ↑
  Eta0            experiment.peak.mixing_eta_0                              0.5        0.469     0.025   6.3% ↓
  a, Å            structure.cell.length_a                                6.8619      6.86251   0.00037   
  c, Å            structure.cell.length_c                               14.1355      14.1373    0.0011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_v: strongly correlated with W (hrpt) (r = -0.95)
      experiment.peak.broad_gauss_w: strongly correlated with V (hrpt) (r = -0.95)
```

## Atom positions

The coordinates the symmetry leaves free: O and H in x and z, Cl in z.

In `structures/hs.edi`, add `()` after the values the stage frees:

```edi
O O 0.21() -0.21 0.06() h 18 1 0.5 Biso
Cl Cl 0 0 0.2() c 6 1 0.5 Biso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_hs-hrpt, 3220 pts fitted / 3220 loaded, 23 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.44        13.79
      1      0.062      8.21         5.15   62.7% ↓
      2      0.067      8.21         5.15   
      3      0.090      8.21         5.15   
  done · converged · 3 iters · reduced χ² 5.15 · Rwp 8.21 % · 0.10 s

  refined parameters (23 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                       513          568        13   10.7% ↑
  intensity       experiment.background[1].intensity                      549.9        539.0       5.6   2.0% ↓
  intensity       experiment.background[2].intensity                      403.2        421.5       3.7   4.6% ↑
  intensity       experiment.background[3].intensity                      509.3        495.2       4.3   2.8% ↓
  intensity       experiment.background[4].intensity                      447.1        485.2       4.2   8.5% ↑
  intensity       experiment.background[5].intensity                      500.6        506.7       4.3   1.2% ↑
  intensity       experiment.background[6].intensity                      450.8        471.4       3.9   4.6% ↑
  intensity       experiment.background[7].intensity                      350.9        442.8       4.2   26.2% ↑
  intensity       experiment.background[8].intensity                      484.7        440.6       5.0   9.1% ↓
  intensity       experiment.background[9].intensity                      501.8        440.8       5.1   12.2% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.1216       0.1128    0.0025   7.3% ↓
  scale           experiment.linked_structures[hs].scale                 0.4261       0.4073    0.0024   4.4% ↓
  U, deg²         experiment.peak.broad_gauss_u                           0.487        0.489     0.016   0.4% ↑
  V, deg²         experiment.peak.broad_gauss_v                          -0.305       -0.453     0.031   48.4% ↓
  W, deg²         experiment.peak.broad_gauss_w                           0.288        0.354     0.013   22.8% ↑
  Eta0            experiment.peak.mixing_eta_0                            0.469        0.432     0.015   7.9% ↓
  z               structure.atom_sites[Cl].fract_z                      0.20000      0.19762   0.00018   1.2% ↓
  x               structure.atom_sites[H].fract_x                       0.13000      0.13364   0.00018   2.8% ↑
  z               structure.atom_sites[H].fract_z                       0.08000      0.08701   0.00014   8.8% ↑
  x               structure.atom_sites[O].fract_x                       0.21000      0.20640   0.00025   1.7% ↓
  z               structure.atom_sites[O].fract_z                       0.06000      0.06275   0.00018   4.6% ↑
  a, Å            structure.cell.length_a                                6.8625      6.86189   0.00023   
  c, Å            structure.cell.length_c                               14.1373     14.13479   0.00056   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Displacements

Every site's displacement.

In `structures/hs.edi`, add `()` after the values the stage frees:

```edi
Zn Zn 0 0 0.5 b 3 1 0.5() Biso
Cu Cu 0.5 0 0 e 9 1 0.5() Biso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_hs-hrpt, 3220 pts fitted / 3220 loaded, 28 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        8.21         5.16
      1      0.069      5.45         2.27   56.0% ↓
      2      0.081      5.45         2.27   
  done · converged · 2 iters · reduced χ² 2.27 · Rwp 5.45 % · 0.09 s

  refined parameters (28 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                       568        517.9       9.2   8.8% ↓
  intensity       experiment.background[1].intensity                        539        536.6       3.8   0.5% ↓
  intensity       experiment.background[2].intensity                      421.5        425.5       2.5   1.0% ↑
  intensity       experiment.background[3].intensity                      495.2        467.2       3.0   5.6% ↓
  intensity       experiment.background[4].intensity                      485.2        482.1       2.8   0.6% ↓
  intensity       experiment.background[5].intensity                      506.7        503.8       2.9   0.6% ↓
  intensity       experiment.background[6].intensity                      471.4        489.9       2.7   3.9% ↑
  intensity       experiment.background[7].intensity                      442.8        502.4       2.8   13.5% ↑
  intensity       experiment.background[8].intensity                      440.6        533.5       3.5   21.1% ↑
  intensity       experiment.background[9].intensity                      440.8        497.8       3.5   12.9% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.1128       0.1100    0.0016   2.5% ↓
  scale           experiment.linked_structures[hs].scale                 0.4073       0.5141    0.0028   26.2% ↑
  U, deg²         experiment.peak.broad_gauss_u                           0.489       0.2850    0.0084   41.7% ↓
  V, deg²         experiment.peak.broad_gauss_v                          -0.453       -0.269     0.018   40.7% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.354       0.3419    0.0077   3.4% ↓
  Eta0            experiment.peak.mixing_eta_0                            0.432       0.3975    0.0096   8.0% ↓
  B iso, Å²       structure.atom_sites[Cl].adp_iso                        0.500        1.399     0.041   179.9% ↑
  z               structure.atom_sites[Cl].fract_z                      0.19762      0.19665   0.00012   0.5% ↓
  B iso, Å²       structure.atom_sites[Cu].adp_iso                        0.500        1.528     0.042   205.6% ↑
  B iso, Å²       structure.atom_sites[H].adp_iso                         0.500        2.497     0.044   399.4% ↑
  x               structure.atom_sites[H].fract_x                       0.13364      0.13258   0.00016   0.8% ↓
  z               structure.atom_sites[H].fract_z                       0.08701      0.08967   0.00014   3.1% ↑
  B iso, Å²       structure.atom_sites[O].adp_iso                         0.500        1.096     0.041   119.3% ↑
  x               structure.atom_sites[O].fract_x                       0.20640      0.20643   0.00017   
  z               structure.atom_sites[O].fract_z                       0.06275      0.06089   0.00014   3.0% ↓
  B iso, Å²       structure.atom_sites[Zn].adp_iso                        0.500        0.277     0.064   44.5% ↓
  a, Å            structure.cell.length_a                                6.8619      6.86132   0.00015   
  c, Å            structure.cell.length_c                               14.1348     14.13556   0.00038   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Asymmetry

Last, the four Bérar-Baldinozzi asymmetry terms.

In `experiments/hrpt.edi`, add `()` after the values the stage frees:

```edi
_peak.asym_beba_a0 0()
_peak.asym_beba_b0 0()
_peak.asym_beba_a1 0()
_peak.asym_beba_b1 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_hs-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_hs-hrpt, 3220 pts fitted / 3220 loaded, 32 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        5.45         2.27
      1      0.068      5.30         2.15   5.3% ↓
      2      0.074      5.30         2.15   
      3      0.086      5.30         2.15   
  done · converged · 3 iters · reduced χ² 2.15 · Rwp 5.30 % · 0.09 s

  refined parameters (32 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     517.9        518.5       9.4   0.1% ↑
  intensity       experiment.background[1].intensity                      536.6        536.9       3.7   
  intensity       experiment.background[2].intensity                      425.5        425.0       2.4   0.1% ↓
  intensity       experiment.background[3].intensity                      467.2        468.3       2.9   0.2% ↑
  intensity       experiment.background[4].intensity                      482.1        482.8       2.7   0.2% ↑
  intensity       experiment.background[5].intensity                      503.8        503.2       2.8   0.1% ↓
  intensity       experiment.background[6].intensity                      489.9        489.9       2.6   
  intensity       experiment.background[7].intensity                      502.4        501.0       2.8   0.3% ↓
  intensity       experiment.background[8].intensity                      533.5        530.5       3.5   0.6% ↓
  intensity       experiment.background[9].intensity                      497.8        499.1       3.4   0.3% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.1100       0.1429    0.0075   29.9% ↑
  scale           experiment.linked_structures[hs].scale                 0.5141       0.5115    0.0027   0.5% ↓
  A₀              experiment.peak.asym_beba_a0                                0       -0.159     0.027   
  A₁              experiment.peak.asym_beba_a1                                0        0.009     0.062   
  B₀              experiment.peak.asym_beba_b0                                0      -0.0424    0.0044   
  B₁              experiment.peak.asym_beba_b1                                0       0.0382    0.0097   
  U, deg²         experiment.peak.broad_gauss_u                           0.285        0.315     0.012   10.6% ↑
  V, deg²         experiment.peak.broad_gauss_v                          -0.269       -0.306     0.020   13.6% ↓
  W, deg²         experiment.peak.broad_gauss_w                          0.3419       0.3513    0.0083   2.7% ↑
  Eta0            experiment.peak.mixing_eta_0                           0.3975       0.3945    0.0094   0.8% ↓
  B iso, Å²       structure.atom_sites[Cl].adp_iso                        1.399        1.380     0.040   1.4% ↓
  z               structure.atom_sites[Cl].fract_z                      0.19665      0.19672   0.00012   
  B iso, Å²       structure.atom_sites[Cu].adp_iso                        1.528        1.528     0.042   
  B iso, Å²       structure.atom_sites[H].adp_iso                         2.497        2.459     0.044   1.5% ↓
  x               structure.atom_sites[H].fract_x                       0.13258      0.13270   0.00016   0.1% ↑
  z               structure.atom_sites[H].fract_z                       0.08967      0.08961   0.00013   0.1% ↓
  B iso, Å²       structure.atom_sites[O].adp_iso                         1.096        1.065     0.040   2.8% ↓
  x               structure.atom_sites[O].fract_x                       0.20643      0.20656   0.00017   0.1% ↑
  z               structure.atom_sites[O].fract_z                       0.06089      0.06099   0.00014   0.2% ↑
  B iso, Å²       structure.atom_sites[Zn].adp_iso                        0.277        0.226     0.064   18.5% ↓
  a, Å            structure.cell.length_a                                6.8613      6.86399   0.00048   
  c, Å            structure.cell.length_c                               14.1356      14.1417    0.0011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-neut-cwl_hs-hrpt --output pd-neut-cwl_hs-hrpt.html
    ```
