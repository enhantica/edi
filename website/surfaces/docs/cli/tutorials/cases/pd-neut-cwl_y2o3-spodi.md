# Rietveld fit: Y₂O₃, SPODI

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit cubic Y₂O₃ to constant-wavelength neutron powder data from SPODI at FRM II, with anisotropic
displacement tensors whose components the site symmetry ties together.

The project is the catalogue case `pd-neut-cwl_y2o3-spodi`, the one the command line and the
app's Examples open.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_y2o3-spodi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_y2o3-spodi
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/spodi.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_twotheta_offset 0
_peak.broad_gauss_u 0.04
_peak.broad_gauss_v -0.07
_peak.broad_gauss_w 0.1
1 12.5856 6400
2 19.4181 6400
```

The same for every other row (20 more).

In `structures/y2o3.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 10.61
Y1 Y -0.03 0 0.25 d 24 1 0.49982 beta
O1 O 0.39 0.15 0.38 e 48 1 0.49982 beta
```

The same for every other row (3 more).

## Scale, 2θ zero and cell

Set the background to its automatic estimate in the experiment file: each fit places its points first, by the arPLS method, a smooth curve under the pattern that ignores the peaks. The scale, the zero shift and the cell length put the peaks in place and at the right height.

In `experiments/spodi.edi`, set:

```edi
_background_estimate.mode auto
_background_estimate.n_points 21
```

In `experiments/spodi.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
y2o3 0.1() 1.0
```

In `structures/y2o3.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 10.61()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_y2o3-spodi, 2509 pts fitted / 3060 loaded, 3 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        3.53         8.11
      1      0.061      2.66         4.61   43.2% ↓
      2      0.072      2.66         4.61   
  done · converged · 2 iters · reduced χ² 4.61 · Rwp 2.66 % · 0.08 s

  refined parameters (3 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0000      -0.0438    0.0013   
  scale           experiment.linked_structures[y2o3].scale                  0.1      0.09417   0.00040   5.8% ↓
  a, Å            structure.cell.length_a                               10.6100     10.60447   0.00014   0.1% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

The estimated points are a starting point; fit them now that the peaks are in place.

In `experiments/spodi.edi`, set:

```edi
_background_estimate.mode manual
```

In `experiments/spodi.edi`, add `()` after the values the stage frees:

```edi
1 12.05 9972.25()
2 22.85 8969()
```

The same for every other row (19 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_y2o3-spodi, 2509 pts fitted / 3060 loaded, 24 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        2.66         4.65
      1      0.073      2.37         3.70   20.3% ↓
  done · converged · 1 iters · reduced χ² 3.70 · Rwp 2.37 % · 0.08 s

  refined parameters (24 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    7.61e3      7.807e3   0.049e3   2.6% ↑
  intensity       experiment.background[11].intensity                    7.74e3      7.806e3   0.015e3   0.8% ↑
  intensity       experiment.background[12].intensity                    7.07e3      7.178e3   0.013e3   1.6% ↑
  intensity       experiment.background[13].intensity                    7.09e3      7.090e3   0.018e3   0.1% ↑
  intensity       experiment.background[14].intensity                    6.75e3      6.884e3   0.022e3   2.0% ↑
  intensity       experiment.background[15].intensity                    6.88e3      6.884e3   0.024e3   0.1% ↑
  intensity       experiment.background[16].intensity                    6.59e3      6.701e3   0.022e3   1.7% ↑
  intensity       experiment.background[17].intensity                    6.59e3      6.626e3   0.022e3   0.6% ↑
  intensity       experiment.background[18].intensity                    6.34e3      6.456e3   0.022e3   1.9% ↑
  intensity       experiment.background[19].intensity                    6.53e3      6.574e3   0.019e3   0.6% ↑
  intensity       experiment.background[1].intensity                     9.97e3      9.957e3   0.069e3   0.1% ↓
  intensity       experiment.background[20].intensity                    6.24e3      6.325e3   0.015e3   1.4% ↑
  intensity       experiment.background[21].intensity                    6.51e3      6.535e3   0.020e3   0.4% ↑
  intensity       experiment.background[2].intensity                     8.97e3      9.116e3   0.044e3   1.6% ↑
  intensity       experiment.background[3].intensity                     8.88e3      8.868e3   0.049e3   0.1% ↓
  intensity       experiment.background[4].intensity                     8.48e3      8.892e3   0.061e3   4.8% ↑
  intensity       experiment.background[5].intensity                     8.63e3      8.709e3   0.025e3   0.9% ↑
  intensity       experiment.background[6].intensity                     7.96e3      7.898e3   0.020e3   0.8% ↓
  intensity       experiment.background[7].intensity                     7.74e3      7.949e3   0.055e3   2.7% ↑
  intensity       experiment.background[8].intensity                     7.70e3      8.248e3   0.064e3   7.2% ↑
  intensity       experiment.background[9].intensity                     7.70e3      8.150e3   0.063e3   5.9% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0438      -0.0438    0.0013   
  scale           experiment.linked_structures[y2o3].scale              0.09417      0.09087   0.00039   3.5% ↓
  a, Å            structure.cell.length_a                               10.6045     10.60446   0.00013   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

In `experiments/spodi.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.04()
_peak.broad_gauss_v -0.07()
_peak.broad_gauss_w 0.1()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_y2o3-spodi, 2509 pts fitted / 3060 loaded, 27 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        2.37         3.71
      1      0.091      1.78         2.10   43.5% ↓
  done · converged · 1 iters · reduced χ² 2.10 · Rwp 1.78 % · 0.10 s

  refined parameters (27 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    7.81e3      7.919e3   0.037e3   1.4% ↑
  intensity       experiment.background[11].intensity                    7.81e3      7.771e3   0.011e3   0.5% ↓
  intensity       experiment.background[12].intensity                    7.18e3     7.1441e3  0.0095e3   0.5% ↓
  intensity       experiment.background[13].intensity                    7.09e3      7.088e3   0.013e3   
  intensity       experiment.background[14].intensity                    6.88e3      6.783e3   0.017e3   1.5% ↓
  intensity       experiment.background[15].intensity                    6.88e3      6.869e3   0.018e3   0.2% ↓
  intensity       experiment.background[16].intensity                    6.70e3      6.640e3   0.017e3   0.9% ↓
  intensity       experiment.background[17].intensity                    6.63e3      6.600e3   0.017e3   0.4% ↓
  intensity       experiment.background[18].intensity                    6.46e3      6.422e3   0.017e3   0.5% ↓
  intensity       experiment.background[19].intensity                    6.57e3      6.540e3   0.014e3   0.5% ↓
  intensity       experiment.background[1].intensity                     9.96e3      9.959e3   0.052e3   
  intensity       experiment.background[20].intensity                    6.33e3      6.304e3   0.012e3   0.3% ↓
  intensity       experiment.background[21].intensity                    6.54e3      6.496e3   0.015e3   0.6% ↓
  intensity       experiment.background[2].intensity                     9.12e3      9.104e3   0.033e3   0.1% ↓
  intensity       experiment.background[3].intensity                     8.87e3      8.882e3   0.037e3   0.2% ↑
  intensity       experiment.background[4].intensity                     8.89e3      8.679e3   0.047e3   2.4% ↓
  intensity       experiment.background[5].intensity                     8.71e3      8.703e3   0.019e3   0.1% ↓
  intensity       experiment.background[6].intensity                     7.90e3      7.871e3   0.015e3   0.3% ↓
  intensity       experiment.background[7].intensity                     7.95e3      8.085e3   0.042e3   1.7% ↑
  intensity       experiment.background[8].intensity                     8.25e3      7.678e3   0.051e3   6.9% ↓
  intensity       experiment.background[9].intensity                     8.15e3      7.637e3   0.050e3   6.3% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0438      -0.0443    0.0011   1.1% ↓
  scale           experiment.linked_structures[y2o3].scale              0.09087      0.10037   0.00039   10.5% ↑
  U, deg²         experiment.peak.broad_gauss_u                            0.04       0.0363    0.0025 ! 9.3% ↓
  V, deg²         experiment.peak.broad_gauss_v                           -0.07      -0.0787    0.0057 ! 12.5% ↓
  W, deg²         experiment.peak.broad_gauss_w                             0.1       0.1401    0.0028   40.1% ↑
  a, Å            structure.cell.length_a                               10.6045    10.604460  0.000098   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (spodi) (r = -0.97)
      experiment.peak.broad_gauss_v: strongly correlated with U (spodi) (r = -0.97)
```

## Atom positions

Y1's x and O1's three coordinates are the ones the symmetry leaves free.

In `structures/y2o3.edi`, add `()` after the values the stage frees:

```edi
Y1 Y -0.03() 0 0.25 d 24 1 0.499298 beta
O1 O 0.39() 0.15() 0.38() e 48 1 0.499298 beta
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_y2o3-spodi, 2509 pts fitted / 3060 loaded, 31 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        1.78         2.10
      1      0.105      1.45         1.39   33.9% ↓
  done · converged · 1 iters · reduced χ² 1.39 · Rwp 1.45 % · 0.12 s

  refined parameters (31 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    7.92e3      7.903e3   0.030e3   0.2% ↓
  intensity       experiment.background[11].intensity                    7.77e3     7.7450e3  0.0090e3   0.3% ↓
  intensity       experiment.background[12].intensity                    7.14e3     7.1374e3  0.0078e3   0.1% ↓
  intensity       experiment.background[13].intensity                    7.09e3      7.052e3   0.011e3   0.5% ↓
  intensity       experiment.background[14].intensity                    6.78e3      6.827e3   0.014e3   0.7% ↑
  intensity       experiment.background[15].intensity                    6.87e3      6.793e3   0.015e3   1.1% ↓
  intensity       experiment.background[16].intensity                    6.64e3      6.637e3   0.014e3   
  intensity       experiment.background[17].intensity                    6.60e3      6.526e3   0.014e3   1.1% ↓
  intensity       experiment.background[18].intensity                    6.42e3      6.429e3   0.014e3   0.1% ↑
  intensity       experiment.background[19].intensity                    6.54e3      6.546e3   0.012e3   0.1% ↑
  intensity       experiment.background[1].intensity                     9.96e3      9.959e3   0.042e3   
  intensity       experiment.background[20].intensity                    6.30e3     6.2805e3  0.0093e3   0.4% ↓
  intensity       experiment.background[21].intensity                    6.50e3      6.520e3   0.012e3   0.4% ↑
  intensity       experiment.background[2].intensity                     9.10e3      9.100e3   0.027e3   
  intensity       experiment.background[3].intensity                     8.88e3      8.884e3   0.030e3   
  intensity       experiment.background[4].intensity                     8.68e3      8.644e3   0.038e3   0.4% ↓
  intensity       experiment.background[5].intensity                     8.70e3      8.700e3   0.016e3   
  intensity       experiment.background[6].intensity                     7.87e3      7.838e3   0.013e3   0.4% ↓
  intensity       experiment.background[7].intensity                     8.09e3      7.990e3   0.034e3   1.2% ↓
  intensity       experiment.background[8].intensity                     7.68e3      7.747e3   0.042e3   0.9% ↑
  intensity       experiment.background[9].intensity                     7.64e3      7.667e3   0.041e3   0.4% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0443     -0.04409   0.00084   0.5% ↑
  scale           experiment.linked_structures[y2o3].scale              0.10037      0.10419   0.00035   3.8% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.0363       0.0350    0.0021 ! 3.6% ↓
  V, deg²         experiment.peak.broad_gauss_v                         -0.0787      -0.0767    0.0047 ! 2.5% ↑
  W, deg²         experiment.peak.broad_gauss_w                          0.1401       0.1400    0.0023   
  x               structure.atom_sites[O1].fract_x                      0.39000      0.39080   0.00017   0.2% ↑
  y               structure.atom_sites[O1].fract_y                      0.15000      0.15166   0.00017   1.1% ↑
  z               structure.atom_sites[O1].fract_z                      0.38000      0.38042   0.00016   0.1% ↑
  x               structure.atom_sites[Y1].fract_x                     -0.03000     -0.03222   0.00012   7.4% ↓
  a, Å            structure.cell.length_a                               10.6045    10.604465  0.000079   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (spodi) (r = -0.97)
      experiment.peak.broad_gauss_v: strongly correlated with U (spodi) (r = -0.97)
```

## Anisotropic displacements

Last, the displacement tensors, each with only the components its site symmetry leaves free.

In `structures/y2o3.edi`, add `()` after the values the stage frees:

```edi
Y1 0.00111() 0.00111() 0.00111() 0 0 0()
Y2 0.00111() 0.00111 0.00111 0() 0 0
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_y2o3-spodi --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_y2o3-spodi, 2509 pts fitted / 3060 loaded, 43 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        1.45         1.39
      1      0.153      1.37         1.24   11.2% ↓
  done · converged · 1 iters · reduced χ² 1.24 · Rwp 1.37 % · 0.17 s

  refined parameters (43 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    7.90e3      7.875e3   0.029e3   0.4% ↓
  intensity       experiment.background[11].intensity                    7.75e3     7.7551e3  0.0086e3   0.1% ↑
  intensity       experiment.background[12].intensity                    7.14e3     7.1379e3  0.0075e3   
  intensity       experiment.background[13].intensity                    7.05e3      7.047e3   0.011e3   0.1% ↓
  intensity       experiment.background[14].intensity                    6.83e3      6.804e3   0.013e3   0.3% ↓
  intensity       experiment.background[15].intensity                    6.79e3      6.781e3   0.015e3   0.2% ↓
  intensity       experiment.background[16].intensity                    6.64e3      6.612e3   0.014e3   0.4% ↓
  intensity       experiment.background[17].intensity                    6.53e3      6.495e3   0.015e3   0.5% ↓
  intensity       experiment.background[18].intensity                    6.43e3      6.403e3   0.013e3   0.4% ↓
  intensity       experiment.background[19].intensity                    6.55e3      6.524e3   0.012e3   0.3% ↓
  intensity       experiment.background[1].intensity                     9.96e3      9.958e3   0.040e3   
  intensity       experiment.background[20].intensity                    6.28e3     6.2572e3  0.0093e3   0.4% ↓
  intensity       experiment.background[21].intensity                    6.52e3      6.473e3   0.013e3   0.7% ↓
  intensity       experiment.background[2].intensity                     9.10e3      9.110e3   0.025e3   0.1% ↑
  intensity       experiment.background[3].intensity                     8.88e3      8.877e3   0.029e3   0.1% ↓
  intensity       experiment.background[4].intensity                     8.64e3      8.749e3   0.037e3   1.2% ↑
  intensity       experiment.background[5].intensity                     8.70e3      8.704e3   0.015e3   
  intensity       experiment.background[6].intensity                     7.84e3      7.851e3   0.012e3   0.2% ↑
  intensity       experiment.background[7].intensity                     7.99e3      7.959e3   0.033e3   0.4% ↓
  intensity       experiment.background[8].intensity                     7.75e3      7.918e3   0.041e3   2.2% ↑
  intensity       experiment.background[9].intensity                     7.67e3      7.820e3   0.039e3   2.0% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0441     -0.04397   0.00079   0.3% ↑
  scale           experiment.linked_structures[y2o3].scale              0.10419      0.09655   0.00056   7.3% ↓
  U, deg²         experiment.peak.broad_gauss_u                           0.035       0.0339    0.0022 ! 3.1% ↓
  V, deg²         experiment.peak.broad_gauss_v                         -0.0767      -0.0601    0.0049 ! 21.6% ↑
  W, deg²         experiment.peak.broad_gauss_w                            0.14       0.1278    0.0023   8.7% ↓
  β₁₁             structure.atom_site_aniso[O1].adp_11                  0.00111       5.5e-4    1.4e-4   50.1% ↓
  β₁₂             structure.atom_site_aniso[O1].adp_12                        0      -1.1e-4    1.2e-4   
  β₁₃             structure.atom_site_aniso[O1].adp_13                        0         3e-5     11e-5   
  β₂₂             structure.atom_site_aniso[O1].adp_22                  0.00111      0.00101   0.00017   9.0% ↓
  β₂₃             structure.atom_site_aniso[O1].adp_23                        0        -5e-5     15e-5   
  β₃₃             structure.atom_site_aniso[O1].adp_33                  0.00111       3.3e-4    1.1e-4   70.3% ↓
  β₁₁             structure.atom_site_aniso[Y1].adp_11                  0.00111       3.2e-4    1.7e-4   70.7% ↓
  β₂₂             structure.atom_site_aniso[Y1].adp_22                  0.00111       3.2e-4    1.4e-4   71.5% ↓
  β₂₃             structure.atom_site_aniso[Y1].adp_23                        0      -2.8e-4    1.9e-4   
  β₃₃             structure.atom_site_aniso[Y1].adp_33                  0.00111       6.2e-4    2.0e-4   44.2% ↓
  β₁₁             structure.atom_site_aniso[Y2].adp_11                  0.00111       6.4e-4    1.4e-4   42.1% ↓
  β₁₂             structure.atom_site_aniso[Y2].adp_12                        0         4e-5     19e-5   
  x               structure.atom_sites[O1].fract_x                      0.39080      0.39067   0.00022   
  y               structure.atom_sites[O1].fract_y                      0.15166      0.15202   0.00023   0.2% ↑
  z               structure.atom_sites[O1].fract_z                      0.38042      0.38024   0.00021   
  x               structure.atom_sites[Y1].fract_x                     -0.03222     -0.03207   0.00013   0.5% ↑
  a, Å            structure.cell.length_a                               10.6045    10.604465  0.000075   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (spodi) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with U (spodi) (r = -0.96)
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-neut-cwl_y2o3-spodi --output pd-neut-cwl_y2o3-spodi.html
    ```
