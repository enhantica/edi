# Two-phase fit: YAlO₃ and Al₂O₃, SPODI

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_yalo3-al2o3-spodi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_yalo3-al2o3-spodi
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/spodi.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_twotheta_offset 0
_peak.broad_gauss_u 0.04
_peak.broad_gauss_v -0.05
_peak.broad_gauss_w 0.1
_peak.mixing_eta_0 0.1
_peak.asym_beba_a0 0
_peak.asym_beba_b0 0
_peak.asym_beba_a1 0
_peak.asym_beba_b1 0
1 4.05 2100
2 4.777 2100
```

The same for every other row (25 more).

In `structures/Al2O3.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 4.76
_cell.length_c 12.97
Al1 Al 0 0 0.33 c 12 1 0.5 Biso
O1 O 0.35 0 0.25 e 18 1 0.5 Biso
```

In `structures/YAlO3.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 5.17
_cell.length_b 5.33
_cell.length_c 7.36
Y Y 0.01 0.55 0.25 c 4 1 0.5 Biso
Al Al 0 0 0 a 4 1 0.5 Biso
```

The same for every other row (2 more).

## Cells, scales and 2θ zero

Both phases' cells and scales, and the zero shift, put the peaks of both phases in place.

In `experiments/spodi.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
YAlO3 30() 0.9922535236803708()
Al2O3 0.2() 0.007746476319629156()
```

In `structures/Al2O3.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 4.76()
_cell.length_c 12.97()
```

In `structures/YAlO3.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 5.17()
_cell.length_b 5.33()
_cell.length_c 7.36()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_yalo3-al2o3-spodi, 2959 pts fitted / 2959 loaded, 8 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       18.59       201.52
      1      0.180     13.38       104.43   48.2% ↓
      2      0.200     13.38       104.42   
      3      0.218     13.38       104.42   
      4      0.235     13.38       104.42   
      5      0.267     13.38       104.42   
  done · converged · 5 iters · reduced χ² 104.42 · Rwp 13.38 % · 0.29 s

  refined parameters (8 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0000       0.0025    0.0012   
  scale           experiment.linked_structures[Al2O3].scale                 0.2        0.214     0.018   7.0% ↑
  scale           experiment.linked_structures[YAlO3].scale                  30        31.72      0.12   5.7% ↑
  a, Å            structures[Al2O3].cell.length_a                        4.7600       4.7561    0.0011   0.1% ↓
  c, Å            structures[Al2O3].cell.length_c                       12.9700      12.9829    0.0051   0.1% ↑
  a, Å            structures[YAlO3].cell.length_a                        5.1700     5.173550  0.000093   0.1% ↑
  b, Å            structures[YAlO3].cell.length_b                        5.3300     5.327681  0.000092   
  c, Å            structures[YAlO3].cell.length_c                        7.3600      7.36230   0.00013   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

In `experiments/spodi.edi`, add `()` after the values the stage frees:

```edi
1 4.05 2100()
2 4.777 2100()
```

The same for every other row (23 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_yalo3-al2o3-spodi, 2959 pts fitted / 2959 loaded, 33 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.38       105.32
      1      0.323     11.96        84.07   20.2% ↓
      2      0.348     11.96        84.06   
      3      0.374     11.96        84.06   
      4      0.398     11.96        84.06   
      5      0.420     11.96        84.06   
      6      0.442     11.96        84.06   
      7      0.546     11.96        84.06   
  done · converged · 7 iters · reduced χ² 84.06 · Rwp 11.96 % · 0.57 s

  refined parameters (33 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    2.10e3      2.135e3   0.058e3   1.7% ↑
  intensity       experiment.background[11].intensity                    2.10e3      2.103e3   0.049e3   0.1% ↑
  intensity       experiment.background[12].intensity                    2.10e3      1.956e3   0.047e3   6.9% ↓
  intensity       experiment.background[13].intensity                    2.10e3      2.274e3   0.050e3   8.3% ↑
  intensity       experiment.background[14].intensity                    2.10e3      2.086e3   0.054e3   0.7% ↓
  intensity       experiment.background[15].intensity                    2.10e3      2.452e3   0.062e3   16.8% ↑
  intensity       experiment.background[16].intensity                    2.10e3      2.038e3   0.077e3   2.9% ↓
  intensity       experiment.background[17].intensity                    2.10e3      2.090e3   0.074e3   0.5% ↓
  intensity       experiment.background[18].intensity                    2.10e3      2.170e3   0.063e3   3.4% ↑
  intensity       experiment.background[19].intensity                    2.10e3      2.161e3   0.060e3   2.9% ↑
  intensity       experiment.background[1].intensity                     2.10e3      1.330e3   0.160e3   36.6% ↓
  intensity       experiment.background[20].intensity                    2.10e3      3.058e3   0.070e3   45.6% ↑
  intensity       experiment.background[21].intensity                    2.10e3      2.431e3   0.062e3   15.7% ↑
  intensity       experiment.background[22].intensity                    2.10e3      2.772e3   0.070e3   32.0% ↑
  intensity       experiment.background[23].intensity                    2.10e3      2.621e3   0.084e3   24.8% ↑
  intensity       experiment.background[24].intensity                    2.10e3      2.980e3   0.110e3   42.0% ↑
  intensity       experiment.background[25].intensity                    2.10e3      2.810e3   0.130e3   33.7% ↑
  intensity       experiment.background[2].intensity                     2.10e3      1.823e3   0.098e3   13.2% ↓
  intensity       experiment.background[3].intensity                     2.10e3      2.431e3   0.064e3   15.8% ↑
  intensity       experiment.background[4].intensity                     2.10e3      2.108e3   0.053e3   0.4% ↑
  intensity       experiment.background[5].intensity                     2.10e3      2.031e3   0.053e3   3.3% ↓
  intensity       experiment.background[6].intensity                     2.10e3      2.100e3   0.048e3   
  intensity       experiment.background[7].intensity                     2.10e3      2.091e3   0.051e3   0.4% ↓
  intensity       experiment.background[8].intensity                     2.10e3      2.111e3   0.054e3   0.5% ↑
  intensity       experiment.background[9].intensity                     2.10e3      1.944e3   0.056e3   7.4% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0025       0.0027    0.0011   8.5% ↑
  scale           experiment.linked_structures[Al2O3].scale               0.214        0.192     0.017   10.3% ↓
  scale           experiment.linked_structures[YAlO3].scale               31.72        31.06      0.12   2.1% ↓
  a, Å            structures[Al2O3].cell.length_a                        4.7561       4.7555    0.0011   
  c, Å            structures[Al2O3].cell.length_c                       12.9829      12.9857    0.0053   
  a, Å            structures[YAlO3].cell.length_a                        5.1735     5.173536  0.000085   
  b, Å            structures[YAlO3].cell.length_b                        5.3277     5.327720  0.000085   
  c, Å            structures[YAlO3].cell.length_c                        7.3623      7.36231   0.00012   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

The Gaussian widths and the mixing η₀.

In `experiments/spodi.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.04()
_peak.broad_gauss_v -0.05()
_peak.broad_gauss_w 0.1()
_peak.mixing_eta_0 0.1()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_yalo3-al2o3-spodi, 2959 pts fitted / 2959 loaded, 37 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.96        84.18
      1      0.278     11.46        77.33   8.1% ↓
      2      0.297     11.46        77.33   
      3      0.320     11.46        77.33   
      4      0.338     11.46        77.33   
      5      0.361     11.46        77.33   
      6      0.380     11.46        77.33   
      7      0.403     11.46        77.33   
      8      0.421     11.46        77.33   
      9      0.446     11.46        77.33   
     10      0.463     11.46        77.33   
     11      0.486     11.46        77.32   
     12      0.504     11.46        77.32   
     13      0.525     11.46        77.32   
     14      0.543     11.46        77.32   
     15      0.565     11.46        77.32   
     16      0.582     11.46        77.32   
     17      0.606     11.46        77.32   
     18      0.707     11.46        77.32   
  done · converged · 18 iters · reduced χ² 77.32 · Rwp 11.46 % · 0.73 s

  refined parameters (37 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    2.13e3      2.061e3   0.058e3   3.5% ↓
  intensity       experiment.background[11].intensity                    2.10e3      2.044e3   0.047e3   2.8% ↓
  intensity       experiment.background[12].intensity                    1.96e3      1.859e3   0.049e3   5.0% ↓
  intensity       experiment.background[13].intensity                    2.27e3      2.210e3   0.050e3   2.8% ↓
  intensity       experiment.background[14].intensity                    2.09e3      1.990e3   0.055e3   4.6% ↓
  intensity       experiment.background[15].intensity                    2.45e3      2.403e3   0.061e3   2.0% ↓
  intensity       experiment.background[16].intensity                    2.04e3      1.992e3   0.076e3   2.3% ↓
  intensity       experiment.background[17].intensity                    2.09e3      2.076e3   0.071e3   0.7% ↓
  intensity       experiment.background[18].intensity                    2.17e3      2.154e3   0.061e3   0.7% ↓
  intensity       experiment.background[19].intensity                    2.16e3      2.144e3   0.059e3   0.8% ↓
  intensity       experiment.background[1].intensity                     1.33e3      1.330e3   0.150e3   0.1% ↑
  intensity       experiment.background[20].intensity                    3.06e3      3.039e3   0.072e3   0.6% ↓
  intensity       experiment.background[21].intensity                    2.43e3      2.422e3   0.061e3   0.4% ↓
  intensity       experiment.background[22].intensity                    2.77e3      2.818e3   0.069e3   1.7% ↑
  intensity       experiment.background[23].intensity                    2.62e3      2.641e3   0.081e3   0.8% ↑
  intensity       experiment.background[24].intensity                    2.98e3      3.040e3   0.100e3   2.0% ↑
  intensity       experiment.background[25].intensity                    2.81e3      2.850e3   0.130e3   1.5% ↑
  intensity       experiment.background[2].intensity                     1.82e3      1.823e3   0.094e3   
  intensity       experiment.background[3].intensity                     2.43e3      2.432e3   0.061e3   
  intensity       experiment.background[4].intensity                     2.11e3      2.108e3   0.051e3   
  intensity       experiment.background[5].intensity                     2.03e3      2.032e3   0.051e3   0.1% ↑
  intensity       experiment.background[6].intensity                     2.10e3      2.096e3   0.046e3   0.2% ↓
  intensity       experiment.background[7].intensity                     2.09e3      2.087e3   0.049e3   0.2% ↓
  intensity       experiment.background[8].intensity                     2.11e3      2.014e3   0.054e3   4.6% ↓
  intensity       experiment.background[9].intensity                     1.94e3      1.745e3   0.063e3   10.2% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0027       0.0033    0.0011   21.0% ↑
  scale           experiment.linked_structures[Al2O3].scale               0.192        0.207     0.017   7.9% ↑
  scale           experiment.linked_structures[YAlO3].scale               31.06        31.51      0.16   1.4% ↑
  U, deg²         experiment.peak.broad_gauss_u                            0.04       0.0279    0.0019   30.2% ↓
  V, deg²         experiment.peak.broad_gauss_v                           -0.05      -0.0401    0.0049   19.7% ↑
  W, deg²         experiment.peak.broad_gauss_w                             0.1       0.1078    0.0025   7.8% ↑
  Eta0            experiment.peak.mixing_eta_0                              0.1        0.132     0.014   32.4% ↑
  a, Å            structures[Al2O3].cell.length_a                        4.7555      4.75571   0.00096   
  c, Å            structures[Al2O3].cell.length_c                       12.9857      12.9880    0.0045   
  a, Å            structures[YAlO3].cell.length_a                        5.1735     5.173563  0.000078   
  b, Å            structures[YAlO3].cell.length_b                        5.3277     5.327774  0.000078   
  c, Å            structures[YAlO3].cell.length_c                        7.3623      7.36239   0.00011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Asymmetry

The four Bérar-Baldinozzi asymmetry terms.

In `experiments/spodi.edi`, add `()` after the values the stage frees:

```edi
_peak.asym_beba_a0 0()
_peak.asym_beba_b0 0()
_peak.asym_beba_a1 0()
_peak.asym_beba_b1 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_yalo3-al2o3-spodi, 2959 pts fitted / 2959 loaded, 41 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.46        77.43
      1      0.240     11.28        74.99   3.2% ↓
      2      0.258     11.28        74.99   
      3      0.363     11.28        74.99   
  done · converged · 3 iters · reduced χ² 74.99 · Rwp 11.28 % · 0.38 s

  refined parameters (41 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    2.06e3      2.064e3   0.057e3   0.2% ↑
  intensity       experiment.background[11].intensity                    2.04e3      2.049e3   0.047e3   0.2% ↑
  intensity       experiment.background[12].intensity                    1.86e3      1.866e3   0.048e3   0.4% ↑
  intensity       experiment.background[13].intensity                    2.21e3      2.213e3   0.049e3   0.2% ↑
  intensity       experiment.background[14].intensity                    1.99e3      1.997e3   0.054e3   0.4% ↑
  intensity       experiment.background[15].intensity                    2.40e3      2.402e3   0.060e3   
  intensity       experiment.background[16].intensity                    1.99e3      1.997e3   0.075e3   0.2% ↑
  intensity       experiment.background[17].intensity                    2.08e3      2.071e3   0.070e3   0.2% ↓
  intensity       experiment.background[18].intensity                    2.15e3      2.159e3   0.060e3   0.2% ↑
  intensity       experiment.background[19].intensity                    2.14e3      2.142e3   0.058e3   0.1% ↓
  intensity       experiment.background[1].intensity                     1.33e3      1.330e3   0.150e3   0.1% ↑
  intensity       experiment.background[20].intensity                    3.04e3      3.032e3   0.071e3   0.2% ↓
  intensity       experiment.background[21].intensity                    2.42e3      2.413e3   0.060e3   0.4% ↓
  intensity       experiment.background[22].intensity                    2.82e3      2.809e3   0.068e3   0.3% ↓
  intensity       experiment.background[23].intensity                    2.64e3      2.643e3   0.080e3   0.1% ↑
  intensity       experiment.background[24].intensity                    3.04e3      3.032e3   0.099e3   0.3% ↓
  intensity       experiment.background[25].intensity                    2.85e3      2.840e3   0.130e3   0.5% ↓
  intensity       experiment.background[2].intensity                     1.82e3      1.823e3   0.093e3   
  intensity       experiment.background[3].intensity                     2.43e3      2.432e3   0.061e3   
  intensity       experiment.background[4].intensity                     2.11e3      2.108e3   0.050e3   
  intensity       experiment.background[5].intensity                     2.03e3      2.032e3   0.050e3   
  intensity       experiment.background[6].intensity                     2.10e3      2.097e3   0.045e3   
  intensity       experiment.background[7].intensity                     2.09e3      2.086e3   0.048e3   0.1% ↓
  intensity       experiment.background[8].intensity                     2.01e3      2.021e3   0.053e3   0.4% ↑
  intensity       experiment.background[9].intensity                     1.75e3      1.764e3   0.062e3   1.1% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0033       0.0123    0.0048   272.7% ↑
  scale           experiment.linked_structures[Al2O3].scale               0.207        0.199     0.017   4.1% ↓
  scale           experiment.linked_structures[YAlO3].scale               31.51        31.53      0.16   0.1% ↑
  A₀              experiment.peak.asym_beba_a0                                0       -0.242     0.054   
  A₁              experiment.peak.asym_beba_a1                                0         0.04      0.13   
  B₀              experiment.peak.asym_beba_b0                                0      -0.0127    0.0077   
  B₁              experiment.peak.asym_beba_b1                                0       -0.043     0.017   
  U, deg²         experiment.peak.broad_gauss_u                          0.0279       0.0321    0.0025   15.2% ↑
  V, deg²         experiment.peak.broad_gauss_v                         -0.0401      -0.0462    0.0053   15.2% ↓
  W, deg²         experiment.peak.broad_gauss_w                          0.1078       0.1112    0.0026   3.1% ↑
  Eta0            experiment.peak.mixing_eta_0                            0.132        0.127     0.014   4.1% ↓
  a, Å            structures[Al2O3].cell.length_a                        4.7557      4.75620   0.00099   
  c, Å            structures[Al2O3].cell.length_c                       12.9880      12.9841    0.0047   
  a, Å            structures[YAlO3].cell.length_a                        5.1736      5.17308   0.00024   
  b, Å            structures[YAlO3].cell.length_b                        5.3278      5.32729   0.00025   
  c, Å            structures[YAlO3].cell.length_c                        7.3624      7.36155   0.00036   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Atom positions

The coordinates the symmetry leaves free in both phases.

In `structures/Al2O3.edi`, add `()` after the values the stage frees:

```edi
Al1 Al 0 0 0.33() c 12 1 0.5 Biso
O1 O 0.35() 0 0.25 e 18 1 0.5 Biso
```

In `structures/YAlO3.edi`, add `()` after the values the stage frees:

```edi
Y Y 0.01() 0.55() 0.25 c 4 1 0.5 Biso
O1 O -0.08() -0.02() 0.25 c 4 1 0.5 Biso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_yalo3-al2o3-spodi, 2959 pts fitted / 2959 loaded, 50 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.28        75.22
      1      0.353      6.46        24.69   67.2% ↓
      2      0.377      6.46        24.69   
      3      0.403      6.46        24.69   
      4      0.437      6.46        24.69   
      5      0.474      6.46        24.69   
      6      0.498      6.46        24.69   
      7      0.519      6.46        24.69   
      8      0.543      6.46        24.69   
      9      0.565      6.46        24.69   
     10      0.588      6.46        24.69   
     11      0.625      6.46        24.69   
     12      0.750      6.46        24.69   
  done · converged · 12 iters · reduced χ² 24.69 · Rwp 6.46 % · 0.78 s

  refined parameters (50 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    2.06e3      1.953e3   0.033e3   5.4% ↓
  intensity       experiment.background[11].intensity                    2.05e3      1.993e3   0.027e3   2.7% ↓
  intensity       experiment.background[12].intensity                    1.87e3      1.964e3   0.028e3   5.2% ↑
  intensity       experiment.background[13].intensity                    2.21e3      2.140e3   0.028e3   3.3% ↓
  intensity       experiment.background[14].intensity                    2.00e3      2.257e3   0.032e3   13.0% ↑
  intensity       experiment.background[15].intensity                    2.40e3      2.323e3   0.035e3   3.3% ↓
  intensity       experiment.background[16].intensity                    2.00e3      2.233e3   0.043e3   11.8% ↑
  intensity       experiment.background[17].intensity                    2.07e3      2.041e3   0.040e3   1.5% ↓
  intensity       experiment.background[18].intensity                    2.16e3      2.062e3   0.036e3   4.5% ↓
  intensity       experiment.background[19].intensity                    2.14e3      2.191e3   0.034e3   2.3% ↑
  intensity       experiment.background[1].intensity                     1.33e3      1.332e3   0.084e3   0.1% ↑
  intensity       experiment.background[20].intensity                    3.03e3      2.905e3   0.042e3   4.2% ↓
  intensity       experiment.background[21].intensity                    2.41e3      2.517e3   0.035e3   4.3% ↑
  intensity       experiment.background[22].intensity                    2.81e3      3.029e3   0.040e3   7.8% ↑
  intensity       experiment.background[23].intensity                    2.64e3      2.827e3   0.047e3   7.0% ↑
  intensity       experiment.background[24].intensity                    3.03e3      3.271e3   0.057e3   7.9% ↑
  intensity       experiment.background[25].intensity                    2.84e3      3.243e3   0.072e3   14.2% ↑
  intensity       experiment.background[2].intensity                     1.82e3      1.823e3   0.053e3   
  intensity       experiment.background[3].intensity                     2.43e3      2.431e3   0.035e3   
  intensity       experiment.background[4].intensity                     2.11e3      2.110e3   0.029e3   0.1% ↑
  intensity       experiment.background[5].intensity                     2.03e3      2.027e3   0.029e3   0.3% ↓
  intensity       experiment.background[6].intensity                     2.10e3      2.066e3   0.026e3   1.5% ↓
  intensity       experiment.background[7].intensity                     2.09e3      2.088e3   0.028e3   0.1% ↑
  intensity       experiment.background[8].intensity                     2.02e3      2.017e3   0.031e3   0.2% ↓
  intensity       experiment.background[9].intensity                     1.76e3      1.823e3   0.036e3   3.3% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0123       0.0107    0.0028   12.6% ↓
  scale           experiment.linked_structures[Al2O3].scale               0.199        0.210     0.012   5.8% ↑
  scale           experiment.linked_structures[YAlO3].scale               31.53       31.720     0.090   0.6% ↑
  A₀              experiment.peak.asym_beba_a0                           -0.242       -0.278     0.034   14.9% ↓
  A₁              experiment.peak.asym_beba_a1                             0.04        0.181     0.076   351.3% ↑
  B₀              experiment.peak.asym_beba_b0                          -0.0127      -0.0173    0.0047   36.3% ↓
  B₁              experiment.peak.asym_beba_b1                           -0.043       -0.023     0.010   46.5% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.0321       0.0296    0.0015   7.9% ↓
  V, deg²         experiment.peak.broad_gauss_v                         -0.0462      -0.0447    0.0030   3.3% ↑
  W, deg²         experiment.peak.broad_gauss_w                          0.1112       0.1120    0.0015   0.7% ↑
  Eta0            experiment.peak.mixing_eta_0                            0.127       0.1062    0.0077   16.4% ↓
  z               structures[Al2O3].atom_sites[Al1].fract_z             0.33000       0.3343    0.0055   1.3% ↑
  x               structures[Al2O3].atom_sites[O1].fract_x              0.35000       0.3564    0.0048   1.8% ↑
  a, Å            structures[Al2O3].cell.length_a                        4.7562      4.75637   0.00055   
  c, Å            structures[Al2O3].cell.length_c                       12.9841      12.9813    0.0025   
  x               structures[YAlO3].atom_sites[O1].fract_x             -0.08000     -0.08396   0.00025   4.9% ↓
  y               structures[YAlO3].atom_sites[O1].fract_y             -0.02000     -0.02189   0.00021   9.4% ↓
  x               structures[YAlO3].atom_sites[O2].fract_x              0.20000      0.20451   0.00016   2.3% ↑
  y               structures[YAlO3].atom_sites[O2].fract_y              0.29000      0.29518   0.00015   1.8% ↑
  z               structures[YAlO3].atom_sites[O2].fract_z              0.04000      0.04448   0.00011   11.2% ↑
  x               structures[YAlO3].atom_sites[Y].fract_x               0.01000      0.01211   0.00019   21.1% ↑
  y               structures[YAlO3].atom_sites[Y].fract_y               0.55000      0.55405   0.00014   0.7% ↑
  a, Å            structures[YAlO3].cell.length_a                        5.1731      5.17290   0.00015   
  b, Å            structures[YAlO3].cell.length_b                        5.3273      5.32719   0.00015   
  c, Å            structures[YAlO3].cell.length_c                        7.3616      7.36146   0.00021   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Displacements

Every site's displacement in both phases.

In `structures/Al2O3.edi`, add `()` after the values the stage frees:

```edi
Al1 Al 0 0 0.3343() c 12 1 0.5() Biso
O1 O 0.3564() 0 0.25 e 18 1 0.5() Biso
```

In `structures/YAlO3.edi`, add `()` after the values the stage frees:

```edi
Y Y 0.01211() 0.55405() 0.25 c 4 1 0.5() Biso
Al Al 0 0 0 a 4 1 0.5() Biso
```

The same for every other row (2 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_yalo3-al2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_yalo3-al2o3-spodi, 2959 pts fitted / 2959 loaded, 56 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        6.46        24.74
      1      0.310      4.06         9.77   60.5% ↓
      2      0.334      4.06         9.77   
      3      0.374      4.06         9.77   
      4      0.409      4.06         9.76   
      5      0.457      4.06         9.76   0.1% ↓
      6      0.499      4.05         9.74   0.1% ↓
      7      0.521      4.05         9.73   0.1% ↓
      8      0.544      4.05         9.73   
      9      0.566      4.05         9.73   
     10      0.594      4.05         9.73   
     11      0.617      4.05         9.73   
     12      0.758      4.05         9.73   
  done · converged · 12 iters · reduced χ² 9.73 · Rwp 4.05 % · 0.78 s

  refined parameters (56 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    1.95e3      2.004e3   0.021e3   2.6% ↑
  intensity       experiment.background[11].intensity                    1.99e3      2.053e3   0.017e3   3.0% ↑
  intensity       experiment.background[12].intensity                    1.96e3      1.983e3   0.018e3   1.0% ↑
  intensity       experiment.background[13].intensity                    2.14e3      2.150e3   0.018e3   0.5% ↑
  intensity       experiment.background[14].intensity                    2.26e3      2.165e3   0.020e3   4.1% ↓
  intensity       experiment.background[15].intensity                    2.32e3      2.150e3   0.023e3   7.4% ↓
  intensity       experiment.background[16].intensity                    2.23e3      2.076e3   0.028e3   7.0% ↓
  intensity       experiment.background[17].intensity                    2.04e3      1.960e3   0.026e3   4.0% ↓
  intensity       experiment.background[18].intensity                    2.06e3      2.009e3   0.022e3   2.6% ↓
  intensity       experiment.background[19].intensity                    2.19e3      1.980e3   0.022e3   9.6% ↓
  intensity       experiment.background[1].intensity                     1.33e3      1.332e3   0.053e3   
  intensity       experiment.background[20].intensity                    2.90e3      2.479e3   0.029e3   14.7% ↓
  intensity       experiment.background[21].intensity                    2.52e3      2.321e3   0.023e3   7.8% ↓
  intensity       experiment.background[22].intensity                    3.03e3      2.675e3   0.026e3   11.7% ↓
  intensity       experiment.background[23].intensity                    2.83e3      2.591e3   0.031e3   8.4% ↓
  intensity       experiment.background[24].intensity                    3.27e3      2.808e3   0.038e3   14.2% ↓
  intensity       experiment.background[25].intensity                    3.24e3      2.763e3   0.048e3   14.8% ↓
  intensity       experiment.background[2].intensity                     1.82e3      1.823e3   0.034e3   
  intensity       experiment.background[3].intensity                     2.43e3      2.431e3   0.022e3   
  intensity       experiment.background[4].intensity                     2.11e3      2.109e3   0.018e3   0.1% ↓
  intensity       experiment.background[5].intensity                     2.03e3      2.030e3   0.018e3   0.2% ↑
  intensity       experiment.background[6].intensity                     2.07e3      2.062e3   0.017e3   0.2% ↓
  intensity       experiment.background[7].intensity                     2.09e3      2.106e3   0.018e3   0.9% ↑
  intensity       experiment.background[8].intensity                     2.02e3      2.168e3   0.020e3   7.5% ↑
  intensity       experiment.background[9].intensity                     1.82e3      2.000e3   0.023e3   9.7% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0107       0.0044    0.0017   58.6% ↓
  scale           experiment.linked_structures[Al2O3].scale                0.21        0.186     0.012   11.3% ↓
  scale           experiment.linked_structures[YAlO3].scale               31.72       27.915     0.077   12.0% ↓
  A₀              experiment.peak.asym_beba_a0                           -0.278       -0.250     0.018   10.1% ↑
  A₁              experiment.peak.asym_beba_a1                            0.181        0.109     0.032   39.8% ↓
  B₀              experiment.peak.asym_beba_b0                          -0.0173      -0.0061    0.0027   64.7% ↑
  B₁              experiment.peak.asym_beba_b1                           -0.023      -0.0553    0.0052   140.5% ↓
  U, deg²         experiment.peak.broad_gauss_u                          0.0296       0.0370    0.0011   25.0% ↑
  V, deg²         experiment.peak.broad_gauss_v                         -0.0447      -0.0424    0.0021   5.1% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.112      0.10490   0.00098   6.3% ↓
  Eta0            experiment.peak.mixing_eta_0                           0.1062       0.1247    0.0051   17.4% ↑
  B iso, Å²       structures[Al2O3].atom_sites[Al1].adp_iso               0.500        -0.37      0.25   174.6% ↓
  z               structures[Al2O3].atom_sites[Al1].fract_z             0.33430       0.3343    0.0031   
  B iso, Å²       structures[Al2O3].atom_sites[O1].adp_iso                0.500         1.19      0.30   137.8% ↑
  x               structures[Al2O3].atom_sites[O1].fract_x              0.35640       0.3126    0.0048   12.3% ↓
  a, Å            structures[Al2O3].cell.length_a                        4.7564      4.75839   0.00043   
  c, Å            structures[Al2O3].cell.length_c                       12.9813      12.9669    0.0022   0.1% ↓
  B iso, Å²       structures[YAlO3].atom_sites[Al].adp_iso                0.500        0.122     0.016   75.6% ↓
  B iso, Å²       structures[YAlO3].atom_sites[O1].adp_iso                0.500        0.066     0.011   86.8% ↓
  x               structures[YAlO3].atom_sites[O1].fract_x             -0.08396     -0.08392   0.00015   
  y               structures[YAlO3].atom_sites[O1].fract_y             -0.02189     -0.02202   0.00013   0.6% ↓
  B iso, Å²       structures[YAlO3].atom_sites[O2].adp_iso                0.500       0.1407    0.0078   71.9% ↓
  x               structures[YAlO3].atom_sites[O2].fract_x              0.20451     0.204695  0.000099   0.1% ↑
  y               structures[YAlO3].atom_sites[O2].fract_y              0.29518     0.294833  0.000088   0.1% ↓
  z               structures[YAlO3].atom_sites[O2].fract_z              0.04448     0.044281  0.000064   0.4% ↓
  B iso, Å²       structures[YAlO3].atom_sites[Y].adp_iso                 0.500       0.1162    0.0089   76.8% ↓
  x               structures[YAlO3].atom_sites[Y].fract_x               0.01211      0.01244   0.00012   2.7% ↑
  y               structures[YAlO3].atom_sites[Y].fract_y               0.55405     0.554035  0.000083   
  a, Å            structures[YAlO3].cell.length_a                        5.1729     5.172477  0.000073   
  b, Å            structures[YAlO3].cell.length_b                        5.3272     5.326739  0.000074   
  c, Å            structures[YAlO3].cell.length_c                        7.3615      7.36083   0.00011   

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
    python -m edi report pd-neut-cwl_yalo3-al2o3-spodi --output pd-neut-cwl_yalo3-al2o3-spodi.html
    ```
