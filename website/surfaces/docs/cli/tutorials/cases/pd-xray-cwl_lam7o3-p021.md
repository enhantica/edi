# Rietveld fit: high-entropy perovskite, P02.1

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-xray-cwl_lam7o3-p021
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-xray-cwl_lam7o3-p021
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/p021.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_twotheta_offset 0
_peak.broad_gauss_u 0.04
_peak.broad_gauss_v -0.01
_peak.broad_gauss_w 0.001
_peak.broad_lorentz_x 0.1
2.0 2.0033379 300
2.3 2.297792 300
```

The same for every other row (19 more).

In `structures/lam7o3.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 5.5
_cell.length_b 7.7
_cell.length_c 5.5
La La 0.48 0.25 0 c 4 1 0.5 Biso
Ti Ti 0 0 0 a 4 0.14286 0.5 Biso
```

The same for every other row (2 more).

## Scale, 2θ zero and cell

The scale, the zero shift and the cell put the peaks in place and at the right height.

In `experiments/p021.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
lam7o3 0.000005() 1.0
```

In `structures/lam7o3.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 5.5()
_cell.length_b 7.7()
_cell.length_c 5.5()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_lam7o3-p021, 1236 pts fitted / 1459 loaded, 5 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       60.60       246.85
      1      0.017     42.69       122.50   50.4% ↓
      2      0.024     38.20        98.09   19.9% ↓
      3      0.031     35.23        83.41   15.0% ↓
      4      0.038     34.19        78.58   5.8% ↓
      5      0.045     33.91        77.27   1.7% ↓
      6      0.052     33.81        76.83   0.6% ↓
      7      0.060     33.76        76.62   0.3% ↓
      8      0.067     33.73        76.49   0.2% ↓
      9      0.074     33.72        76.41   0.1% ↓
     10      0.081     33.70        76.35   0.1% ↓
     11      0.088     33.69        76.31   0.1% ↓
     12      0.094     33.69        76.29   
     13      0.101     33.68        76.27   
     14      0.107     33.68        76.26   
     15      0.114     33.68        76.25   
     16      0.121     33.68        76.25   
     17      0.127     33.68        76.24   
     18      0.134     33.68        76.24   
     19      0.140     33.68        76.24   
     20      0.151     33.68        76.24   
  done · converged · 20 iters · reduced χ² 76.24 · Rwp 33.68 % · 0.16 s

  refined parameters (5 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0000      0.00177   0.00092   
  scale           experiment.linked_structures[lam7o3].scale            5.00e-6     3.596e-6  0.068e-6   28.1% ↓
  a, Å            structure.cell.length_a                                5.5000       5.4992    0.0011   
  b, Å            structure.cell.length_b                                7.7000       7.7337    0.0017   0.4% ↑
  c, Å            structure.cell.length_c                                5.5000       5.4619    0.0011   0.7% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

In `experiments/p021.edi`, add `()` after the values the stage frees:

```edi
2.0 2.0033379 300()
2.3 2.297792 300()
```

The same for every other row (18 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_lam7o3-p021, 1236 pts fitted / 1459 loaded, 25 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       33.68        77.50
      1      0.022     10.57         7.63   90.2% ↓
      2      0.030     10.53         7.58   0.6% ↓
      3      0.039     10.53         7.58   0.1% ↓
      4      0.046     10.53         7.58   
      5      0.054     10.53         7.57   
      6      0.061     10.53         7.57   
      7      0.068     10.53         7.57   
      8      0.076     10.53         7.57   
      9      0.083     10.53         7.57   
     10      0.091     10.53         7.57   
     11      0.099     10.52         7.57   
     12      0.107     10.52         7.57   
     13      0.114     10.52         7.57   
     14      0.122     10.52         7.57   
     15      0.135     10.52         7.57   
  done · converged · 15 iters · reduced χ² 7.57 · Rwp 10.52 % · 0.14 s

  refined parameters (25 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                       300        467.2       7.4   55.7% ↑
  intensity       experiment.background[11].intensity                       300        360.3       6.6   20.1% ↑
  intensity       experiment.background[12].intensity                       300        353.7       5.7   17.9% ↑
  intensity       experiment.background[14.7].intensity                     300        298.1       6.5   0.6% ↓
  intensity       experiment.background[15.0].intensity                     300          272        16   9.4% ↓
  intensity       experiment.background[2.0].intensity                      300          582        24   94.0% ↑
  intensity       experiment.background[2.3].intensity                      300          687        18   128.8% ↑
  intensity       experiment.background[2.7].intensity                      300          949        21   216.3% ↑
  intensity       experiment.background[2.9].intensity                      300          986        31   228.7% ↑
  intensity       experiment.background[3.0].intensity                      300      1.010e3   0.034e3   236.5% ↑
  intensity       experiment.background[3.1].intensity                      300          906        19   201.9% ↑
  intensity       experiment.background[3.7].intensity                      300          609        14   102.9% ↑
  intensity       experiment.background[4.1].intensity                      300          547        18   82.4% ↑
  intensity       experiment.background[4.3].intensity                      300          690        32   130.1% ↑
  intensity       experiment.background[4.4].intensity                      300          703        31   134.3% ↑
  intensity       experiment.background[4.5].intensity                      300          486        18   61.9% ↑
  intensity       experiment.background[4.9].intensity                      300          465        15   55.1% ↑
  intensity       experiment.background[5.1].intensity                      300        445.9       7.9   48.6% ↑
  intensity       experiment.background[7].intensity                        300        439.1       7.3   46.4% ↑
  intensity       experiment.background[8].intensity                        300        448.3       7.6   49.4% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0018      0.00133   0.00033   24.6% ↓
  scale           experiment.linked_structures[lam7o3].scale            3.60e-6     3.238e-6  0.023e-6   10.0% ↓
  a, Å            structure.cell.length_a                                5.4992      5.49643   0.00039   0.1% ↓
  b, Å            structure.cell.length_b                                7.7337      7.73508   0.00058   
  c, Å            structure.cell.length_c                                5.4619      5.46171   0.00038   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

The Gaussian widths and the Lorentzian X.

In `experiments/p021.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.04()
_peak.broad_gauss_v -0.01()
_peak.broad_gauss_w 0.001()
_peak.broad_lorentz_x 0.1()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_lam7o3-p021, 1236 pts fitted / 1459 loaded, 29 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       10.52         7.59
      1      0.021      7.07         3.43   54.9% ↓
      2      0.029      6.29         2.71   20.8% ↓
      3      0.036      6.04         2.50   7.8% ↓
      4      0.045      5.89         2.38   5.0% ↓
      5      0.053      5.77         2.29   3.9% ↓
      6      0.062      5.74         2.26   1.1% ↓
      7      0.086      5.57         2.13   5.9% ↓
      8      0.094      5.40         2.00   6.0% ↓
      9      0.102      5.20         1.86   7.3% ↓
     10      0.110      3.76         0.97   47.8% ↓
     11      0.118      3.60         0.89   8.2% ↓
     12      0.126      3.57         0.87   1.9% ↓
     13      0.134      3.56         0.87   0.3% ↓
     14      0.141      3.56         0.87   0.1% ↓
     15      0.149      3.56         0.87   0.1% ↓
     16      0.157      3.55         0.87   0.4% ↓
     17      0.165      3.54         0.86   1.0% ↓
     18      0.173      3.49         0.84   2.3% ↓
     19      0.180      3.43         0.81   3.6% ↓
     20      0.188      3.36         0.77   4.2% ↓
     21      0.196      3.24         0.72   6.8% ↓
     22      0.204      3.04         0.63   12.2% ↓
     23      0.212      2.85         0.56   12.1% ↓
     24      0.220      2.80         0.54   3.6% ↓
     25      0.228      2.79         0.53   0.2% ↓
     26      0.236      2.79         0.53   
     27      0.250      2.79         0.53   
  done · converged · 27 iters · reduced χ² 0.53 · Rwp 2.79 % · 0.26 s

  refined parameters (29 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     467.2        446.8       2.1   4.4% ↓
  intensity       experiment.background[11].intensity                     360.3        350.9       1.8   2.6% ↓
  intensity       experiment.background[12].intensity                     353.7        341.6       1.6   3.4% ↓
  intensity       experiment.background[14.7].intensity                   298.1        290.3       1.8   2.6% ↓
  intensity       experiment.background[15.0].intensity                     272        264.6       4.2   2.7% ↓
  intensity       experiment.background[2.0].intensity                      582        581.8       6.2   
  intensity       experiment.background[2.3].intensity                      687        686.7       4.7   
  intensity       experiment.background[2.7].intensity                      949        947.5       5.6   0.2% ↓
  intensity       experiment.background[2.9].intensity                      986        992.4       8.2   0.7% ↑
  intensity       experiment.background[3.0].intensity                   1.01e3        967.9       9.0   4.2% ↓
  intensity       experiment.background[3.1].intensity                      906        888.5       5.0   1.9% ↓
  intensity       experiment.background[3.7].intensity                      609        607.7       3.7   0.2% ↓
  intensity       experiment.background[4.1].intensity                      547        551.3       4.6   0.8% ↑
  intensity       experiment.background[4.3].intensity                      690        520.0       9.7   24.6% ↓
  intensity       experiment.background[4.4].intensity                      703        511.8       9.6   27.2% ↓
  intensity       experiment.background[4.5].intensity                      486        500.8       4.6   3.0% ↑
  intensity       experiment.background[4.9].intensity                      465        455.1       4.0   2.1% ↓
  intensity       experiment.background[5.1].intensity                    445.9        432.4       2.2   3.0% ↓
  intensity       experiment.background[7].intensity                      439.1        414.6       2.1   5.6% ↓
  intensity       experiment.background[8].intensity                      448.3        442.6       2.1   1.3% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0013      -6.7e-4    1.1e-4   150.3% ↓
  scale           experiment.linked_structures[lam7o3].scale            3.24e-6    3.6035e-6 0.0094e-6   11.3% ↑
  U, deg²         experiment.peak.broad_gauss_u                            0.04        0.067     0.014 ! 67.4% ↑
  V, deg²         experiment.peak.broad_gauss_v                           -0.01      -0.0098    0.0018 ! 1.8% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.001     0.001259  0.000049 ! 25.9% ↑
  X, deg          experiment.peak.broad_lorentz_x                           0.1       0.1736    0.0039   73.6% ↑
  a, Å            structure.cell.length_a                                5.4964      5.46218   0.00019   0.6% ↓
  b, Å            structure.cell.length_b                                7.7351      7.73307   0.00028   
  c, Å            structure.cell.length_c                                5.4617      5.49044   0.00018   0.5% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (p021) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with W (p021) (r = -0.98)
      experiment.peak.broad_gauss_w: strongly correlated with V (p021) (r = -0.98)
```

## Background from the fitted model

With a fitted peak model, estimate the background again with the calculated peaks subtracted,
which follows the low-angle background better, then free the new points and fit again.

In `experiments/p021.edi`, set:

```edi
_background_estimate.mode manual
_background_estimate.n_points 20
_background_estimate.use_model subtract
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_lam7o3-p021, 1236 pts fitted / 1459 loaded, 29 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        2.79         0.53
      1      0.021      2.79         0.53   
      2      0.035      2.79         0.53   
  done · converged · 2 iters · reduced χ² 0.53 · Rwp 2.79 % · 0.05 s

  refined parameters (29 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     446.8        446.8       2.1   
  intensity       experiment.background[11].intensity                     350.9        350.9       1.8   
  intensity       experiment.background[12].intensity                     341.6        341.6       1.6   
  intensity       experiment.background[14.7].intensity                   290.3        290.3       1.8   
  intensity       experiment.background[15.0].intensity                   264.6        264.5       4.2   
  intensity       experiment.background[2.0].intensity                    581.8        581.8       6.2   
  intensity       experiment.background[2.3].intensity                    686.7        686.7       4.7   
  intensity       experiment.background[2.7].intensity                    947.5        947.5       5.6   
  intensity       experiment.background[2.9].intensity                    992.4        992.4       8.2   
  intensity       experiment.background[3.0].intensity                    967.9        967.9       9.0   
  intensity       experiment.background[3.1].intensity                    888.5        888.5       5.0   
  intensity       experiment.background[3.7].intensity                    607.7        607.7       3.7   
  intensity       experiment.background[4.1].intensity                    551.3        551.3       4.6   
  intensity       experiment.background[4.3].intensity                      520        519.9       9.7   
  intensity       experiment.background[4.4].intensity                    511.8        511.8       9.6   
  intensity       experiment.background[4.5].intensity                    500.8        500.8       4.6   
  intensity       experiment.background[4.9].intensity                    455.1        455.1       4.0   
  intensity       experiment.background[5.1].intensity                    432.4        432.4       2.2   
  intensity       experiment.background[7].intensity                      414.6        414.6       2.1   
  intensity       experiment.background[8].intensity                      442.6        442.6       2.1   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset          -6.70e-4      -6.7e-4    1.1e-4   0.2% ↑
  scale           experiment.linked_structures[lam7o3].scale            3.60e-6    3.6036e-6 0.0094e-6   
  U, deg²         experiment.peak.broad_gauss_u                           0.067        0.067     0.014 ! 
  V, deg²         experiment.peak.broad_gauss_v                         -0.0098      -0.0098    0.0018 ! 0.3% ↓
  W, deg²         experiment.peak.broad_gauss_w                        0.001259     0.001259  0.000049 ! 
  X, deg          experiment.peak.broad_lorentz_x                        0.1736       0.1737    0.0039   
  a, Å            structure.cell.length_a                                5.4622      5.46218   0.00019   
  b, Å            structure.cell.length_b                                7.7331      7.73307   0.00028   
  c, Å            structure.cell.length_c                                5.4904      5.49044   0.00018   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (p021) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with W (p021) (r = -0.98)
      experiment.peak.broad_gauss_w: strongly correlated with V (p021) (r = -0.98)
```

## Atom positions

In `structures/lam7o3.edi`, add `()` after the values the stage frees:

```edi
La La 0.48() 0.25 0() c 4 1 0.5 Biso
O1 O 0.51() 0.25 0.57() c 4 1 0.5 Biso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_lam7o3-p021, 1236 pts fitted / 1459 loaded, 36 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        2.79         0.54
      1      0.022      1.90         0.25   54.0% ↓
      2      0.032      1.87         0.24   3.1% ↓
      3      0.041      1.87         0.24   
      4      0.050      1.86         0.24   0.1% ↓
      5      0.060      1.86         0.24   0.2% ↓
      6      0.069      1.86         0.24   0.5% ↓
      7      0.077      1.85         0.24   1.2% ↓
      8      0.086      1.83         0.23   2.4% ↓
      9      0.095      1.80         0.22   2.8% ↓
     10      0.104      1.79         0.22   1.7% ↓
     11      0.112      1.78         0.22   0.7% ↓
     12      0.121      1.78         0.22   0.2% ↓
     13      0.129      1.78         0.22   
     14      0.137      1.78         0.22   
     15      0.152      1.78         0.22   
  done · converged · 15 iters · reduced χ² 0.22 · Rwp 1.78 % · 0.16 s

  refined parameters (36 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     446.8        442.1       1.4   1.1% ↓
  intensity       experiment.background[11].intensity                     350.9        346.0       1.2   1.4% ↓
  intensity       experiment.background[12].intensity                     341.6       338.23      0.98   1.0% ↓
  intensity       experiment.background[14.7].intensity                   290.3        287.1       1.2   1.1% ↓
  intensity       experiment.background[15.0].intensity                   264.5        262.3       2.7   0.8% ↓
  intensity       experiment.background[2.0].intensity                    581.8        581.5       4.0   0.1% ↓
  intensity       experiment.background[2.3].intensity                    686.7        687.3       3.0   0.1% ↑
  intensity       experiment.background[2.7].intensity                    947.5        944.1       3.7   0.4% ↓
  intensity       experiment.background[2.9].intensity                    992.4        993.9       5.3   0.1% ↑
  intensity       experiment.background[3.0].intensity                    967.9        965.6       5.7   0.2% ↓
  intensity       experiment.background[3.1].intensity                    888.5        882.5       3.2   0.7% ↓
  intensity       experiment.background[3.7].intensity                    607.7        606.0       2.4   0.3% ↓
  intensity       experiment.background[4.1].intensity                    551.3        552.7       3.0   0.3% ↑
  intensity       experiment.background[4.3].intensity                    519.9        512.4       6.2   1.4% ↓
  intensity       experiment.background[4.4].intensity                    511.8        510.9       6.2   0.2% ↓
  intensity       experiment.background[4.5].intensity                    500.8        488.9       3.1   2.4% ↓
  intensity       experiment.background[4.9].intensity                    455.1        454.8       2.6   0.1% ↓
  intensity       experiment.background[5.1].intensity                    432.4        428.5       1.4   0.9% ↓
  intensity       experiment.background[7].intensity                      414.6        409.0       1.4   1.3% ↓
  intensity       experiment.background[8].intensity                      442.6        438.8       1.4   0.9% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset          -6.70e-4     -6.54e-4   0.68e-4   2.4% ↑
  scale           experiment.linked_structures[lam7o3].scale            3.60e-6    3.6699e-6 0.0064e-6   1.8% ↑
  U, deg²         experiment.peak.broad_gauss_u                           0.067       0.0603    0.0086 ! 9.9% ↓
  V, deg²         experiment.peak.broad_gauss_v                         -0.0098      -0.0087    0.0012 ! 11.6% ↑
  W, deg²         experiment.peak.broad_gauss_w                        0.001259     0.001237  0.000032 ! 1.8% ↓
  X, deg          experiment.peak.broad_lorentz_x                        0.1737       0.1720    0.0025   1.0% ↓
  x               structure.atom_sites[La].fract_x                      0.48000     0.476610  0.000085   0.7% ↓
  z               structure.atom_sites[La].fract_z                      0.00000      0.00569   0.00023   
  x               structure.atom_sites[O1].fract_x                      0.51000       0.5077    0.0011   0.4% ↓
  z               structure.atom_sites[O1].fract_z                      0.57000       0.5670    0.0018   0.5% ↓
  x               structure.atom_sites[O2].fract_x                      0.22000       0.2228    0.0016   1.3% ↑
  y               structure.atom_sites[O2].fract_y                      0.03000       0.0334    0.0011   11.5% ↑
  z               structure.atom_sites[O2].fract_z                      0.27000       0.2780    0.0015   3.0% ↑
  a, Å            structure.cell.length_a                                5.4622      5.46221   0.00012   
  b, Å            structure.cell.length_b                                7.7331      7.73308   0.00018   
  c, Å            structure.cell.length_c                                5.4904      5.49028   0.00012   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (p021) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with W (p021) (r = -0.98)
      experiment.peak.broad_gauss_w: strongly correlated with V (p021) (r = -0.98)
```

## Displacements

La's, the mixed site's (through Ti) and O1's; O2's follows O1's.

In `structures/lam7o3.edi`, add `()` after the values the stage frees:

```edi
La La 0.476610() 0.25 0.00569() c 4 1 0.5() Biso
Ti Ti 0 0 0 a 4 0.14286 0.5() Biso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_lam7o3-p021 --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_lam7o3-p021, 1236 pts fitted / 1459 loaded, 39 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        1.78         0.22
      1      0.026      1.70         0.20   8.0% ↓
      2      0.036      1.69         0.20   2.2% ↓
      3      0.046      1.68         0.20   0.4% ↓
      4      0.056      1.68         0.19   0.3% ↓
      5      0.066      1.68         0.19   0.2% ↓
      6      0.075      1.68         0.19   0.2% ↓
      7      0.085      1.67         0.19   0.5% ↓
      8      0.095      1.66         0.19   1.0% ↓
      9      0.106      1.65         0.19   1.3% ↓
     10      0.116      1.65         0.19   0.8% ↓
     11      0.125      1.64         0.19   0.2% ↓
     12      0.135      1.64         0.19   
     13      0.145      1.64         0.19   
     14      0.154      1.64         0.19   
     15      0.171      1.64         0.19   
  done · converged · 15 iters · reduced χ² 0.19 · Rwp 1.64 % · 0.18 s

  refined parameters (39 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     442.1        446.5       1.3   1.0% ↑
  intensity       experiment.background[11].intensity                       346        349.0       1.2   0.9% ↑
  intensity       experiment.background[12].intensity                    338.23       342.72      0.99   1.3% ↑
  intensity       experiment.background[14.7].intensity                   287.1        291.4       1.2   1.5% ↑
  intensity       experiment.background[15.0].intensity                   262.3        262.6       2.5   0.1% ↑
  intensity       experiment.background[2.0].intensity                    581.5        581.6       3.7   
  intensity       experiment.background[2.3].intensity                    687.3        687.1       2.8   
  intensity       experiment.background[2.7].intensity                    944.1        945.5       3.4   0.1% ↑
  intensity       experiment.background[2.9].intensity                    993.9        993.4       4.9   0.1% ↓
  intensity       experiment.background[3.0].intensity                    965.6        966.7       5.3   0.1% ↑
  intensity       experiment.background[3.1].intensity                    882.5        883.3       3.0   0.1% ↑
  intensity       experiment.background[3.7].intensity                      606        606.0       2.2   
  intensity       experiment.background[4.1].intensity                    552.7        553.2       2.7   0.1% ↑
  intensity       experiment.background[4.3].intensity                    512.4        516.5       5.8   0.8% ↑
  intensity       experiment.background[4.4].intensity                    510.9        514.4       5.8   0.7% ↑
  intensity       experiment.background[4.5].intensity                    488.9        490.3       2.8   0.3% ↑
  intensity       experiment.background[4.9].intensity                    454.8        454.9       2.4   
  intensity       experiment.background[5.1].intensity                    428.5        429.2       1.3   0.2% ↑
  intensity       experiment.background[7].intensity                        409        411.6       1.3   0.6% ↑
  intensity       experiment.background[8].intensity                      438.8        439.7       1.3   0.2% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset          -6.54e-4     -6.96e-4   0.63e-4   6.4% ↓
  scale           experiment.linked_structures[lam7o3].scale            3.67e-6    3.6857e-6 0.0070e-6   0.4% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.0603       0.0483    0.0081 ! 19.9% ↓
  V, deg²         experiment.peak.broad_gauss_v                         -0.0087      -0.0073    0.0011 ! 15.9% ↑
  W, deg²         experiment.peak.broad_gauss_w                        0.001237     0.001216  0.000029 ! 1.7% ↓
  X, deg          experiment.peak.broad_lorentz_x                         0.172       0.1667    0.0024   3.1% ↓
  B iso, Å²       structure.atom_sites[La].adp_iso                        0.500        0.606     0.010   21.1% ↑
  x               structure.atom_sites[La].fract_x                      0.47661     0.476785  0.000084   
  z               structure.atom_sites[La].fract_z                      0.00569      0.00428   0.00031   24.9% ↓
  B iso, Å²       structure.atom_sites[O1].adp_iso                        0.500        0.312     0.068   37.7% ↓
  x               structure.atom_sites[O1].fract_x                      0.50770       0.5078    0.0011   
  z               structure.atom_sites[O1].fract_z                      0.56700       0.5692    0.0017   0.4% ↑
  x               structure.atom_sites[O2].fract_x                      0.22280       0.2240    0.0015   0.5% ↑
  y               structure.atom_sites[O2].fract_y                      0.03340      0.03515   0.00094   5.2% ↑
  z               structure.atom_sites[O2].fract_z                      0.27800       0.2765    0.0014   0.5% ↓
  B iso, Å²       structure.atom_sites[Ti].adp_iso                        0.500        0.389     0.014   22.3% ↓
  a, Å            structure.cell.length_a                                5.4622      5.46218   0.00011   
  b, Å            structure.cell.length_b                                7.7331      7.73302   0.00017   
  c, Å            structure.cell.length_c                                5.4903      5.49022   0.00011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (p021) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with W (p021) (r = -0.98)
      experiment.peak.broad_gauss_w: strongly correlated with V (p021) (r = -0.98)
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-xray-cwl_lam7o3-p021 --output pd-xray-cwl_lam7o3-p021.html
    ```
