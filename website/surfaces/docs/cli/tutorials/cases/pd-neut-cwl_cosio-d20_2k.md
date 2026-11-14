# Magnetic structure fit: Co₂SiO₄ at 2.3 K, D20

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit the magnetic structure of the olivine Co₂SiO₄ to constant-wavelength neutron powder data
from D20 at ILL, measured at 2.3 K, below its ordering temperature. The cobalt moments order with
k = 0 in the magnetic space group Pnma.1: Co1 may point in any direction, Co2 only along b.

The project is the catalogue case `pd-neut-cwl_cosio-d20_2k`, the one the command line and the
app's Examples open. Its two Co sites share one displacement, and the two FCJ asymmetry terms are
tied, from the start.

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
Co1 Co 0 0 0 a 4 1 0.269 Biso
Co2 Co 0.2809 0.25 0.9836 c 4 1 0.269 Biso
```

The same for every other row (7 more).

## Scale, 2θ zero, cell and magnetic moments

The first stage frees the phase scale, the 2θ zero shift, the three cell lengths and the magnetic
model: the moment components the magnetic space group allows (Co1 in any direction, Co2 only
along b) and the j2 term of the Co²⁺ form factor, which sets how the magnetic intensities fall
with angle.

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
Co1 2() 2() 2() Mx,My,Mz
Co2 0 2() 0 0,My,0
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_cosio-d20_2k --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 10 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.38        35.87
      1      0.066      5.97         9.88   72.5% ↓
      2      0.074      5.97         9.88   
      3      0.085      5.97         9.88   
      4      0.097      5.97         9.88   
  done · converged · 4 iters · reduced χ² 9.88 · Rwp 5.97 % · 0.10 s

  refined parameters (10 free):
  name            parameter                                                 start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset              0.2943       0.2764    0.0024   6.1% ↓
  scale           experiment.linked_structures[cosio].scale                1.8172        1.772     0.011   2.5% ↓
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x            2.0000        0.843     0.046   57.9% ↓
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y            2.0000        2.753     0.021   37.7% ↑
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z            2.0000         0.05      0.76   97.6% ↓
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y            2.0000        2.636     0.042   31.8% ↑
  a, Å            structure.cell.length_a                                 10.3081     10.30590   0.00035   
  b, Å            structure.cell.length_b                                  6.0022      6.00065   0.00021   
  c, Å            structure.cell.length_c                                  4.7874      4.78645   0.00016   
  C₂              structure.magnetic_form_factor[Co].j2_coefficient        0.0000        0.666     0.065   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

The second stage frees the sixteen background points, which follow the level between the peaks.

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
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 26 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        5.97         9.99
      1      0.100      5.65         8.93   10.6% ↓
      2      0.114      5.65         8.93   
      3      0.127      5.65         8.93   
      4      0.140      5.65         8.93   
      5      0.159      5.65         8.93   
      6      0.172      5.65         8.93   
      7      0.182      5.65         8.93   
      8      0.192      5.65         8.93   
      9      0.203      5.65         8.93   
     10      0.217      5.65         8.93   
  done · converged · 10 iters · reduced χ² 8.93 · Rwp 5.65 % · 0.23 s

  refined parameters (26 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiment.background[10].intensity                      373.16        372.6       3.3   0.2% ↓
  intensity       experiment.background[11].intensity                      406.37        404.0       2.8   0.6% ↓
  intensity       experiment.background[12].intensity                      408.51        403.0       2.7   1.3% ↓
  intensity       experiment.background[13].intensity                         396        392.6       2.7   0.9% ↓
  intensity       experiment.background[14].intensity                      345.92        342.5       2.6   1.0% ↓
  intensity       experiment.background[15].intensity                      279.04        277.5       2.4   0.5% ↓
  intensity       experiment.background[16].intensity                       230.7        224.2       3.3   2.8% ↓
  intensity       experiment.background[1].intensity                        603.5          615        32   2.0% ↑
  intensity       experiment.background[2].intensity                          585          591        20   1.0% ↑
  intensity       experiment.background[3].intensity                        568.5          543        17   4.5% ↓
  intensity       experiment.background[4].intensity                        528.8        612.6       8.1   15.8% ↑
  intensity       experiment.background[5].intensity                        418.9        439.8       8.0   5.0% ↑
  intensity       experiment.background[6].intensity                        420.2          423        16   0.6% ↑
  intensity       experiment.background[7].intensity                        416.5          419        11   0.6% ↑
  intensity       experiment.background[8].intensity                       416.05        415.3       4.8   0.2% ↓
  intensity       experiment.background[9].intensity                       394.77        396.1       4.5   0.3% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset              0.2764       0.2765    0.0022   
  scale           experiment.linked_structures[cosio].scale                 1.772        1.783     0.011   0.6% ↑
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x            0.8430        0.821     0.044   2.6% ↓
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y            2.7530        2.685     0.022   2.5% ↓
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z            0.0500         0.06      0.67   11.3% ↑
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y            2.6360        2.651     0.042   0.6% ↑
  a, Å            structure.cell.length_a                                 10.3059     10.30589   0.00033   
  b, Å            structure.cell.length_b                                  6.0007      6.00063   0.00020   
  c, Å            structure.cell.length_c                                  4.7865      4.78646   0.00015   
  C₂              structure.magnetic_form_factor[Co].j2_coefficient        0.6660        0.761     0.066   14.3% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Atomic displacements and positions

The third stage frees the atoms: each site's isotropic displacement (Co2's follows Co1's by the
project's constraint) and the coordinates the symmetry leaves free. Co1 sits on a centre of
symmetry, so it has none; the other sites lie on the mirror plane, except O3.

In `structures/cosio.edi`, add `()` after the values the stage frees:

```edi
Co1 Co 0 0 0 a 4 1 0.269() Biso
Co2 Co 0.2809() 0.25 0.9836() c 4 1 0.269 Biso
```

The same for every other row (4 more).

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
                        5.65         9.03
      1      0.082      5.59         8.86   1.8% ↓
      2      0.093      5.59         8.86   
      3      0.103      5.59         8.86   
      4      0.115      5.59         8.86   
      5      0.130      5.59         8.86   
  done · converged · 5 iters · reduced χ² 8.86 · Rwp 5.59 % · 0.14 s

  refined parameters (42 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiment.background[10].intensity                       372.6        373.5       3.3   0.2% ↑
  intensity       experiment.background[11].intensity                         404        403.0       2.9   0.2% ↓
  intensity       experiment.background[12].intensity                         403        402.3       2.8   0.2% ↓
  intensity       experiment.background[13].intensity                       392.6        394.0       2.8   0.4% ↑
  intensity       experiment.background[14].intensity                       342.5        342.6       2.7   
  intensity       experiment.background[15].intensity                       277.5        277.8       2.6   0.1% ↑
  intensity       experiment.background[16].intensity                       224.2        226.5       3.8   1.0% ↑
  intensity       experiment.background[1].intensity                          615          615        32   0.1% ↑
  intensity       experiment.background[2].intensity                          591          591        20   0.1% ↓
  intensity       experiment.background[3].intensity                          543          543        17   
  intensity       experiment.background[4].intensity                        612.6        612.3       8.1   
  intensity       experiment.background[5].intensity                        439.8        439.1       8.0   0.2% ↓
  intensity       experiment.background[6].intensity                          423          423        16   0.1% ↓
  intensity       experiment.background[7].intensity                          419          419        11   0.1% ↓
  intensity       experiment.background[8].intensity                        415.3        415.7       4.8   0.1% ↑
  intensity       experiment.background[9].intensity                        396.1        395.2       4.5   0.2% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset              0.2765       0.2765    0.0023   
  scale           experiment.linked_structures[cosio].scale                 1.783        1.795     0.022   0.6% ↑
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x            0.8210        0.818     0.044   0.3% ↓
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y            2.6850        2.645     0.026   1.5% ↓
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z            0.0600         0.05      0.68   14.2% ↓
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y            2.6510        2.638     0.047   0.5% ↓
  B iso, Å²       structure.atom_sites[Co1].adp_iso                         0.269         0.26      0.11   1.9% ↓
  x               structure.atom_sites[Co2].fract_x                       0.28090      0.27870   0.00070   0.8% ↓
  z               structure.atom_sites[Co2].fract_z                       0.98360       0.9824    0.0021   0.1% ↓
  B iso, Å²       structure.atom_sites[O1].adp_iso                          0.778        0.800     0.081   2.8% ↑
  x               structure.atom_sites[O1].fract_x                        0.08960      0.09049   0.00043   1.0% ↑
  z               structure.atom_sites[O1].fract_z                        0.77300      0.77228   0.00094   0.1% ↓
  B iso, Å²       structure.atom_sites[O2].adp_iso                          0.642        0.680     0.082   5.9% ↑
  x               structure.atom_sites[O2].fract_x                        0.44780      0.44816   0.00037   0.1% ↑
  z               structure.atom_sites[O2].fract_z                        0.21790      0.21652   0.00098   0.6% ↓
  B iso, Å²       structure.atom_sites[O3].adp_iso                          0.917        0.981     0.067   6.9% ↑
  x               structure.atom_sites[O3].fract_x                        0.16390      0.16361   0.00034   0.2% ↓
  y               structure.atom_sites[O3].fract_y                        0.03210      0.03191   0.00047   0.6% ↓
  z               structure.atom_sites[O3].fract_z                        0.28050      0.27972   0.00072   0.3% ↓
  B iso, Å²       structure.atom_sites[Si].adp_iso                          0.466        0.642     0.092   37.7% ↑
  x               structure.atom_sites[Si].fract_x                        0.09330      0.09372   0.00057   0.5% ↑
  z               structure.atom_sites[Si].fract_z                        0.42780       0.4282    0.0013   0.1% ↑
  a, Å            structure.cell.length_a                                 10.3059     10.30588   0.00033   
  b, Å            structure.cell.length_b                                  6.0006      6.00061   0.00020   
  c, Å            structure.cell.length_c                                  4.7865      4.78644   0.00015   
  C₂              structure.magnetic_form_factor[Co].j2_coefficient        0.7610        0.880     0.074   15.6% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

The fourth stage frees the peak profile: the Gaussian widths U, V and W and the Lorentzian Y.

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
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 46 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        5.59         8.89
      1      0.094      5.58         8.86   0.3% ↓
      2      0.106      5.58         8.86   
      3      0.117      5.58         8.86   
      4      0.130      5.58         8.86   
      5      0.142      5.58         8.86   
      6      0.155      5.58         8.86   
      7      0.167      5.58         8.86   
      8      0.179      5.58         8.86   
      9      0.191      5.58         8.86   
     10      0.208      5.58         8.86   
  done · converged · 10 iters · reduced χ² 8.86 · Rwp 5.58 % · 0.22 s

  refined parameters (46 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiment.background[10].intensity                       373.5        373.2       3.3   0.1% ↓
  intensity       experiment.background[11].intensity                         403        401.8       3.1   0.3% ↓
  intensity       experiment.background[12].intensity                       402.3        402.0       2.9   0.1% ↓
  intensity       experiment.background[13].intensity                         394        393.8       3.0   0.1% ↓
  intensity       experiment.background[14].intensity                       342.6        343.1       2.9   0.2% ↑
  intensity       experiment.background[15].intensity                       277.8        278.2       2.7   0.1% ↑
  intensity       experiment.background[16].intensity                       226.5        227.1       4.3   0.3% ↑
  intensity       experiment.background[1].intensity                          615          615        32   0.1% ↑
  intensity       experiment.background[2].intensity                          591          591        20   0.1% ↓
  intensity       experiment.background[3].intensity                          543          543        17   
  intensity       experiment.background[4].intensity                        612.3        612.0       8.1   0.1% ↓
  intensity       experiment.background[5].intensity                        439.1        437.9       8.0   0.3% ↓
  intensity       experiment.background[6].intensity                          423          423        16   
  intensity       experiment.background[7].intensity                          419          419        11   0.1% ↓
  intensity       experiment.background[8].intensity                        415.7        415.7       4.8   
  intensity       experiment.background[9].intensity                        395.2        393.9       4.7   0.3% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset              0.2765       0.2762    0.0023   0.1% ↓
  scale           experiment.linked_structures[cosio].scale                 1.795        1.807     0.024   0.7% ↑
  U, deg²         experiment.peak.broad_gauss_u                           0.27353       0.2720    0.0087   0.6% ↓
  V, deg²         experiment.peak.broad_gauss_v                          -0.58972       -0.598     0.017   1.4% ↓
  W, deg²         experiment.peak.broad_gauss_w                           0.41301        0.421     0.010   1.9% ↑
  Y, deg          experiment.peak.broad_lorentz_y                        0.017548       0.0191    0.0055   8.9% ↑
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x            0.8180        0.821     0.044   0.4% ↑
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y            2.6450        2.645     0.027   
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z            0.0500         0.05      0.68   6.0% ↑
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y            2.6380        2.637     0.047   
  B iso, Å²       structure.atom_sites[Co1].adp_iso                         0.260         0.29      0.12   13.4% ↑
  x               structure.atom_sites[Co2].fract_x                       0.27870      0.27879   0.00070   
  z               structure.atom_sites[Co2].fract_z                       0.98240       0.9825    0.0021   
  B iso, Å²       structure.atom_sites[O1].adp_iso                          0.800        0.821     0.084   2.6% ↑
  x               structure.atom_sites[O1].fract_x                        0.09049      0.09052   0.00043   
  z               structure.atom_sites[O1].fract_z                        0.77228      0.77230   0.00095   
  B iso, Å²       structure.atom_sites[O2].adp_iso                          0.680        0.705     0.085   3.7% ↑
  x               structure.atom_sites[O2].fract_x                        0.44816      0.44818   0.00037   
  z               structure.atom_sites[O2].fract_z                        0.21652      0.21651   0.00098   
  B iso, Å²       structure.atom_sites[O3].adp_iso                          0.981        1.006     0.069   2.6% ↑
  x               structure.atom_sites[O3].fract_x                        0.16361      0.16366   0.00034   
  y               structure.atom_sites[O3].fract_y                        0.03191      0.03195   0.00047   0.1% ↑
  z               structure.atom_sites[O3].fract_z                        0.27972      0.27966   0.00073   
  B iso, Å²       structure.atom_sites[Si].adp_iso                          0.642        0.661     0.094   3.0% ↑
  x               structure.atom_sites[Si].fract_x                        0.09372      0.09372   0.00057   
  z               structure.atom_sites[Si].fract_z                        0.42820       0.4282    0.0013   
  a, Å            structure.cell.length_a                                 10.3059     10.30591   0.00033   
  b, Å            structure.cell.length_b                                  6.0006      6.00056   0.00020   
  c, Å            structure.cell.length_c                                  4.7864      4.78643   0.00015   
  C₂              structure.magnetic_form_factor[Co].j2_coefficient        0.8800        0.885     0.075   0.5% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak asymmetry

The last stage frees the asymmetry: the low-angle peaks lean towards low angle. One FCJ term is
freed; the other follows it by the project's constraint.

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
edi fit: project pd-neut-cwl_cosio-d20_2k, 1438 pts fitted / 1506 loaded, 47 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        5.58         8.87
      1      0.418      5.51         8.62   2.8% ↓
      2      0.430      5.44         8.41   2.4% ↓
      3      0.443      5.36         8.16   2.9% ↓
      4      0.455      5.23         7.77   4.9% ↓
      5      0.470      4.94         6.93   10.7% ↓
      6      0.488      4.76         6.45   6.9% ↓
      7      0.502      4.70         6.28   2.8% ↓
      8      0.518      4.70         6.27   0.1% ↓
      9      0.534      4.69         6.27   
     10      0.552      4.69         6.26   0.1% ↓
     11      0.570      4.69         6.26   0.1% ↓
     12      0.585      4.69         6.25   0.1% ↓
     13      0.604      4.69         6.25   
     14      0.622      4.69         6.25   
     15      0.640      4.69         6.25   
     16      0.655      4.69         6.25   
     17      0.677      4.69         6.25   
     18      0.692      4.69         6.25   
     19      0.715      4.69         6.25   
  done · converged · 19 iters · reduced χ² 6.25 · Rwp 4.69 % · 0.73 s

  refined parameters (47 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiment.background[10].intensity                       373.2        370.7       2.8   0.7% ↓
  intensity       experiment.background[11].intensity                       401.8        405.0       2.7   0.8% ↑
  intensity       experiment.background[12].intensity                         402        403.4       2.4   0.3% ↑
  intensity       experiment.background[13].intensity                       393.8        396.6       2.6   0.7% ↑
  intensity       experiment.background[14].intensity                       343.1        343.3       2.4   0.1% ↑
  intensity       experiment.background[15].intensity                       278.2        279.1       2.3   0.3% ↑
  intensity       experiment.background[16].intensity                       227.1        234.1       3.5   3.1% ↑
  intensity       experiment.background[1].intensity                          615          619        27   0.7% ↑
  intensity       experiment.background[2].intensity                          591          584        17   1.2% ↓
  intensity       experiment.background[3].intensity                          543          565        15   4.0% ↑
  intensity       experiment.background[4].intensity                          612        535.4       8.0   12.5% ↓
  intensity       experiment.background[5].intensity                        437.9        425.2       6.8   2.9% ↓
  intensity       experiment.background[6].intensity                          423          425        14   0.6% ↑
  intensity       experiment.background[7].intensity                          419        420.1       8.9   0.3% ↑
  intensity       experiment.background[8].intensity                        415.7        411.2       4.0   1.1% ↓
  intensity       experiment.background[9].intensity                        393.9        382.7       4.0   2.8% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset              0.2762       0.3855    0.0031   39.6% ↑
  scale           experiment.linked_structures[cosio].scale                 1.807        1.781     0.020   1.4% ↓
  S/L             experiment.peak.asym_fcj_1                                    0      0.06117   0.00088   
  U, deg²         experiment.peak.broad_gauss_u                             0.272       0.2005    0.0073   26.3% ↓
  V, deg²         experiment.peak.broad_gauss_v                            -0.598       -0.407     0.015   31.9% ↑
  W, deg²         experiment.peak.broad_gauss_w                             0.421       0.3089    0.0089   26.6% ↓
  Y, deg          experiment.peak.broad_lorentz_y                          0.0191       0.0135    0.0047   29.3% ↓
  Mx, μB          structure.atom_site_moment[Co1].crystalaxis_x            0.8210        1.005     0.039   22.4% ↑
  My, μB          structure.atom_site_moment[Co1].crystalaxis_y            2.6450        3.002     0.027   13.5% ↑
  Mz, μB          structure.atom_site_moment[Co1].crystalaxis_z            0.0500         0.03      0.80   43.4% ↓
  My, μB          structure.atom_site_moment[Co2].crystalaxis_y            2.6370        2.597     0.040   1.5% ↓
  B iso, Å²       structure.atom_sites[Co1].adp_iso                         0.290        0.350     0.096   20.6% ↑
  x               structure.atom_sites[Co2].fract_x                       0.27879      0.27737   0.00061   0.5% ↓
  z               structure.atom_sites[Co2].fract_z                       0.98250       0.9826    0.0018   
  B iso, Å²       structure.atom_sites[O1].adp_iso                          0.821        0.795     0.070   3.2% ↓
  x               structure.atom_sites[O1].fract_x                        0.09052      0.09046   0.00036   0.1% ↓
  z               structure.atom_sites[O1].fract_z                        0.77230      0.77149   0.00079   0.1% ↓
  B iso, Å²       structure.atom_sites[O2].adp_iso                          0.705        0.669     0.071   5.1% ↓
  x               structure.atom_sites[O2].fract_x                        0.44818      0.44832   0.00031   
  z               structure.atom_sites[O2].fract_z                        0.21651      0.21510   0.00082   0.6% ↓
  B iso, Å²       structure.atom_sites[O3].adp_iso                          1.006        1.005     0.059   
  x               structure.atom_sites[O3].fract_x                        0.16366      0.16343   0.00028   0.1% ↓
  y               structure.atom_sites[O3].fract_y                        0.03195      0.03184   0.00040   0.3% ↓
  z               structure.atom_sites[O3].fract_z                        0.27966      0.27938   0.00062   0.1% ↓
  B iso, Å²       structure.atom_sites[Si].adp_iso                          0.661        0.567     0.078   14.2% ↓
  x               structure.atom_sites[Si].fract_x                        0.09372      0.09441   0.00047   0.7% ↑
  z               structure.atom_sites[Si].fract_z                        0.42820       0.4288    0.0011   0.1% ↑
  a, Å            structure.cell.length_a                                 10.3059     10.31472   0.00034   0.1% ↑
  b, Å            structure.cell.length_b                                  6.0006      6.00590   0.00021   0.1% ↑
  c, Å            structure.cell.length_c                                  4.7864      4.79065   0.00016   0.1% ↑
  C₂              structure.magnetic_form_factor[Co].j2_coefficient        0.8850        0.609     0.060   31.2% ↓

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
