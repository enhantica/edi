# Rietveld fit: PbSO₄, laboratory X-ray

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-xray-cwl_pbso4-lab
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-xray-cwl_pbso4-lab
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/lab.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_twotheta_offset 0
_peak.broad_gauss_u 0.02
_peak.broad_gauss_v -0.02
_peak.broad_gauss_w 0.008
_peak.mixing_eta_0 0.5
_peak.asym_beba_a0 0
_peak.asym_beba_b0 0
1 0 140
2 1 0
```

The same for every other row (5 more).

In `structures/pbso4.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 8.47
_cell.length_b 5.39
_cell.length_c 6.95
Pb Pb 0.19 0.25 0.17 c 4 1 0.5 Biso
S S 0.07 0.25 0.68 c 4 1 0.5 Biso
```

The same for every other row (3 more).

## Scale and 2θ zero

The 2θ zero first: freed together with the cell from the start, the two pull against each
other and the fit cannot take a step.

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
pbso4 0.001() 1.0
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 2 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                      114.69       551.55
      1      0.017     58.28       142.41   74.2% ↓
      2      0.029     56.65       134.57   5.5% ↓
      3      0.040     54.94       126.54   6.0% ↓
      4      0.051     53.17       118.53   6.3% ↓
      5      0.061     51.27       110.21   7.0% ↓
      6      0.071     49.26       101.76   7.7% ↓
      7      0.081     47.28        93.73   7.9% ↓
      8      0.092     45.50        86.81   7.4% ↓
      9      0.103     44.08        81.48   6.1% ↓
     10      0.114     43.08        77.81   4.5% ↓
     11      0.125     42.43        75.49   3.0% ↓
     12      0.135     42.04        74.09   1.9% ↓
     13      0.145     41.80        73.27   1.1% ↓
     14      0.156     41.67        72.80   0.6% ↓
     15      0.167     41.59        72.54   0.4% ↓
     16      0.178     41.55        72.39   0.2% ↓
     17      0.187     41.53        72.31   0.1% ↓
     18      0.197     41.52        72.27   0.1% ↓
     19      0.206     41.51        72.25   
     20      0.216     41.51        72.23   
     21      0.226     41.50        72.23   
     22      0.236     41.50        72.22   
     23      0.247     41.50        72.22   
     24      0.257     41.50        72.22   
     25      0.267     41.50        72.22   
     26      0.277     41.50        72.22   
     27      0.300     41.50        72.22   
  done · converged · 27 iters · reduced χ² 72.22 · Rwp 41.50 % · 0.31 s

  refined parameters (2 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0000     -0.10598   0.00045   
  scale           experiment.linked_structures[pbso4].scale               0.001     5.549e-4  0.051e-4   44.5% ↓

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Cell

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 8.47()
_cell.length_b 5.39()
_cell.length_c 6.95()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 5 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       41.50        72.26
      1      0.034     39.32        64.85   10.3% ↓
      2      0.051     36.89        57.10   11.9% ↓
      3      0.068     34.51        49.96   12.5% ↓
      4      0.087     32.61        44.61   10.7% ↓
      5      0.104     31.42        41.42   7.1% ↓
      6      0.121     30.72        39.60   4.4% ↓
      7      0.187     30.68        39.48   0.3% ↓
      8      0.205     30.48        38.97   1.3% ↓
      9      0.220     30.45        38.90   0.2% ↓
     10      0.246     30.42        38.81   0.2% ↓
     11      0.267     30.38        38.72   0.2% ↓
     12      0.282     30.35        38.64   0.2% ↓
     13      0.299     30.32        38.57   0.2% ↓
     14      0.316     30.30        38.51   0.2% ↓
     15      0.331     30.27        38.45   0.2% ↓
     16      0.345     30.25        38.38   0.2% ↓
     17      0.360     30.22        38.32   0.2% ↓
     18      0.375     30.21        38.28   0.1% ↓
     19      0.390     30.20        38.25   0.1% ↓
     20      0.405     30.19        38.23   0.1% ↓
     21      0.423     30.18        38.20   0.1% ↓
     22      0.443     30.16        38.16   0.1% ↓
     23      0.459     30.14        38.11   0.1% ↓
     24      0.474     30.12        38.05   0.1% ↓
     25      0.490     30.10        38.01   0.1% ↓
     26      0.506     30.09        37.98   0.1% ↓
     27      0.522     30.08        37.97   
     28      0.536     30.08        37.96   
     29      0.551     30.08        37.96   
     30      0.567     30.08        37.96   
     31      0.582     30.08        37.95   
     32      0.596     30.08        37.95   
     33      0.623     30.08        37.95   
  done · converged · 33 iters · reduced χ² 37.95 · Rwp 30.08 % · 0.64 s

  refined parameters (5 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.1060     -0.04475   0.00042   57.8% ↑
  scale           experiment.linked_structures[pbso4].scale             5.55e-4     6.419e-4  0.041e-4   15.7% ↑
  a, Å            structure.cell.length_a                                8.4700     8.479623  0.000051   0.1% ↑
  b, Å            structure.cell.length_b                                5.3900     5.398587  0.000078   0.2% ↑
  c, Å            structure.cell.length_c                                6.9500     6.959133  0.000090   0.1% ↑

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

The six Chebyshev terms.

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
1 0 140()
2 1 0()
```

The same for every other row (4 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 11 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       30.08        38.00
      1      0.041     29.27        35.97   5.3% ↓
      2      0.058     29.27        35.97   
      3      0.073     29.27        35.97   
      4      0.097     29.26        35.96   
      5      0.117     29.26        35.96   
      6      0.137     29.26        35.96   
      7      0.157     29.26        35.96   
      8      0.173     29.26        35.95   
      9      0.192     29.25        35.92   0.1% ↓
     10      0.208     29.19        35.79   0.4% ↓
     11      0.222     29.16        35.71   0.2% ↓
     12      0.237     29.15        35.69   0.1% ↓
     13      0.252     29.15        35.68   
     14      0.268     29.15        35.68   
     15      0.284     29.15        35.68   
     16      0.298     29.15        35.68   
     17      0.325     29.15        35.68   
  done · converged · 17 iters · reduced χ² 35.68 · Rwp 29.15 % · 0.34 s

  refined parameters (11 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                             140        156.6       1.6   11.9% ↑
  coefficient     experiment.background[2].coef                               0         31.1       2.5   
  coefficient     experiment.background[3].coef                               0          2.6       2.3   
  coefficient     experiment.background[4].coef                               0         22.6       2.2   
  coefficient     experiment.background[5].coef                               0        -15.4       2.0   
  coefficient     experiment.background[6].coef                               0         -2.8       2.0   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0447     -0.04031   0.00064   9.9% ↑
  scale           experiment.linked_structures[pbso4].scale             6.42e-4     6.340e-4  0.042e-4   1.2% ↓
  a, Å            structure.cell.length_a                                8.4796      8.48076   0.00013   
  b, Å            structure.cell.length_b                                5.3986     5.398772  0.000080   
  c, Å            structure.cell.length_c                                6.9591      6.95971   0.00011   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.02()
_peak.broad_gauss_v -0.02()
_peak.broad_gauss_w 0.008()
_peak.mixing_eta_0 0.5()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 15 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       29.15        35.71
      1      0.043     17.53        12.92   63.8% ↓
      2      0.063     14.02         8.26   36.1% ↓
      3      0.082     13.51         7.67   7.2% ↓
      4      0.104     13.46         7.62   0.7% ↓
      5      0.123     13.46         7.62   
      6      0.143     13.46         7.62   
      7      0.163     13.46         7.62   
      8      0.194     13.46         7.62   
  done · converged · 8 iters · reduced χ² 7.62 · Rwp 13.46 % · 0.22 s

  refined parameters (15 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                           156.6       111.67      0.98   28.7% ↓
  coefficient     experiment.background[2].coef                            31.1         30.5       1.4   2.0% ↓
  coefficient     experiment.background[3].coef                             2.6         13.2       1.2   408.6% ↑
  coefficient     experiment.background[4].coef                            22.6         10.2       1.1   55.0% ↓
  coefficient     experiment.background[5].coef                           -15.4        -7.18      0.92   53.4% ↑
  coefficient     experiment.background[6].coef                            -2.8        -6.72      0.90   140.1% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0403     -0.04573   0.00048   13.5% ↓
  scale           experiment.linked_structures[pbso4].scale             6.34e-4     8.503e-4  0.026e-4   34.1% ↑
  U, deg²         experiment.peak.broad_gauss_u                            0.02       0.0484    0.0020   141.8% ↑
  V, deg²         experiment.peak.broad_gauss_v                           -0.02      -0.0215    0.0020   7.7% ↓
  W, deg²         experiment.peak.broad_gauss_w                           0.008      0.01047   0.00046   30.9% ↑
  Eta0            experiment.peak.mixing_eta_0                              0.5        0.827     0.011   65.3% ↑
  a, Å            structure.cell.length_a                                8.4808      8.47968   0.00013   
  b, Å            structure.cell.length_b                                5.3988     5.398177  0.000084   
  c, Å            structure.cell.length_c                                6.9597      6.95956   0.00011   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak asymmetry

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
_peak.asym_beba_a0 0()
_peak.asym_beba_b0 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 17 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.46         7.62
      1      0.050     12.84         6.93   9.0% ↓
      2      0.071     12.76         6.85   1.3% ↓
      3      0.094     12.76         6.84   0.1% ↓
      4      0.118     12.76         6.84   
      5      0.139     12.76         6.84   
      6      0.158     12.76         6.84   
      7      0.179     12.76         6.84   
      8      0.200     12.76         6.84   
      9      0.237     12.76         6.84   
  done · converged · 9 iters · reduced χ² 6.84 · Rwp 12.76 % · 0.26 s

  refined parameters (17 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                          111.67       112.16      0.77   0.4% ↑
  coefficient     experiment.background[2].coef                            30.5         31.7       1.1   4.0% ↑
  coefficient     experiment.background[3].coef                            13.2         13.9       1.0   5.4% ↑
  coefficient     experiment.background[4].coef                            10.2        11.18      0.97   9.6% ↑
  coefficient     experiment.background[5].coef                           -7.18        -6.90      0.87   3.9% ↑
  coefficient     experiment.background[6].coef                           -6.72        -6.82      0.85   1.5% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0457      -0.0324    0.0012   29.2% ↑
  scale           experiment.linked_structures[pbso4].scale             8.50e-4     8.533e-4  0.025e-4   0.4% ↑
  A₀              experiment.peak.asym_beba_a0                                0      -0.2155    0.0087   
  B₀              experiment.peak.asym_beba_b0                                0      -0.0344    0.0015   
  U, deg²         experiment.peak.broad_gauss_u                          0.0484       0.0555    0.0020   14.7% ↑
  V, deg²         experiment.peak.broad_gauss_v                         -0.0215      -0.0307    0.0020   43.0% ↓
  W, deg²         experiment.peak.broad_gauss_w                         0.01047      0.01282   0.00046   22.4% ↑
  Eta0            experiment.peak.mixing_eta_0                            0.827        0.820     0.010   0.8% ↓
  a, Å            structure.cell.length_a                                8.4797      8.48072   0.00014   
  b, Å            structure.cell.length_b                                5.3982     5.398856  0.000090   
  c, Å            structure.cell.length_c                                6.9596      6.96041   0.00012   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Lead and sulphur positions

X-rays see the heavy atoms first, so their coordinates come before the oxygens'.

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
Pb Pb 0.19() 0.25 0.17() c 4 1 0.5 Biso
S S 0.07() 0.25 0.68() c 4 1 0.5 Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 21 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       12.76         6.85
      1      0.056     11.94         6.00   12.3% ↓
      2      0.080     11.93         5.99   0.2% ↓
      3      0.105     11.93         5.99   
      4      0.151     11.93         5.99   
  done · converged · 4 iters · reduced χ² 5.99 · Rwp 11.93 % · 0.18 s

  refined parameters (21 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                          112.16       113.26      0.72   1.0% ↑
  coefficient     experiment.background[2].coef                            31.7         35.9       1.1   13.2% ↑
  coefficient     experiment.background[3].coef                            13.9        16.99      0.95   22.2% ↑
  coefficient     experiment.background[4].coef                           11.18        14.62      0.92   30.7% ↑
  coefficient     experiment.background[5].coef                            -6.9        -5.41      0.82   21.6% ↑
  coefficient     experiment.background[6].coef                           -6.82        -5.27      0.80   22.7% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0324      -0.0324    0.0011   
  scale           experiment.linked_structures[pbso4].scale             8.53e-4     8.576e-4  0.023e-4   0.5% ↑
  A₀              experiment.peak.asym_beba_a0                          -0.2155      -0.2056    0.0081   4.6% ↑
  B₀              experiment.peak.asym_beba_b0                          -0.0344      -0.0328    0.0013   4.7% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.0555       0.0566    0.0019   1.9% ↑
  V, deg²         experiment.peak.broad_gauss_v                         -0.0307      -0.0317    0.0018   3.4% ↓
  W, deg²         experiment.peak.broad_gauss_w                         0.01282      0.01293   0.00044   0.8% ↑
  Eta0            experiment.peak.mixing_eta_0                             0.82       0.8286    0.0093   1.0% ↑
  x               structure.atom_sites[Pb].fract_x                      0.19000     0.187750  0.000098   1.2% ↓
  z               structure.atom_sites[Pb].fract_z                      0.17000      0.16779   0.00013   1.3% ↓
  x               structure.atom_sites[S].fract_x                       0.07000      0.06528   0.00056   6.7% ↓
  z               structure.atom_sites[S].fract_z                       0.68000      0.68668   0.00075   1.0% ↑
  a, Å            structure.cell.length_a                                8.4807      8.48070   0.00013   
  b, Å            structure.cell.length_b                                5.3989     5.398877  0.000084   
  c, Å            structure.cell.length_c                                6.9604      6.96043   0.00011   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Oxygen positions

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
O1 O 0.91() 0.25 0.6() c 4 1 0.5 Biso
O2 O 0.19() 0.25 0.54() c 4 1 0.5 Biso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 28 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.93         6.00
      1      0.060     11.83         5.90   1.7% ↓
      2      0.096     11.83         5.90   0.1% ↓
      3      0.128     11.83         5.90   
      4      0.159     11.83         5.90   
      5      0.203     11.83         5.90   
  done · converged · 5 iters · reduced χ² 5.90 · Rwp 11.83 % · 0.23 s

  refined parameters (28 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                          113.26       112.46      0.73   0.7% ↓
  coefficient     experiment.background[2].coef                            35.9         35.5       1.1   1.2% ↓
  coefficient     experiment.background[3].coef                           16.99        16.98      0.95   0.1% ↓
  coefficient     experiment.background[4].coef                           14.62        14.04      0.92   4.0% ↓
  coefficient     experiment.background[5].coef                           -5.41        -5.43      0.82   0.4% ↓
  coefficient     experiment.background[6].coef                           -5.27        -5.37      0.80   1.9% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0324      -0.0327    0.0011   0.9% ↓
  scale           experiment.linked_structures[pbso4].scale             8.58e-4     8.600e-4  0.023e-4   0.3% ↑
  A₀              experiment.peak.asym_beba_a0                          -0.2056      -0.2020    0.0081   1.8% ↑
  B₀              experiment.peak.asym_beba_b0                          -0.0328      -0.0323    0.0013   1.4% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.0566       0.0560    0.0019   1.0% ↓
  V, deg²         experiment.peak.broad_gauss_v                         -0.0317      -0.0313    0.0018   1.2% ↑
  W, deg²         experiment.peak.broad_gauss_w                         0.01293      0.01288   0.00043   0.4% ↓
  Eta0            experiment.peak.mixing_eta_0                           0.8286       0.8283    0.0093   
  x               structure.atom_sites[O1].fract_x                      0.91000       0.9062    0.0014   0.4% ↓
  z               structure.atom_sites[O1].fract_z                      0.60000       0.5928    0.0016   1.2% ↓
  x               structure.atom_sites[O2].fract_x                      0.19000       0.1821    0.0016   4.1% ↓
  z               structure.atom_sites[O2].fract_z                      0.54000       0.5530    0.0018   2.4% ↑
  x               structure.atom_sites[O3].fract_x                      0.08000      0.07792   0.00092   2.6% ↓
  y               structure.atom_sites[O3].fract_y                      0.03000       0.0240    0.0014   20.1% ↓
  z               structure.atom_sites[O3].fract_z                      0.81000       0.8141    0.0014   0.5% ↑
  x               structure.atom_sites[Pb].fract_x                      0.18775     0.187854  0.000099   0.1% ↑
  z               structure.atom_sites[Pb].fract_z                      0.16779      0.16791   0.00013   0.1% ↑
  x               structure.atom_sites[S].fract_x                       0.06528      0.06391   0.00059   2.1% ↓
  z               structure.atom_sites[S].fract_z                       0.68668      0.68660   0.00076   
  a, Å            structure.cell.length_a                                8.4807      8.48066   0.00013   
  b, Å            structure.cell.length_b                                5.3989     5.398869  0.000083   
  c, Å            structure.cell.length_c                                6.9604      6.96038   0.00011   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Displacements

The correlations after this stage show how far the oxygen displacements can be told apart; the
case keeps them separate.

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
Pb Pb 0.187854() 0.25 0.16791() c 4 1 0.5() Biso
S S 0.06391() 0.25 0.68660() c 4 1 0.5() Biso
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 33 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.83         5.90
      1      0.062      8.96         3.38   42.6% ↓
      2      0.089      8.41         2.98   12.0% ↓
      3      0.113      8.40         2.98   0.1% ↓
      4      0.133      8.40         2.98   
      5      0.195      8.40         2.98   
  done · converged · 5 iters · reduced χ² 2.98 · Rwp 8.40 % · 0.22 s

  refined parameters (33 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                          112.46       148.82      0.63   32.3% ↑
  coefficient     experiment.background[2].coef                            35.5        78.71      0.86   121.7% ↑
  coefficient     experiment.background[3].coef                           16.98        12.06      0.67   29.0% ↓
  coefficient     experiment.background[4].coef                           14.04         4.48      0.66   68.1% ↓
  coefficient     experiment.background[5].coef                           -5.43        -6.13      0.58   13.0% ↓
  coefficient     experiment.background[6].coef                           -5.37       -12.30      0.58   129.0% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0327     -0.03246   0.00084   0.7% ↑
  scale           experiment.linked_structures[pbso4].scale             8.60e-4     9.810e-4  0.025e-4   14.1% ↑
  A₀              experiment.peak.asym_beba_a0                           -0.202      -0.2063    0.0059   2.1% ↓
  B₀              experiment.peak.asym_beba_b0                          -0.0323     -0.03230   0.00088   
  U, deg²         experiment.peak.broad_gauss_u                           0.056      0.02036   0.00088   63.6% ↓
  V, deg²         experiment.peak.broad_gauss_v                         -0.0313      -0.0100    0.0011   68.1% ↑
  W, deg²         experiment.peak.broad_gauss_w                         0.01288      0.01222   0.00029   5.1% ↓
  Eta0            experiment.peak.mixing_eta_0                           0.8283       0.7103    0.0061   14.2% ↓
  B iso, Å²       structure.atom_sites[O1].adp_iso                        0.500         1.04      0.21   107.0% ↑
  x               structure.atom_sites[O1].fract_x                      0.90620      0.90756   0.00098   0.1% ↑
  z               structure.atom_sites[O1].fract_z                      0.59280       0.5948    0.0012   0.3% ↑
  B iso, Å²       structure.atom_sites[O2].adp_iso                        0.500         1.42      0.21   184.1% ↑
  x               structure.atom_sites[O2].fract_x                      0.18210       0.1866    0.0012   2.5% ↑
  z               structure.atom_sites[O2].fract_z                      0.55300       0.5382    0.0015   2.7% ↓
  B iso, Å²       structure.atom_sites[O3].adp_iso                        0.500         1.28      0.14   156.1% ↑
  x               structure.atom_sites[O3].fract_x                      0.07792      0.07822   0.00067   0.4% ↑
  y               structure.atom_sites[O3].fract_y                      0.02400      0.02559   0.00094   6.6% ↑
  z               structure.atom_sites[O3].fract_z                      0.81410      0.81447   0.00099   
  B iso, Å²       structure.atom_sites[Pb].adp_iso                        0.500        1.605     0.017   221.1% ↑
  x               structure.atom_sites[Pb].fract_x                      0.18785     0.187933  0.000076   
  z               structure.atom_sites[Pb].fract_z                      0.16791      0.16739   0.00012   0.3% ↓
  B iso, Å²       structure.atom_sites[S].adp_iso                         0.500        1.026     0.078   105.2% ↑
  x               structure.atom_sites[S].fract_x                       0.06391      0.06369   0.00044   0.3% ↓
  z               structure.atom_sites[S].fract_z                       0.68660      0.68360   0.00059   0.4% ↓
  a, Å            structure.cell.length_a                                8.4807     8.480763  0.000089   
  b, Å            structure.cell.length_b                                5.3989     5.398867  0.000059   
  c, Å            structure.cell.length_c                                6.9604     6.960385  0.000076   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-xray-cwl_pbso4-lab --output pd-xray-cwl_pbso4-lab.html
    ```
