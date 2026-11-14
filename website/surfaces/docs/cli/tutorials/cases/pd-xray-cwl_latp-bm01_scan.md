# Sequential fit: LATP, BM01

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit three phases, LATP and two AlPO₄ forms, to 73 synchrotron X-ray patterns from BM01 at ESRF,
one after another, with linked displacement parameters.

The project is the catalogue case `pd-xray-cwl_latp-bm01_scan`, the one the command line and the
app's Examples open. Al shares Ti's site, coordinate and displacement, and the impurity phase's
displacements are shared, from the start.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-xray-cwl_latp-bm01_scan
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-xray-cwl_latp-bm01_scan
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/bm01.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_twotheta_offset -0.0388
_peak.broad_gauss_u 0.019
_peak.broad_gauss_v 0.019
_peak.broad_gauss_w 0.0156
_peak.mixing_eta_0 0.374
_peak.asym_beba_a0 0.088
_peak.asym_beba_b0 0.0043
4 4.0117 37000000
5 5.3148 41700000
```

The same for every other row (28 more).

In `structures/alpo4_c2221.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 6.97
_cell.length_b 7.11
_cell.length_c 7.004
```

In `structures/alpo4_p63mc.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 4.983
_cell.length_c 9.504
```

In `structures/latp.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 8.4953
_cell.length_c 20.8268
Ti1 Ti 0 0 0.14184 c 12 0.85 0.33 Biso
P1 P 0.2877 0 0.25 e 18 1 0.23 Biso
```

The same for every other row (2 more).

## Scales, 2θ zero and cells

Switch the fitting mode to a single fit, so the stages fit the template alone. The three phases' scales and cells and the zero shift.

In `analysis/analysis.edi`, set:

```edi
_fitting_mode.type single
```

In `experiments/bm01.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset -0.0388()
latp 4.15() 0.986411827549678()
alpo4_c2221 0.54() 0.007257470839458675()
```

The same for every other row (1 more).

In `structures/alpo4_c2221.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 6.97()
_cell.length_b 7.11()
_cell.length_c 7.004()
```

In `structures/alpo4_p63mc.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 4.983()
_cell.length_c 9.504()
```

In `structures/latp.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 8.4953()
_cell.length_c 20.8268()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_latp-bm01_scan, 3114 pts fitted / 3163 loaded, 11 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.51 140198364.17
      1      0.575      4.51 140107944.41   0.1% ↓
      2      0.657      4.51 140107929.77   
  done · converged · 2 iters · reduced χ² 140107929.77 · Rwp 4.51 % · 0.71 s

  refined parameters (11 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0388      -0.0387    0.0005   0.2% ↑
  scale           experiment.linked_structures[alpo4_c2221].scale          0.54         0.55      0.11   1.4% ↑
  scale           experiment.linked_structures[alpo4_p63mc].scale           1.6          1.6       0.4   0.7% ↑
  scale           experiment.linked_structures[latp].scale                 4.15        4.140     0.012   0.2% ↓
  a, Å            structures[alpo4_c2221].cell.length_a                  6.9700         6.97      0.02   
  b, Å            structures[alpo4_c2221].cell.length_b                  7.1100         7.11      0.02   
  c, Å            structures[alpo4_c2221].cell.length_c                  7.0040        7.003     0.019   
  a, Å            structures[alpo4_p63mc].cell.length_a                  4.9830        4.983     0.007   
  c, Å            structures[alpo4_p63mc].cell.length_c                  9.5040        9.504     0.018   
  a, Å            structures[latp].cell.length_a                         8.4953      8.49522   0.00017   
  c, Å            structures[latp].cell.length_c                        20.8268      20.8270    0.0008   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

In `experiments/bm01.edi`, add `()` after the values the stage frees:

```edi
4 4.0117 37000000()
5 5.3148 41700000()
```

The same for every other row (28 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_latp-bm01_scan, 3114 pts fitted / 3163 loaded, 41 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.51 141478227.17
      1      0.884      4.51 141465283.67   
  done · converged · 1 iters · reduced χ² 141465283.67 · Rwp 4.51 % · 0.93 s

  refined parameters (41 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    7.98e7  7.9900000e70.1000000e7   0.1% ↑
  intensity       experiment.background[12].intensity                    4.82e7  4.8200000e70.0700000e7   
  intensity       experiment.background[14].intensity                    3.71e7  3.7200000e70.0700000e7   0.2% ↑
  intensity       experiment.background[16].intensity                    3.07e7  3.0700000e70.0600000e7   
  intensity       experiment.background[18].intensity                    2.61e7  2.6100000e70.0400000e7   0.1% ↓
  intensity       experiment.background[20].intensity                    2.43e7  2.4400000e70.0400000e7   0.2% ↑
  intensity       experiment.background[23].intensity                    2.29e7  2.2900000e70.0400000e7   0.1% ↓
  intensity       experiment.background[25].intensity                    2.27e7  2.2800000e70.0400000e7   0.4% ↑
  intensity       experiment.background[27].intensity                    2.51e7  2.5100000e70.0400000e7   
  intensity       experiment.background[30].intensity                    2.44e7  2.4400000e70.0300000e7   0.2% ↑
  intensity       experiment.background[33].intensity                    2.59e7  2.5900000e70.0300000e7   0.1% ↑
  intensity       experiment.background[36].intensity                    1.93e7  1.9300000e70.0170000e7   0.1% ↑
  intensity       experiment.background[38].intensity                    1.59e7  1.5970000e70.0150000e7   0.1% ↑
  intensity       experiment.background[40].intensity                    1.66e7  1.6600000e70.0140000e7   0.1% ↑
  intensity       experiment.background[43].intensity                    1.89e7  1.8860000e70.0150000e7   0.1% ↑
  intensity       experiment.background[45].intensity                    1.81e7  1.8080000e70.0140000e7   
  intensity       experiment.background[47].intensity                    1.79e7  1.7900000e70.0130000e7   
  intensity       experiment.background[49].intensity                    1.95e7  1.9490000e70.0130000e7   0.1% ↑
  intensity       experiment.background[4].intensity                     3.70e7  3.7000000e70.3000000e7   
  intensity       experiment.background[51].intensity                    2.04e7  2.0370000e70.0120000e7   
  intensity       experiment.background[53].intensity                    2.19e7  2.1930000e70.0110000e7   
  intensity       experiment.background[55].intensity                    2.24e7  2.2390000e70.0100000e7   
  intensity       experiment.background[57].intensity                    2.18e7  2.1840000e70.0100000e7   
  intensity       experiment.background[59].intensity                    2.38e7  2.3840000e70.0080000e7   
  intensity       experiment.background[5].intensity                     4.17e7  4.1700000e70.1100000e7   
  intensity       experiment.background[61].intensity                    1.90e7  1.8960000e70.0090000e7   
  intensity       experiment.background[62].intensity                    1.55e7  1.5500000e70.0300000e7   
  intensity       experiment.background[7].intensity                     5.27e7  5.2800000e70.1100000e7   0.1% ↑
  intensity       experiment.background[8].intensity                     6.72e7  6.7200000e70.1300000e7   
  intensity       experiment.background[9].intensity                     8.27e7  8.2700000e70.1500000e7   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0387      -0.0387    0.0005   
  scale           experiment.linked_structures[alpo4_c2221].scale          0.55         0.53      0.12   3.0% ↓
  scale           experiment.linked_structures[alpo4_p63mc].scale           1.6          1.6       0.5   2.0% ↓
  scale           experiment.linked_structures[latp].scale                 4.14        4.138     0.014   
  a, Å            structures[alpo4_c2221].cell.length_a                  6.9700         6.97      0.03   
  b, Å            structures[alpo4_c2221].cell.length_b                  7.1100         7.11      0.03   
  c, Å            structures[alpo4_c2221].cell.length_c                  7.0030        7.003     0.019   
  a, Å            structures[alpo4_p63mc].cell.length_a                  4.9830        4.983     0.007   
  c, Å            structures[alpo4_p63mc].cell.length_c                  9.5040        9.504     0.019   
  a, Å            structures[latp].cell.length_a                         8.4952      8.49522   0.00017   
  c, Å            structures[latp].cell.length_c                        20.8270      20.8270    0.0008   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

In `experiments/bm01.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.019()
_peak.broad_gauss_v 0.019()
_peak.broad_gauss_w 0.0156()
_peak.mixing_eta_0 0.374()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_latp-bm01_scan, 3114 pts fitted / 3163 loaded, 45 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.51 141658096.73
      1      0.722      4.51 141616161.48   
      2      0.784      4.51 141612687.24   
      3      0.849      4.51 141612409.67   
      4      1.080      4.51 141612395.32   
  done · converged · 4 iters · reduced χ² 141612395.32 · Rwp 4.51 % · 1.13 s

  refined parameters (45 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    7.99e7  7.9800000e70.1100000e7   0.1% ↓
  intensity       experiment.background[12].intensity                    4.82e7  4.8200000e70.0700000e7   
  intensity       experiment.background[14].intensity                    3.72e7  3.7100000e70.0700000e7   0.2% ↓
  intensity       experiment.background[16].intensity                    3.07e7  3.0700000e70.0600000e7   0.1% ↓
  intensity       experiment.background[18].intensity                    2.61e7  2.6100000e70.0400000e7   0.1% ↓
  intensity       experiment.background[20].intensity                    2.44e7  2.4300000e70.0400000e7   0.3% ↓
  intensity       experiment.background[23].intensity                    2.29e7  2.2900000e70.0400000e7   0.2% ↓
  intensity       experiment.background[25].intensity                    2.28e7  2.2700000e70.0400000e7   0.2% ↓
  intensity       experiment.background[27].intensity                    2.51e7  2.5100000e70.0400000e7   0.1% ↓
  intensity       experiment.background[30].intensity                    2.44e7  2.4400000e70.0300000e7   
  intensity       experiment.background[33].intensity                    2.59e7  2.5900000e70.0300000e7   
  intensity       experiment.background[36].intensity                    1.93e7  1.9290000e70.0170000e7   0.1% ↓
  intensity       experiment.background[38].intensity                    1.60e7  1.5950000e70.0160000e7   0.1% ↓
  intensity       experiment.background[40].intensity                    1.66e7  1.6580000e70.0150000e7   0.1% ↓
  intensity       experiment.background[43].intensity                    1.89e7  1.8850000e70.0150000e7   0.1% ↓
  intensity       experiment.background[45].intensity                    1.81e7  1.8070000e70.0150000e7   
  intensity       experiment.background[47].intensity                    1.79e7  1.7900000e70.0130000e7   
  intensity       experiment.background[49].intensity                    1.95e7  1.9470000e70.0140000e7   0.1% ↓
  intensity       experiment.background[4].intensity                     3.70e7  3.7000000e70.3000000e7   
  intensity       experiment.background[51].intensity                    2.04e7  2.0360000e70.0120000e7   
  intensity       experiment.background[53].intensity                    2.19e7  2.1910000e70.0120000e7   0.1% ↓
  intensity       experiment.background[55].intensity                    2.24e7  2.2380000e70.0110000e7   
  intensity       experiment.background[57].intensity                    2.18e7  2.1830000e70.0100000e7   
  intensity       experiment.background[59].intensity                    2.38e7  2.3830000e70.0080000e7   
  intensity       experiment.background[5].intensity                     4.17e7  4.1700000e70.1100000e7   
  intensity       experiment.background[61].intensity                    1.90e7  1.8950000e70.0090000e7   
  intensity       experiment.background[62].intensity                    1.55e7  1.5500000e70.0300000e7   
  intensity       experiment.background[7].intensity                     5.28e7  5.2700000e70.1100000e7   0.1% ↓
  intensity       experiment.background[8].intensity                     6.72e7  6.7200000e70.1300000e7   
  intensity       experiment.background[9].intensity                     8.27e7  8.2700000e70.1500000e7   0.1% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0387      -0.0387    0.0005   0.1% ↓
  scale           experiment.linked_structures[alpo4_c2221].scale          0.53         0.53      0.12   0.8% ↑
  scale           experiment.linked_structures[alpo4_p63mc].scale           1.6          1.6       0.5   1.6% ↓
  scale           experiment.linked_structures[latp].scale                4.138         4.15      0.03   0.2% ↑
  U, deg²         experiment.peak.broad_gauss_u                           0.019        0.019     0.008 ! 0.6% ↓
  V, deg²         experiment.peak.broad_gauss_v                           0.019        0.020     0.005 ! 3.8% ↑
  W, deg²         experiment.peak.broad_gauss_w                          0.0156       0.0156    0.0006   
  Eta0            experiment.peak.mixing_eta_0                            0.374        0.374     0.016   0.1% ↓
  a, Å            structures[alpo4_c2221].cell.length_a                  6.9700         6.97      0.03   
  b, Å            structures[alpo4_c2221].cell.length_b                  7.1100         7.11      0.03   
  c, Å            structures[alpo4_c2221].cell.length_c                  7.0030        7.003     0.019   
  a, Å            structures[alpo4_p63mc].cell.length_a                  4.9830        4.983     0.007   
  c, Å            structures[alpo4_p63mc].cell.length_c                  9.5040        9.504     0.019   
  a, Å            structures[latp].cell.length_a                         8.4952      8.49525   0.00018   
  c, Å            structures[latp].cell.length_c                        20.8270      20.8268    0.0008   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (bm01) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with U (bm01) (r = -0.96)
```

## Peak asymmetry

In `experiments/bm01.edi`, add `()` after the values the stage frees:

```edi
_peak.asym_beba_a0 0.088()
_peak.asym_beba_b0 0.0043()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_latp-bm01_scan, 3114 pts fitted / 3163 loaded, 47 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.51 141730697.09
      1      0.747      4.51 141699783.02   
      2      0.813      4.51 141696298.52   
      3      1.077      4.51 141696205.35   
  done · converged · 3 iters · reduced χ² 141696205.35 · Rwp 4.51 % · 1.14 s

  refined parameters (47 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    7.98e7  7.9800000e70.1100000e7   
  intensity       experiment.background[12].intensity                    4.82e7  4.8200000e70.0700000e7   
  intensity       experiment.background[14].intensity                    3.71e7  3.7100000e70.0700000e7   0.1% ↑
  intensity       experiment.background[16].intensity                    3.07e7  3.0700000e70.0600000e7   0.1% ↓
  intensity       experiment.background[18].intensity                    2.61e7  2.6100000e70.0400000e7   0.1% ↓
  intensity       experiment.background[20].intensity                    2.43e7  2.4300000e70.0400000e7   0.1% ↑
  intensity       experiment.background[23].intensity                    2.29e7  2.2900000e70.0400000e7   0.2% ↓
  intensity       experiment.background[25].intensity                    2.27e7  2.2800000e70.0400000e7   0.2% ↑
  intensity       experiment.background[27].intensity                    2.51e7  2.5100000e70.0400000e7   0.1% ↓
  intensity       experiment.background[30].intensity                    2.44e7  2.4400000e70.0300000e7   0.1% ↑
  intensity       experiment.background[33].intensity                    2.59e7  2.5900000e70.0300000e7   
  intensity       experiment.background[36].intensity                    1.93e7  1.9290000e70.0170000e7   
  intensity       experiment.background[38].intensity                    1.59e7  1.5950000e70.0160000e7   
  intensity       experiment.background[40].intensity                    1.66e7  1.6580000e70.0150000e7   
  intensity       experiment.background[43].intensity                    1.89e7  1.8850000e70.0150000e7   
  intensity       experiment.background[45].intensity                    1.81e7  1.8070000e70.0150000e7   
  intensity       experiment.background[47].intensity                    1.79e7  1.7900000e70.0130000e7   
  intensity       experiment.background[49].intensity                    1.95e7  1.9470000e70.0140000e7   
  intensity       experiment.background[4].intensity                     3.70e7  3.7000000e70.3000000e7   
  intensity       experiment.background[51].intensity                    2.04e7  2.0360000e70.0120000e7   
  intensity       experiment.background[53].intensity                    2.19e7  2.1910000e70.0120000e7   
  intensity       experiment.background[55].intensity                    2.24e7  2.2380000e70.0110000e7   
  intensity       experiment.background[57].intensity                    2.18e7  2.1830000e70.0100000e7   
  intensity       experiment.background[59].intensity                    2.38e7  2.3830000e70.0080000e7   
  intensity       experiment.background[5].intensity                     4.17e7  4.1700000e70.1100000e7   
  intensity       experiment.background[61].intensity                    1.90e7  1.8960000e70.0090000e7   
  intensity       experiment.background[62].intensity                    1.55e7  1.5500000e70.0300000e7   
  intensity       experiment.background[7].intensity                     5.27e7  5.2800000e70.1100000e7   0.1% ↑
  intensity       experiment.background[8].intensity                     6.72e7  6.7200000e70.1400000e7   0.1% ↓
  intensity       experiment.background[9].intensity                     8.27e7  8.2700000e70.1500000e7   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0387      -0.0392    0.0014   1.3% ↓
  scale           experiment.linked_structures[alpo4_c2221].scale          0.53         0.53      0.12   0.4% ↑
  scale           experiment.linked_structures[alpo4_p63mc].scale           1.6          1.6       0.5   0.2% ↑
  scale           experiment.linked_structures[latp].scale                 4.15         4.14      0.03   0.1% ↓
  A₀              experiment.peak.asym_beba_a0                            0.088        0.090     0.005   1.9% ↑
  B₀              experiment.peak.asym_beba_b0                           0.0043       0.0044    0.0011   2.4% ↑
  U, deg²         experiment.peak.broad_gauss_u                           0.019        0.020     0.009 ! 3.6% ↑
  V, deg²         experiment.peak.broad_gauss_v                            0.02        0.019     0.006 ! 5.0% ↓
  W, deg²         experiment.peak.broad_gauss_w                          0.0156       0.0158    0.0009   1.1% ↑
  Eta0            experiment.peak.mixing_eta_0                            0.374        0.372     0.016   0.4% ↓
  a, Å            structures[alpo4_c2221].cell.length_a                  6.9700         6.97      0.03   
  b, Å            structures[alpo4_c2221].cell.length_b                  7.1100         7.11      0.03   
  c, Å            structures[alpo4_c2221].cell.length_c                  7.0030        7.003     0.019   
  a, Å            structures[alpo4_p63mc].cell.length_a                  4.9830        4.983     0.007   
  c, Å            structures[alpo4_p63mc].cell.length_c                  9.5040        9.504     0.019   
  a, Å            structures[latp].cell.length_a                         8.4953       8.4952    0.0003   
  c, Å            structures[latp].cell.length_c                        20.8268      20.8267    0.0009   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (bm01) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with U (bm01) (r = -0.96)
```

## LATP positions

The main phase's free coordinates; Al's follows Ti's.

In `structures/latp.edi`, add `()` after the values the stage frees:

```edi
Ti1 Ti 0 0 0.14184() c 12 0.85 0.33 Biso
P1 P 0.2877() 0 0.25 e 18 1 0.23 Biso
```

The same for every other row (2 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_latp-bm01_scan, 3114 pts fitted / 3163 loaded, 55 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.51 142093212.27
      1      0.820      4.51 142052227.84   
      2      1.067      4.51 142050818.62   
  done · converged · 2 iters · reduced χ² 142050818.62 · Rwp 4.51 % · 1.12 s

  refined parameters (55 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    7.98e7  7.9800000e70.1100000e7   
  intensity       experiment.background[12].intensity                    4.82e7  4.8200000e70.0700000e7   
  intensity       experiment.background[14].intensity                    3.71e7  3.7100000e70.0700000e7   
  intensity       experiment.background[16].intensity                    3.07e7  3.0700000e70.0600000e7   0.1% ↓
  intensity       experiment.background[18].intensity                    2.61e7  2.6100000e70.0400000e7   
  intensity       experiment.background[20].intensity                    2.43e7  2.4300000e70.0400000e7   0.1% ↑
  intensity       experiment.background[23].intensity                    2.29e7  2.2800000e70.0400000e7   0.2% ↓
  intensity       experiment.background[25].intensity                    2.28e7  2.2800000e70.0400000e7   0.2% ↓
  intensity       experiment.background[27].intensity                    2.51e7  2.5100000e70.0400000e7   
  intensity       experiment.background[30].intensity                    2.44e7  2.4400000e70.0300000e7   
  intensity       experiment.background[33].intensity                    2.59e7  2.5900000e70.0300000e7   
  intensity       experiment.background[36].intensity                    1.93e7  1.9300000e70.0170000e7   
  intensity       experiment.background[38].intensity                    1.59e7  1.5950000e70.0160000e7   
  intensity       experiment.background[40].intensity                    1.66e7  1.6570000e70.0160000e7   0.1% ↓
  intensity       experiment.background[43].intensity                    1.89e7  1.8850000e70.0150000e7   
  intensity       experiment.background[45].intensity                    1.81e7  1.8070000e70.0150000e7   
  intensity       experiment.background[47].intensity                    1.79e7  1.7900000e70.0130000e7   
  intensity       experiment.background[49].intensity                    1.95e7  1.9470000e70.0140000e7   
  intensity       experiment.background[4].intensity                     3.70e7  3.7000000e70.3000000e7   
  intensity       experiment.background[51].intensity                    2.04e7  2.0360000e70.0120000e7   
  intensity       experiment.background[53].intensity                    2.19e7  2.1920000e70.0120000e7   
  intensity       experiment.background[55].intensity                    2.24e7  2.2380000e70.0110000e7   
  intensity       experiment.background[57].intensity                    2.18e7  2.1830000e70.0100000e7   
  intensity       experiment.background[59].intensity                    2.38e7  2.3830000e70.0080000e7   
  intensity       experiment.background[5].intensity                     4.17e7  4.1700000e70.1100000e7   
  intensity       experiment.background[61].intensity                    1.90e7  1.8950000e70.0100000e7   
  intensity       experiment.background[62].intensity                    1.55e7  1.5500000e70.0300000e7   
  intensity       experiment.background[7].intensity                     5.28e7  5.2800000e70.1100000e7   
  intensity       experiment.background[8].intensity                     6.72e7  6.7100000e70.1400000e7   0.1% ↓
  intensity       experiment.background[9].intensity                     8.27e7  8.2700000e70.1500000e7   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0392      -0.0393    0.0014   0.2% ↓
  scale           experiment.linked_structures[alpo4_c2221].scale          0.53         0.53      0.12   0.5% ↑
  scale           experiment.linked_structures[alpo4_p63mc].scale           1.6          1.6       0.5   0.5% ↑
  scale           experiment.linked_structures[latp].scale                 4.14         4.15      0.03   0.1% ↑
  A₀              experiment.peak.asym_beba_a0                             0.09        0.090     0.005   0.1% ↓
  B₀              experiment.peak.asym_beba_b0                           0.0044       0.0044    0.0011   0.3% ↑
  U, deg²         experiment.peak.broad_gauss_u                            0.02        0.020     0.009 ! 2.3% ↓
  V, deg²         experiment.peak.broad_gauss_v                           0.019        0.019     0.006 ! 0.2% ↑
  W, deg²         experiment.peak.broad_gauss_w                          0.0158       0.0158    0.0009   0.1% ↓
  Eta0            experiment.peak.mixing_eta_0                            0.372        0.373     0.016   0.1% ↑
  a, Å            structures[alpo4_c2221].cell.length_a                  6.9700         6.97      0.03   
  b, Å            structures[alpo4_c2221].cell.length_b                  7.1100         7.11      0.03   
  c, Å            structures[alpo4_c2221].cell.length_c                  7.0030        7.003     0.019   
  a, Å            structures[alpo4_p63mc].cell.length_a                  4.9830        4.983     0.007   
  c, Å            structures[alpo4_p63mc].cell.length_c                  9.5040        9.504     0.019   
  x               structures[latp].atom_sites[O1].fract_x               0.18170       0.1818    0.0007   
  y               structures[latp].atom_sites[O1].fract_y               0.99110       0.9911    0.0007   
  z               structures[latp].atom_sites[O1].fract_z               0.18890       0.1889    0.0003   
  x               structures[latp].atom_sites[O2].fract_x               0.18780       0.1879    0.0005   
  y               structures[latp].atom_sites[O2].fract_y               0.16280       0.1627    0.0005   
  z               structures[latp].atom_sites[O2].fract_z               0.08180       0.0817    0.0002   0.1% ↓
  x               structures[latp].atom_sites[P1].fract_x               0.28770       0.2877    0.0003   
  z               structures[latp].atom_sites[Ti1].fract_z              0.14184      0.14185   0.00009   
  a, Å            structures[latp].cell.length_a                         8.4952       8.4952    0.0003   
  c, Å            structures[latp].cell.length_c                        20.8267      20.8267    0.0009   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (bm01) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with U (bm01) (r = -0.96)
```

## LATP displacements

In `structures/latp.edi`, add `()` after the values the stage frees:

```edi
Ti1 Ti 0 0 0.14185() c 12 0.85 0.33() Biso
P1 P 0.2877() 0 0.25 e 18 1 0.23() Biso
```

The same for every other row (2 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_latp-bm01_scan --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_latp-bm01_scan, 3114 pts fitted / 3163 loaded, 59 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.51 142256063.67
      1      0.805      4.51 142234677.52   
      2      0.874      4.51 142229324.85   
      3      0.938      4.51 142228737.76   
      4      1.166      4.51 142228666.81   
  done · converged · 4 iters · reduced χ² 142228666.81 · Rwp 4.51 % · 1.22 s

  refined parameters (59 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    7.98e7  7.9800000e70.1100000e7   
  intensity       experiment.background[12].intensity                    4.82e7  4.8200000e70.0700000e7   
  intensity       experiment.background[14].intensity                    3.71e7  3.7100000e70.0700000e7   
  intensity       experiment.background[16].intensity                    3.07e7  3.0600000e70.0600000e7   0.2% ↓
  intensity       experiment.background[18].intensity                    2.61e7  2.6100000e70.0400000e7   
  intensity       experiment.background[20].intensity                    2.43e7  2.4300000e70.0400000e7   
  intensity       experiment.background[23].intensity                    2.28e7  2.2800000e70.0400000e7   0.2% ↑
  intensity       experiment.background[25].intensity                    2.28e7  2.2800000e70.0400000e7   0.2% ↓
  intensity       experiment.background[27].intensity                    2.51e7  2.5100000e70.0400000e7   0.1% ↓
  intensity       experiment.background[30].intensity                    2.44e7  2.4400000e70.0300000e7   
  intensity       experiment.background[33].intensity                    2.59e7  2.5900000e70.0300000e7   
  intensity       experiment.background[36].intensity                    1.93e7  1.9300000e70.0180000e7   
  intensity       experiment.background[38].intensity                    1.59e7  1.5950000e70.0160000e7   
  intensity       experiment.background[40].intensity                    1.66e7  1.6570000e70.0160000e7   
  intensity       experiment.background[43].intensity                    1.89e7  1.8860000e70.0150000e7   
  intensity       experiment.background[45].intensity                    1.81e7  1.8080000e70.0150000e7   
  intensity       experiment.background[47].intensity                    1.79e7  1.7900000e70.0130000e7   
  intensity       experiment.background[49].intensity                    1.95e7  1.9490000e70.0150000e7   0.1% ↑
  intensity       experiment.background[4].intensity                     3.70e7  3.7000000e70.3000000e7   
  intensity       experiment.background[51].intensity                    2.04e7  2.0370000e70.0130000e7   
  intensity       experiment.background[53].intensity                    2.19e7  2.1930000e70.0130000e7   
  intensity       experiment.background[55].intensity                    2.24e7  2.2390000e70.0120000e7   
  intensity       experiment.background[57].intensity                    2.18e7  2.1840000e70.0100000e7   
  intensity       experiment.background[59].intensity                    2.38e7  2.3850000e70.0090000e7   0.1% ↑
  intensity       experiment.background[5].intensity                     4.17e7  4.1700000e70.1100000e7   
  intensity       experiment.background[61].intensity                    1.90e7  1.8970000e70.0110000e7   0.1% ↑
  intensity       experiment.background[62].intensity                    1.55e7  1.5500000e70.0300000e7   
  intensity       experiment.background[7].intensity                     5.28e7  5.2800000e70.1100000e7   
  intensity       experiment.background[8].intensity                     6.71e7  6.7100000e70.1400000e7   0.1% ↑
  intensity       experiment.background[9].intensity                     8.27e7  8.2700000e70.1500000e7   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0393      -0.0394    0.0014   0.2% ↓
  scale           experiment.linked_structures[alpo4_c2221].scale          0.53         0.53      0.12   0.9% ↑
  scale           experiment.linked_structures[alpo4_p63mc].scale           1.6          1.6       0.5   0.6% ↑
  scale           experiment.linked_structures[latp].scale                 4.15         4.15      0.04   
  A₀              experiment.peak.asym_beba_a0                             0.09        0.090     0.005   0.2% ↓
  B₀              experiment.peak.asym_beba_b0                           0.0044       0.0044    0.0011   0.8% ↓
  U, deg²         experiment.peak.broad_gauss_u                            0.02        0.019     0.009   6.3% ↓
  V, deg²         experiment.peak.broad_gauss_v                           0.019        0.019     0.006   0.7% ↑
  W, deg²         experiment.peak.broad_gauss_w                          0.0158       0.0158    0.0009   0.2% ↑
  Eta0            experiment.peak.mixing_eta_0                            0.373        0.372     0.016   0.3% ↓
  a, Å            structures[alpo4_c2221].cell.length_a                  6.9700         6.97      0.03   
  b, Å            structures[alpo4_c2221].cell.length_b                  7.1100         7.11      0.03   
  c, Å            structures[alpo4_c2221].cell.length_c                  7.0030        7.003     0.019   
  a, Å            structures[alpo4_p63mc].cell.length_a                  4.9830        4.983     0.007   
  c, Å            structures[alpo4_p63mc].cell.length_c                  9.5040        9.504     0.019   
  B iso, Å²       structures[latp].atom_sites[O1].adp_iso                 0.940         0.95      0.07   1.0% ↑
  x               structures[latp].atom_sites[O1].fract_x               0.18180       0.1818    0.0007   
  y               structures[latp].atom_sites[O1].fract_y               0.99110       0.9911    0.0007   
  z               structures[latp].atom_sites[O1].fract_z               0.18890       0.1889    0.0003   
  B iso, Å²       structures[latp].atom_sites[O2].adp_iso                 0.540         0.55      0.06   2.2% ↑
  x               structures[latp].atom_sites[O2].fract_x               0.18790       0.1879    0.0005   
  y               structures[latp].atom_sites[O2].fract_y               0.16270       0.1627    0.0005   
  z               structures[latp].atom_sites[O2].fract_z               0.08170       0.0817    0.0003   
  B iso, Å²       structures[latp].atom_sites[P1].adp_iso                 0.230         0.23      0.03   1.4% ↑
  x               structures[latp].atom_sites[P1].fract_x               0.28770       0.2877    0.0003   
  B iso, Å²       structures[latp].atom_sites[Ti1].adp_iso                0.330         0.33      0.02   1.4% ↑
  z               structures[latp].atom_sites[Ti1].fract_z              0.14185      0.14185   0.00009   
  a, Å            structures[latp].cell.length_a                         8.4952       8.4952    0.0003   
  c, Å            structures[latp].cell.length_c                        20.8267      20.8267    0.0009   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Fit the scan

Back to the sequential mode: every pattern is fitted in turn, each from the fit before it.

In `analysis/analysis.edi`, set:

```edi
_fitting_mode.type sequential
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_latp-bm01_scan
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_latp-bm01_scan
    ```

```text
[░░░░░░░░░░░░░░] · 1/73 · 1% · elapsed 2s · eta 2m32s · 1 ok · 0 fail · latp_312 · reduced χ² 142229626.70
[░░░░░░░░░░░░░░] · 2/73 · 3% · elapsed 3s · eta 1m55s · 2 ok · 0 fail · latp_311 · reduced χ² 145127699.82
[█░░░░░░░░░░░░░] · 3/73 · 4% · elapsed 5s · eta 1m50s · 3 ok · 0 fail · latp_310 · reduced χ² 143755384.27
[█░░░░░░░░░░░░░] · 4/73 · 5% · elapsed 6s · eta 1m49s · 4 ok · 0 fail · latp_309 · reduced χ² 147076823.95
[█░░░░░░░░░░░░░] · 5/73 · 7% · elapsed 8s · eta 1m45s · 5 ok · 0 fail · latp_308 · reduced χ² 146985656.48
[█░░░░░░░░░░░░░] · 6/73 · 8% · elapsed 9s · eta 1m41s · 6 ok · 0 fail · latp_307 · reduced χ² 147115481.27
…
[█████████████░] · 69/73 · 95% · elapsed 2m08s · eta 7s · 69 ok · 0 fail · latp_244 · reduced χ² 45839457.15
[█████████████░] · 70/73 · 96% · elapsed 2m09s · eta 6s · 70 ok · 0 fail · latp_243 · reduced χ² 38966574.31
[██████████████] · 71/73 · 97% · elapsed 2m11s · eta 4s · 71 ok · 0 fail · latp_242 · reduced χ² 37983723.70
[██████████████] · 72/73 · 99% · elapsed 2m14s · eta 2s · 72 ok · 0 fail · latp_241 · reduced χ² 36267052.67
[██████████████] · 73/73 · 100% · elapsed 2m16s · 73 ok · 0 fail
scan · 73 files · 73 converged · 0 failed · reduced χ² 36267052.67-152294380.50 · 2m16s
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-xray-cwl_latp-bm01_scan --output pd-xray-cwl_latp-bm01_scan.html
    ```
