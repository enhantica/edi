# Sequential magnetic fit: Co₂SiO₄, D20 scan from 2.3 K

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_cosio-d20_scan-213f
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_cosio-d20_scan-213f
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/d20.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_twotheta_offset 0.29433
_peak.broad_gauss_u 0.273527
_peak.broad_gauss_v -0.589718
_peak.broad_gauss_w 0.413007
1 6 603.5
2 6.5 585
```

The same for every other row (15 more).

In `structures/cosio.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 10.3081
_cell.length_b 6.00219
_cell.length_c 4.78739
Co1 Co 0 0 0 a 4 1 0.269 Biso
Co2 Co 0.2809 0.25 0.9836 c 4 1 0.269 Biso
```

The same for every other row (6 more).

## Scale, 2θ zero and cell

Switch the fitting mode to a single fit, so the stages fit the template alone.

In `analysis/analysis.edi`, set:

```edi
_fitting_mode.type single
```

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
    edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_scan-213f, 1438 pts fitted / 1506 loaded, 5 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       15.23        64.02
      1      0.021     14.24        55.94   12.6% ↓
      2      0.030     14.22        55.83   0.2% ↓
      3      0.040     14.22        55.83   
      4      0.056     14.22        55.83   
  done · converged · 4 iters · reduced χ² 55.83 · Rwp 14.22 % · 0.07 s

  refined parameters (5 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2943       0.3803    0.0068   29.2% ↑
  scale           experiment.linked_structures[cosio].scale              1.8172        1.946     0.021   7.1% ↑
  a, Å            structure.cell.length_a                               10.3081     10.31441   0.00085   0.1% ↑
  b, Å            structure.cell.length_b                                6.0022      6.00580   0.00050   0.1% ↑
  c, Å            structure.cell.length_c                                4.7874      4.79043   0.00039   0.1% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

The sixteen background points follow the level between the peaks.

In `experiments/d20.edi`, add `()` after the values the stage frees:

```edi
1 6 603.5()
2 6.5 585()
```

The same for every other row (14 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_scan-213f, 1438 pts fitted / 1506 loaded, 21 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       14.22        56.46
      1      0.028     13.46        50.59   10.4% ↓
      2      0.048     13.46        50.59   
  done · converged · 2 iters · reduced χ² 50.59 · Rwp 13.46 % · 0.06 s

  refined parameters (21 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    373.16        379.4       7.6   1.7% ↑
  intensity       experiment.background[11].intensity                    406.37        417.5       6.7   2.7% ↑
  intensity       experiment.background[12].intensity                    408.51        413.9       6.3   1.3% ↑
  intensity       experiment.background[13].intensity                       396        396.1       6.3   
  intensity       experiment.background[14].intensity                    345.92        342.3       6.1   1.0% ↓
  intensity       experiment.background[15].intensity                    279.04        275.5       5.6   1.3% ↓
  intensity       experiment.background[16].intensity                     230.7        224.7       7.6   2.6% ↓
  intensity       experiment.background[1].intensity                      603.5          614        75   1.8% ↑
  intensity       experiment.background[2].intensity                        585          593        47   1.3% ↑
  intensity       experiment.background[3].intensity                      568.5          536        40   5.7% ↓
  intensity       experiment.background[4].intensity                      528.8          636        20   20.3% ↑
  intensity       experiment.background[5].intensity                      418.9          531        19   26.9% ↑
  intensity       experiment.background[6].intensity                      420.2          404        38   3.8% ↓
  intensity       experiment.background[7].intensity                      416.5          419        26   0.5% ↑
  intensity       experiment.background[8].intensity                     416.05          423        12   1.6% ↑
  intensity       experiment.background[9].intensity                     394.77          453        11   14.7% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.3803       0.3807    0.0065   0.1% ↑
  scale           experiment.linked_structures[cosio].scale               1.946        1.934     0.023   0.6% ↓
  a, Å            structure.cell.length_a                               10.3144     10.31448   0.00081   
  b, Å            structure.cell.length_b                                6.0058      6.00579   0.00048   
  c, Å            structure.cell.length_c                                4.7904      4.79045   0.00037   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

U, V and W only: across a temperature scan the Lorentzian term and the asymmetry stay at their
2.3 K values, as do the form factor's j2 term.

In `experiments/d20.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.273527()
_peak.broad_gauss_v -0.589718()
_peak.broad_gauss_w 0.413007()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_scan-213f, 1438 pts fitted / 1506 loaded, 24 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.46        50.70
      1      0.031     13.29        49.39   2.6% ↓
      2      0.043     13.29        49.35   0.1% ↓
      3      0.056     13.28        49.35   
      4      0.079     13.28        49.35   
  done · converged · 4 iters · reduced χ² 49.35 · Rwp 13.28 % · 0.09 s

  refined parameters (24 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     379.4        379.4       7.5   
  intensity       experiment.background[11].intensity                     417.5        422.6       6.7   1.2% ↑
  intensity       experiment.background[12].intensity                     413.9        414.3       6.3   0.1% ↑
  intensity       experiment.background[13].intensity                     396.1        395.3       6.3   0.2% ↓
  intensity       experiment.background[14].intensity                     342.3        341.0       6.0   0.4% ↓
  intensity       experiment.background[15].intensity                     275.5        276.3       5.5   0.3% ↑
  intensity       experiment.background[16].intensity                     224.7        225.9       7.5   0.5% ↑
  intensity       experiment.background[1].intensity                        614          614        75   
  intensity       experiment.background[2].intensity                        593          593        46   0.1% ↓
  intensity       experiment.background[3].intensity                        536          536        40   
  intensity       experiment.background[4].intensity                        636          636        19   
  intensity       experiment.background[5].intensity                        531          532        19   0.2% ↑
  intensity       experiment.background[6].intensity                        404          404        38   
  intensity       experiment.background[7].intensity                        419          419        25   0.1% ↓
  intensity       experiment.background[8].intensity                        423          423        11   0.1% ↓
  intensity       experiment.background[9].intensity                        453          455        11   0.4% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.3807       0.3814    0.0060   0.2% ↑
  scale           experiment.linked_structures[cosio].scale               1.934        1.926     0.024   0.4% ↓
  U, deg²         experiment.peak.broad_gauss_u                         0.27353        0.189     0.019   30.8% ↓
  V, deg²         experiment.peak.broad_gauss_v                        -0.58972       -0.349     0.042 ! 40.8% ↑
  W, deg²         experiment.peak.broad_gauss_w                         0.41301        0.272     0.023 ! 34.3% ↓
  a, Å            structure.cell.length_a                               10.3145     10.31423   0.00080   
  b, Å            structure.cell.length_b                                6.0058      6.00589   0.00048   
  c, Å            structure.cell.length_c                                4.7904      4.79046   0.00037   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_v: strongly correlated with W (d20) (r = -0.96)
      experiment.peak.broad_gauss_w: strongly correlated with V (d20) (r = -0.96)
```

## Atom positions

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co2 Co 0.2809() 0.25 0.9836() c 4 1 0.269 Biso
Si Si 0.0933() 0.25 0.4278() c 4 1 0.466 Biso
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_scan-213f, 1438 pts fitted / 1506 loaded, 35 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.28        49.74
      1      0.029     13.22        49.28   0.9% ↓
      2      0.041     13.22        49.27   
      3      0.051     13.22        49.27   
      4      0.070     13.22        49.27   
  done · converged · 4 iters · reduced χ² 49.27 · Rwp 13.22 % · 0.08 s

  refined parameters (35 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     379.4        379.4       7.6   
  intensity       experiment.background[11].intensity                     422.6        422.3       6.7   0.1% ↓
  intensity       experiment.background[12].intensity                     414.3        413.1       6.4   0.3% ↓
  intensity       experiment.background[13].intensity                     395.3        395.2       6.5   
  intensity       experiment.background[14].intensity                       341        339.6       6.2   0.4% ↓
  intensity       experiment.background[15].intensity                     276.3        275.7       5.8   0.2% ↓
  intensity       experiment.background[16].intensity                     225.9        229.3       8.3   1.5% ↑
  intensity       experiment.background[1].intensity                        614          614        74   
  intensity       experiment.background[2].intensity                        593          593        46   0.1% ↓
  intensity       experiment.background[3].intensity                        536          536        40   0.1% ↑
  intensity       experiment.background[4].intensity                        636          636        19   0.1% ↓
  intensity       experiment.background[5].intensity                        532          532        19   0.1% ↓
  intensity       experiment.background[6].intensity                        404          404        38   
  intensity       experiment.background[7].intensity                        419          419        25   
  intensity       experiment.background[8].intensity                        423          422        12   0.3% ↓
  intensity       experiment.background[9].intensity                        455          455        11   0.1% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.3814       0.3819    0.0061   0.1% ↑
  scale           experiment.linked_structures[cosio].scale               1.926        1.937     0.025   0.6% ↑
  U, deg²         experiment.peak.broad_gauss_u                           0.189        0.187     0.020   0.9% ↓
  V, deg²         experiment.peak.broad_gauss_v                          -0.349       -0.342     0.043 ! 1.9% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.272        0.268     0.023 ! 1.4% ↓
  x               structure.atom_sites[Co2].fract_x                     0.28090       0.2787    0.0020   0.8% ↓
  z               structure.atom_sites[Co2].fract_z                     0.98360       0.9774    0.0044   0.6% ↓
  x               structure.atom_sites[O1].fract_x                      0.08960      0.08805   0.00086   1.7% ↓
  z               structure.atom_sites[O1].fract_z                      0.77300       0.7770    0.0020   0.5% ↑
  x               structure.atom_sites[O2].fract_x                      0.44780      0.44807   0.00076   0.1% ↑
  z               structure.atom_sites[O2].fract_z                      0.21790       0.2180    0.0021   
  x               structure.atom_sites[O3].fract_x                      0.16390      0.16277   0.00066   0.7% ↓
  y               structure.atom_sites[O3].fract_y                      0.03210       0.0318    0.0010   1.1% ↓
  z               structure.atom_sites[O3].fract_z                      0.28050       0.2807    0.0015   0.1% ↑
  x               structure.atom_sites[Si].fract_x                      0.09330       0.0925    0.0012   0.8% ↓
  z               structure.atom_sites[Si].fract_z                      0.42780       0.4283    0.0025   0.1% ↑
  a, Å            structure.cell.length_a                               10.3142     10.31429   0.00080   
  b, Å            structure.cell.length_b                                6.0059      6.00592   0.00049   
  c, Å            structure.cell.length_c                                4.7905      4.79048   0.00038   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_v: strongly correlated with W (d20) (r = -0.96)
      experiment.peak.broad_gauss_w: strongly correlated with V (d20) (r = -0.96)
```

## Displacements

Co2's displacement follows Co1's by the project's constraint.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co1 Co 0 0 0 a 4 1 0.269() Biso
Si Si 0.0925() 0.25 0.4283() c 4 1 0.466() Biso
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_scan-213f, 1438 pts fitted / 1506 loaded, 40 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.22        49.45
      1      0.029     13.01        47.86   3.2% ↓
      2      0.040     13.00        47.83   0.1% ↓
      3      0.051     13.00        47.83   
      4      0.071     13.00        47.83   
  done · converged · 4 iters · reduced χ² 47.83 · Rwp 13.00 % · 0.09 s

  refined parameters (40 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     379.4        373.0       7.6   1.7% ↓
  intensity       experiment.background[11].intensity                     422.3        413.7       6.8   2.0% ↓
  intensity       experiment.background[12].intensity                     413.1        411.5       6.4   0.4% ↓
  intensity       experiment.background[13].intensity                     395.2        400.3       6.4   1.3% ↑
  intensity       experiment.background[14].intensity                     339.6        350.9       6.3   3.3% ↑
  intensity       experiment.background[15].intensity                     275.7        286.8       5.9   4.0% ↑
  intensity       experiment.background[16].intensity                     229.3        250.8       8.7   9.4% ↑
  intensity       experiment.background[1].intensity                        614          614        73   
  intensity       experiment.background[2].intensity                        593          592        45   0.1% ↓
  intensity       experiment.background[3].intensity                        536          537        39   0.2% ↑
  intensity       experiment.background[4].intensity                        636          634        19   0.3% ↓
  intensity       experiment.background[5].intensity                        532          530        18   0.4% ↓
  intensity       experiment.background[6].intensity                        404          404        37   0.1% ↑
  intensity       experiment.background[7].intensity                        419          419        25   0.1% ↓
  intensity       experiment.background[8].intensity                        422          422        11   0.1% ↑
  intensity       experiment.background[9].intensity                        455          449        11   1.3% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.3819       0.3833    0.0059   0.4% ↑
  scale           experiment.linked_structures[cosio].scale               1.937        2.243     0.055   15.8% ↑
  U, deg²         experiment.peak.broad_gauss_u                           0.187        0.178     0.019   5.0% ↓
  V, deg²         experiment.peak.broad_gauss_v                          -0.342       -0.362     0.041 ! 5.8% ↓
  W, deg²         experiment.peak.broad_gauss_w                           0.268        0.291     0.022 ! 8.8% ↑
  B iso, Å²       structure.atom_sites[Co1].adp_iso                       0.269         0.88      0.26   226.3% ↑
  x               structure.atom_sites[Co2].fract_x                     0.27870       0.2796    0.0021   0.3% ↑
  z               structure.atom_sites[Co2].fract_z                     0.97740       0.9764    0.0047   0.1% ↓
  B iso, Å²       structure.atom_sites[O1].adp_iso                        0.778         1.53      0.19   96.8% ↑
  x               structure.atom_sites[O1].fract_x                      0.08805      0.08841   0.00092   0.4% ↑
  z               structure.atom_sites[O1].fract_z                      0.77700       0.7780    0.0021   0.1% ↑
  B iso, Å²       structure.atom_sites[O2].adp_iso                        0.642         1.17      0.19   82.9% ↑
  x               structure.atom_sites[O2].fract_x                      0.44807      0.44871   0.00078   0.1% ↑
  z               structure.atom_sites[O2].fract_z                      0.21800       0.2191    0.0021   0.5% ↑
  B iso, Å²       structure.atom_sites[O3].adp_iso                        0.917         1.61      0.16   75.5% ↑
  x               structure.atom_sites[O3].fract_x                      0.16277      0.16254   0.00070   0.1% ↓
  y               structure.atom_sites[O3].fract_y                      0.03180       0.0322    0.0011   1.1% ↑
  z               structure.atom_sites[O3].fract_z                      0.28070       0.2797    0.0016   0.4% ↓
  B iso, Å²       structure.atom_sites[Si].adp_iso                        0.466         1.24      0.21   166.0% ↑
  x               structure.atom_sites[Si].fract_x                      0.09250       0.0919    0.0013   0.7% ↓
  z               structure.atom_sites[Si].fract_z                      0.42830       0.4255    0.0026   0.7% ↓
  a, Å            structure.cell.length_a                               10.3143     10.31437   0.00080   
  b, Å            structure.cell.length_b                                6.0059      6.00597   0.00049   
  c, Å            structure.cell.length_c                                4.7905      4.79048   0.00038   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_v: strongly correlated with W (d20) (r = -0.95)
      experiment.peak.broad_gauss_w: strongly correlated with V (d20) (r = -0.95)
```

## Magnetic moments

Last, the moments: Co1 in any direction, Co2 along b.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co1 0() 1() 0() Mx,My,Mz
Co2 0 1() 0 0,My,0
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_scan-213f --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_scan-213f, 1438 pts fitted / 1506 loaded, 44 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.00        47.97
      1      0.031      5.89         9.83   79.5% ↓
      2      0.043      4.71         6.29   36.1% ↓
      3      0.056      4.70         6.25   0.6% ↓
      4      0.070      4.69         6.25   0.1% ↓
      5      0.086      4.69         6.25   
      6      0.101      4.69         6.25   0.1% ↓
      7      0.118      4.69         6.24   
      8      0.131      4.69         6.24   0.1% ↓
      9      0.146      4.69         6.24   
     10      0.160      4.69         6.24   
     11      0.184      4.69         6.24   
  done · converged · 11 iters · reduced χ² 6.24 · Rwp 4.69 % · 0.20 s

  refined parameters (44 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                       373        370.6       2.8   0.6% ↓
  intensity       experiment.background[11].intensity                     413.7        405.5       2.5   2.0% ↓
  intensity       experiment.background[12].intensity                     411.5        403.6       2.4   1.9% ↓
  intensity       experiment.background[13].intensity                     400.3        397.2       2.3   0.8% ↓
  intensity       experiment.background[14].intensity                     350.9        343.6       2.3   2.1% ↓
  intensity       experiment.background[15].intensity                     286.8        279.3       2.2   2.6% ↓
  intensity       experiment.background[16].intensity                     250.8        234.9       3.3   6.4% ↓
  intensity       experiment.background[1].intensity                        614          620        27   0.9% ↑
  intensity       experiment.background[2].intensity                        592          584        17   1.4% ↓
  intensity       experiment.background[3].intensity                        537          566        15   5.4% ↑
  intensity       experiment.background[4].intensity                        634        532.2       7.0   16.1% ↓
  intensity       experiment.background[5].intensity                        530        425.6       6.7   19.7% ↓
  intensity       experiment.background[6].intensity                        404          425        14   5.3% ↑
  intensity       experiment.background[7].intensity                        419        420.3       8.9   0.3% ↑
  intensity       experiment.background[8].intensity                        422        411.0       4.0   2.6% ↓
  intensity       experiment.background[9].intensity                        449        382.4       3.9   14.8% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.3833       0.3875    0.0019   1.1% ↑
  scale           experiment.linked_structures[cosio].scale               2.243        1.779     0.019   20.7% ↓
  U, deg²         experiment.peak.broad_gauss_u                           0.178       0.1998    0.0064   12.2% ↑
  V, deg²         experiment.peak.broad_gauss_v                          -0.362       -0.404     0.014   11.5% ↓
  W, deg²         experiment.peak.broad_gauss_w                           0.291       0.3077    0.0067   5.8% ↑
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x          0.0000        1.011     0.038   
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y          1.0000        3.013     0.024   201.3% ↑
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z          0.0000         0.03      0.81   
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y          1.0000        2.601     0.037   160.1% ↑
  B iso, Å²       structure.atom_sites[Co1].adp_iso                       0.880        0.351     0.088   60.2% ↓
  x               structure.atom_sites[Co2].fract_x                     0.27960      0.27735   0.00060   0.8% ↓
  z               structure.atom_sites[Co2].fract_z                     0.97640       0.9825    0.0018   0.6% ↑
  B iso, Å²       structure.atom_sites[O1].adp_iso                        1.530        0.799     0.069   47.8% ↓
  x               structure.atom_sites[O1].fract_x                      0.08841      0.09044   0.00036   2.3% ↑
  z               structure.atom_sites[O1].fract_z                      0.77800      0.77149   0.00079   0.8% ↓
  B iso, Å²       structure.atom_sites[O2].adp_iso                        1.170        0.671     0.071   42.6% ↓
  x               structure.atom_sites[O2].fract_x                      0.44871      0.44831   0.00031   0.1% ↓
  z               structure.atom_sites[O2].fract_z                      0.21910      0.21508   0.00082   1.8% ↓
  B iso, Å²       structure.atom_sites[O3].adp_iso                        1.610        1.008     0.058   37.4% ↓
  x               structure.atom_sites[O3].fract_x                      0.16254      0.16344   0.00028   0.6% ↑
  y               structure.atom_sites[O3].fract_y                      0.03220      0.03186   0.00040   1.1% ↓
  z               structure.atom_sites[O3].fract_z                      0.27970      0.27936   0.00061   0.1% ↓
  B iso, Å²       structure.atom_sites[Si].adp_iso                        1.240        0.568     0.076   54.2% ↓
  x               structure.atom_sites[Si].fract_x                      0.09190      0.09442   0.00047   2.7% ↑
  z               structure.atom_sites[Si].fract_z                      0.42550       0.4288    0.0011   0.8% ↑
  a, Å            structure.cell.length_a                               10.3144     10.31488   0.00028   
  b, Å            structure.cell.length_b                                6.0060      6.00600   0.00017   
  c, Å            structure.cell.length_c                                4.7905      4.79073   0.00013   

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
    edi fit pd-neut-cwl_cosio-d20_scan-213f
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_scan-213f
    ```

```text
[░░░░░░░░░░░░░░] · 1/213 · 0% · elapsed 0s · eta 1m00s · 1 ok · 0 fail · 01_213_002p3440 · reduced χ² 6.24
[░░░░░░░░░░░░░░] · 2/213 · 1% · elapsed 0s · eta 46s · 2 ok · 0 fail · 01_212_002p3560 · reduced χ² 5.95
[░░░░░░░░░░░░░░] · 3/213 · 1% · elapsed 1s · eta 47s · 3 ok · 0 fail · 01_211_002p3630 · reduced χ² 6.25
[░░░░░░░░░░░░░░] · 4/213 · 2% · elapsed 1s · eta 46s · 4 ok · 0 fail · 01_210_002p3820 · reduced χ² 6.08
[░░░░░░░░░░░░░░] · 5/213 · 2% · elapsed 1s · eta 44s · 5 ok · 0 fail · 01_209_002p4210 · reduced χ² 6.06
[░░░░░░░░░░░░░░] · 6/213 · 3% · elapsed 1s · eta 48s · 6 ok · 0 fail · 01_208_008p5330 · reduced χ² 5.99
…
[██████████████] · 209/213 · 98% · elapsed 48s · eta 1s · 209 ok · 0 fail · 01_005_496p5900 · reduced χ² 5.23
[██████████████] · 210/213 · 99% · elapsed 48s · eta 1s · 210 ok · 0 fail · 01_004_497p0360 · reduced χ² 5.20
[██████████████] · 211/213 · 99% · elapsed 48s · eta 0s · 211 ok · 0 fail · 01_003_497p2280 · reduced χ² 5.52
[██████████████] · 212/213 · 100% · elapsed 48s · eta 0s · 212 ok · 0 fail · 01_002_497p3410 · reduced χ² 5.50
[██████████████] · 213/213 · 100% · elapsed 49s · 213 ok · 0 fail
scan · 213 files · 213 converged · 0 failed · reduced χ² 4.32-6.25 · 49s
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-neut-cwl_cosio-d20_scan-213f --output pd-neut-cwl_cosio-d20_scan-213f.html
    ```
