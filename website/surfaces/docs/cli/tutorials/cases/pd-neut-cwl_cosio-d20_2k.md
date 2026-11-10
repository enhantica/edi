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
                       14.28        56.28
      1      0.020     14.03        54.28   3.6% ↓
      2      0.035     14.03        54.28   
  done · converged · 2 iters · reduced χ² 54.28 · Rwp 14.03 % · 0.04 s

  refined parameters (5 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2943       0.2906    0.0064   1.3% ↓
  scale           experiment.linked_structures[cosio].scale              1.8172        1.959     0.021   7.8% ↑
  a, Å            structure.cell.length_a                               10.3081     10.30705   0.00082   
  b, Å            structure.cell.length_b                                6.0022      6.00164   0.00049   
  c, Å            structure.cell.length_c                                4.7874      4.78692   0.00038   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
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
                       14.03        54.89
      1      0.024     13.20        48.60   11.5% ↓
      2      0.041     13.20        48.60   
  done · converged · 2 iters · reduced χ² 48.60 · Rwp 13.20 % · 0.05 s

  refined parameters (21 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    373.16        379.7       7.5   1.7% ↑
  intensity       experiment.background[11].intensity                    406.37        419.7       6.5   3.3% ↑
  intensity       experiment.background[12].intensity                    408.51        413.6       6.2   1.2% ↑
  intensity       experiment.background[13].intensity                       396        395.4       6.2   0.1% ↓
  intensity       experiment.background[14].intensity                    345.92        342.2       5.9   1.1% ↓
  intensity       experiment.background[15].intensity                    279.04        275.8       5.4   1.2% ↓
  intensity       experiment.background[16].intensity                     230.7        224.0       7.4   2.9% ↓
  intensity       experiment.background[1].intensity                      603.5          614        74   1.7% ↑
  intensity       experiment.background[2].intensity                        585          593        46   1.4% ↑
  intensity       experiment.background[3].intensity                      568.5          534        40   6.0% ↓
  intensity       experiment.background[4].intensity                      528.8          643        19   21.7% ↑
  intensity       experiment.background[5].intensity                      418.9          529        18   26.2% ↑
  intensity       experiment.background[6].intensity                      420.2          405        37   3.7% ↓
  intensity       experiment.background[7].intensity                      416.5          418        25   0.5% ↑
  intensity       experiment.background[8].intensity                     416.05          423        11   1.6% ↑
  intensity       experiment.background[9].intensity                     394.77          457        11   15.6% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2906       0.2904    0.0061   0.1% ↓
  scale           experiment.linked_structures[cosio].scale               1.959        1.948     0.023   0.6% ↓
  a, Å            structure.cell.length_a                               10.3071     10.30707   0.00078   
  b, Å            structure.cell.length_b                                6.0016      6.00159   0.00046   
  c, Å            structure.cell.length_c                                4.7869      4.78692   0.00036   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
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
                       13.20        48.74
      1      0.023     13.13        48.24   1.0% ↓
      2      0.031     13.13        48.23   
      3      0.048     13.13        48.23   
  done · converged · 3 iters · reduced χ² 48.23 · Rwp 13.13 % · 0.06 s

  refined parameters (25 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     379.7        379.7       7.4   
  intensity       experiment.background[11].intensity                     419.7        419.8       7.0   
  intensity       experiment.background[12].intensity                     413.6        412.7       6.3   0.2% ↓
  intensity       experiment.background[13].intensity                     395.4        392.3       6.7   0.8% ↓
  intensity       experiment.background[14].intensity                     342.2        340.2       6.1   0.6% ↓
  intensity       experiment.background[15].intensity                     275.8        275.3       5.5   0.2% ↓
  intensity       experiment.background[16].intensity                       224        222.6       7.8   0.6% ↓
  intensity       experiment.background[1].intensity                        614          614        74   
  intensity       experiment.background[2].intensity                        593          593        45   
  intensity       experiment.background[3].intensity                        534          534        40   
  intensity       experiment.background[4].intensity                        643          643        19   0.1% ↑
  intensity       experiment.background[5].intensity                        529          529        18   
  intensity       experiment.background[6].intensity                        405          404        37   0.1% ↓
  intensity       experiment.background[7].intensity                        418          418        25   0.1% ↑
  intensity       experiment.background[8].intensity                        423          423        11   
  intensity       experiment.background[9].intensity                        457          457        11   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2904       0.2908    0.0059   0.1% ↑
  scale           experiment.linked_structures[cosio].scale               1.948        1.970     0.036   1.1% ↑
  U, deg²         experiment.peak.broad_gauss_u                         0.27353        0.216     0.020   20.9% ↓
  V, deg²         experiment.peak.broad_gauss_v                        -0.58972       -0.443     0.041   24.9% ↑
  W, deg²         experiment.peak.broad_gauss_w                         0.41301        0.323     0.024   21.8% ↓
  Y, deg          experiment.peak.broad_lorentz_y                      0.017548        0.031     0.013   75.9% ↑
  a, Å            structure.cell.length_a                               10.3071     10.30697   0.00078   
  b, Å            structure.cell.length_b                                6.0016      6.00166   0.00047   
  c, Å            structure.cell.length_c                                4.7869      4.78694   0.00037   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
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
                       13.13        48.26
      1      0.070     13.13        48.26   
      2      0.083     13.13        48.26   
      3      0.091     13.13        48.26   
      4      0.100     13.13        48.26   
      5      0.108     13.13        48.26   
      6      0.117     13.13        48.26   
      7      0.127     13.13        48.26   
      8      0.148     13.13        48.26   
      9      0.158     13.13        48.25   
     10      0.168     13.13        48.25   
     11      0.176     13.13        48.25   
     12      0.185     13.13        48.25   
     13      0.203     13.13        48.25   
  done · converged · 13 iters · reduced χ² 48.25 · Rwp 13.13 % · 0.21 s

  refined parameters (26 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     379.7        379.7       7.4   
  intensity       experiment.background[11].intensity                     419.8        419.8       7.0   
  intensity       experiment.background[12].intensity                     412.7        412.7       6.3   
  intensity       experiment.background[13].intensity                     392.3        392.3       6.7   
  intensity       experiment.background[14].intensity                     340.2        340.2       6.1   
  intensity       experiment.background[15].intensity                     275.3        275.3       5.5   
  intensity       experiment.background[16].intensity                     222.6        222.6       7.8   
  intensity       experiment.background[1].intensity                        614          614        74   
  intensity       experiment.background[2].intensity                        593          593        45   
  intensity       experiment.background[3].intensity                        534          534        40   
  intensity       experiment.background[4].intensity                        643          643        19   
  intensity       experiment.background[5].intensity                        529          529        18   0.1% ↑
  intensity       experiment.background[6].intensity                        404          404        37   0.1% ↑
  intensity       experiment.background[7].intensity                        418          418        25   0.1% ↑
  intensity       experiment.background[8].intensity                        423          423        11   
  intensity       experiment.background[9].intensity                        457          457        11   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2908        0.296     0.016   1.6% ↑
  scale           experiment.linked_structures[cosio].scale                1.97        1.970     0.036   
  S/L             experiment.peak.asym_fcj_1                                  0        0.014     0.021   
  U, deg²         experiment.peak.broad_gauss_u                           0.216        0.216     0.020   0.2% ↑
  V, deg²         experiment.peak.broad_gauss_v                          -0.443       -0.443     0.041   
  W, deg²         experiment.peak.broad_gauss_w                           0.323        0.323     0.024   
  Y, deg          experiment.peak.broad_lorentz_y                         0.031        0.031     0.013   0.4% ↓
  a, Å            structure.cell.length_a                               10.3070      10.3074    0.0014   
  b, Å            structure.cell.length_b                                6.0017      6.00188   0.00080   
  c, Å            structure.cell.length_c                                4.7869      4.78712   0.00065   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
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
                       13.13        48.63
      1      0.032     13.06        48.16   1.0% ↓
      2      0.042     13.06        48.15   
      3      0.068     13.06        48.14   
      4      0.086     13.06        48.14   
      5      0.104     13.06        48.14   
      6      0.118     13.06        48.14   
      7      0.148     13.06        48.14   
  done · converged · 7 iters · reduced χ² 48.14 · Rwp 13.06 % · 0.16 s

  refined parameters (37 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     379.7        379.9       7.5   
  intensity       experiment.background[11].intensity                     419.8        419.2       7.1   0.1% ↓
  intensity       experiment.background[12].intensity                     412.7        412.1       6.4   0.2% ↓
  intensity       experiment.background[13].intensity                     392.3        391.7       6.8   0.2% ↓
  intensity       experiment.background[14].intensity                     340.2        339.4       6.3   0.2% ↓
  intensity       experiment.background[15].intensity                     275.3        275.0       5.8   0.1% ↓
  intensity       experiment.background[16].intensity                     222.6        224.6       8.6   0.9% ↑
  intensity       experiment.background[1].intensity                        614          614        74   
  intensity       experiment.background[2].intensity                        593          593        45   
  intensity       experiment.background[3].intensity                        534          534        40   
  intensity       experiment.background[4].intensity                        643          643        19   
  intensity       experiment.background[5].intensity                        529          529        18   
  intensity       experiment.background[6].intensity                        404          404        37   0.1% ↑
  intensity       experiment.background[7].intensity                        418          419        25   0.2% ↑
  intensity       experiment.background[8].intensity                        423          422        11   0.3% ↓
  intensity       experiment.background[9].intensity                        457          458        11   0.2% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2960        0.296     0.016   
  scale           experiment.linked_structures[cosio].scale                1.97        1.980     0.037   0.5% ↑
  S/L             experiment.peak.asym_fcj_1                              0.014        0.014     0.020   0.2% ↓
  U, deg²         experiment.peak.broad_gauss_u                           0.216        0.216     0.021   
  V, deg²         experiment.peak.broad_gauss_v                          -0.443       -0.440     0.042   0.7% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.323        0.321     0.025   0.6% ↓
  Y, deg          experiment.peak.broad_lorentz_y                         0.031        0.031     0.013   0.2% ↓
  x               structure.atom_sites[Co2].fract_x                     0.28090       0.2788    0.0020   0.8% ↓
  z               structure.atom_sites[Co2].fract_z                     0.98360       0.9785    0.0044   0.5% ↓
  x               structure.atom_sites[O1].fract_x                      0.08960      0.08834   0.00085   1.4% ↓
  z               structure.atom_sites[O1].fract_z                      0.77300       0.7775    0.0020   0.6% ↑
  x               structure.atom_sites[O2].fract_x                      0.44780      0.44805   0.00075   0.1% ↑
  z               structure.atom_sites[O2].fract_z                      0.21790       0.2190    0.0020   0.5% ↑
  x               structure.atom_sites[O3].fract_x                      0.16390      0.16278   0.00065   0.7% ↓
  y               structure.atom_sites[O3].fract_y                      0.03210      0.03133   0.00099   2.4% ↓
  z               structure.atom_sites[O3].fract_z                      0.28050       0.2810    0.0015   0.2% ↑
  x               structure.atom_sites[Si].fract_x                      0.09330       0.0917    0.0012   1.8% ↓
  z               structure.atom_sites[Si].fract_z                      0.42780       0.4279    0.0024   
  a, Å            structure.cell.length_a                               10.3074      10.3074    0.0014   
  b, Å            structure.cell.length_b                                6.0019      6.00187   0.00081   
  c, Å            structure.cell.length_c                                4.7871      4.78716   0.00066   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Magnetic moments

With the nuclear peaks fitted, the moments fit the magnetic peaks. The magnetic space group lets
Co1 point in any direction and Co2 only along b.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co1 0() 1() 0() Mx,My,Mz
Co2 0 1() 0 0,My,0
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
                       13.06        48.28
      1      0.042     10.59        31.77   34.2% ↓
      2      0.053      7.03        14.00   55.9% ↓
      3      0.065      6.73        12.82   8.4% ↓
      4      0.077      6.04        10.32   19.5% ↓
      5      0.088      5.57         8.79   14.8% ↓
      6      0.102      5.43         8.35   5.0% ↓
      7      0.113      5.04         7.19   13.9% ↓
      8      0.123      4.89         6.78   5.7% ↓
      9      0.144      4.88         6.75   0.5% ↓
     10      0.154      4.88         6.75   
     11      0.186      4.87         6.72   0.3% ↓
     12      0.208      4.87         6.72   0.1% ↓
     13      0.221      4.87         6.72   
     14      0.238      4.87         6.72   
     15      0.255      4.87         6.72   
     16      0.268      4.87         6.72   
     17      0.284      4.87         6.72   
     18      0.298      4.87         6.72   
     19      0.312      4.87         6.72   
     20      0.329      4.87         6.72   
     21      0.349      4.87         6.72   
     22      0.364      4.87         6.71   
     23      0.380      4.87         6.71   
     24      0.396      4.87         6.71   
     25      0.410      4.87         6.71   
     26      0.429      4.87         6.71   
     27      0.446      4.87         6.71   
     28      0.460      4.87         6.71   
     29      0.476      4.87         6.71   
     30      0.491      4.87         6.71   
     31      0.504      4.87         6.71   
     32      0.521      4.87         6.71   
     33      0.538      4.87         6.71   
     34      0.552      4.87         6.71   
     35      0.569      4.87         6.71   
     36      0.583      4.87         6.71   
     37      0.599      4.87         6.71   
     38      0.612      4.87         6.71   
     39      0.629      4.87         6.71   
     40      0.647      4.87         6.71   
     41      0.675      4.87         6.71   
     42      0.693      4.87         6.71   
     43      0.711      4.87         6.71   
     44      0.724      4.87         6.71   
     45      0.752      4.87         6.71   
  done · converged · 45 iters · reduced χ² 6.71 · Rwp 4.87 % · 0.77 s

  refined parameters (41 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     379.9        370.2       2.9   2.5% ↓
  intensity       experiment.background[11].intensity                     419.2        408.1       2.7   2.7% ↓
  intensity       experiment.background[12].intensity                     412.1        407.7       2.4   1.1% ↓
  intensity       experiment.background[13].intensity                     391.7        398.8       2.6   1.8% ↑
  intensity       experiment.background[14].intensity                     339.4        345.2       2.4   1.7% ↑
  intensity       experiment.background[15].intensity                       275        279.1       2.2   1.5% ↑
  intensity       experiment.background[16].intensity                     224.6        236.7       3.2   5.4% ↑
  intensity       experiment.background[1].intensity                        614          620        28   0.9% ↑
  intensity       experiment.background[2].intensity                        593          584        17   1.6% ↓
  intensity       experiment.background[3].intensity                        534          567        15   6.2% ↑
  intensity       experiment.background[4].intensity                        643        528.6       8.4   17.8% ↓
  intensity       experiment.background[5].intensity                        529        424.8       7.0   19.7% ↓
  intensity       experiment.background[6].intensity                        404          425        14   5.3% ↑
  intensity       experiment.background[7].intensity                        419        420.4       9.2   0.3% ↑
  intensity       experiment.background[8].intensity                        422        410.6       4.2   2.7% ↓
  intensity       experiment.background[9].intensity                        458        380.0       4.1   17.0% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2960       0.3910    0.0031   32.1% ↑
  scale           experiment.linked_structures[cosio].scale                1.98        1.783     0.014   9.9% ↓
  S/L             experiment.peak.asym_fcj_1                              0.014      0.06255   0.00090   346.8% ↑
  U, deg²         experiment.peak.broad_gauss_u                           0.216       0.2023    0.0076   6.3% ↓
  V, deg²         experiment.peak.broad_gauss_v                           -0.44       -0.403     0.016   8.4% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.321       0.3041    0.0090   5.3% ↓
  Y, deg          experiment.peak.broad_lorentz_y                         0.031       0.0117    0.0047   62.2% ↓
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x          0.0000        0.991     0.041   
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y          1.0000        3.086     0.025   208.6% ↑
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z          0.0000         0.03      0.95   
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y          1.0000        2.746     0.038   174.6% ↑
  x               structure.atom_sites[Co2].fract_x                     0.27880      0.27857   0.00064   0.1% ↓
  z               structure.atom_sites[Co2].fract_z                     0.97850       0.9824    0.0018   0.4% ↑
  x               structure.atom_sites[O1].fract_x                      0.08834      0.08983   0.00036   1.7% ↑
  z               structure.atom_sites[O1].fract_z                      0.77750      0.77202   0.00080   0.7% ↓
  x               structure.atom_sites[O2].fract_x                      0.44805      0.44810   0.00031   
  z               structure.atom_sites[O2].fract_z                      0.21900      0.21550   0.00083   1.6% ↓
  x               structure.atom_sites[O3].fract_x                      0.16278      0.16361   0.00027   0.5% ↑
  y               structure.atom_sites[O3].fract_y                      0.03133      0.03190   0.00040   1.8% ↑
  z               structure.atom_sites[O3].fract_z                      0.28100      0.27979   0.00060   0.4% ↓
  x               structure.atom_sites[Si].fract_x                      0.09170      0.09411   0.00047   2.6% ↑
  z               structure.atom_sites[Si].fract_z                      0.42790      0.42846   0.00098   0.1% ↑
  a, Å            structure.cell.length_a                               10.3074     10.31519   0.00035   0.1% ↑
  b, Å            structure.cell.length_b                                6.0019      6.00633   0.00021   0.1% ↑
  c, Å            structure.cell.length_c                                4.7872      4.79084   0.00017   0.1% ↑

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
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
      1      0.032      4.79         6.50   3.2% ↓
      2      0.045      4.70         6.26   3.7% ↓
      3      0.072      4.70         6.26   
      4      0.086      4.70         6.26   0.1% ↓
      5      0.109      4.70         6.25   0.1% ↓
      6      0.125      4.70         6.25   
      7      0.139      4.70         6.25   
      8      0.157      4.70         6.25   
      9      0.170      4.70         6.25   
     10      0.187      4.70         6.25   
     11      0.201      4.70         6.25   
     12      0.215      4.70         6.25   
     13      0.232      4.70         6.25   
     14      0.245      4.70         6.25   
     15      0.273      4.70         6.25   
  done · converged · 15 iters · reduced χ² 6.25 · Rwp 4.70 % · 0.31 s

  refined parameters (42 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiment.background[10].intensity                       370.2        371.2       2.8   0.3% ↑
  intensity       experiment.background[11].intensity                       408.1        405.4       2.6   0.7% ↓
  intensity       experiment.background[12].intensity                       407.7        403.1       2.4   1.1% ↓
  intensity       experiment.background[13].intensity                       398.8        396.0       2.5   0.7% ↓
  intensity       experiment.background[14].intensity                       345.2        342.0       2.3   0.9% ↓
  intensity       experiment.background[15].intensity                       279.1        277.6       2.1   0.5% ↓
  intensity       experiment.background[16].intensity                       236.7        231.7       3.1   2.1% ↓
  intensity       experiment.background[1].intensity                          620          619        27   0.1% ↓
  intensity       experiment.background[2].intensity                          584          584        17   
  intensity       experiment.background[3].intensity                          567          565        15   0.4% ↓
  intensity       experiment.background[4].intensity                        528.6        535.5       7.9   1.3% ↑
  intensity       experiment.background[5].intensity                        424.8        425.0       6.8   
  intensity       experiment.background[6].intensity                          425          425        14   0.1% ↑
  intensity       experiment.background[7].intensity                        420.4        420.1       8.9   0.1% ↓
  intensity       experiment.background[8].intensity                        410.6        411.1       4.0   0.1% ↑
  intensity       experiment.background[9].intensity                          380        382.9       4.0   0.8% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset              0.3910       0.3854    0.0030   1.4% ↓
  scale           experiment.linked_structures[cosio].scale                 1.783        1.761     0.013   1.2% ↓
  S/L             experiment.peak.asym_fcj_1                              0.06255      0.06111   0.00088   2.3% ↓
  U, deg²         experiment.peak.broad_gauss_u                            0.2023       0.2012    0.0073   0.5% ↓
  V, deg²         experiment.peak.broad_gauss_v                            -0.403       -0.406     0.015   0.7% ↓
  W, deg²         experiment.peak.broad_gauss_w                            0.3041       0.3062    0.0087   0.7% ↑
  Y, deg          experiment.peak.broad_lorentz_y                          0.0117       0.0154    0.0045   31.7% ↑
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x            0.9910        1.011     0.039   2.0% ↑
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y            3.0860        3.019     0.024   2.2% ↓
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z            0.0300         0.04      0.75   18.4% ↑
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y            2.7460        2.616     0.038   4.7% ↓
  x               structure.atom_sites[Co2].fract_x                       0.27857      0.27719   0.00060   0.5% ↓
  z               structure.atom_sites[Co2].fract_z                       0.98240       0.9829    0.0017   0.1% ↑
  x               structure.atom_sites[O1].fract_x                        0.08983      0.09047   0.00036   0.7% ↑
  z               structure.atom_sites[O1].fract_z                        0.77202      0.77144   0.00079   0.1% ↓
  x               structure.atom_sites[O2].fract_x                        0.44810      0.44830   0.00031   
  z               structure.atom_sites[O2].fract_z                        0.21550      0.21500   0.00082   0.2% ↓
  x               structure.atom_sites[O3].fract_x                        0.16361      0.16342   0.00027   0.1% ↓
  y               structure.atom_sites[O3].fract_y                        0.03190      0.03174   0.00039   0.5% ↓
  z               structure.atom_sites[O3].fract_z                        0.27979      0.27947   0.00060   0.1% ↓
  x               structure.atom_sites[Si].fract_x                        0.09411      0.09445   0.00046   0.4% ↑
  z               structure.atom_sites[Si].fract_z                        0.42846      0.42907   0.00097   0.1% ↑
  a, Å            structure.cell.length_a                                 10.3152     10.31471   0.00034   
  b, Å            structure.cell.length_b                                  6.0063      6.00591   0.00021   
  c, Å            structure.cell.length_c                                  4.7908      4.79065   0.00016   
  C₂              structure.magnetic_form_factor[Co].j2_coefficient        0.0000        0.589     0.055   

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
    python -m edi report pd-neut-cwl_cosio-d20_2k --output pd-neut-cwl_cosio-d20_2k.html
    ```
