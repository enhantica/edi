# Co₂SiO₄ on D20

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

This tutorial fits the olivine Co₂SiO₄ to constant-wavelength neutron powder data measured on
D20 at the ILL. Its structure and its measured pattern come from EasyDiffraction's collection;
the tutorial describes the experiment, links the two and fits the coordinates, the
displacements and the oxygen occupancies.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_cosio-d20
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_cosio-d20
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/d20.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_twotheta_offset 0
_peak.broad_gauss_u 0.2
_peak.broad_gauss_v -0.5
_peak.broad_gauss_w 0.4
_peak.broad_lorentz_y 0.01
1 8 340
2 9 340
```

The same for every other row (13 more).

In `structures/cosio.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 10.3
_cell.length_b 6
_cell.length_c 4.8
Co1 Co 0 0 0 a 4 1 0.5 Biso
Co2 Co 0.28 0.25 0.98 c 4 1 0.5 Biso
```

The same for every other row (4 more).

## Scale, 2θ zero and cell

The scale sets the overall height of the pattern, and the zero shift and the three cell lengths
put the peaks where they are measured.

In `experiments/d20.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
cosio 1() 1.0
```

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 10.3()
_cell.length_b 6()
_cell.length_c 4.8()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20, 1418 pts fitted / 1418 loaded, 5 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       40.51       452.05
      1      0.014     32.67       294.01   35.0% ↓
      2      0.019     28.53       224.11   23.8% ↓
      3      0.024     24.08       159.67   28.8% ↓
      4      0.028     20.62       117.12   26.6% ↓
      5      0.033     20.11       111.36   4.9% ↓
      6      0.037     20.10       111.23   0.1% ↓
      7      0.041     20.10       111.22   
      8      0.046     20.10       111.22   
      9      0.054     20.10       111.22   
  done · converged · 9 iters · reduced χ² 111.22 · Rwp 20.10 % · 0.06 s

  refined parameters (5 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0000       0.2871    0.0086   
  scale           experiment.linked_structures[cosio].scale                   1        1.185     0.019   18.5% ↑
  a, Å            structure.cell.length_a                               10.3000     10.30861   0.00098   0.1% ↑
  b, Å            structure.cell.length_b                                6.0000      6.00413   0.00061   0.1% ↑
  c, Å            structure.cell.length_c                                4.8000      4.78646   0.00048   0.3% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

With the peaks in place, the fourteen background points follow the level between them.

In `experiments/d20.edi`, add `()` after the values the stage frees:

```edi
1 8 340()
2 9 340()
```

The same for every other row (12 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20, 1418 pts fitted / 1418 loaded, 19 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       20.10       112.33
      1      0.019      5.51         8.45   92.5% ↓
      2      0.024      5.51         8.45   
      3      0.028      5.51         8.45   
      4      0.039      5.51         8.45   
  done · converged · 4 iters · reduced χ² 8.45 · Rwp 5.51 % · 0.04 s

  refined parameters (19 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                       340        432.6       2.7   27.2% ↑
  intensity       experiment.background[11].intensity                       340        418.5       2.6   23.1% ↑
  intensity       experiment.background[12].intensity                       340        364.3       2.5   7.1% ↑
  intensity       experiment.background[13].intensity                       340        293.5       2.3   13.7% ↓
  intensity       experiment.background[14].intensity                       340        232.9       3.1   31.5% ↓
  intensity       experiment.background[1].intensity                        340          609        20   79.2% ↑
  intensity       experiment.background[2].intensity                        340          581        14   70.9% ↑
  intensity       experiment.background[3].intensity                        340          563        13   65.7% ↑
  intensity       experiment.background[4].intensity                        340          540        12   59.0% ↑
  intensity       experiment.background[5].intensity                        340        521.1       8.3   53.3% ↑
  intensity       experiment.background[6].intensity                        340        505.4       4.8   48.7% ↑
  intensity       experiment.background[7].intensity                        340        462.8       4.3   36.1% ↑
  intensity       experiment.background[8].intensity                        340        436.0       3.3   28.2% ↑
  intensity       experiment.background[9].intensity                        340        454.9       2.8   33.8% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2871       0.2869    0.0026   0.1% ↓
  scale           experiment.linked_structures[cosio].scale               1.185       1.1135    0.0059   6.0% ↓
  a, Å            structure.cell.length_a                               10.3086     10.30903   0.00029   
  b, Å            structure.cell.length_b                                6.0041      6.00368   0.00018   
  c, Å            structure.cell.length_c                                4.7865      4.78661   0.00014   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

The profile terms now fit the widths and shapes of the peaks. diffraction-lib's tutorial also
fits a peak asymmetry; this case's profile has none.

In `experiments/d20.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.2()
_peak.broad_gauss_v -0.5()
_peak.broad_gauss_w 0.4()
_peak.broad_lorentz_y 0.01()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20, 1418 pts fitted / 1418 loaded, 23 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        5.51         8.47
      1      0.020      4.84         6.54   22.8% ↓
      2      0.025      4.80         6.43   1.7% ↓
      3      0.030      4.80         6.43   0.1% ↓
      4      0.035      4.80         6.43   
      5      0.042      4.80         6.43   
      6      0.053      4.80         6.43   
  done · converged · 6 iters · reduced χ² 6.43 · Rwp 4.80 % · 0.06 s

  refined parameters (23 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     432.6        431.0       2.4   0.4% ↓
  intensity       experiment.background[11].intensity                     418.5        413.7       2.5   1.1% ↓
  intensity       experiment.background[12].intensity                     364.3        358.4       2.3   1.6% ↓
  intensity       experiment.background[13].intensity                     293.5        288.3       2.1   1.8% ↓
  intensity       experiment.background[14].intensity                     232.9        225.0       2.9   3.4% ↓
  intensity       experiment.background[1].intensity                        609          609        18   0.1% ↑
  intensity       experiment.background[2].intensity                        581          581        12   
  intensity       experiment.background[3].intensity                        563          563        11   0.1% ↑
  intensity       experiment.background[4].intensity                        540          540        11   0.1% ↑
  intensity       experiment.background[5].intensity                      521.1        521.0       7.2   
  intensity       experiment.background[6].intensity                      505.4        505.7       4.2   0.1% ↑
  intensity       experiment.background[7].intensity                      462.8        461.4       3.8   0.3% ↓
  intensity       experiment.background[8].intensity                        436        435.1       2.8   0.2% ↓
  intensity       experiment.background[9].intensity                      454.9        451.6       2.6   0.7% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2869       0.2882    0.0024   0.5% ↑
  scale           experiment.linked_structures[cosio].scale              1.1135       1.1604    0.0084   4.2% ↑
  U, deg²         experiment.peak.broad_gauss_u                             0.2       0.2479    0.0081 ! 23.9% ↑
  V, deg²         experiment.peak.broad_gauss_v                            -0.5       -0.529     0.018 ! 5.8% ↓
  W, deg²         experiment.peak.broad_gauss_w                             0.4        0.372     0.011   6.9% ↓
  Y, deg          experiment.peak.broad_lorentz_y                          0.01       0.0263    0.0049   163.2% ↑
  a, Å            structure.cell.length_a                               10.3090     10.30863   0.00030   
  b, Å            structure.cell.length_b                                6.0037      6.00398   0.00019   
  c, Å            structure.cell.length_c                                4.7866      4.78673   0.00014   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (d20) (r = -0.95)
      experiment.peak.broad_gauss_v: strongly correlated with U (d20) (r = -0.95)
```

## Atom positions

The peak intensities now depend mostly on where the atoms are. Co1 sits on a centre of
symmetry and the other sites on the mirror plane, so only their free coordinates are fitted.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co2 Co 0.28() 0.25 0.98() c 4 1 0.5 Biso
Si Si 0.09() 0.25 0.43() c 4 1 0.5 Biso
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20, 1418 pts fitted / 1418 loaded, 34 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.80         6.48
      1      0.021      4.15         4.84   25.2% ↓
      2      0.026      4.14         4.82   0.5% ↓
      3      0.032      4.14         4.82   
      4      0.037      4.14         4.82   
      5      0.049      4.14         4.82   
  done · converged · 5 iters · reduced χ² 4.82 · Rwp 4.14 % · 0.06 s

  refined parameters (34 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                       431        432.5       2.1   0.4% ↑
  intensity       experiment.background[11].intensity                     413.7        412.6       2.2   0.3% ↓
  intensity       experiment.background[12].intensity                     358.4        359.8       2.0   0.4% ↑
  intensity       experiment.background[13].intensity                     288.3        290.5       1.9   0.8% ↑
  intensity       experiment.background[14].intensity                       225        236.1       2.8   5.0% ↑
  intensity       experiment.background[1].intensity                        609          609        15   0.1% ↑
  intensity       experiment.background[2].intensity                        581          581        10   
  intensity       experiment.background[3].intensity                        563        563.4       9.5   0.1% ↑
  intensity       experiment.background[4].intensity                        540        540.7       9.1   0.1% ↑
  intensity       experiment.background[5].intensity                        521        520.2       6.3   0.2% ↓
  intensity       experiment.background[6].intensity                      505.7        507.6       3.6   0.4% ↑
  intensity       experiment.background[7].intensity                      461.4        464.0       3.3   0.6% ↑
  intensity       experiment.background[8].intensity                      435.1        436.3       2.5   0.3% ↑
  intensity       experiment.background[9].intensity                      451.6        452.3       2.3   0.2% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2882       0.2857    0.0021   0.9% ↓
  scale           experiment.linked_structures[cosio].scale              1.1604       1.1534    0.0076   0.6% ↓
  U, deg²         experiment.peak.broad_gauss_u                          0.2479       0.2382    0.0069 ! 3.9% ↓
  V, deg²         experiment.peak.broad_gauss_v                          -0.529       -0.514     0.015 ! 2.9% ↑
  W, deg²         experiment.peak.broad_gauss_w                           0.372       0.3721    0.0089   
  Y, deg          experiment.peak.broad_lorentz_y                        0.0263       0.0184    0.0043   29.9% ↓
  x               structure.atom_sites[Co2].fract_x                     0.28000      0.27799   0.00073   0.7% ↓
  z               structure.atom_sites[Co2].fract_z                     0.98000       0.9851    0.0016   0.5% ↑
  x               structure.atom_sites[O1].fract_x                      0.09000      0.09104   0.00030   1.2% ↑
  z               structure.atom_sites[O1].fract_z                      0.77000      0.77155   0.00067   0.2% ↑
  x               structure.atom_sites[O2].fract_x                      0.45000      0.44818   0.00026   0.4% ↓
  z               structure.atom_sites[O2].fract_z                      0.22000      0.21622   0.00072   1.7% ↓
  x               structure.atom_sites[O3].fract_x                      0.16000      0.16346   0.00023   2.2% ↑
  y               structure.atom_sites[O3].fract_y                      0.03000      0.03157   0.00033   5.2% ↑
  z               structure.atom_sites[O3].fract_z                      0.28000      0.28071   0.00049   0.3% ↑
  x               structure.atom_sites[Si].fract_x                      0.09000      0.09391   0.00042   4.3% ↑
  z               structure.atom_sites[Si].fract_z                      0.43000      0.43089   0.00086   0.2% ↑
  a, Å            structure.cell.length_a                               10.3086     10.30866   0.00026   
  b, Å            structure.cell.length_b                                6.0040      6.00382   0.00016   
  c, Å            structure.cell.length_c                                4.7867      4.78665   0.00012   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.peak.broad_gauss_u: strongly correlated with V (d20) (r = -0.95)
      experiment.peak.broad_gauss_v: strongly correlated with U (d20) (r = -0.95)
```

## Displacements

The displacements change the intensities more at high angle.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co1 Co 0 0 0 a 4 1 0.5() Biso
Co2 Co 0.27799() 0.25 0.9851() c 4 1 0.5() Biso
```

The same for every other row (4 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20, 1418 pts fitted / 1418 loaded, 40 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.14         4.84
      1      0.020      3.99         4.50   7.1% ↓
      2      0.026      3.99         4.49   0.1% ↓
      3      0.033      3.99         4.49   
      4      0.045      3.99         4.49   
  done · converged · 4 iters · reduced χ² 4.49 · Rwp 3.99 % · 0.05 s

  refined parameters (40 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     432.5        430.7       2.0   0.4% ↓
  intensity       experiment.background[11].intensity                     412.6        414.5       2.2   0.5% ↑
  intensity       experiment.background[12].intensity                     359.8        360.4       2.1   0.2% ↑
  intensity       experiment.background[13].intensity                     290.5        291.1       2.0   0.2% ↑
  intensity       experiment.background[14].intensity                     236.1        240.9       3.0   2.0% ↑
  intensity       experiment.background[1].intensity                        609          609        15   0.1% ↑
  intensity       experiment.background[2].intensity                        581        581.2       9.7   
  intensity       experiment.background[3].intensity                      563.4        563.4       9.2   
  intensity       experiment.background[4].intensity                      540.7        540.7       8.8   
  intensity       experiment.background[5].intensity                      520.2        520.2       6.1   
  intensity       experiment.background[6].intensity                      507.6        507.7       3.5   
  intensity       experiment.background[7].intensity                        464        463.5       3.2   0.1% ↓
  intensity       experiment.background[8].intensity                      436.3        434.8       2.4   0.3% ↓
  intensity       experiment.background[9].intensity                      452.3        451.2       2.3   0.2% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2857       0.2858    0.0020   
  scale           experiment.linked_structures[cosio].scale              1.1534        1.190     0.011   3.2% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.2382       0.2426    0.0068   1.8% ↑
  V, deg²         experiment.peak.broad_gauss_v                          -0.514       -0.528     0.015   2.7% ↓
  W, deg²         experiment.peak.broad_gauss_w                          0.3721       0.3835    0.0090   3.1% ↑
  Y, deg          experiment.peak.broad_lorentz_y                        0.0184       0.0154    0.0044   16.4% ↓
  B iso, Å²       structure.atom_sites[Co1].adp_iso                       0.500        -0.32      0.14   163.1% ↓
  B iso, Å²       structure.atom_sites[Co2].adp_iso                       0.500         0.75      0.14   49.2% ↑
  x               structure.atom_sites[Co2].fract_x                     0.27799      0.28043   0.00076   0.9% ↑
  z               structure.atom_sites[Co2].fract_z                     0.98510       0.9842    0.0016   0.1% ↓
  B iso, Å²       structure.atom_sites[O1].adp_iso                        0.500        0.597     0.059   19.5% ↑
  x               structure.atom_sites[O1].fract_x                      0.09104      0.09132   0.00030   0.3% ↑
  z               structure.atom_sites[O1].fract_z                      0.77155      0.77144   0.00064   
  B iso, Å²       structure.atom_sites[O2].adp_iso                        0.500        0.558     0.058   11.5% ↑
  x               structure.atom_sites[O2].fract_x                      0.44818      0.44824   0.00026   
  z               structure.atom_sites[O2].fract_z                      0.21622      0.21634   0.00068   0.1% ↑
  B iso, Å²       structure.atom_sites[O3].adp_iso                        0.500        0.819     0.049   63.9% ↑
  x               structure.atom_sites[O3].fract_x                      0.16346      0.16375   0.00023   0.2% ↑
  y               structure.atom_sites[O3].fract_y                      0.03157      0.03188   0.00034   1.0% ↑
  z               structure.atom_sites[O3].fract_z                      0.28071      0.28003   0.00049   0.2% ↓
  B iso, Å²       structure.atom_sites[Si].adp_iso                        0.500        0.389     0.063   22.2% ↓
  x               structure.atom_sites[Si].fract_x                      0.09391      0.09389   0.00039   
  z               structure.atom_sites[Si].fract_z                      0.43089      0.42933   0.00084   0.4% ↓
  a, Å            structure.cell.length_a                               10.3087     10.30872   0.00026   
  b, Å            structure.cell.length_b                                6.0038      6.00384   0.00016   
  c, Å            structure.cell.length_c                                4.7866      4.78665   0.00012   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Constrain the two Co sites

The correlations show no strong pair for the two Co sites, yet the fit gives them very different
displacements, Co1's even negative, which no atom can have: both are Co and scatter alike, so
the pattern cannot tell their thermal motions apart. Give each an alias and constrain Co2's to
follow Co1's, starting again from 0.5 Å², then fit again; the shared displacement is positive and
its s.u. smaller than either had alone.

In `analysis/analysis.edi`, add these rows to its alias and constraint loops:

```edi
biso_Co1 cosio.atom_site.Co1.adp_iso
biso_Co2 cosio.atom_site.Co2.adp_iso
```

The same for every other row (1 more).

In `structures/cosio.edi`, set the values the stage starts again from:

```edi
Co1 Co 0 0 0 a 4 1 0.50() Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20, 1418 pts fitted / 1418 loaded, 39 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.05         4.64
      1      0.020      4.02         4.57   1.6% ↓
      2      0.025      4.02         4.57   
      3      0.030      4.02         4.57   
      4      0.040      4.02         4.57   
  done · converged · 4 iters · reduced χ² 4.57 · Rwp 4.02 % · 0.05 s

  refined parameters (39 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     430.7        430.7       2.1   
  intensity       experiment.background[11].intensity                     414.5        414.5       2.2   
  intensity       experiment.background[12].intensity                     360.4        361.7       2.1   0.4% ↑
  intensity       experiment.background[13].intensity                     291.1        291.2       2.0   
  intensity       experiment.background[14].intensity                     240.9        239.1       3.0   0.7% ↓
  intensity       experiment.background[1].intensity                        609          609        15   0.1% ↑
  intensity       experiment.background[2].intensity                      581.2        581.2       9.8   
  intensity       experiment.background[3].intensity                      563.4        563.4       9.3   
  intensity       experiment.background[4].intensity                      540.7        540.7       8.8   
  intensity       experiment.background[5].intensity                      520.2        520.2       6.1   
  intensity       experiment.background[6].intensity                      507.7        507.7       3.5   
  intensity       experiment.background[7].intensity                      463.5        463.3       3.2   
  intensity       experiment.background[8].intensity                      434.8        434.4       2.4   0.1% ↓
  intensity       experiment.background[9].intensity                      451.2        451.3       2.3   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2858       0.2861    0.0020   0.1% ↑
  scale           experiment.linked_structures[cosio].scale                1.19        1.195     0.011   0.4% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.2426       0.2425    0.0068   
  V, deg²         experiment.peak.broad_gauss_v                          -0.528       -0.529     0.015   0.2% ↓
  W, deg²         experiment.peak.broad_gauss_w                          0.3835       0.3842    0.0090   0.2% ↑
  Y, deg          experiment.peak.broad_lorentz_y                        0.0154       0.0156    0.0044   1.3% ↑
  B iso, Å²       structure.atom_sites[Co1].adp_iso                       0.500        0.277     0.081   44.7% ↓
  x               structure.atom_sites[Co2].fract_x                     0.28043      0.27931   0.00070   0.4% ↓
  z               structure.atom_sites[Co2].fract_z                     0.98420       0.9848    0.0015   0.1% ↑
  B iso, Å²       structure.atom_sites[O1].adp_iso                        0.597        0.648     0.059   8.5% ↑
  x               structure.atom_sites[O1].fract_x                      0.09132      0.09107   0.00030   0.3% ↓
  z               structure.atom_sites[O1].fract_z                      0.77144      0.77136   0.00065   
  B iso, Å²       structure.atom_sites[O2].adp_iso                        0.558        0.581     0.059   4.1% ↑
  x               structure.atom_sites[O2].fract_x                      0.44824      0.44824   0.00026   
  z               structure.atom_sites[O2].fract_z                      0.21634      0.21660   0.00069   0.1% ↑
  B iso, Å²       structure.atom_sites[O3].adp_iso                        0.819        0.836     0.049   2.1% ↑
  x               structure.atom_sites[O3].fract_x                      0.16375      0.16355   0.00024   0.1% ↓
  y               structure.atom_sites[O3].fract_y                      0.03188      0.03166   0.00033   0.7% ↓
  z               structure.atom_sites[O3].fract_z                      0.28003      0.28003   0.00050   
  B iso, Å²       structure.atom_sites[Si].adp_iso                        0.389        0.347     0.063   10.8% ↓
  x               structure.atom_sites[Si].fract_x                      0.09389      0.09379   0.00039   0.1% ↓
  z               structure.atom_sites[Si].fract_z                      0.42933      0.42905   0.00084   0.1% ↓
  a, Å            structure.cell.length_a                               10.3087     10.30879   0.00026   
  b, Å            structure.cell.length_b                                6.0038      6.00381   0.00016   
  c, Å            structure.cell.length_c                                4.7866      4.78667   0.00012   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Oxygen occupancies

Last, the oxygen occupancies, which change the intensities as the displacements do.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
O1 O 0.09107() 0.25 0.77136() c 4 1() 0.648() Biso
O2 O 0.44824() 0.25 0.21660() c 4 1() 0.581() Biso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20 --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20, 1418 pts fitted / 1418 loaded, 42 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.02         4.58
      1      0.020      3.98         4.48   2.2% ↓
      2      0.025      3.97         4.45   0.5% ↓
      3      0.030      3.97         4.45   
      4      0.041      3.97         4.45   
  done · converged · 4 iters · reduced χ² 4.45 · Rwp 3.97 % · 0.05 s

  refined parameters (42 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     430.7        429.4       2.0   0.3% ↓
  intensity       experiment.background[11].intensity                     414.5        414.1       2.2   0.1% ↓
  intensity       experiment.background[12].intensity                     361.7        362.3       2.1   0.2% ↑
  intensity       experiment.background[13].intensity                     291.2        292.9       2.0   0.6% ↑
  intensity       experiment.background[14].intensity                     239.1        241.3       3.0   0.9% ↑
  intensity       experiment.background[1].intensity                        609          609        15   0.1% ↑
  intensity       experiment.background[2].intensity                      581.2        581.2       9.7   
  intensity       experiment.background[3].intensity                      563.4        563.4       9.2   
  intensity       experiment.background[4].intensity                      540.7        540.7       8.7   
  intensity       experiment.background[5].intensity                      520.2        520.1       6.0   
  intensity       experiment.background[6].intensity                      507.7        507.8       3.5   
  intensity       experiment.background[7].intensity                      463.3        462.8       3.2   0.1% ↓
  intensity       experiment.background[8].intensity                      434.4        431.1       2.5   0.8% ↓
  intensity       experiment.background[9].intensity                      451.3        451.8       2.2   0.1% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.2861       0.2857    0.0020   0.1% ↓
  scale           experiment.linked_structures[cosio].scale               1.195        1.328     0.030   11.1% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.2425       0.2411    0.0067   0.6% ↓
  V, deg²         experiment.peak.broad_gauss_v                          -0.529       -0.528     0.015   0.2% ↑
  W, deg²         experiment.peak.broad_gauss_w                          0.3842       0.3859    0.0089   0.4% ↑
  Y, deg          experiment.peak.broad_lorentz_y                        0.0156       0.0143    0.0044   8.6% ↓
  B iso, Å²       structure.atom_sites[Co1].adp_iso                       0.277         0.66      0.11   140.0% ↑
  x               structure.atom_sites[Co2].fract_x                     0.27931      0.27919   0.00072   
  z               structure.atom_sites[Co2].fract_z                     0.98480       0.9847    0.0015   
  B iso, Å²       structure.atom_sites[O1].adp_iso                        0.648        0.461     0.079   28.8% ↓
  x               structure.atom_sites[O1].fract_x                      0.09107      0.09106   0.00030   
  z               structure.atom_sites[O1].fract_z                      0.77136      0.77149   0.00065   
  occ             structure.atom_sites[O1].occupancy                     1.0000        0.916     0.014   8.4% ↓
  B iso, Å²       structure.atom_sites[O2].adp_iso                        0.581        0.663     0.081   14.1% ↑
  x               structure.atom_sites[O2].fract_x                      0.44824      0.44815   0.00026   
  z               structure.atom_sites[O2].fract_z                      0.21660      0.21687   0.00068   0.1% ↑
  occ             structure.atom_sites[O2].occupancy                     1.0000        0.959     0.014   4.1% ↓
  B iso, Å²       structure.atom_sites[O3].adp_iso                        0.836        0.846     0.062   1.2% ↑
  x               structure.atom_sites[O3].fract_x                      0.16355      0.16357   0.00023   
  y               structure.atom_sites[O3].fract_y                      0.03166      0.03154   0.00033   0.4% ↓
  z               structure.atom_sites[O3].fract_z                      0.28003      0.28011   0.00049   
  occ             structure.atom_sites[O3].occupancy                     1.0000        0.954     0.012   4.6% ↓
  B iso, Å²       structure.atom_sites[Si].adp_iso                        0.347        0.667     0.089   92.1% ↑
  x               structure.atom_sites[Si].fract_x                      0.09379      0.09395   0.00039   0.2% ↑
  z               structure.atom_sites[Si].fract_z                      0.42905      0.42943   0.00082   0.1% ↑
  a, Å            structure.cell.length_a                               10.3088     10.30873   0.00026   
  b, Å            structure.cell.length_b                                6.0038      6.00379   0.00015   
  c, Å            structure.cell.length_c                                4.7867      4.78665   0.00012   

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
    python -m edi report pd-neut-cwl_cosio-d20 --output pd-neut-cwl_cosio-d20.html
    ```
