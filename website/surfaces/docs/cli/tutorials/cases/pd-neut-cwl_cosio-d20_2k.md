# Magnetic structure fit: Co₂SiO₄ at 2.3 K, D20

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_cosio-d20_2k
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_cosio-d20_2k
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/d20.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_twotheta_offset 0.29433
_peak.broad_gauss_u 0.273527
_peak.broad_gauss_v -0.589718
_peak.broad_gauss_w 0.413007
_peak.broad_lorentz_y 0.017548
_peak.asym_fcj_1 0
1 6 603.5
2 6.5 585
```

The same for every other row (15 more).

In `structures/cosio.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 10.3081
_cell.length_b 6.00219
_cell.length_c 4.78739
Co2 Co 0.2809 0.25 0.9836 c 4 1 0.269 Biso
Si Si 0.0933 0.25 0.4278 c 4 1 0.466 Biso
```

The same for every other row (6 more).

## Scale, 2θ zero and cell

In `experiments/d20.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0.29433()
cosio 1.81723() 1.0
```

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 10.3081()
_cell.length_b 6.00219()
_cell.length_c 4.78739()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 5 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.38        35.74
      1      0.072     11.32        35.36   1.1% ↓
  done · converged · 1 iters · reduced χ² 35.36 · Rwp 11.32 % · 0.08 s

  refined parameters (5 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2943       0.2851    0.0046   3.1% ↓
  scale           experiment.linked_structures[cosio].scale              1.8172        1.791     0.015   1.4% ↓
  a, Å            structure.cell.length_a                               10.3081     10.30664   0.00067   
  b, Å            structure.cell.length_b                                6.0022      6.00127   0.00040   
  c, Å            structure.cell.length_c                                4.7874      4.78676   0.00031   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

With the peaks in place, the sixteen background points follow the level between them.

In `experiments/d20.edi`, add `()` after the values the stage frees:

```edi
1 6 603.5()
2 6.5 585()
```

The same for every other row (14 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 21 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.32        35.75
      1      0.076     10.76        32.31   9.6% ↓
  done · converged · 1 iters · reduced χ² 32.31 · Rwp 10.76 % · 0.08 s

  refined parameters (21 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    373.16        348.4       6.1   6.6% ↓
  intensity       experiment.background[11].intensity                    406.37        411.4       5.3   1.2% ↑
  intensity       experiment.background[12].intensity                    408.51        403.4       5.1   1.3% ↓
  intensity       experiment.background[13].intensity                       396        398.4       5.0   0.6% ↑
  intensity       experiment.background[14].intensity                    345.92        345.7       4.8   0.1% ↓
  intensity       experiment.background[15].intensity                    279.04        279.3       4.4   0.1% ↑
  intensity       experiment.background[16].intensity                     230.7        232.7       6.0   0.9% ↑
  intensity       experiment.background[1].intensity                      603.5          615        60   1.8% ↑
  intensity       experiment.background[2].intensity                        585          592        37   1.2% ↑
  intensity       experiment.background[3].intensity                      568.5          538        32   5.3% ↓
  intensity       experiment.background[4].intensity                      528.8          629        16   19.0% ↑
  intensity       experiment.background[5].intensity                      418.9          487        15   16.2% ↑
  intensity       experiment.background[6].intensity                      420.2          408        31   2.9% ↓
  intensity       experiment.background[7].intensity                      416.5          437        21   5.0% ↑
  intensity       experiment.background[8].intensity                     416.05        371.2       9.0   10.8% ↓
  intensity       experiment.background[9].intensity                     394.77        394.3       8.3   0.1% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2851       0.2847    0.0044   0.1% ↓
  scale           experiment.linked_structures[cosio].scale               1.791        1.799     0.017   0.5% ↑
  a, Å            structure.cell.length_a                               10.3066     10.30660   0.00064   
  b, Å            structure.cell.length_b                                6.0013      6.00126   0.00038   
  c, Å            structure.cell.length_c                                4.7868      4.78675   0.00030   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

In `experiments/d20.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.273527()
_peak.broad_gauss_v -0.589718()
_peak.broad_gauss_w 0.413007()
_peak.broad_lorentz_y 0.017548()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 25 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       10.76        32.41
      1      0.083     10.71        32.12   0.9% ↓
      2      0.098     10.71        32.12   
  done · converged · 2 iters · reduced χ² 32.12 · Rwp 10.71 % · 0.11 s

  refined parameters (25 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     348.4        348.2       6.1   0.1% ↓
  intensity       experiment.background[11].intensity                     411.4        411.3       5.8   
  intensity       experiment.background[12].intensity                     403.4        403.7       5.2   0.1% ↑
  intensity       experiment.background[13].intensity                     398.4        400.2       5.4   0.5% ↑
  intensity       experiment.background[14].intensity                     345.7        346.3       5.0   0.2% ↑
  intensity       experiment.background[15].intensity                     279.3        279.4       4.5   
  intensity       experiment.background[16].intensity                     232.7        233.1       6.3   0.2% ↑
  intensity       experiment.background[1].intensity                        615          615        60   0.1% ↓
  intensity       experiment.background[2].intensity                        592          592        37   
  intensity       experiment.background[3].intensity                        538          538        32   0.1% ↑
  intensity       experiment.background[4].intensity                        629          629        16   
  intensity       experiment.background[5].intensity                        487          486        15   0.3% ↓
  intensity       experiment.background[6].intensity                        408          409        30   0.2% ↑
  intensity       experiment.background[7].intensity                        437          437        21   0.1% ↑
  intensity       experiment.background[8].intensity                      371.2        371.3       8.9   
  intensity       experiment.background[9].intensity                      394.3        393.1       8.5   0.3% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2847       0.2837    0.0046   0.3% ↓
  scale           experiment.linked_structures[cosio].scale               1.799        1.792     0.027   0.4% ↓
  U, deg²         experiment.peak.broad_gauss_u                         0.27353        0.320     0.019 ! 17.2% ↑
  V, deg²         experiment.peak.broad_gauss_v                        -0.58972       -0.699     0.036 ! 18.5% ↓
  W, deg²         experiment.peak.broad_gauss_w                         0.41301        0.481     0.021   16.5% ↑
  Y, deg          experiment.peak.broad_lorentz_y                      0.017548        0.005     0.011   73.7% ↓
  a, Å            structure.cell.length_a                               10.3066     10.30657   0.00065   
  b, Å            structure.cell.length_b                                6.0013      6.00120   0.00038   
  c, Å            structure.cell.length_c                                4.7867      4.78671   0.00029   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (d20) (r = -0.95)
      experiment.peak.broad_gauss_v: strongly correlated with U (d20) (r = -0.95)
```

## Peak asymmetry

The low-angle peaks lean towards low angle. One FCJ term is freed; the other follows it by the
project's constraint.

In `experiments/d20.edi`, add `()` after the values the stage frees:

```edi
_peak.asym_fcj_1 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 26 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       10.71        32.14
      1      0.184     10.70        32.07   0.2% ↓
      2      0.194     10.70        32.05   
      3      0.203     10.69        32.02   0.1% ↓
      4      0.213     10.68        31.95   0.2% ↓
      5      0.223     10.67        31.88   0.2% ↓
      6      0.233     10.66        31.83   0.2% ↓
      7      0.242     10.65        31.79   0.1% ↓
      8      0.252     10.65        31.74   0.1% ↓
      9      0.262     10.64        31.68   0.2% ↓
     10      0.272     10.62        31.60   0.2% ↓
     11      0.282     10.61        31.53   0.2% ↓
     12      0.293     10.60        31.48   0.2% ↓
     13      0.304     10.60        31.45   0.1% ↓
     14      0.315     10.60        31.44   
     15      0.326     10.60        31.44   
     16      0.336     10.60        31.44   
     17      0.347     10.60        31.44   
     18      0.369     10.60        31.44   
  done · converged · 18 iters · reduced χ² 31.44 · Rwp 10.60 % · 0.38 s

  refined parameters (26 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     348.2        347.1       6.1   0.3% ↓
  intensity       experiment.background[11].intensity                     411.3        410.4       5.7   0.2% ↓
  intensity       experiment.background[12].intensity                     403.7        403.1       5.1   0.2% ↓
  intensity       experiment.background[13].intensity                     400.2        397.8       5.4   0.6% ↓
  intensity       experiment.background[14].intensity                     346.3        344.5       4.9   0.5% ↓
  intensity       experiment.background[15].intensity                     279.4        278.3       4.5   0.4% ↓
  intensity       experiment.background[16].intensity                     233.1        232.2       6.2   0.4% ↓
  intensity       experiment.background[1].intensity                        615          616        60   0.1% ↑
  intensity       experiment.background[2].intensity                        592          590        37   0.3% ↓
  intensity       experiment.background[3].intensity                        538          544        32   1.1% ↑
  intensity       experiment.background[4].intensity                        629          610        16   3.0% ↓
  intensity       experiment.background[5].intensity                        486          493        15   1.4% ↑
  intensity       experiment.background[6].intensity                        409          407        30   0.6% ↓
  intensity       experiment.background[7].intensity                        437          439        20   0.5% ↑
  intensity       experiment.background[8].intensity                      371.3        367.0       8.9   1.2% ↓
  intensity       experiment.background[9].intensity                      393.1        389.7       8.4   0.9% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2837       0.3698    0.0080   30.3% ↑
  scale           experiment.linked_structures[cosio].scale               1.792        1.817     0.027   1.4% ↑
  S/L             experiment.peak.asym_fcj_1                                  0       0.0549    0.0025   
  U, deg²         experiment.peak.broad_gauss_u                            0.32        0.257     0.020 ! 19.7% ↓
  V, deg²         experiment.peak.broad_gauss_v                          -0.699       -0.541     0.041 ! 22.6% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.481        0.386     0.024   19.8% ↓
  Y, deg          experiment.peak.broad_lorentz_y                         0.005        0.011     0.011   118.7% ↑
  a, Å            structure.cell.length_a                               10.3066     10.31351   0.00083   0.1% ↑
  b, Å            structure.cell.length_b                                6.0012      6.00527   0.00049   0.1% ↑
  c, Å            structure.cell.length_c                                4.7867      4.79006   0.00039   0.1% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (d20) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with U (d20) (r = -0.96)
```

## Atom positions

Co1 sits on a centre of symmetry and the other sites on the mirror plane, so only their free
coordinates are fitted. The displacements stay at their room-temperature values.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co2 Co 0.2809() 0.25 0.9836() c 4 1 0.269 Biso
Si Si 0.0933() 0.25 0.4278() c 4 1 0.466 Biso
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 37 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       10.60        31.69
      1      0.114     10.50        31.11   1.8% ↓
  done · converged · 1 iters · reduced χ² 31.11 · Rwp 10.50 % · 0.13 s

  refined parameters (37 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     347.1        350.4       6.1   1.0% ↑
  intensity       experiment.background[11].intensity                     410.4        409.6       5.8   0.2% ↓
  intensity       experiment.background[12].intensity                     403.1        405.7       5.1   0.6% ↑
  intensity       experiment.background[13].intensity                     397.8        395.5       5.5   0.6% ↓
  intensity       experiment.background[14].intensity                     344.5        346.0       5.0   0.4% ↑
  intensity       experiment.background[15].intensity                     278.3        280.7       4.6   0.9% ↑
  intensity       experiment.background[16].intensity                     232.2        240.2       6.7   3.4% ↑
  intensity       experiment.background[1].intensity                        616          616        59   0.1% ↓
  intensity       experiment.background[2].intensity                        590          590        37   0.1% ↑
  intensity       experiment.background[3].intensity                        544          544        32   
  intensity       experiment.background[4].intensity                        610          609        16   0.1% ↓
  intensity       experiment.background[5].intensity                        493          492        15   0.2% ↓
  intensity       experiment.background[6].intensity                        407          407        30   
  intensity       experiment.background[7].intensity                        439          439        20   
  intensity       experiment.background[8].intensity                        367        367.4       8.8   0.1% ↑
  intensity       experiment.background[9].intensity                      389.7        390.5       8.5   0.2% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.3698       0.3707    0.0080   0.2% ↑
  scale           experiment.linked_structures[cosio].scale               1.817        1.815     0.027   0.1% ↓
  S/L             experiment.peak.asym_fcj_1                             0.0549       0.0549    0.0025   
  U, deg²         experiment.peak.broad_gauss_u                           0.257        0.243     0.019 ! 5.6% ↓
  V, deg²         experiment.peak.broad_gauss_v                          -0.541       -0.512     0.040 ! 5.4% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.386        0.372     0.023   3.6% ↓
  Y, deg          experiment.peak.broad_lorentz_y                         0.011        0.012     0.011   13.3% ↑
  x               structure.atom_sites[Co2].fract_x                     0.28090       0.2793    0.0016   0.6% ↓
  z               structure.atom_sites[Co2].fract_z                     0.98360       0.9849    0.0037   0.1% ↑
  x               structure.atom_sites[O1].fract_x                      0.08960      0.08953   0.00076   0.1% ↓
  z               structure.atom_sites[O1].fract_z                      0.77300       0.7718    0.0017   0.2% ↓
  x               structure.atom_sites[O2].fract_x                      0.44780      0.44649   0.00066   0.3% ↓
  z               structure.atom_sites[O2].fract_z                      0.21790       0.2163    0.0018   0.7% ↓
  x               structure.atom_sites[O3].fract_x                      0.16390      0.16430   0.00058   0.2% ↑
  y               structure.atom_sites[O3].fract_y                      0.03210      0.02975   0.00086   7.3% ↓
  z               structure.atom_sites[O3].fract_z                      0.28050       0.2810    0.0013   0.2% ↑
  x               structure.atom_sites[Si].fract_x                      0.09330      0.09488   0.00098   1.7% ↑
  z               structure.atom_sites[Si].fract_z                      0.42780       0.4318    0.0021   0.9% ↑
  a, Å            structure.cell.length_a                               10.3135     10.31355   0.00084   
  b, Å            structure.cell.length_b                                6.0053      6.00542   0.00049   
  c, Å            structure.cell.length_c                                4.7901      4.79009   0.00039   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (d20) (r = -0.96)
      experiment.peak.broad_gauss_v: strongly correlated with U (d20) (r = -0.96)
```

## Magnetic moments

With the nuclear peaks fitted, the moments fit the magnetic peaks. The magnetic space group lets
Co1 point in any direction and Co2 only along b.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co1 2() 2() 2() Mx,My,Mz
Co2 0 2() 0 0,My,0
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 41 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       10.50        31.20
      1      0.109      4.87         6.72   78.5% ↓
      2      0.125      4.87         6.72   
      3      0.142      4.87         6.71   
      4      0.154      4.87         6.71   
      5      0.171      4.87         6.71   
      6      0.188      4.87         6.71   
      7      0.204      4.87         6.71   
      8      0.220      4.87         6.71   
      9      0.237      4.87         6.71   
     10      0.267      4.87         6.71   
  done · converged · 10 iters · reduced χ² 6.71 · Rwp 4.87 % · 0.28 s

  refined parameters (41 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     350.4        370.2       2.9   5.6% ↑
  intensity       experiment.background[11].intensity                     409.6        408.2       2.7   0.4% ↓
  intensity       experiment.background[12].intensity                     405.7        407.8       2.4   0.5% ↑
  intensity       experiment.background[13].intensity                     395.5        398.9       2.6   0.9% ↑
  intensity       experiment.background[14].intensity                       346        345.3       2.4   0.2% ↓
  intensity       experiment.background[15].intensity                     280.7        279.2       2.2   0.5% ↓
  intensity       experiment.background[16].intensity                     240.2        236.8       3.2   1.4% ↓
  intensity       experiment.background[1].intensity                        616          620        28   0.6% ↑
  intensity       experiment.background[2].intensity                        590          584        17   1.1% ↓
  intensity       experiment.background[3].intensity                        544          567        15   4.3% ↑
  intensity       experiment.background[4].intensity                        609        527.2       8.4   13.4% ↓
  intensity       experiment.background[5].intensity                        492        424.4       7.0   13.7% ↓
  intensity       experiment.background[6].intensity                        407          426        14   4.6% ↑
  intensity       experiment.background[7].intensity                        439        420.4       9.2   4.2% ↓
  intensity       experiment.background[8].intensity                      367.4        410.5       4.1   11.7% ↑
  intensity       experiment.background[9].intensity                      390.5        379.8       4.1   2.7% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.3707       0.3915    0.0031   5.6% ↑
  scale           experiment.linked_structures[cosio].scale               1.815        1.781     0.014   1.9% ↓
  S/L             experiment.peak.asym_fcj_1                             0.0549      0.06274   0.00090   14.3% ↑
  U, deg²         experiment.peak.broad_gauss_u                           0.243       0.2022    0.0076   16.8% ↓
  V, deg²         experiment.peak.broad_gauss_v                          -0.512       -0.402     0.016   21.4% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.372       0.3039    0.0090   18.3% ↓
  Y, deg          experiment.peak.broad_lorentz_y                         0.012       0.0113    0.0047   5.9% ↓
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x          2.0000        0.999     0.041   50.0% ↓
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y          2.0000        3.095     0.025   54.8% ↑
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z          2.0000      -8.6e-4  12000e-4   100.0% ↓
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y          2.0000        2.743     0.038   37.1% ↑
  x               structure.atom_sites[Co2].fract_x                     0.27930      0.27861   0.00064   0.2% ↓
  z               structure.atom_sites[Co2].fract_z                     0.98490       0.9824    0.0018   0.3% ↓
  x               structure.atom_sites[O1].fract_x                      0.08953      0.08984   0.00036   0.3% ↑
  z               structure.atom_sites[O1].fract_z                      0.77180      0.77201   0.00080   
  x               structure.atom_sites[O2].fract_x                      0.44649      0.44809   0.00031   0.4% ↑
  z               structure.atom_sites[O2].fract_z                      0.21630      0.21547   0.00083   0.4% ↓
  x               structure.atom_sites[O3].fract_x                      0.16430      0.16361   0.00027   0.4% ↓
  y               structure.atom_sites[O3].fract_y                      0.02975      0.03190   0.00040   7.2% ↑
  z               structure.atom_sites[O3].fract_z                      0.28100      0.27976   0.00060   0.4% ↓
  x               structure.atom_sites[Si].fract_x                      0.09488      0.09412   0.00047   0.8% ↓
  z               structure.atom_sites[Si].fract_z                      0.43180      0.42847   0.00099   0.8% ↓
  a, Å            structure.cell.length_a                               10.3135     10.31523   0.00035   
  b, Å            structure.cell.length_b                                6.0054      6.00635   0.00021   
  c, Å            structure.cell.length_c                                4.7901      4.79086   0.00017   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Magnetic form factor

Last, the j2 term of the Co²⁺ form factor, which changes how the magnetic intensities fall with
angle. It moves together with the moments, so it comes after them.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co Co2+ dipole 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 42 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.87         6.72
      1      0.117      4.70         6.25   7.0% ↓
      2      0.135      4.70         6.25   
      3      0.152      4.70         6.25   
      4      0.170      4.70         6.25   
      5      0.188      4.70         6.25   
      6      0.205      4.70         6.25   
      7      0.224      4.70         6.25   
      8      0.238      4.70         6.25   
      9      0.255      4.70         6.25   
     10      0.281      4.70         6.25   
  done · converged · 10 iters · reduced χ² 6.25 · Rwp 4.70 % · 0.30 s

  refined parameters (42 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiment.background[10].intensity                       370.2        371.2       2.8   0.3% ↑
  intensity       experiment.background[11].intensity                       408.2        405.4       2.6   0.7% ↓
  intensity       experiment.background[12].intensity                       407.8        403.1       2.4   1.1% ↓
  intensity       experiment.background[13].intensity                       398.9        396.1       2.5   0.7% ↓
  intensity       experiment.background[14].intensity                       345.3        342.1       2.3   0.9% ↓
  intensity       experiment.background[15].intensity                       279.2        277.6       2.1   0.6% ↓
  intensity       experiment.background[16].intensity                       236.8        231.7       3.1   2.1% ↓
  intensity       experiment.background[1].intensity                          620          619        27   0.1% ↓
  intensity       experiment.background[2].intensity                          584          584        17   
  intensity       experiment.background[3].intensity                          567          565        15   0.4% ↓
  intensity       experiment.background[4].intensity                        527.2        535.2       7.9   1.5% ↑
  intensity       experiment.background[5].intensity                        424.4        425.0       6.8   0.1% ↑
  intensity       experiment.background[6].intensity                          426          425        14   0.2% ↓
  intensity       experiment.background[7].intensity                        420.4        420.1       8.9   0.1% ↓
  intensity       experiment.background[8].intensity                        410.5        411.1       4.0   0.1% ↑
  intensity       experiment.background[9].intensity                        379.8        382.8       4.0   0.8% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset              0.3915       0.3856    0.0030   1.5% ↓
  scale           experiment.linked_structures[cosio].scale                 1.781        1.760     0.013   1.2% ↓
  S/L             experiment.peak.asym_fcj_1                              0.06274      0.06117   0.00088   2.5% ↓
  U, deg²         experiment.peak.broad_gauss_u                            0.2022       0.2011    0.0073   0.5% ↓
  V, deg²         experiment.peak.broad_gauss_v                            -0.402       -0.406     0.015   0.9% ↓
  W, deg²         experiment.peak.broad_gauss_w                            0.3039       0.3061    0.0087   0.7% ↑
  Y, deg          experiment.peak.broad_lorentz_y                          0.0113       0.0153    0.0045   35.5% ↑
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x            0.9990        1.012     0.039   1.3% ↑
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y            3.0950        3.020     0.024   2.4% ↓
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z          -8.60e-4         0.04      0.74   4.56e3 % ↑
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y            2.7430        2.619     0.038   4.5% ↓
  x               structure.atom_sites[Co2].fract_x                       0.27861      0.27718   0.00060   0.5% ↓
  z               structure.atom_sites[Co2].fract_z                       0.98240       0.9829    0.0017   0.1% ↑
  x               structure.atom_sites[O1].fract_x                        0.08984      0.09047   0.00036   0.7% ↑
  z               structure.atom_sites[O1].fract_z                        0.77201      0.77143   0.00079   0.1% ↓
  x               structure.atom_sites[O2].fract_x                        0.44809      0.44830   0.00031   
  z               structure.atom_sites[O2].fract_z                        0.21547      0.21500   0.00082   0.2% ↓
  x               structure.atom_sites[O3].fract_x                        0.16361      0.16342   0.00027   0.1% ↓
  y               structure.atom_sites[O3].fract_y                        0.03190      0.03174   0.00039   0.5% ↓
  z               structure.atom_sites[O3].fract_z                        0.27976      0.27946   0.00060   0.1% ↓
  x               structure.atom_sites[Si].fract_x                        0.09412      0.09445   0.00046   0.4% ↑
  z               structure.atom_sites[Si].fract_z                        0.42847      0.42907   0.00097   0.1% ↑
  a, Å            structure.cell.length_a                                 10.3152     10.31473   0.00034   
  b, Å            structure.cell.length_b                                  6.0064      6.00591   0.00021   
  c, Å            structure.cell.length_c                                  4.7909      4.79066   0.00016   
  C₂              structure.magnetic_form_factor[Co].j2_coefficient        0.0000        0.586     0.055   

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
    python -m edi report pd-neut-cwl_cosio-d20_2k --output pd-neut-cwl_cosio-d20_2k.html
    ```
