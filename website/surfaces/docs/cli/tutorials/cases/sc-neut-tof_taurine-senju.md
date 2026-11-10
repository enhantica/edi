# Single-crystal fit: taurine, SENJU

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data sc-neut-tof_taurine-senju
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-tof_taurine-senju
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/senju_1.edi`, remove the `()` from every value; they now read:

```edi
_extinction.coefficient_11 0
_extinction.coefficient_22 0
_extinction.coefficient_33 0
taurine 2.762
```

In `experiments/senju_2.edi`, remove the `()` from every value; they now read:

```edi
taurine 3.829
```

In `experiments/senju_3.edi`, remove the `()` from every value; they now read:

```edi
taurine 3.211
```

In `experiments/senju_4.edi`, remove the `()` from every value; they now read:

```edi
taurine 2.809
```

In `experiments/senju_5.edi`, remove the `()` from every value; they now read:

```edi
taurine 2.739
```

In `experiments/senju_6.edi`, remove the `()` from every value; they now read:

```edi
taurine 2.936
```

In `structures/taurine.edi`, remove the `()` from every value; they now read:

```edi
S1 S 0.208 0.34676 0.35118 e 4 1 0 beta
O1 O 0.33902 0.23701 0.35341 e 4 1 0 beta
```

The same for every other row (26 more).

## Scales, every site isotropic

Each bank's scale, with every site's displacement isotropic for now.

In `experiments/senju_1.edi`, add `()` after the values the stage frees:

```edi
taurine 2.762()
```

In `experiments/senju_2.edi`, add `()` after the values the stage frees:

```edi
taurine 3.829()
```

In `experiments/senju_3.edi`, add `()` after the values the stage frees:

```edi
taurine 3.211()
```

In `experiments/senju_4.edi`, add `()` after the values the stage frees:

```edi
taurine 2.809()
```

In `experiments/senju_5.edi`, add `()` after the values the stage frees:

```edi
taurine 2.739()
```

In `experiments/senju_6.edi`, add `()` after the values the stage frees:

```edi
taurine 2.936()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

```text
edi fit: joint project sc-neut-tof_taurine-senju, 6 banks (senju_1, senju_2, senju_3, senju_4, senju_5, senju_6), 947 pts fitted / 1540 loaded, 6 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                       179.47      5665.97
      1      0.039      51.73       470.74   91.7% ↓
      2      0.083      51.73       470.73   
  done · converged · 2 iters · reduced χ² 470.73 · wR(F²) 51.73 % · 0.12 s

  per-bank wR(F²) (%):   senju_1 60.04   senju_2 70.32   senju_3 39.79   senju_4 53.79   senju_5 41.41   senju_6 51.44

  refined parameters (6 free):
  name            parameter                                                     start        value      s.u.   change
  scale           experiments[senju_1].linked_structures[taurine].scale         2.762        0.878     0.047   68.2% ↓
  scale           experiments[senju_2].linked_structures[taurine].scale         3.829        0.813     0.054   78.8% ↓
  scale           experiments[senju_3].linked_structures[taurine].scale         3.211        1.440     0.049   55.1% ↓
  scale           experiments[senju_4].linked_structures[taurine].scale         2.809        0.874     0.050   68.9% ↓
  scale           experiments[senju_5].linked_structures[taurine].scale         2.739        0.992     0.047   63.8% ↓
  scale           experiments[senju_6].linked_structures[taurine].scale         2.936        1.012     0.056   65.5% ↓

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Isotropic displacements

Every site's isotropic displacement.

In `structures/taurine.edi`, add `()` after the values the stage frees:

```edi
S1 S 0.208 0.34676 0.35118 e 4 1 0() Biso
O1 O 0.33902 0.23701 0.35341 e 4 1 0() Biso
```

The same for every other row (12 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

```text
edi fit: joint project sc-neut-tof_taurine-senju, 6 banks (senju_1, senju_2, senju_3, senju_4, senju_5, senju_6), 947 pts fitted / 1540 loaded, 20 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        51.73       477.84
      1      0.073      31.17       173.47   63.7% ↓
      2      0.107      27.18       131.89   24.0% ↓
      3      0.157      26.94       129.62   1.7% ↓
      4      0.199      26.94       129.57   
      5      0.227      26.94       129.56   
      6      0.302      26.94       129.56   
  done · converged · 6 iters · reduced χ² 129.56 · wR(F²) 26.94 % · 0.38 s

  per-bank wR(F²) (%):   senju_1 30.06   senju_2 28.38   senju_3 23.25   senju_4 24.93   senju_5 30.58   senju_6 26.29

  refined parameters (20 free):
  name            parameter                                                     start        value      s.u.   change
  scale           experiments[senju_1].linked_structures[taurine].scale         0.878        2.006     0.055   128.4% ↑
  scale           experiments[senju_2].linked_structures[taurine].scale         0.813        2.579     0.083   217.2% ↑
  scale           experiments[senju_3].linked_structures[taurine].scale          1.44        2.241     0.044   55.7% ↑
  scale           experiments[senju_4].linked_structures[taurine].scale         0.874        1.939     0.061   121.8% ↑
  scale           experiments[senju_5].linked_structures[taurine].scale         0.992        1.539     0.040   55.1% ↑
  scale           experiments[senju_6].linked_structures[taurine].scale         1.012        2.109     0.064   108.4% ↑
  B iso, Å²       structure.atom_sites[C1].adp_iso                              0.000         1.07      0.11   
  B iso, Å²       structure.atom_sites[C2].adp_iso                              0.000         1.30      0.12   
  B iso, Å²       structure.atom_sites[H11].adp_iso                             0.000         3.88      0.38   
  B iso, Å²       structure.atom_sites[H12].adp_iso                             0.000         2.04      0.26   
  B iso, Å²       structure.atom_sites[H1].adp_iso                              0.000         2.16      0.26   
  B iso, Å²       structure.atom_sites[H21].adp_iso                             0.000         3.35      0.31   
  B iso, Å²       structure.atom_sites[H22].adp_iso                             0.000         3.99      0.39   
  B iso, Å²       structure.atom_sites[H2].adp_iso                              0.000         2.91      0.31   
  B iso, Å²       structure.atom_sites[H3].adp_iso                              0.000         2.68      0.30   
  B iso, Å²       structure.atom_sites[N1].adp_iso                              0.000        1.467     0.099   
  B iso, Å²       structure.atom_sites[O1].adp_iso                              0.000         2.36      0.18   
  B iso, Å²       structure.atom_sites[O2].adp_iso                              0.000         2.00      0.17   
  B iso, Å²       structure.atom_sites[O3].adp_iso                              0.000         1.61      0.16   
  B iso, Å²       structure.atom_sites[S1].adp_iso                              0.000         1.52      0.30   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Extinction

Bank 1's three extinction terms, which the other banks share.

In `experiments/senju_1.edi`, add `()` after the values the stage frees:

```edi
_extinction.coefficient_11 0()
_extinction.coefficient_22 0()
_extinction.coefficient_33 0()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

```text
edi fit: joint project sc-neut-tof_taurine-senju, 6 banks (senju_1, senju_2, senju_3, senju_4, senju_5, senju_6), 947 pts fitted / 1540 loaded, 23 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        26.94       129.98
      1      0.071      22.14        87.85   32.4% ↓
      2      0.127      20.47        75.09   14.5% ↓
      3      0.157      20.27        73.57   2.0% ↓
      4      0.196      20.26        73.55   
      5      0.249      20.26        73.55   
  done · converged · 5 iters · reduced χ² 73.55 · wR(F²) 20.26 % · 0.31 s

  per-bank wR(F²) (%):   senju_1 25.78   senju_2 22.57   senju_3 15.51   senju_4 17.82   senju_5 19.59   senju_6 22.41

  refined parameters (23 free):
  name            parameter                                                     start        value      s.u.   change
  x11             experiments[senju_1].extinction.coefficient_11                    0       0.0647    0.0050   
  x22             experiments[senju_1].extinction.coefficient_22                    0       0.0078    0.0016   
  x33             experiments[senju_1].extinction.coefficient_33                    0       0.0127    0.0020   
  scale           experiments[senju_1].linked_structures[taurine].scale         2.006        2.859     0.076   42.5% ↑
  scale           experiments[senju_2].linked_structures[taurine].scale         2.579         3.68      0.11   42.7% ↑
  scale           experiments[senju_3].linked_structures[taurine].scale         2.241        3.431     0.082   53.1% ↑
  scale           experiments[senju_4].linked_structures[taurine].scale         1.939        2.800     0.082   44.4% ↑
  scale           experiments[senju_5].linked_structures[taurine].scale         1.539        2.922     0.084   89.9% ↑
  scale           experiments[senju_6].linked_structures[taurine].scale         2.109        3.024     0.084   43.4% ↑
  B iso, Å²       structure.atom_sites[C1].adp_iso                              1.070        1.656     0.090   54.7% ↑
  B iso, Å²       structure.atom_sites[C2].adp_iso                              1.300         2.00      0.11   53.7% ↑
  B iso, Å²       structure.atom_sites[H11].adp_iso                             3.880         3.80      0.25   2.2% ↓
  B iso, Å²       structure.atom_sites[H12].adp_iso                             2.040         3.25      0.22   59.1% ↑
  B iso, Å²       structure.atom_sites[H1].adp_iso                              2.160         3.38      0.23   56.7% ↑
  B iso, Å²       structure.atom_sites[H21].adp_iso                             3.350         4.02      0.24   19.9% ↑
  B iso, Å²       structure.atom_sites[H22].adp_iso                             3.990         4.16      0.26   4.2% ↑
  B iso, Å²       structure.atom_sites[H2].adp_iso                              2.910         3.90      0.24   34.0% ↑
  B iso, Å²       structure.atom_sites[H3].adp_iso                              2.680         3.40      0.23   26.8% ↑
  B iso, Å²       structure.atom_sites[N1].adp_iso                              1.467        1.939     0.077   32.2% ↑
  B iso, Å²       structure.atom_sites[O1].adp_iso                              2.360         2.88      0.13   21.8% ↑
  B iso, Å²       structure.atom_sites[O2].adp_iso                              2.000         2.81      0.13   40.5% ↑
  B iso, Å²       structure.atom_sites[O3].adp_iso                              1.610         2.17      0.12   34.8% ↑
  B iso, Å²       structure.atom_sites[S1].adp_iso                              1.520         1.61      0.20   5.6% ↑

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Positions

All fourteen sites' coordinates.

In `structures/taurine.edi`, add `()` after the values the stage frees:

```edi
S1 S 0.208() 0.34676() 0.35118() e 4 1 1.61() Biso
O1 O 0.33902() 0.23701() 0.35341() e 4 1 2.88() Biso
```

The same for every other row (12 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

```text
edi fit: joint project sc-neut-tof_taurine-senju, 6 banks (senju_1, senju_2, senju_3, senju_4, senju_5, senju_6), 947 pts fitted / 1540 loaded, 65 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        20.26        77.05
      1      0.080      17.17        55.36   28.2% ↓
      2      0.125      17.04        54.51   1.5% ↓
      3      0.188      17.04        54.49   
      4      0.247      17.04        54.49   
  done · converged · 4 iters · reduced χ² 54.49 · wR(F²) 17.04 % · 0.32 s

  per-bank wR(F²) (%):   senju_1 22.17   senju_2 18.60   senju_3 13.00   senju_4 14.02   senju_5 17.01   senju_6 18.75

  refined parameters (65 free):
  name            parameter                                                     start        value      s.u.   change
  x11             experiments[senju_1].extinction.coefficient_11               0.0647       0.0642    0.0049   0.8% ↓
  x22             experiments[senju_1].extinction.coefficient_22               0.0078       0.0091    0.0015   16.6% ↑
  x33             experiments[senju_1].extinction.coefficient_33               0.0127       0.0133    0.0021   5.0% ↑
  scale           experiments[senju_1].linked_structures[taurine].scale         2.859        2.887     0.078   1.0% ↑
  scale           experiments[senju_2].linked_structures[taurine].scale          3.68         3.74      0.11   1.6% ↑
  scale           experiments[senju_3].linked_structures[taurine].scale         3.431        3.459     0.083   0.8% ↑
  scale           experiments[senju_4].linked_structures[taurine].scale           2.8        2.793     0.079   0.3% ↓
  scale           experiments[senju_5].linked_structures[taurine].scale         2.922        2.982     0.082   2.0% ↑
  scale           experiments[senju_6].linked_structures[taurine].scale         3.024        3.080     0.081   1.9% ↑
  B iso, Å²       structure.atom_sites[C1].adp_iso                              1.656        1.626     0.081   1.8% ↓
  x               structure.atom_sites[C1].fract_x                            0.33574      0.34023   0.00092   1.3% ↑
  y               structure.atom_sites[C1].fract_y                            0.43812      0.43773   0.00042   0.1% ↓
  z               structure.atom_sites[C1].fract_z                            0.19983      0.20025   0.00051   0.2% ↑
  B iso, Å²       structure.atom_sites[C2].adp_iso                              2.000        2.037     0.094   1.9% ↑
  x               structure.atom_sites[C2].fract_x                            0.20803       0.2079    0.0011   0.1% ↓
  y               structure.atom_sites[C2].fract_y                            0.55562      0.55619   0.00044   0.1% ↑
  z               structure.atom_sites[C2].fract_z                            0.18084      0.17999   0.00055   0.5% ↓
  B iso, Å²       structure.atom_sites[H11].adp_iso                             3.800         3.33      0.21   12.4% ↓
  x               structure.atom_sites[H11].fract_x                           0.53973       0.5403    0.0021   0.1% ↑
  y               structure.atom_sites[H11].fract_y                           0.44320       0.4442    0.0011   0.2% ↑
  z               structure.atom_sites[H11].fract_z                           0.23493       0.2356    0.0012   0.3% ↑
  B iso, Å²       structure.atom_sites[H12].adp_iso                             3.250         3.33      0.21   2.3% ↑
  x               structure.atom_sites[H12].fract_x                           0.32105       0.3255    0.0021   1.4% ↑
  y               structure.atom_sites[H12].fract_y                           0.39069      0.39210   0.00094   0.4% ↑
  z               structure.atom_sites[H12].fract_z                           0.08168       0.0805    0.0012   1.4% ↓
  B iso, Å²       structure.atom_sites[H1].adp_iso                              3.380         3.96      0.23   17.1% ↑
  x               structure.atom_sites[H1].fract_x                            0.17000       0.1795    0.0022   5.6% ↑
  y               structure.atom_sites[H1].fract_y                            0.59950       0.5999    0.0011   0.1% ↑
  z               structure.atom_sites[H1].fract_z                            0.43173       0.4320    0.0014   0.1% ↑
  B iso, Å²       structure.atom_sites[H21].adp_iso                             4.020         3.69      0.21   8.3% ↓
  x               structure.atom_sites[H21].fract_x                           0.28448       0.2834    0.0022   0.4% ↓
  y               structure.atom_sites[H21].fract_y                           0.59948       0.6003    0.0011   0.1% ↑
  z               structure.atom_sites[H21].fract_z                           0.07592       0.0771    0.0014   1.5% ↑
  B iso, Å²       structure.atom_sites[H22].adp_iso                             4.160         4.22      0.25   1.5% ↑
  x               structure.atom_sites[H22].fract_x                           0.00169       0.0032    0.0025   92.0% ↑
  y               structure.atom_sites[H22].fract_y                           0.54787       0.5472    0.0011   0.1% ↓
  z               structure.atom_sites[H22].fract_z                           0.16446       0.1639    0.0014   0.3% ↓
  B iso, Å²       structure.atom_sites[H2].adp_iso                              3.900         3.66      0.21   6.1% ↓
  x               structure.atom_sites[H2].fract_x                            0.19405       0.1915    0.0020   1.3% ↓
  y               structure.atom_sites[H2].fract_y                            0.70895       0.7075    0.0011   0.2% ↓
  z               structure.atom_sites[H2].fract_z                            0.30623       0.3077    0.0013   0.5% ↑
  B iso, Å²       structure.atom_sites[H3].adp_iso                              3.400         4.03      0.24   18.6% ↑
  x               structure.atom_sites[H3].fract_x                            0.45233       0.4537    0.0025   0.3% ↑
  y               structure.atom_sites[H3].fract_y                            0.63476       0.6340    0.0011   0.1% ↓
  z               structure.atom_sites[H3].fract_z                            0.36061       0.3629    0.0014   0.6% ↑
  B iso, Å²       structure.atom_sites[N1].adp_iso                              1.939        1.855     0.069   4.3% ↓
  x               structure.atom_sites[N1].fract_x                            0.26440      0.26359   0.00074   0.3% ↓
  y               structure.atom_sites[N1].fract_y                            0.62996      0.63009   0.00031   
  z               structure.atom_sites[N1].fract_z                            0.33658      0.33238   0.00040   1.2% ↓
  B iso, Å²       structure.atom_sites[O1].adp_iso                              2.880         2.68      0.12   6.9% ↓
  x               structure.atom_sites[O1].fract_x                            0.33902       0.3383    0.0012   0.2% ↓
  y               structure.atom_sites[O1].fract_y                            0.23701      0.24191   0.00055   2.1% ↑
  z               structure.atom_sites[O1].fract_z                            0.35341      0.35398   0.00068   0.2% ↑
  B iso, Å²       structure.atom_sites[O2].adp_iso                              2.810         2.81      0.13   0.1% ↑
  x               structure.atom_sites[O2].fract_x                           -0.06427      -0.0634    0.0012   1.3% ↑
  y               structure.atom_sites[O2].fract_y                            0.33875      0.33843   0.00065   0.1% ↓
  z               structure.atom_sites[O2].fract_z                            0.29137      0.29050   0.00067   0.3% ↓
  B iso, Å²       structure.atom_sites[O3].adp_iso                              2.170         2.14      0.11   1.2% ↓
  x               structure.atom_sites[O3].fract_x                            0.23286       0.2339    0.0011   0.4% ↑
  y               structure.atom_sites[O3].fract_y                            0.40985      0.41042   0.00057   0.1% ↑
  z               structure.atom_sites[O3].fract_z                            0.51108      0.51082   0.00058   0.1% ↓
  B iso, Å²       structure.atom_sites[S1].adp_iso                              1.610         1.36      0.17   15.7% ↓
  x               structure.atom_sites[S1].fract_x                            0.20800       0.2028    0.0018   2.5% ↓
  y               structure.atom_sites[S1].fract_y                            0.34676      0.34798   0.00097   0.4% ↑
  z               structure.atom_sites[S1].fract_z                            0.35118       0.3512    0.0011   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Anisotropic displacements

Back to anisotropic displacements (edi converts the values), with every tensor component free.

=== "Standalone executable"

    ```console
    edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-tof_taurine-senju --verbosity full
    ```

```text
edi fit: joint project sc-neut-tof_taurine-senju, 6 banks (senju_1, senju_2, senju_3, senju_4, senju_5, senju_6), 947 pts fitted / 1540 loaded, 135 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        17.04        59.18
      1      0.085      13.02        34.58   41.6% ↓
      2      0.167      12.20        30.32   12.3% ↓
      3      0.242      12.19        30.27   0.2% ↓
      4      0.303      12.19        30.27   
  done · converged · 4 iters · reduced χ² 30.27 · wR(F²) 12.19 % · 0.43 s

  per-bank wR(F²) (%):   senju_1 18.19   senju_2 11.06   senju_3 9.02   senju_4 8.62   senju_5 12.28   senju_6 13.04

  refined parameters (135 free):
  name            parameter                                                     start        value      s.u.   change
  x11             experiments[senju_1].extinction.coefficient_11               0.0642       0.0584    0.0036   9.1% ↓
  x22             experiments[senju_1].extinction.coefficient_22               0.0091       0.0139    0.0015   52.8% ↑
  x33             experiments[senju_1].extinction.coefficient_33               0.0133       0.0076    0.0015   42.7% ↓
  scale           experiments[senju_1].linked_structures[taurine].scale         2.887        2.805     0.060   2.9% ↓
  scale           experiments[senju_2].linked_structures[taurine].scale          3.74        3.871     0.090   3.5% ↑
  scale           experiments[senju_3].linked_structures[taurine].scale         3.459        3.253     0.064   6.0% ↓
  scale           experiments[senju_4].linked_structures[taurine].scale         2.793        2.838     0.065   1.6% ↑
  scale           experiments[senju_5].linked_structures[taurine].scale         2.982        2.780     0.064   6.8% ↓
  scale           experiments[senju_6].linked_structures[taurine].scale          3.08        2.974     0.064   3.5% ↓
  β₁₁             structure.atom_site_aniso[C1].adp_11                        0.01469       0.0179    0.0017   22.1% ↑
  β₁₂             structure.atom_site_aniso[C1].adp_12                              0       3.4e-4    5.2e-4   
  β₁₃             structure.atom_site_aniso[C1].adp_13                        6.91e-4      0.00297   0.00069   330.3% ↑
  β₂₂             structure.atom_site_aniso[C1].adp_22                        0.00299      0.00220   0.00034   26.3% ↓
  β₂₃             structure.atom_site_aniso[C1].adp_23                              0      -4.3e-4    3.0e-4   
  β₃₃             structure.atom_site_aniso[C1].adp_33                        0.00665      0.00725   0.00055   8.9% ↑
  β₁₁             structure.atom_site_aniso[C2].adp_11                        0.01841       0.0176    0.0018   4.2% ↓
  β₁₂             structure.atom_site_aniso[C2].adp_12                              0        -2e-5     61e-5   
  β₁₃             structure.atom_site_aniso[C2].adp_13                        8.66e-4        -6e-5     71e-5   107.3% ↓
  β₂₂             structure.atom_site_aniso[C2].adp_22                        0.00375      0.00324   0.00038   13.6% ↓
  β₂₃             structure.atom_site_aniso[C2].adp_23                              0       5.5e-4    3.3e-4   
  β₃₃             structure.atom_site_aniso[C2].adp_33                        0.00833      0.00728   0.00057   12.7% ↓
  β₁₁             structure.atom_site_aniso[H11].adp_11                        0.0301       0.0180    0.0041   40.1% ↓
  β₁₂             structure.atom_site_aniso[H11].adp_12                             0       0.0027    0.0014   
  β₁₃             structure.atom_site_aniso[H11].adp_13                      0.001416       0.0079    0.0019   459.1% ↑
  β₂₂             structure.atom_site_aniso[H11].adp_22                       0.00613       0.0070    0.0011   14.9% ↑
  β₂₃             structure.atom_site_aniso[H11].adp_23                             0      -1.1e-4    8.2e-4   
  β₃₃             structure.atom_site_aniso[H11].adp_33                       0.01362       0.0198    0.0017   45.3% ↑
  β₁₁             structure.atom_site_aniso[H12].adp_11                        0.0301       0.0509    0.0046   69.0% ↑
  β₁₂             structure.atom_site_aniso[H12].adp_12                             0       0.0038    0.0015   
  β₁₃             structure.atom_site_aniso[H12].adp_13                      0.001416       0.0091    0.0019   544.0% ↑
  β₂₂             structure.atom_site_aniso[H12].adp_22                       0.00613      0.00494   0.00095   19.4% ↓
  β₂₃             structure.atom_site_aniso[H12].adp_23                             0     -0.00169   0.00073   
  β₃₃             structure.atom_site_aniso[H12].adp_33                       0.01362       0.0110    0.0013   19.0% ↓
  β₁₁             structure.atom_site_aniso[H1].adp_11                         0.0358       0.0455    0.0046   27.1% ↑
  β₁₂             structure.atom_site_aniso[H1].adp_12                              0      -0.0060    0.0015   
  β₁₃             structure.atom_site_aniso[H1].adp_13                       0.001684       0.0123    0.0021   632.5% ↑
  β₂₂             structure.atom_site_aniso[H1].adp_22                        0.00729      0.00638   0.00094   12.4% ↓
  β₂₃             structure.atom_site_aniso[H1].adp_23                              0        -1e-5     83e-5   
  β₃₃             structure.atom_site_aniso[H1].adp_33                        0.01619       0.0129    0.0015   20.2% ↓
  β₁₁             structure.atom_site_aniso[H21].adp_11                        0.0333       0.0512    0.0045   53.6% ↑
  β₁₂             structure.atom_site_aniso[H21].adp_12                             0      -0.0029    0.0016   
  β₁₃             structure.atom_site_aniso[H21].adp_13                      0.001569       0.0111    0.0018   606.6% ↑
  β₂₂             structure.atom_site_aniso[H21].adp_22                       0.00679       0.0076    0.0011   11.2% ↑
  β₂₃             structure.atom_site_aniso[H21].adp_23                             0      0.00266   0.00081   
  β₃₃             structure.atom_site_aniso[H21].adp_33                       0.01509       0.0097    0.0013   36.0% ↓
  β₁₁             structure.atom_site_aniso[H22].adp_11                        0.0381       0.0288    0.0043   24.5% ↓
  β₁₂             structure.atom_site_aniso[H22].adp_12                             0        -5e-4     15e-4   
  β₁₃             structure.atom_site_aniso[H22].adp_13                       0.00179      -0.0052    0.0021   391.1% ↓
  β₂₂             structure.atom_site_aniso[H22].adp_22                       0.00776      0.00651   0.00097   16.1% ↓
  β₂₃             structure.atom_site_aniso[H22].adp_23                             0       2.6e-4    8.8e-4   
  β₃₃             structure.atom_site_aniso[H22].adp_33                        0.0173       0.0201    0.0018   16.3% ↑
  β₁₁             structure.atom_site_aniso[H2].adp_11                         0.0331       0.0384    0.0042   16.1% ↑
  β₁₂             structure.atom_site_aniso[H2].adp_12                              0        -2e-4     14e-4   
  β₁₃             structure.atom_site_aniso[H2].adp_13                       0.001556        -6e-4     19e-4   139.6% ↓
  β₂₂             structure.atom_site_aniso[H2].adp_22                        0.00673      0.00327   0.00089   51.3% ↓
  β₂₃             structure.atom_site_aniso[H2].adp_23                              0       5.7e-4    8.3e-4   
  β₃₃             structure.atom_site_aniso[H2].adp_33                        0.01497       0.0159    0.0014   6.4% ↑
  β₁₁             structure.atom_site_aniso[H3].adp_11                         0.0364       0.0262    0.0042   28.0% ↓
  β₁₂             structure.atom_site_aniso[H3].adp_12                              0         4e-4     14e-4   
  β₁₃             structure.atom_site_aniso[H3].adp_13                        0.00171       0.0021    0.0020   22.3% ↑
  β₂₂             structure.atom_site_aniso[H3].adp_22                        0.00741      0.00525   0.00099   29.2% ↓
  β₂₃             structure.atom_site_aniso[H3].adp_23                              0     -0.00516   0.00085   
  β₃₃             structure.atom_site_aniso[H3].adp_33                        0.01648       0.0191    0.0017   15.6% ↑
  β₁₁             structure.atom_site_aniso[N1].adp_11                        0.01676       0.0166    0.0013   1.1% ↓
  β₁₂             structure.atom_site_aniso[N1].adp_12                              0       5.6e-4    4.8e-4   
  β₁₃             structure.atom_site_aniso[N1].adp_13                        7.89e-4      0.00274   0.00054   247.7% ↑
  β₂₂             structure.atom_site_aniso[N1].adp_22                        0.00341      0.00261   0.00029   23.5% ↓
  β₂₃             structure.atom_site_aniso[N1].adp_23                              0         6e-5     25e-5   
  β₃₃             structure.atom_site_aniso[N1].adp_33                        0.00759      0.00844   0.00043   11.2% ↑
  β₁₁             structure.atom_site_aniso[O1].adp_11                         0.0242       0.0240    0.0022   0.9% ↓
  β₁₂             structure.atom_site_aniso[O1].adp_12                              0      0.00449   0.00065   
  β₁₃             structure.atom_site_aniso[O1].adp_13                       0.001139      0.00632   0.00099   454.8% ↑
  β₂₂             structure.atom_site_aniso[O1].adp_22                        0.00493      0.00281   0.00049   42.9% ↓
  β₂₃             structure.atom_site_aniso[O1].adp_23                              0       6.9e-4    4.0e-4   
  β₃₃             structure.atom_site_aniso[O1].adp_33                        0.01096      0.01343   0.00074   22.6% ↑
  β₁₁             structure.atom_site_aniso[O2].adp_11                         0.0254       0.0109    0.0018   57.0% ↓
  β₁₂             structure.atom_site_aniso[O2].adp_12                              0     -0.00174   0.00065   
  β₁₃             structure.atom_site_aniso[O2].adp_13                       0.001195     -0.00133   0.00093   211.0% ↓
  β₂₂             structure.atom_site_aniso[O2].adp_22                        0.00517      0.00363   0.00049   29.8% ↓
  β₂₃             structure.atom_site_aniso[O2].adp_23                              0     -0.00155   0.00047   
  β₃₃             structure.atom_site_aniso[O2].adp_33                        0.01149      0.01827   0.00093   59.0% ↑
  β₁₁             structure.atom_site_aniso[O3].adp_11                         0.0193       0.0214    0.0022   10.6% ↑
  β₁₂             structure.atom_site_aniso[O3].adp_12                              0       4.4e-4    6.4e-4   
  β₁₃             structure.atom_site_aniso[O3].adp_13                        9.10e-4      0.00246   0.00089   170.7% ↑
  β₂₂             structure.atom_site_aniso[O3].adp_22                        0.00394      0.00407   0.00045   3.4% ↑
  β₂₃             structure.atom_site_aniso[O3].adp_23                              0      -8.2e-4    3.4e-4   
  β₃₃             structure.atom_site_aniso[O3].adp_33                        0.00875      0.00713   0.00065   18.5% ↓
  β₁₁             structure.atom_site_aniso[S1].adp_11                         0.0123       0.0061    0.0029   50.4% ↓
  β₁₂             structure.atom_site_aniso[S1].adp_12                              0       4.5e-4    9.9e-4   
  β₁₃             structure.atom_site_aniso[S1].adp_13                        5.78e-4       0.0019    0.0015   229.4% ↑
  β₂₂             structure.atom_site_aniso[S1].adp_22                         0.0025      0.00133   0.00070   46.7% ↓
  β₂₃             structure.atom_site_aniso[S1].adp_23                              0      -3.6e-4    6.1e-4   
  β₃₃             structure.atom_site_aniso[S1].adp_33                        0.00556       0.0087    0.0013   57.2% ↑
  x               structure.atom_sites[C1].fract_x                            0.34023      0.34057   0.00083   0.1% ↑
  y               structure.atom_sites[C1].fract_y                            0.43773      0.43815   0.00035   0.1% ↑
  z               structure.atom_sites[C1].fract_z                            0.20025      0.19980   0.00043   0.2% ↓
  x               structure.atom_sites[C2].fract_x                            0.20790      0.20813   0.00090   0.1% ↑
  y               structure.atom_sites[C2].fract_y                            0.55619      0.55567   0.00034   0.1% ↓
  z               structure.atom_sites[C2].fract_z                            0.17999      0.18096   0.00043   0.5% ↑
  x               structure.atom_sites[H11].fract_x                           0.54030       0.5403    0.0018   
  y               structure.atom_sites[H11].fract_y                           0.44420      0.44323   0.00086   0.2% ↓
  z               structure.atom_sites[H11].fract_z                           0.23560       0.2353    0.0011   0.1% ↓
  x               structure.atom_sites[H12].fract_x                           0.32550       0.3205    0.0019   1.5% ↓
  y               structure.atom_sites[H12].fract_y                           0.39210      0.39081   0.00075   0.3% ↓
  z               structure.atom_sites[H12].fract_z                           0.08050      0.08149   0.00093   1.2% ↑
  x               structure.atom_sites[H1].fract_x                            0.17950       0.1702    0.0018   5.2% ↓
  y               structure.atom_sites[H1].fract_y                            0.59990      0.59952   0.00079   0.1% ↓
  z               structure.atom_sites[H1].fract_z                            0.43200      0.43200   0.00099   
  x               structure.atom_sites[H21].fract_x                           0.28340       0.2841    0.0020   0.3% ↑
  y               structure.atom_sites[H21].fract_y                           0.60030      0.59969   0.00081   0.1% ↓
  z               structure.atom_sites[H21].fract_z                           0.07710      0.07587   0.00094   1.6% ↓
  x               structure.atom_sites[H22].fract_x                           0.00320       0.0017    0.0020   48.3% ↓
  y               structure.atom_sites[H22].fract_y                           0.54720      0.54758   0.00086   0.1% ↑
  z               structure.atom_sites[H22].fract_z                           0.16390       0.1645    0.0011   0.4% ↑
  x               structure.atom_sites[H2].fract_x                            0.19150       0.1941    0.0018   1.3% ↑
  y               structure.atom_sites[H2].fract_y                            0.70750      0.70902   0.00084   0.2% ↑
  z               structure.atom_sites[H2].fract_z                            0.30770      0.30624   0.00099   0.5% ↓
  x               structure.atom_sites[H3].fract_x                            0.45370       0.4524    0.0019   0.3% ↓
  y               structure.atom_sites[H3].fract_y                            0.63400      0.63471   0.00079   0.1% ↑
  z               structure.atom_sites[H3].fract_z                            0.36290       0.3610    0.0011   0.5% ↓
  x               structure.atom_sites[N1].fract_x                            0.26359      0.26437   0.00066   0.3% ↑
  y               structure.atom_sites[N1].fract_y                            0.63009      0.62992   0.00027   
  z               structure.atom_sites[N1].fract_z                            0.33238      0.33152   0.00035   0.3% ↓
  x               structure.atom_sites[O1].fract_x                            0.33830      0.33890   0.00089   0.2% ↑
  y               structure.atom_sites[O1].fract_y                            0.24191      0.24191   0.00043   
  z               structure.atom_sites[O1].fract_z                            0.35398      0.35348   0.00052   0.1% ↓
  x               structure.atom_sites[O2].fract_x                           -0.06340     -0.06415   0.00083   1.2% ↓
  y               structure.atom_sites[O2].fract_y                            0.33843      0.33864   0.00050   0.1% ↑
  z               structure.atom_sites[O2].fract_z                            0.29050      0.29152   0.00058   0.4% ↑
  x               structure.atom_sites[O3].fract_x                            0.23390      0.23276   0.00082   0.5% ↓
  y               structure.atom_sites[O3].fract_y                            0.41042      0.40992   0.00046   0.1% ↓
  z               structure.atom_sites[O3].fract_z                            0.51082      0.51105   0.00044   
  x               structure.atom_sites[S1].fract_x                            0.20280       0.2030    0.0014   0.1% ↑
  y               structure.atom_sites[S1].fract_y                            0.34798      0.34694   0.00075   0.3% ↓
  z               structure.atom_sites[S1].fract_z                            0.35120      0.35134   0.00086   

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
    python -m edi report sc-neut-tof_taurine-senju --output sc-neut-tof_taurine-senju.html
    ```
