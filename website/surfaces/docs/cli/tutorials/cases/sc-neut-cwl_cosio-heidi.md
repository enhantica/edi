# Single-crystal fit: Co₂SiO₄ at three temperatures, HEiDi

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit one Co₂SiO₄ crystal measured on HEiDi at MLZ at 300 K, 55 K and 2.5 K. Each temperature has
its own structure and its own reflections, and the three are fitted independently: each fit sees
only its own data and gives its own goodness of fit and uncertainties. At 2.5 K the cobalt
moments order, and the magnetic structure is fitted too.

The data are those of Sazonov et al., Acta Cryst. B 64 (2008) 661-668. The 2.5 K file has no
usable uncertainties, so they are estimated from the 55 K data of the same crystal (see the
case's provenance); the fitted 2.5 K uncertainties depend on that estimate.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p sc-neut-cwl_cosio-heidi/structures sc-neut-cwl_cosio-heidi/experiments sc-neut-cwl_cosio-heidi/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name             sc-neut-cwl_cosio-heidi
_metadata.title "Co₂SiO₄ [Pnma] at 300 K, 55 K and 2.5 K · HEiDi @ MLZ (FRM II)"
_metadata.description "Single crystal · Three temperatures fitted independently, moments at 2.5 K"
_metadata.authors .
_metadata.created          "09 Nov 2026 18:00:00"
_metadata.last_modified    "09 Nov 2026 18:00:00"
_metadata.timestamp        ?
```

## Define the structures

Download the structures from EasyDiffraction's collection into `structures`. Each CIF gives its space group, cell and atom sites.

=== "Standalone executable"

    ```console
    edi download-data sc-neut-cwl_cosio-heidi-cosio_2k5
    mv data/sc-neut-cwl_cosio-heidi-cosio_2k5.edi sc-neut-cwl_cosio-heidi/structures/cosio_2k5.edi
    edi download-data sc-neut-cwl_cosio-heidi-cosio_300k
    mv data/sc-neut-cwl_cosio-heidi-cosio_300k.edi sc-neut-cwl_cosio-heidi/structures/cosio_300k.edi
    edi download-data sc-neut-cwl_cosio-heidi-cosio_55k
    mv data/sc-neut-cwl_cosio-heidi-cosio_55k.edi sc-neut-cwl_cosio-heidi/structures/cosio_55k.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-cwl_cosio-heidi-cosio_2k5
    mv data/sc-neut-cwl_cosio-heidi-cosio_2k5.edi sc-neut-cwl_cosio-heidi/structures/cosio_2k5.edi
    python -m edi download-data sc-neut-cwl_cosio-heidi-cosio_300k
    mv data/sc-neut-cwl_cosio-heidi-cosio_300k.edi sc-neut-cwl_cosio-heidi/structures/cosio_300k.edi
    python -m edi download-data sc-neut-cwl_cosio-heidi-cosio_55k
    mv data/sc-neut-cwl_cosio-heidi-cosio_55k.edi sc-neut-cwl_cosio-heidi/structures/cosio_55k.edi
    ```

## Define the experiments

Download the experiments into `experiments`: each file declares its instrument, peak profile, background, the structures it links and its measured data.

=== "Standalone executable"

    ```console
    edi download-data sc-neut-cwl_cosio-heidi-heidi_2k5
    mv data/sc-neut-cwl_cosio-heidi-heidi_2k5.edi sc-neut-cwl_cosio-heidi/experiments/heidi_2k5.edi
    edi download-data sc-neut-cwl_cosio-heidi-heidi_300k
    mv data/sc-neut-cwl_cosio-heidi-heidi_300k.edi sc-neut-cwl_cosio-heidi/experiments/heidi_300k.edi
    edi download-data sc-neut-cwl_cosio-heidi-heidi_55k
    mv data/sc-neut-cwl_cosio-heidi-heidi_55k.edi sc-neut-cwl_cosio-heidi/experiments/heidi_55k.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-cwl_cosio-heidi-heidi_2k5
    mv data/sc-neut-cwl_cosio-heidi-heidi_2k5.edi sc-neut-cwl_cosio-heidi/experiments/heidi_2k5.edi
    python -m edi download-data sc-neut-cwl_cosio-heidi-heidi_300k
    mv data/sc-neut-cwl_cosio-heidi-heidi_300k.edi sc-neut-cwl_cosio-heidi/experiments/heidi_300k.edi
    python -m edi download-data sc-neut-cwl_cosio-heidi-heidi_55k
    mv data/sc-neut-cwl_cosio-heidi-heidi_55k.edi sc-neut-cwl_cosio-heidi/experiments/heidi_55k.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_fitting_mode.type independent

_edi.schema_version 3
```

## 300 K: scale

The scale brings the calculated intensities to the measured ones.

In `experiments/heidi_300k.edi`, add `()` after the values the stage frees:

```edi
cosio_300k 10()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 1 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        33.39        14.24
      1      0.068      15.51         3.07   78.4% ↓
  done · converged · 1 iters · reduced χ² 3.07 · wR(F²) 15.51 % · 0.08 s

  per-bank wR(F²) (%):   heidi_300k 15.51

  refined parameters (1 free):
  name            parameter                                                           start        value      s.u.   change
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale            10       14.272     0.056   42.7% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 300 K: coordinates

In `structures/cosio_300k.edi`, add `()` after the values the stage frees:

```edi
Co2 Co 0.27645() 0.25 0.99143() c 4 1 0.003 Uani
Si Si 0.09491() 0.25 0.42821() c 4 1 0.003 Uani
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 12 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        15.51         3.10
      1      0.079      15.34         3.03   2.2% ↓
  done · converged · 1 iters · reduced χ² 3.03 · wR(F²) 15.34 % · 0.09 s

  per-bank wR(F²) (%):   heidi_300k 15.34

  refined parameters (12 free):
  name            parameter                                                           start        value      s.u.   change
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        14.272       14.286     0.056   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27645      0.27632   0.00022   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99143      0.99115   0.00044   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09205     0.092305  0.000099   0.3% ↑
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76712      0.76634   0.00019   0.1% ↓
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44872     0.448706  0.000090   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21560      0.21574   0.00021   0.1% ↑
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164352  0.000066   0.1% ↑
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03363      0.03353   0.00011   0.3% ↓
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28171      0.28151   0.00012   0.1% ↓
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09491      0.09502   0.00014   0.1% ↑
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42821      0.42807   0.00025   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 300 K: displacements

In `structures/cosio_300k.edi`, add `()` after the values the stage frees:

```edi
Co1 0.003() 0.003() 0.003() 0() 0() 0()
Co2 0.003() 0.003() 0.003() 0 0() 0
```

The same for every other row (4 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 40 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        15.34         3.08
      1      0.114       7.67         0.77   75.0% ↓
  done · converged · 1 iters · reduced χ² 0.77 · wR(F²) 7.67 % · 0.13 s

  per-bank wR(F²) (%):   heidi_300k 7.67

  refined parameters (40 free):
  name            parameter                                                           start        value      s.u.   change
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        14.286       16.950     0.064   18.6% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00300      0.00585   0.00031   95.1% ↑
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12                0.00000     -0.00107   0.00025   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                0.00000        -3e-5     22e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00300      0.00352   0.00027   17.2% ↑
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23                0.00000      -5.4e-4    2.3e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00300      0.00365   0.00023   21.7% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00300      0.00350   0.00028   16.5% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                0.00000       4.0e-4    2.4e-4   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00300      0.00473   0.00027   57.6% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00300      0.00483   0.00026   61.0% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00300      0.00570   0.00015   89.9% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 0.00000      -5.6e-5    9.9e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00300      0.00523   0.00013   74.5% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00300      0.00254   0.00011   15.4% ↓
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00300      0.00348   0.00013   15.9% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 0.00000         7e-5     11e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00300      0.00575   0.00014   91.6% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00300      0.00456   0.00012   52.0% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00300     0.006420  0.000098   114.0% ↑
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00000     0.001878  0.000081   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 0.00000      2.49e-4   0.87e-4   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00300     0.004698  0.000089   56.6% ↑
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                 0.00000     -3.78e-4   0.70e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00300     0.004751  0.000073   58.4% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00300      0.00316   0.00018   5.5% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 0.00000       1.9e-4    1.3e-4   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00300      0.00339   0.00017   12.9% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00300      0.00229   0.00015   23.7% ↓
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27632      0.27662   0.00012   0.1% ↑
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99115      0.99137   0.00024   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09230     0.092105  0.000056   0.2% ↓
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76634     0.767044  0.000093   0.1% ↑
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44871     0.448703  0.000047   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21574      0.21542   0.00011   0.1% ↓
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16435     0.164197  0.000037   0.1% ↓
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03353     0.033688  0.000058   0.5% ↑
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28151     0.281782  0.000067   0.1% ↑
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09502     0.094855  0.000069   0.2% ↓
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42807      0.42811   0.00012   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 300 K: extinction

Larson's anisotropic extinction, its six coefficients starting at zero.

In `experiments/heidi_300k.edi`, add `()` after the values the stage frees:

```edi
_extinction.coefficient_11 0()
_extinction.coefficient_22 0()
_extinction.coefficient_33 0()
_extinction.coefficient_12 0()
_extinction.coefficient_13 0()
_extinction.coefficient_23 0()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         7.67         0.77
      1      0.124       6.15         0.50   35.6% ↓
  done · converged · 1 iters · reduced χ² 0.50 · wR(F²) 6.15 % · 0.15 s

  per-bank wR(F²) (%):   heidi_300k 6.15

  refined parameters (46 free):
  name            parameter                                                           start        value      s.u.   change
  x11             experiments[heidi_300k].extinction.coefficient_11                       0        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                       0       -0.076     0.037   
  x13             experiments[heidi_300k].extinction.coefficient_13                       0       -0.100     0.053   
  x22             experiments[heidi_300k].extinction.coefficient_22                       0        0.283     0.016   
  x23             experiments[heidi_300k].extinction.coefficient_23                       0         0.14      0.12   
  x33             experiments[heidi_300k].extinction.coefficient_33                       0        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale         16.95       18.744     0.089   10.6% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00585      0.00671   0.00025   14.6% ↑
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -0.00107      -9.0e-4    2.0e-4   16.2% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13               -3.00e-5         8e-5     18e-5   371.7% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00352      0.00412   0.00022   17.1% ↑
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.40e-4      -5.1e-4    1.9e-4   5.0% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00365      0.00410   0.00019   12.4% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00350      0.00447   0.00024   27.7% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                4.00e-4       2.9e-4    2.0e-4   26.7% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00473      0.00539   0.00022   14.0% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00483      0.00524   0.00021   8.5% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00570      0.00639   0.00012   12.0% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                -5.60e-5       3.8e-5    8.0e-5   168.7% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00523      0.00586   0.00011   12.0% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00254     0.003074  0.000087   21.0% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00348      0.00413   0.00011   18.7% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 7.00e-5       2.5e-5    8.6e-5   64.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00575      0.00642   0.00011   11.7% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00456     0.004944  0.000092   8.4% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00642     0.007137  0.000084   11.2% ↑
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00188     0.001897  0.000066   1.0% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.49e-4      2.39e-4   0.69e-4   4.0% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00470     0.005365  0.000077   14.2% ↑
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.78e-4     -3.57e-4   0.56e-4   5.6% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00475     0.005205  0.000062   9.5% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00316      0.00386   0.00015   22.1% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.90e-4       1.8e-4    1.1e-4   3.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00339      0.00396   0.00014   16.7% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00229      0.00278   0.00012   21.5% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27662     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99137      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09211     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76704     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44870     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21542     0.215555  0.000085   0.1% ↑
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16420     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03369     0.033602  0.000047   0.3% ↓
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28178     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09485     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42811     0.428146  0.000093   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 55 K: scale

The 300 K parameters stay free, so the 300 K experiment is fitted again from where it ended.

In `experiments/heidi_55k.edi`, add `()` after the values the stage frees:

```edi
cosio_55k 10()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.15         0.50
      1      0.096       6.15         0.50   
edi fit: project sc-neut-cwl_cosio-heidi, 1465 pts fitted / 1465 loaded, 1 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        36.94        70.00
      1      0.072       8.90         4.07   94.2% ↓
  done · converged · 2 iters · reduced χ² 2.22 · wR(F²) 8.39 % · 0.20 s

  per-bank wR(F²) (%):   heidi_300k 6.15   heidi_55k 8.90

  refined parameters (47 free):
  name            parameter                                                           start        value      s.u.   change
  x11             experiments[heidi_300k].extinction.coefficient_11                   0.117        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                  -0.076       -0.076     0.037   0.2% ↓
  x13             experiments[heidi_300k].extinction.coefficient_13                    -0.1       -0.100     0.053   0.2% ↓
  x22             experiments[heidi_300k].extinction.coefficient_22                   0.283        0.283     0.016   0.1% ↓
  x23             experiments[heidi_300k].extinction.coefficient_23                    0.14         0.14      0.12   2.0% ↑
  x33             experiments[heidi_300k].extinction.coefficient_33                   1.156        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        18.744       18.744     0.089   
  scale           experiments[heidi_55k].linked_structures[cosio_55k].scale              10       15.624     0.037   56.2% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00671      0.00671   0.00025   0.1% ↓
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -9.00e-4      -9.0e-4    2.0e-4   0.4% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                8.00e-5         8e-5     18e-5   1.9% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00412      0.00412   0.00022   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.10e-4      -5.1e-4    1.9e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00410      0.00410   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00447      0.00447   0.00024   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                2.90e-4       2.9e-4    2.0e-4   1.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00539      0.00539   0.00022   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00524      0.00524   0.00021   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00639      0.00639   0.00012   0.1% ↓
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 3.80e-5       3.9e-5    8.0e-5   1.3% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00586      0.00586   0.00011   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00307     0.003074  0.000087   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00413      0.00413   0.00011   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 2.50e-5       2.5e-5    8.6e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00642      0.00642   0.00011   0.1% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00494     0.004944  0.000092   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00714     0.007137  0.000084   
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00190     0.001897  0.000066   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.39e-4      2.39e-4   0.69e-4   0.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00536     0.005366  0.000077   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.57e-4     -3.57e-4   0.56e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00521     0.005205  0.000062   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00386      0.00386   0.00015   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.80e-4       1.8e-4    1.1e-4   2.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00396      0.00396   0.00014   0.1% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00278      0.00278   0.00012   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27656     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99133      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09206     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76709     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44869     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21555     0.215555  0.000085   
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03360     0.033602  0.000047   
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28170     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09488     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42815     0.428146  0.000093   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 55 K: coordinates

In `structures/cosio_55k.edi`, add `()` after the values the stage frees:

```edi
Co2 Co 0.27603() 0.25 0.99136() c 4 1 0.003 Uani
Si Si 0.09489() 0.25 0.42824() c 4 1 0.003 Uani
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.15         0.50
      1      0.090       6.15         0.50   
edi fit: project sc-neut-cwl_cosio-heidi, 1465 pts fitted / 1465 loaded, 12 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         8.90         4.10
      1      0.077       8.78         3.99   2.7% ↓
  done · converged · 2 iters · reduced χ² 2.17 · wR(F²) 8.29 % · 0.20 s

  per-bank wR(F²) (%):   heidi_300k 6.15   heidi_55k 8.78

  refined parameters (58 free):
  name            parameter                                                           start        value      s.u.   change
  x11             experiments[heidi_300k].extinction.coefficient_11                   0.117        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                  -0.076       -0.076     0.037   0.2% ↓
  x13             experiments[heidi_300k].extinction.coefficient_13                    -0.1       -0.100     0.053   0.2% ↓
  x22             experiments[heidi_300k].extinction.coefficient_22                   0.283        0.283     0.016   0.1% ↓
  x23             experiments[heidi_300k].extinction.coefficient_23                    0.14         0.14      0.12   2.0% ↑
  x33             experiments[heidi_300k].extinction.coefficient_33                   1.156        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        18.744       18.744     0.089   
  scale           experiments[heidi_55k].linked_structures[cosio_55k].scale          15.624       15.642     0.037   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00671      0.00671   0.00025   0.1% ↓
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -9.00e-4      -9.0e-4    2.0e-4   0.4% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                8.00e-5         8e-5     18e-5   1.9% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00412      0.00412   0.00022   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.10e-4      -5.1e-4    1.9e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00410      0.00410   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00447      0.00447   0.00024   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                2.90e-4       2.9e-4    2.0e-4   1.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00539      0.00539   0.00022   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00524      0.00524   0.00021   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00639      0.00639   0.00012   0.1% ↓
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 3.90e-5       3.9e-5    8.0e-5   1.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00586      0.00586   0.00011   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00307     0.003074  0.000087   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00413      0.00413   0.00011   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 2.50e-5       2.5e-5    8.6e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00642      0.00642   0.00011   0.1% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00494     0.004944  0.000092   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00714     0.007137  0.000084   
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00190     0.001897  0.000066   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.39e-4      2.39e-4   0.69e-4   0.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00537     0.005366  0.000077   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.57e-4     -3.57e-4   0.56e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00521     0.005205  0.000062   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00386      0.00386   0.00015   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.80e-4       1.8e-4    1.1e-4   2.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00396      0.00396   0.00014   0.1% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00278      0.00278   0.00012   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27656     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99133      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09206     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76709     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44869     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21555     0.215555  0.000085   
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03360     0.033602  0.000047   
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28170     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09488     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42815     0.428146  0.000093   
  x               structures[cosio_55k].atom_sites[Co2].fract_x                     0.27603      0.27595   0.00014   
  z               structures[cosio_55k].atom_sites[Co2].fract_z                     0.99136      0.99150   0.00032   
  x               structures[cosio_55k].atom_sites[O1].fract_x                      0.09184     0.092037  0.000058   0.2% ↑
  z               structures[cosio_55k].atom_sites[O1].fract_z                      0.76739      0.76709   0.00013   
  x               structures[cosio_55k].atom_sites[O2].fract_x                      0.44849     0.448504  0.000054   
  z               structures[cosio_55k].atom_sites[O2].fract_z                      0.21578      0.21541   0.00014   0.2% ↓
  x               structures[cosio_55k].atom_sites[O3].fract_x                      0.16428     0.164375  0.000037   0.1% ↑
  y               structures[cosio_55k].atom_sites[O3].fract_y                      0.03324     0.033210  0.000084   0.1% ↓
  z               structures[cosio_55k].atom_sites[O3].fract_z                      0.28116     0.281386  0.000088   0.1% ↑
  x               structures[cosio_55k].atom_sites[Si].fract_x                      0.09489     0.094918  0.000083   
  z               structures[cosio_55k].atom_sites[Si].fract_z                      0.42824      0.42784   0.00018   0.1% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 55 K: extinction

At 55 K the displacements are small. Freed before the extinction, they would take its place and
Co1's tensor would stop being positive definite, so the extinction comes before them here.

In `experiments/heidi_55k.edi`, add `()` after the values the stage frees:

```edi
_extinction.coefficient_11 0()
_extinction.coefficient_22 0()
_extinction.coefficient_33 0()
_extinction.coefficient_12 0()
_extinction.coefficient_13 0()
_extinction.coefficient_23 0()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.15         0.50
      1      0.088       6.15         0.50   
edi fit: project sc-neut-cwl_cosio-heidi, 1465 pts fitted / 1465 loaded, 18 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         8.78         4.00
      1      0.070       6.58         2.25   43.8% ↓
      2      0.080       6.58         2.25   
  done · converged · 3 iters · reduced χ² 1.34 · wR(F²) 6.49 % · 0.20 s

  per-bank wR(F²) (%):   heidi_300k 6.15   heidi_55k 6.58

  refined parameters (64 free):
  name            parameter                                                           start        value      s.u.   change
  x11             experiments[heidi_300k].extinction.coefficient_11                   0.117        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                  -0.076       -0.076     0.037   0.2% ↓
  x13             experiments[heidi_300k].extinction.coefficient_13                    -0.1       -0.100     0.053   0.2% ↓
  x22             experiments[heidi_300k].extinction.coefficient_22                   0.283        0.283     0.016   0.1% ↓
  x23             experiments[heidi_300k].extinction.coefficient_23                    0.14         0.14      0.12   2.0% ↑
  x33             experiments[heidi_300k].extinction.coefficient_33                   1.156        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        18.744       18.744     0.089   
  x11             experiments[heidi_55k].extinction.coefficient_11                        0        0.290     0.026   
  x12             experiments[heidi_55k].extinction.coefficient_12                        0        -0.05      0.11   
  x13             experiments[heidi_55k].extinction.coefficient_13                        0        0.380     0.088   
  x22             experiments[heidi_55k].extinction.coefficient_22                        0         0.28      0.13   
  x23             experiments[heidi_55k].extinction.coefficient_23                        0        -0.12      0.15   
  x33             experiments[heidi_55k].extinction.coefficient_33                        0        1.658     0.088   
  scale           experiments[heidi_55k].linked_structures[cosio_55k].scale          15.642       16.830     0.053   7.6% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00671      0.00671   0.00025   0.1% ↓
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -9.00e-4      -9.0e-4    2.0e-4   0.4% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                8.00e-5         8e-5     18e-5   1.9% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00412      0.00412   0.00022   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.10e-4      -5.1e-4    1.9e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00410      0.00410   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00447      0.00447   0.00024   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                2.90e-4       2.9e-4    2.0e-4   1.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00539      0.00539   0.00022   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00524      0.00524   0.00021   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00639      0.00639   0.00012   0.1% ↓
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 3.90e-5       3.9e-5    8.0e-5   1.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00586      0.00586   0.00011   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00307     0.003074  0.000087   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00413      0.00413   0.00011   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 2.50e-5       2.5e-5    8.6e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00642      0.00642   0.00011   0.1% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00494     0.004944  0.000092   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00714     0.007137  0.000084   
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00190     0.001897  0.000066   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.39e-4      2.39e-4   0.69e-4   0.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00537     0.005366  0.000077   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.57e-4     -3.57e-4   0.56e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00521     0.005205  0.000062   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00386      0.00386   0.00015   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.80e-4       1.8e-4    1.1e-4   2.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00396      0.00396   0.00014   0.1% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00278      0.00278   0.00012   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27656     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99133      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09206     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76709     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44869     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21555     0.215555  0.000085   
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03360     0.033602  0.000047   
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28170     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09488     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42815     0.428146  0.000093   
  x               structures[cosio_55k].atom_sites[Co2].fract_x                     0.27595     0.275878  0.000099   
  z               structures[cosio_55k].atom_sites[Co2].fract_z                     0.99150      0.99163   0.00023   
  x               structures[cosio_55k].atom_sites[O1].fract_x                      0.09204     0.091981  0.000043   0.1% ↓
  z               structures[cosio_55k].atom_sites[O1].fract_z                      0.76709     0.767221  0.000096   
  x               structures[cosio_55k].atom_sites[O2].fract_x                      0.44850     0.448460  0.000040   
  z               structures[cosio_55k].atom_sites[O2].fract_z                      0.21541      0.21573   0.00011   0.1% ↑
  x               structures[cosio_55k].atom_sites[O3].fract_x                      0.16437     0.164340  0.000028   
  y               structures[cosio_55k].atom_sites[O3].fract_y                      0.03321     0.033284  0.000063   0.2% ↑
  z               structures[cosio_55k].atom_sites[O3].fract_z                      0.28139     0.281213  0.000064   0.1% ↓
  x               structures[cosio_55k].atom_sites[Si].fract_x                      0.09492     0.094872  0.000061   
  z               structures[cosio_55k].atom_sites[Si].fract_z                      0.42784      0.42798   0.00014   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 55 K: displacements

In `structures/cosio_55k.edi`, add `()` after the values the stage frees:

```edi
Co1 0.003() 0.003() 0.003() 0() 0() 0()
Co2 0.003() 0.003() 0.003() 0 0() 0
```

The same for every other row (4 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.15         0.50
      1      0.089       6.15         0.50   
edi fit: project sc-neut-cwl_cosio-heidi, 1465 pts fitted / 1465 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.58         2.29
      1      0.112       3.79         0.76   66.8% ↓
  done · converged · 2 iters · reduced χ² 0.62 · wR(F²) 4.41 % · 0.24 s

  per-bank wR(F²) (%):   heidi_300k 6.15   heidi_55k 3.79

  refined parameters (92 free):
  name            parameter                                                           start        value      s.u.   change
  x11             experiments[heidi_300k].extinction.coefficient_11                   0.117        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                  -0.076       -0.076     0.037   0.2% ↓
  x13             experiments[heidi_300k].extinction.coefficient_13                    -0.1       -0.100     0.053   0.2% ↓
  x22             experiments[heidi_300k].extinction.coefficient_22                   0.283        0.283     0.016   0.1% ↓
  x23             experiments[heidi_300k].extinction.coefficient_23                    0.14         0.14      0.12   2.0% ↑
  x33             experiments[heidi_300k].extinction.coefficient_33                   1.156        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        18.744       18.744     0.089   
  x11             experiments[heidi_55k].extinction.coefficient_11                     0.29        0.130     0.015   55.2% ↓
  x12             experiments[heidi_55k].extinction.coefficient_12                    -0.05        0.186     0.059   472.9% ↑
  x13             experiments[heidi_55k].extinction.coefficient_13                     0.38        0.191     0.048   49.8% ↓
  x22             experiments[heidi_55k].extinction.coefficient_22                     0.28        0.068     0.067   75.6% ↓
  x23             experiments[heidi_55k].extinction.coefficient_23                    -0.12        0.078     0.082   165.1% ↑
  x33             experiments[heidi_55k].extinction.coefficient_33                    1.658        1.356     0.054   18.2% ↓
  scale           experiments[heidi_55k].linked_structures[cosio_55k].scale           16.83       16.018     0.065   4.8% ↓
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00671      0.00671   0.00025   0.1% ↓
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -9.00e-4      -9.0e-4    2.0e-4   0.4% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                8.00e-5         8e-5     18e-5   1.9% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00412      0.00412   0.00022   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.10e-4      -5.1e-4    1.9e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00410      0.00410   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00447      0.00447   0.00024   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                2.90e-4       2.9e-4    2.0e-4   1.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00539      0.00539   0.00022   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00524      0.00524   0.00021   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00639      0.00639   0.00012   0.1% ↓
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 3.90e-5       3.9e-5    8.0e-5   1.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00586      0.00586   0.00011   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00307     0.003074  0.000087   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00413      0.00413   0.00011   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 2.50e-5       2.5e-5    8.6e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00642      0.00642   0.00011   0.1% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00494     0.004944  0.000092   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00714     0.007137  0.000084   
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00190     0.001897  0.000066   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.39e-4      2.39e-4   0.69e-4   0.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00537     0.005366  0.000077   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.57e-4     -3.57e-4   0.56e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00521     0.005205  0.000062   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00386      0.00386   0.00015   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.80e-4       1.8e-4    1.1e-4   2.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00396      0.00396   0.00014   0.1% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00278      0.00278   0.00012   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27656     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99133      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09206     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76709     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44869     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21555     0.215555  0.000085   
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03360     0.033602  0.000047   
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28170     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09488     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42815     0.428146  0.000093   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_11                 0.00300      0.00244   0.00015   18.5% ↓
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_12                 0.00000      -1.5e-4    1.1e-4   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_13                 0.00000         5e-5     11e-5   
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_22                 0.00300      0.00101   0.00024   66.2% ↓
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_23                 0.00000      -1.2e-4    1.3e-4   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_33                 0.00300      0.00167   0.00015   44.3% ↓
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_11                 0.00300      0.00176   0.00015   41.2% ↓
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_13                 0.00000      -1.7e-4    1.1e-4   
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_22                 0.00300      0.00159   0.00023   47.1% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_33                 0.00300      0.00184   0.00015   38.7% ↓
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_11                  0.00300     0.003460  0.000072   15.3% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_13                  0.00000       4.8e-5    5.4e-5   
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_22                  0.00300      0.00296   0.00012   1.5% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_33                  0.00300     0.002010  0.000073   33.0% ↓
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_11                  0.00300     0.002226  0.000070   25.8% ↓
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_13                  0.00000       5.1e-5    5.7e-5   
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_22                  0.00300      0.00290   0.00012   3.3% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_33                  0.00300     0.002941  0.000072   2.0% ↓
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_11                  0.00300     0.003514  0.000053   17.1% ↑
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_12                  0.00000      7.07e-4   0.35e-4   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_13                  0.00000      1.62e-4   0.43e-4   
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_22                  0.00300     0.002207  0.000082   26.4% ↓
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_23                  0.00000     -1.57e-4   0.45e-4   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_33                  0.00300     0.003080  0.000052   2.7% ↑
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_11                  0.00300     0.001810  0.000090   39.7% ↓
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_13                  0.00000      -3.6e-5    6.9e-5   
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_22                  0.00300      0.00112   0.00015   62.6% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_33                  0.00300     0.001541  0.000092   48.6% ↓
  x               structures[cosio_55k].atom_sites[Co2].fract_x                     0.27588     0.276023  0.000055   0.1% ↑
  z               structures[cosio_55k].atom_sites[Co2].fract_z                     0.99163      0.99134   0.00013   
  x               structures[cosio_55k].atom_sites[O1].fract_x                      0.09198     0.091844  0.000027   0.1% ↓
  z               structures[cosio_55k].atom_sites[O1].fract_z                      0.76722     0.767395  0.000056   
  x               structures[cosio_55k].atom_sites[O2].fract_x                      0.44846     0.448486  0.000023   
  z               structures[cosio_55k].atom_sites[O2].fract_z                      0.21573     0.215778  0.000059   
  x               structures[cosio_55k].atom_sites[O3].fract_x                      0.16434     0.164276  0.000017   
  y               structures[cosio_55k].atom_sites[O3].fract_y                      0.03328     0.033241  0.000038   0.1% ↓
  z               structures[cosio_55k].atom_sites[O3].fract_z                      0.28121     0.281158  0.000040   
  x               structures[cosio_55k].atom_sites[Si].fract_x                      0.09487     0.094886  0.000034   
  z               structures[cosio_55k].atom_sites[Si].fract_z                      0.42798     0.428231  0.000071   0.1% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 2.5 K: scale

The nuclear structure first, with every moment still at zero, in the order 55 K needed.

In `experiments/heidi_2k5.edi`, add `()` after the values the stage frees:

```edi
cosio_2k5 10()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1424 pts fitted / 1424 loaded, 1 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        39.11        63.53
      1      0.135      13.12         7.15   88.7% ↓
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.15         0.50
      1      0.090       6.15         0.50   
edi fit: project sc-neut-cwl_cosio-heidi, 1465 pts fitted / 1465 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         3.79         0.76
      1      0.078       3.79         0.76   
  done · converged · 3 iters · reduced χ² 2.72 · wR(F²) 8.82 % · 0.36 s

  per-bank wR(F²) (%):   heidi_2k5 13.12   heidi_300k 6.15   heidi_55k 3.79

  refined parameters (93 free):
  name            parameter                                                           start        value      s.u.   change
  scale           experiments[heidi_2k5].linked_structures[cosio_2k5].scale              10       15.915     0.056   59.2% ↑
  x11             experiments[heidi_300k].extinction.coefficient_11                   0.117        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                  -0.076       -0.076     0.037   0.2% ↓
  x13             experiments[heidi_300k].extinction.coefficient_13                    -0.1       -0.100     0.053   0.2% ↓
  x22             experiments[heidi_300k].extinction.coefficient_22                   0.283        0.283     0.016   0.1% ↓
  x23             experiments[heidi_300k].extinction.coefficient_23                    0.14         0.14      0.12   2.0% ↑
  x33             experiments[heidi_300k].extinction.coefficient_33                   1.156        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        18.744       18.744     0.089   
  x11             experiments[heidi_55k].extinction.coefficient_11                     0.13        0.130     0.015   
  x12             experiments[heidi_55k].extinction.coefficient_12                    0.186        0.186     0.059   0.2% ↑
  x13             experiments[heidi_55k].extinction.coefficient_13                    0.191        0.191     0.048   0.1% ↓
  x22             experiments[heidi_55k].extinction.coefficient_22                    0.068        0.068     0.067   0.6% ↑
  x23             experiments[heidi_55k].extinction.coefficient_23                    0.078        0.078     0.082   0.1% ↑
  x33             experiments[heidi_55k].extinction.coefficient_33                    1.356        1.356     0.054   
  scale           experiments[heidi_55k].linked_structures[cosio_55k].scale          16.018       16.018     0.065   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00671      0.00671   0.00025   0.1% ↓
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -9.00e-4      -9.0e-4    2.0e-4   0.4% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                8.00e-5         8e-5     18e-5   1.9% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00412      0.00412   0.00022   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.10e-4      -5.1e-4    1.9e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00410      0.00410   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00447      0.00447   0.00024   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                2.90e-4       2.9e-4    2.0e-4   1.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00539      0.00539   0.00022   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00524      0.00524   0.00021   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00639      0.00639   0.00012   0.1% ↓
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 3.90e-5       3.9e-5    8.0e-5   1.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00586      0.00586   0.00011   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00307     0.003074  0.000087   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00413      0.00413   0.00011   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 2.50e-5       2.5e-5    8.6e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00642      0.00642   0.00011   0.1% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00494     0.004944  0.000092   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00714     0.007137  0.000084   
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00190     0.001897  0.000066   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.39e-4      2.39e-4   0.69e-4   0.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00537     0.005366  0.000077   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.57e-4     -3.57e-4   0.56e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00521     0.005205  0.000062   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00386      0.00386   0.00015   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.80e-4       1.8e-4    1.1e-4   2.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00396      0.00396   0.00014   0.1% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00278      0.00278   0.00012   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27656     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99133      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09206     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76709     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44869     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21555     0.215555  0.000085   
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03360     0.033602  0.000047   
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28170     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09488     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42815     0.428146  0.000093   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_11                 0.00244      0.00244   0.00015   0.2% ↑
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_12                -1.50e-4      -1.5e-4    1.1e-4   1.3% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_13                 5.00e-5         5e-5     11e-5   4.3% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_22                 0.00101      0.00101   0.00024   0.3% ↑
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_23                -1.20e-4      -1.2e-4    1.3e-4   3.5% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_33                 0.00167      0.00167   0.00015   0.1% ↑
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_11                 0.00176      0.00176   0.00015   0.1% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_13                -1.70e-4      -1.7e-4    1.1e-4   2.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_22                 0.00159      0.00159   0.00023   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_33                 0.00184      0.00184   0.00015   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_11                  0.00346     0.003460  0.000072   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_13                  4.80e-5       4.8e-5    5.4e-5   0.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_22                  0.00296      0.00296   0.00012   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_33                  0.00201     0.002010  0.000073   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_11                  0.00223     0.002226  0.000070   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_13                  5.10e-5       5.1e-5    5.7e-5   0.5% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_22                  0.00290      0.00290   0.00012   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_33                  0.00294     0.002941  0.000072   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_11                  0.00351     0.003514  0.000053   
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_12                  7.07e-4      7.07e-4   0.35e-4   0.1% ↓
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_13                  1.62e-4      1.62e-4   0.43e-4   0.1% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_22                  0.00221     0.002207  0.000082   
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_23                 -1.57e-4     -1.57e-4   0.45e-4   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_33                  0.00308     0.003080  0.000052   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_11                  0.00181     0.001810  0.000090   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_13                 -3.60e-5      -3.6e-5    6.9e-5   0.3% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_22                  0.00112      0.00112   0.00015   0.1% ↑
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_33                  0.00154     0.001541  0.000092   
  x               structures[cosio_55k].atom_sites[Co2].fract_x                     0.27602     0.276023  0.000055   
  z               structures[cosio_55k].atom_sites[Co2].fract_z                     0.99134      0.99134   0.00013   
  x               structures[cosio_55k].atom_sites[O1].fract_x                      0.09184     0.091844  0.000027   
  z               structures[cosio_55k].atom_sites[O1].fract_z                      0.76740     0.767395  0.000056   
  x               structures[cosio_55k].atom_sites[O2].fract_x                      0.44849     0.448486  0.000023   
  z               structures[cosio_55k].atom_sites[O2].fract_z                      0.21578     0.215778  0.000059   
  x               structures[cosio_55k].atom_sites[O3].fract_x                      0.16428     0.164276  0.000017   
  y               structures[cosio_55k].atom_sites[O3].fract_y                      0.03324     0.033241  0.000038   
  z               structures[cosio_55k].atom_sites[O3].fract_z                      0.28116     0.281158  0.000040   
  x               structures[cosio_55k].atom_sites[Si].fract_x                      0.09489     0.094886  0.000034   
  z               structures[cosio_55k].atom_sites[Si].fract_z                      0.42823     0.428231  0.000071   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 2.5 K: coordinates

In `structures/cosio_2k5.edi`, add `()` after the values the stage frees:

```edi
Co2 Co 0.27597() 0.25 0.99115() c 4 1 0.003 Uani
Si Si 0.09479() 0.25 0.42838() c 4 1 0.003 Uani
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1424 pts fitted / 1424 loaded, 12 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        13.12         7.21
      1      0.111      13.01         7.09   1.7% ↓
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.15         0.50
      1      0.084       6.15         0.50   
edi fit: project sc-neut-cwl_cosio-heidi, 1465 pts fitted / 1465 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         3.79         0.76
      1      0.080       3.79         0.76   
  done · converged · 3 iters · reduced χ² 2.69 · wR(F²) 8.75 % · 0.33 s

  per-bank wR(F²) (%):   heidi_2k5 13.01   heidi_300k 6.15   heidi_55k 3.79

  refined parameters (104 free):
  name            parameter                                                           start        value      s.u.   change
  scale           experiments[heidi_2k5].linked_structures[cosio_2k5].scale          15.915       15.935     0.056   0.1% ↑
  x11             experiments[heidi_300k].extinction.coefficient_11                   0.117        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                  -0.076       -0.076     0.037   0.2% ↓
  x13             experiments[heidi_300k].extinction.coefficient_13                    -0.1       -0.100     0.053   0.2% ↓
  x22             experiments[heidi_300k].extinction.coefficient_22                   0.283        0.283     0.016   0.1% ↓
  x23             experiments[heidi_300k].extinction.coefficient_23                    0.14         0.14      0.12   2.0% ↑
  x33             experiments[heidi_300k].extinction.coefficient_33                   1.156        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        18.744       18.744     0.089   
  x11             experiments[heidi_55k].extinction.coefficient_11                     0.13        0.130     0.015   
  x12             experiments[heidi_55k].extinction.coefficient_12                    0.186        0.186     0.059   0.2% ↑
  x13             experiments[heidi_55k].extinction.coefficient_13                    0.191        0.191     0.048   0.1% ↓
  x22             experiments[heidi_55k].extinction.coefficient_22                    0.068        0.068     0.067   0.6% ↑
  x23             experiments[heidi_55k].extinction.coefficient_23                    0.078        0.078     0.082   0.1% ↑
  x33             experiments[heidi_55k].extinction.coefficient_33                    1.356        1.356     0.054   
  scale           experiments[heidi_55k].linked_structures[cosio_55k].scale          16.018       16.018     0.065   
  x               structures[cosio_2k5].atom_sites[Co2].fract_x                     0.27597      0.27598   0.00021   
  z               structures[cosio_2k5].atom_sites[Co2].fract_z                     0.99115      0.99142   0.00045   
  x               structures[cosio_2k5].atom_sites[O1].fract_x                      0.09180     0.091932  0.000090   0.1% ↑
  z               structures[cosio_2k5].atom_sites[O1].fract_z                      0.76731      0.76714   0.00019   
  x               structures[cosio_2k5].atom_sites[O2].fract_x                      0.44854     0.448537  0.000082   
  z               structures[cosio_2k5].atom_sites[O2].fract_z                      0.21605      0.21563   0.00020   0.2% ↓
  x               structures[cosio_2k5].atom_sites[O3].fract_x                      0.16438     0.164492  0.000058   0.1% ↑
  y               structures[cosio_2k5].atom_sites[O3].fract_y                      0.03313      0.03338   0.00014   0.8% ↑
  z               structures[cosio_2k5].atom_sites[O3].fract_z                      0.28129      0.28157   0.00013   0.1% ↑
  x               structures[cosio_2k5].atom_sites[Si].fract_x                      0.09479      0.09485   0.00013   0.1% ↑
  z               structures[cosio_2k5].atom_sites[Si].fract_z                      0.42838      0.42787   0.00026   0.1% ↓
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00671      0.00671   0.00025   0.1% ↓
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -9.00e-4      -9.0e-4    2.0e-4   0.4% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                8.00e-5         8e-5     18e-5   1.9% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00412      0.00412   0.00022   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.10e-4      -5.1e-4    1.9e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00410      0.00410   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00447      0.00447   0.00024   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                2.90e-4       2.9e-4    2.0e-4   1.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00539      0.00539   0.00022   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00524      0.00524   0.00021   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00639      0.00639   0.00012   0.1% ↓
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 3.90e-5       3.9e-5    8.0e-5   1.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00586      0.00586   0.00011   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00307     0.003074  0.000087   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00413      0.00413   0.00011   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 2.50e-5       2.5e-5    8.6e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00642      0.00642   0.00011   0.1% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00494     0.004944  0.000092   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00714     0.007137  0.000084   
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00190     0.001897  0.000066   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.39e-4      2.39e-4   0.69e-4   0.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00537     0.005366  0.000077   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.57e-4     -3.57e-4   0.56e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00521     0.005205  0.000062   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00386      0.00386   0.00015   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.80e-4       1.8e-4    1.1e-4   2.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00396      0.00396   0.00014   0.1% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00278      0.00278   0.00012   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27656     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99133      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09206     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76709     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44869     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21555     0.215555  0.000085   
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03360     0.033602  0.000047   
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28170     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09488     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42815     0.428146  0.000093   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_11                 0.00244      0.00244   0.00015   0.2% ↑
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_12                -1.50e-4      -1.5e-4    1.1e-4   1.3% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_13                 5.00e-5         5e-5     11e-5   4.3% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_22                 0.00101      0.00101   0.00024   0.3% ↑
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_23                -1.20e-4      -1.2e-4    1.3e-4   3.5% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_33                 0.00167      0.00167   0.00015   0.1% ↑
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_11                 0.00176      0.00176   0.00015   0.1% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_13                -1.70e-4      -1.7e-4    1.1e-4   2.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_22                 0.00159      0.00159   0.00023   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_33                 0.00184      0.00184   0.00015   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_11                  0.00346     0.003460  0.000072   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_13                  4.80e-5       4.8e-5    5.4e-5   0.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_22                  0.00296      0.00296   0.00012   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_33                  0.00201     0.002010  0.000073   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_11                  0.00223     0.002226  0.000070   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_13                  5.10e-5       5.1e-5    5.7e-5   0.5% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_22                  0.00290      0.00290   0.00012   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_33                  0.00294     0.002941  0.000072   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_11                  0.00351     0.003514  0.000053   
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_12                  7.07e-4      7.07e-4   0.35e-4   0.1% ↓
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_13                  1.62e-4      1.62e-4   0.43e-4   0.1% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_22                  0.00221     0.002207  0.000082   
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_23                 -1.57e-4     -1.57e-4   0.45e-4   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_33                  0.00308     0.003080  0.000052   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_11                  0.00181     0.001810  0.000090   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_13                 -3.60e-5      -3.6e-5    6.9e-5   0.3% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_22                  0.00112      0.00112   0.00015   0.1% ↑
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_33                  0.00154     0.001541  0.000092   
  x               structures[cosio_55k].atom_sites[Co2].fract_x                     0.27602     0.276023  0.000055   
  z               structures[cosio_55k].atom_sites[Co2].fract_z                     0.99134      0.99134   0.00013   
  x               structures[cosio_55k].atom_sites[O1].fract_x                      0.09184     0.091844  0.000027   
  z               structures[cosio_55k].atom_sites[O1].fract_z                      0.76740     0.767395  0.000056   
  x               structures[cosio_55k].atom_sites[O2].fract_x                      0.44849     0.448486  0.000023   
  z               structures[cosio_55k].atom_sites[O2].fract_z                      0.21578     0.215778  0.000059   
  x               structures[cosio_55k].atom_sites[O3].fract_x                      0.16428     0.164276  0.000017   
  y               structures[cosio_55k].atom_sites[O3].fract_y                      0.03324     0.033241  0.000038   
  z               structures[cosio_55k].atom_sites[O3].fract_z                      0.28116     0.281158  0.000040   
  x               structures[cosio_55k].atom_sites[Si].fract_x                      0.09489     0.094886  0.000034   
  z               structures[cosio_55k].atom_sites[Si].fract_z                      0.42823     0.428231  0.000071   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 2.5 K: extinction

In `experiments/heidi_2k5.edi`, add `()` after the values the stage frees:

```edi
_extinction.coefficient_11 0()
_extinction.coefficient_22 0()
_extinction.coefficient_33 0()
_extinction.coefficient_12 0()
_extinction.coefficient_13 0()
_extinction.coefficient_23 0()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1424 pts fitted / 1424 loaded, 18 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        13.01         7.12
      1      0.118      11.88         5.93   16.6% ↓
      2      0.134      11.88         5.93   
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.15         0.50
      1      0.086       6.15         0.50   
edi fit: project sc-neut-cwl_cosio-heidi, 1465 pts fitted / 1465 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         3.79         0.76
      1      0.080       3.79         0.76   
  done · converged · 4 iters · reduced χ² 2.32 · wR(F²) 8.12 % · 0.35 s

  per-bank wR(F²) (%):   heidi_2k5 11.88   heidi_300k 6.15   heidi_55k 3.79

  refined parameters (110 free):
  name            parameter                                                           start        value      s.u.   change
  x11             experiments[heidi_2k5].extinction.coefficient_11                        0        0.210     0.037   
  x12             experiments[heidi_2k5].extinction.coefficient_12                        0         0.03      0.14   
  x13             experiments[heidi_2k5].extinction.coefficient_13                        0        -0.28      0.12   
  x22             experiments[heidi_2k5].extinction.coefficient_22                        0         0.29      0.18   
  x23             experiments[heidi_2k5].extinction.coefficient_23                        0         0.07      0.20   
  x33             experiments[heidi_2k5].extinction.coefficient_33                        0         1.38      0.14   
  scale           experiments[heidi_2k5].linked_structures[cosio_2k5].scale          15.935       16.962     0.093   6.4% ↑
  x11             experiments[heidi_300k].extinction.coefficient_11                   0.117        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                  -0.076       -0.076     0.037   0.2% ↓
  x13             experiments[heidi_300k].extinction.coefficient_13                    -0.1       -0.100     0.053   0.2% ↓
  x22             experiments[heidi_300k].extinction.coefficient_22                   0.283        0.283     0.016   0.1% ↓
  x23             experiments[heidi_300k].extinction.coefficient_23                    0.14         0.14      0.12   2.0% ↑
  x33             experiments[heidi_300k].extinction.coefficient_33                   1.156        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        18.744       18.744     0.089   
  x11             experiments[heidi_55k].extinction.coefficient_11                     0.13        0.130     0.015   
  x12             experiments[heidi_55k].extinction.coefficient_12                    0.186        0.186     0.059   0.2% ↑
  x13             experiments[heidi_55k].extinction.coefficient_13                    0.191        0.191     0.048   0.1% ↓
  x22             experiments[heidi_55k].extinction.coefficient_22                    0.068        0.068     0.067   0.6% ↑
  x23             experiments[heidi_55k].extinction.coefficient_23                    0.078        0.078     0.082   0.1% ↑
  x33             experiments[heidi_55k].extinction.coefficient_33                    1.356        1.356     0.054   
  scale           experiments[heidi_55k].linked_structures[cosio_55k].scale          16.018       16.018     0.065   
  x               structures[cosio_2k5].atom_sites[Co2].fract_x                     0.27598      0.27586   0.00019   
  z               structures[cosio_2k5].atom_sites[Co2].fract_z                     0.99142      0.99159   0.00040   
  x               structures[cosio_2k5].atom_sites[O1].fract_x                      0.09193     0.091945  0.000081   
  z               structures[cosio_2k5].atom_sites[O1].fract_z                      0.76714      0.76724   0.00017   
  x               structures[cosio_2k5].atom_sites[O2].fract_x                      0.44854     0.448518  0.000074   
  z               structures[cosio_2k5].atom_sites[O2].fract_z                      0.21563      0.21592   0.00018   0.1% ↑
  x               structures[cosio_2k5].atom_sites[O3].fract_x                      0.16449     0.164472  0.000053   
  y               structures[cosio_2k5].atom_sites[O3].fract_y                      0.03338      0.03331   0.00013   0.2% ↓
  z               structures[cosio_2k5].atom_sites[O3].fract_z                      0.28157      0.28143   0.00012   0.1% ↓
  x               structures[cosio_2k5].atom_sites[Si].fract_x                      0.09485      0.09480   0.00012   0.1% ↓
  z               structures[cosio_2k5].atom_sites[Si].fract_z                      0.42787      0.42809   0.00023   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00671      0.00671   0.00025   0.1% ↓
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -9.00e-4      -9.0e-4    2.0e-4   0.4% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                8.00e-5         8e-5     18e-5   1.9% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00412      0.00412   0.00022   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.10e-4      -5.1e-4    1.9e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00410      0.00410   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00447      0.00447   0.00024   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                2.90e-4       2.9e-4    2.0e-4   1.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00539      0.00539   0.00022   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00524      0.00524   0.00021   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00639      0.00639   0.00012   0.1% ↓
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 3.90e-5       3.9e-5    8.0e-5   1.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00586      0.00586   0.00011   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00307     0.003074  0.000087   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00413      0.00413   0.00011   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 2.50e-5       2.5e-5    8.6e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00642      0.00642   0.00011   0.1% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00494     0.004944  0.000092   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00714     0.007137  0.000084   
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00190     0.001897  0.000066   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.39e-4      2.39e-4   0.69e-4   0.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00537     0.005366  0.000077   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.57e-4     -3.57e-4   0.56e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00521     0.005205  0.000062   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00386      0.00386   0.00015   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.80e-4       1.8e-4    1.1e-4   2.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00396      0.00396   0.00014   0.1% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00278      0.00278   0.00012   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27656     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99133      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09206     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76709     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44869     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21555     0.215555  0.000085   
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03360     0.033602  0.000047   
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28170     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09488     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42815     0.428146  0.000093   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_11                 0.00244      0.00244   0.00015   0.2% ↑
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_12                -1.50e-4      -1.5e-4    1.1e-4   1.3% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_13                 5.00e-5         5e-5     11e-5   4.3% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_22                 0.00101      0.00101   0.00024   0.3% ↑
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_23                -1.20e-4      -1.2e-4    1.3e-4   3.5% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_33                 0.00167      0.00167   0.00015   0.1% ↑
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_11                 0.00176      0.00176   0.00015   0.1% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_13                -1.70e-4      -1.7e-4    1.1e-4   2.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_22                 0.00159      0.00159   0.00023   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_33                 0.00184      0.00184   0.00015   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_11                  0.00346     0.003460  0.000072   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_13                  4.80e-5       4.8e-5    5.4e-5   0.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_22                  0.00296      0.00296   0.00012   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_33                  0.00201     0.002010  0.000073   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_11                  0.00223     0.002226  0.000070   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_13                  5.10e-5       5.1e-5    5.7e-5   0.5% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_22                  0.00290      0.00290   0.00012   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_33                  0.00294     0.002941  0.000072   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_11                  0.00351     0.003514  0.000053   
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_12                  7.07e-4      7.07e-4   0.35e-4   0.1% ↓
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_13                  1.62e-4      1.62e-4   0.43e-4   0.1% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_22                  0.00221     0.002207  0.000082   
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_23                 -1.57e-4     -1.57e-4   0.45e-4   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_33                  0.00308     0.003080  0.000052   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_11                  0.00181     0.001810  0.000090   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_13                 -3.60e-5      -3.6e-5    6.9e-5   0.3% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_22                  0.00112      0.00112   0.00015   0.1% ↑
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_33                  0.00154     0.001541  0.000092   
  x               structures[cosio_55k].atom_sites[Co2].fract_x                     0.27602     0.276023  0.000055   
  z               structures[cosio_55k].atom_sites[Co2].fract_z                     0.99134      0.99134   0.00013   
  x               structures[cosio_55k].atom_sites[O1].fract_x                      0.09184     0.091844  0.000027   
  z               structures[cosio_55k].atom_sites[O1].fract_z                      0.76740     0.767395  0.000056   
  x               structures[cosio_55k].atom_sites[O2].fract_x                      0.44849     0.448486  0.000023   
  z               structures[cosio_55k].atom_sites[O2].fract_z                      0.21578     0.215778  0.000059   
  x               structures[cosio_55k].atom_sites[O3].fract_x                      0.16428     0.164276  0.000017   
  y               structures[cosio_55k].atom_sites[O3].fract_y                      0.03324     0.033241  0.000038   
  z               structures[cosio_55k].atom_sites[O3].fract_z                      0.28116     0.281158  0.000040   
  x               structures[cosio_55k].atom_sites[Si].fract_x                      0.09489     0.094886  0.000034   
  z               structures[cosio_55k].atom_sites[Si].fract_z                      0.42823     0.428231  0.000071   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## 2.5 K: displacements

In `structures/cosio_2k5.edi`, add `()` after the values the stage frees:

```edi
Co1 0.003() 0.003() 0.003() 0() 0() 0()
Co2 0.003() 0.003() 0.003() 0 0() 0
```

The same for every other row (4 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1424 pts fitted / 1424 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        11.88         6.05
      1      0.188      10.52         4.74   21.7% ↓
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.15         0.50
      1      0.080       6.15         0.50   
edi fit: project sc-neut-cwl_cosio-heidi, 1465 pts fitted / 1465 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         3.79         0.76
      1      0.077       3.79         0.76   
  done · converged · 3 iters · reduced χ² 1.92 · wR(F²) 7.36 % · 0.41 s

  per-bank wR(F²) (%):   heidi_2k5 10.52   heidi_300k 6.15   heidi_55k 3.79

  refined parameters (138 free):
  name            parameter                                                           start        value      s.u.   change
  x11             experiments[heidi_2k5].extinction.coefficient_11                     0.21        0.077     0.032   63.3% ↓
  x12             experiments[heidi_2k5].extinction.coefficient_12                     0.03         0.19      0.11   527.7% ↑
  x13             experiments[heidi_2k5].extinction.coefficient_13                    -0.28       -0.206     0.095   26.4% ↑
  x22             experiments[heidi_2k5].extinction.coefficient_22                     0.29         0.16      0.16   45.3% ↓
  x23             experiments[heidi_2k5].extinction.coefficient_23                     0.07         0.15      0.17   115.7% ↑
  x33             experiments[heidi_2k5].extinction.coefficient_33                     1.38         1.10      0.13   20.0% ↓
  scale           experiments[heidi_2k5].linked_structures[cosio_2k5].scale          16.962        16.15      0.17   4.8% ↓
  x11             experiments[heidi_300k].extinction.coefficient_11                   0.117        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                  -0.076       -0.076     0.037   0.2% ↓
  x13             experiments[heidi_300k].extinction.coefficient_13                    -0.1       -0.100     0.053   0.2% ↓
  x22             experiments[heidi_300k].extinction.coefficient_22                   0.283        0.283     0.016   0.1% ↓
  x23             experiments[heidi_300k].extinction.coefficient_23                    0.14         0.14      0.12   2.0% ↑
  x33             experiments[heidi_300k].extinction.coefficient_33                   1.156        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        18.744       18.744     0.089   
  x11             experiments[heidi_55k].extinction.coefficient_11                     0.13        0.130     0.015   
  x12             experiments[heidi_55k].extinction.coefficient_12                    0.186        0.186     0.059   0.2% ↑
  x13             experiments[heidi_55k].extinction.coefficient_13                    0.191        0.191     0.048   0.1% ↓
  x22             experiments[heidi_55k].extinction.coefficient_22                    0.068        0.068     0.067   0.6% ↑
  x23             experiments[heidi_55k].extinction.coefficient_23                    0.078        0.078     0.082   0.1% ↑
  x33             experiments[heidi_55k].extinction.coefficient_33                    1.356        1.356     0.054   
  scale           experiments[heidi_55k].linked_structures[cosio_55k].scale          16.018       16.018     0.065   
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_11                 0.00300      0.00207   0.00038   30.8% ↓
  U₁₂, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_12                 0.00000      -2.4e-4    3.4e-4   
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_13                 0.00000         2e-5     29e-5   
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_22                 0.00300      0.00159   0.00074   47.1% ↓
  U₂₃, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_23                 0.00000         7e-5     39e-5   
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_33                 0.00300      0.00161   0.00037   46.4% ↓
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[Co2].adp_11                 0.00300      0.00215   0.00040   28.2% ↓
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[Co2].adp_13                 0.00000       1.3e-4    3.1e-4   
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[Co2].adp_22                 0.00300       7.0e-4    7.2e-4 ! 76.6% ↓
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[Co2].adp_33                 0.00300      0.00210   0.00037   29.9% ↓
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[O1].adp_11                  0.00300      0.00355   0.00019   18.4% ↑
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[O1].adp_13                  0.00000         3e-5     15e-5   
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[O1].adp_22                  0.00300      0.00280   0.00039   6.7% ↓
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[O1].adp_33                  0.00300      0.00191   0.00019   36.2% ↓
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[O2].adp_11                  0.00300      0.00211   0.00019   29.6% ↓
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[O2].adp_13                  0.00000       1.2e-4    1.6e-4   
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[O2].adp_22                  0.00300      0.00291   0.00038   2.9% ↓
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[O2].adp_33                  0.00300      0.00293   0.00019   2.3% ↓
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_11                  0.00300      0.00357   0.00014   19.1% ↑
  U₁₂, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_12                  0.00000       7.8e-4    1.2e-4   
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_13                  0.00000       1.5e-4    1.2e-4   
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_22                  0.00300      0.00211   0.00027   29.7% ↓
  U₂₃, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_23                  0.00000      -3.0e-4    1.3e-4   
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_33                  0.00300      0.00307   0.00014   2.5% ↑
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[Si].adp_11                  0.00300      0.00195   0.00024   35.1% ↓
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[Si].adp_13                  0.00000         2e-5     19e-5   
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[Si].adp_22                  0.00300      0.00128   0.00045   57.3% ↓
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[Si].adp_33                  0.00300      0.00146   0.00024   51.4% ↓
  x               structures[cosio_2k5].atom_sites[Co2].fract_x                     0.27586      0.27601   0.00016   0.1% ↑
  z               structures[cosio_2k5].atom_sites[Co2].fract_z                     0.99159      0.99136   0.00035   
  x               structures[cosio_2k5].atom_sites[O1].fract_x                      0.09194     0.091794  0.000078   0.2% ↓
  z               structures[cosio_2k5].atom_sites[O1].fract_z                      0.76724      0.76746   0.00016   
  x               structures[cosio_2k5].atom_sites[O2].fract_x                      0.44852     0.448532  0.000066   
  z               structures[cosio_2k5].atom_sites[O2].fract_z                      0.21592      0.21597   0.00016   
  x               structures[cosio_2k5].atom_sites[O3].fract_x                      0.16447     0.164413  0.000050   
  y               structures[cosio_2k5].atom_sites[O3].fract_y                      0.03331      0.03315   0.00012   0.5% ↓
  z               structures[cosio_2k5].atom_sites[O3].fract_z                      0.28143      0.28131   0.00011   
  x               structures[cosio_2k5].atom_sites[Si].fract_x                      0.09480     0.094765  0.000099   
  z               structures[cosio_2k5].atom_sites[Si].fract_z                      0.42809      0.42831   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00671      0.00671   0.00025   0.1% ↓
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -9.00e-4      -9.0e-4    2.0e-4   0.4% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                8.00e-5         8e-5     18e-5   1.9% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00412      0.00412   0.00022   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.10e-4      -5.1e-4    1.9e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00410      0.00410   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00447      0.00447   0.00024   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                2.90e-4       2.9e-4    2.0e-4   1.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00539      0.00539   0.00022   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00524      0.00524   0.00021   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00639      0.00639   0.00012   0.1% ↓
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 3.90e-5       3.9e-5    8.0e-5   1.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00586      0.00586   0.00011   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00307     0.003074  0.000087   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00413      0.00413   0.00011   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 2.50e-5       2.5e-5    8.6e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00642      0.00642   0.00011   0.1% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00494     0.004944  0.000092   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00714     0.007137  0.000084   
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00190     0.001897  0.000066   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.39e-4      2.39e-4   0.69e-4   0.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00537     0.005366  0.000077   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.57e-4     -3.57e-4   0.56e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00521     0.005205  0.000062   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00386      0.00386   0.00015   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.80e-4       1.8e-4    1.1e-4   2.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00396      0.00396   0.00014   0.1% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00278      0.00278   0.00012   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27656     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99133      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09206     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76709     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44869     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21555     0.215555  0.000085   
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03360     0.033602  0.000047   
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28170     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09488     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42815     0.428146  0.000093   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_11                 0.00244      0.00244   0.00015   0.2% ↑
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_12                -1.50e-4      -1.5e-4    1.1e-4   1.3% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_13                 5.00e-5         5e-5     11e-5   4.3% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_22                 0.00101      0.00101   0.00024   0.3% ↑
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_23                -1.20e-4      -1.2e-4    1.3e-4   3.5% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_33                 0.00167      0.00167   0.00015   0.1% ↑
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_11                 0.00176      0.00176   0.00015   0.1% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_13                -1.70e-4      -1.7e-4    1.1e-4   2.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_22                 0.00159      0.00159   0.00023   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_33                 0.00184      0.00184   0.00015   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_11                  0.00346     0.003460  0.000072   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_13                  4.80e-5       4.8e-5    5.4e-5   0.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_22                  0.00296      0.00296   0.00012   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_33                  0.00201     0.002010  0.000073   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_11                  0.00223     0.002226  0.000070   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_13                  5.10e-5       5.1e-5    5.7e-5   0.5% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_22                  0.00290      0.00290   0.00012   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_33                  0.00294     0.002941  0.000072   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_11                  0.00351     0.003514  0.000053   
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_12                  7.07e-4      7.07e-4   0.35e-4   0.1% ↓
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_13                  1.62e-4      1.62e-4   0.43e-4   0.1% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_22                  0.00221     0.002207  0.000082   
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_23                 -1.57e-4     -1.57e-4   0.45e-4   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_33                  0.00308     0.003080  0.000052   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_11                  0.00181     0.001810  0.000090   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_13                 -3.60e-5      -3.6e-5    6.9e-5   0.3% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_22                  0.00112      0.00112   0.00015   0.1% ↑
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_33                  0.00154     0.001541  0.000092   
  x               structures[cosio_55k].atom_sites[Co2].fract_x                     0.27602     0.276023  0.000055   
  z               structures[cosio_55k].atom_sites[Co2].fract_z                     0.99134      0.99134   0.00013   
  x               structures[cosio_55k].atom_sites[O1].fract_x                      0.09184     0.091844  0.000027   
  z               structures[cosio_55k].atom_sites[O1].fract_z                      0.76740     0.767395  0.000056   
  x               structures[cosio_55k].atom_sites[O2].fract_x                      0.44849     0.448486  0.000023   
  z               structures[cosio_55k].atom_sites[O2].fract_z                      0.21578     0.215778  0.000059   
  x               structures[cosio_55k].atom_sites[O3].fract_x                      0.16428     0.164276  0.000017   
  y               structures[cosio_55k].atom_sites[O3].fract_y                      0.03324     0.033241  0.000038   
  z               structures[cosio_55k].atom_sites[O3].fract_z                      0.28116     0.281158  0.000040   
  x               structures[cosio_55k].atom_sites[Si].fract_x                      0.09489     0.094886  0.000034   
  z               structures[cosio_55k].atom_sites[Si].fract_z                      0.42823     0.428231  0.000071   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      structures[cosio_2k5].atom_site_aniso[Co2].adp_22: s.u. larger than the value
```

## 2.5 K: the magnetic moments

Free the moment components the magnetic space group allows. They start at zero, where the
magnetic intensity has no slope, so the fit starts them at 1 μB and says so.

In `structures/cosio_2k5.edi`, add `()` after the values the stage frees:

```edi
Co1 0() 0() 0() Mx,My,Mz
Co2 0 0() 0 0,My,0
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_cosio-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_cosio-heidi, 1424 pts fitted / 1424 loaded, 50 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        10.52         4.76
      1      0.200       3.77         0.61   87.1% ↓
      2      0.230       3.77         0.61   
      3      0.261       3.77         0.61   
edi fit: project sc-neut-cwl_cosio-heidi, 1624 pts fitted / 1624 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.15         0.50
      1      0.084       6.15         0.50   
edi fit: project sc-neut-cwl_cosio-heidi, 1465 pts fitted / 1465 loaded, 46 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         3.79         0.76
      1      0.082       3.79         0.76   
  done · converged · 5 iters · reduced χ² 0.62 · wR(F²) 4.18 % · 0.49 s

  per-bank wR(F²) (%):   heidi_2k5 3.77   heidi_300k 6.15   heidi_55k 3.79

  refined parameters (142 free):
  name            parameter                                                           start        value      s.u.   change
  x11             experiments[heidi_2k5].extinction.coefficient_11                    0.077        0.137     0.012   78.2% ↑
  x12             experiments[heidi_2k5].extinction.coefficient_12                     0.19        0.019     0.041   90.2% ↓
  x13             experiments[heidi_2k5].extinction.coefficient_13                   -0.206        0.014     0.035   106.6% ↑
  x22             experiments[heidi_2k5].extinction.coefficient_22                     0.16        0.274     0.056   71.0% ↑
  x23             experiments[heidi_2k5].extinction.coefficient_23                     0.15        0.024     0.062   84.0% ↓
  x33             experiments[heidi_2k5].extinction.coefficient_33                      1.1        1.216     0.041   10.5% ↑
  scale           experiments[heidi_2k5].linked_structures[cosio_2k5].scale           16.15       16.067     0.060   0.5% ↓
  x11             experiments[heidi_300k].extinction.coefficient_11                   0.117        0.117     0.014   
  x12             experiments[heidi_300k].extinction.coefficient_12                  -0.076       -0.076     0.037   0.2% ↓
  x13             experiments[heidi_300k].extinction.coefficient_13                    -0.1       -0.100     0.053   0.2% ↓
  x22             experiments[heidi_300k].extinction.coefficient_22                   0.283        0.283     0.016   0.1% ↓
  x23             experiments[heidi_300k].extinction.coefficient_23                    0.14         0.14      0.12   2.0% ↑
  x33             experiments[heidi_300k].extinction.coefficient_33                   1.156        1.156     0.078   
  scale           experiments[heidi_300k].linked_structures[cosio_300k].scale        18.744       18.744     0.089   
  x11             experiments[heidi_55k].extinction.coefficient_11                     0.13        0.130     0.015   
  x12             experiments[heidi_55k].extinction.coefficient_12                    0.186        0.186     0.059   0.2% ↑
  x13             experiments[heidi_55k].extinction.coefficient_13                    0.191        0.191     0.048   0.1% ↓
  x22             experiments[heidi_55k].extinction.coefficient_22                    0.068        0.068     0.067   0.6% ↑
  x23             experiments[heidi_55k].extinction.coefficient_23                    0.078        0.078     0.082   0.1% ↑
  x33             experiments[heidi_55k].extinction.coefficient_33                    1.356        1.356     0.054   
  scale           experiments[heidi_55k].linked_structures[cosio_55k].scale          16.018       16.018     0.065   
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_11                 0.00207      0.00196   0.00014   5.5% ↓
  U₁₂, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_12                -2.40e-4      -2.1e-4    1.3e-4   10.4% ↑
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_13                 2.00e-5         1e-5     11e-5   37.7% ↓
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_22                 0.00159      0.00152   0.00027   4.1% ↓
  U₂₃, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_23                 7.00e-5         2e-5     14e-5   69.9% ↓
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[Co1].adp_33                 0.00161      0.00153   0.00013   5.2% ↓
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[Co2].adp_11                 0.00215      0.00198   0.00015   8.0% ↓
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[Co2].adp_13                 1.30e-4       1.1e-4    1.1e-4   13.7% ↓
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[Co2].adp_22                 7.00e-4       6.7e-4    2.6e-4   4.1% ↓
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[Co2].adp_33                 0.00210      0.00204   0.00014   2.7% ↓
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[O1].adp_11                  0.00355     0.003457  0.000069   2.6% ↓
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[O1].adp_13                  3.00e-5       4.1e-5    5.3e-5   37.2% ↑
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[O1].adp_22                  0.00280      0.00279   0.00014   0.3% ↓
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[O1].adp_33                  0.00191     0.001863  0.000069   2.5% ↓
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[O2].adp_11                  0.00211     0.002032  0.000067   3.7% ↓
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[O2].adp_13                  1.20e-4      1.15e-4   0.56e-4   3.8% ↓
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[O2].adp_22                  0.00291      0.00293   0.00014   0.7% ↑
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[O2].adp_33                  0.00293     0.002835  0.000068   3.2% ↓
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_11                  0.00357     0.003482  0.000050   2.5% ↓
  U₁₂, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_12                  7.80e-4      7.58e-4   0.41e-4   2.8% ↓
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_13                  1.50e-4      1.55e-4   0.43e-4   3.5% ↑
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_22                  0.00211     0.002064  0.000096   2.2% ↓
  U₂₃, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_23                 -3.00e-4     -3.02e-4   0.46e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[O3].adp_33                  0.00307     0.003003  0.000048   2.2% ↓
  U₁₁, Å²         structures[cosio_2k5].atom_site_aniso[Si].adp_11                  0.00195     0.001839  0.000086   5.7% ↓
  U₁₃, Å²         structures[cosio_2k5].atom_site_aniso[Si].adp_13                  2.00e-5       1.0e-5    6.9e-5   48.2% ↓
  U₂₂, Å²         structures[cosio_2k5].atom_site_aniso[Si].adp_22                  0.00128      0.00128   0.00017   0.2% ↓
  U₃₃, Å²         structures[cosio_2k5].atom_site_aniso[Si].adp_33                  0.00146     0.001402  0.000087   4.0% ↓
  Mx, μB          structures[cosio_2k5].atom_site_moment[Co1].crystalaxis_x          0.0000        1.198     0.048   
  My, μB          structures[cosio_2k5].atom_site_moment[Co1].crystalaxis_y          0.0000        3.553     0.043   
  Mz, μB          structures[cosio_2k5].atom_site_moment[Co1].crystalaxis_z          0.0000         0.75      0.14   
  My, μB          structures[cosio_2k5].atom_site_moment[Co2].crystalaxis_y          0.0000        3.313     0.045   
  x               structures[cosio_2k5].atom_sites[Co2].fract_x                     0.27601     0.276023  0.000057   
  z               structures[cosio_2k5].atom_sites[Co2].fract_z                     0.99136      0.99132   0.00013   
  x               structures[cosio_2k5].atom_sites[O1].fract_x                      0.09179     0.091791  0.000028   
  z               structures[cosio_2k5].atom_sites[O1].fract_z                      0.76746     0.767441  0.000055   
  x               structures[cosio_2k5].atom_sites[O2].fract_x                      0.44853     0.448525  0.000024   
  z               structures[cosio_2k5].atom_sites[O2].fract_z                      0.21597     0.216017  0.000058   
  x               structures[cosio_2k5].atom_sites[O3].fract_x                      0.16441     0.164404  0.000018   
  y               structures[cosio_2k5].atom_sites[O3].fract_y                      0.03315     0.033156  0.000042   
  z               structures[cosio_2k5].atom_sites[O3].fract_z                      0.28131     0.281308  0.000039   
  x               structures[cosio_2k5].atom_sites[Si].fract_x                      0.09477     0.094770  0.000036   
  z               structures[cosio_2k5].atom_sites[Si].fract_z                      0.42831     0.428332  0.000068   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_11                0.00671      0.00671   0.00025   0.1% ↓
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_12               -9.00e-4      -9.0e-4    2.0e-4   0.4% ↑
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_13                8.00e-5         8e-5     18e-5   1.9% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_22                0.00412      0.00412   0.00022   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_23               -5.10e-4      -5.1e-4    1.9e-4   0.6% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co1].adp_33                0.00410      0.00410   0.00019   0.1% ↑
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_11                0.00447      0.00447   0.00024   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_13                2.90e-4       2.9e-4    2.0e-4   1.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_22                0.00539      0.00539   0.00022   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Co2].adp_33                0.00524      0.00524   0.00021   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_11                 0.00639      0.00639   0.00012   0.1% ↓
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_13                 3.90e-5       3.9e-5    8.0e-5   1.3% ↓
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_22                 0.00586      0.00586   0.00011   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O1].adp_33                 0.00307     0.003074  0.000087   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_11                 0.00413      0.00413   0.00011   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_13                 2.50e-5       2.5e-5    8.6e-5   
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_22                 0.00642      0.00642   0.00011   0.1% ↑
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O2].adp_33                 0.00494     0.004944  0.000092   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_11                 0.00714     0.007137  0.000084   
  U₁₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_12                 0.00190     0.001897  0.000066   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_13                 2.39e-4      2.39e-4   0.69e-4   0.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_22                 0.00537     0.005366  0.000077   
  U₂₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_23                -3.57e-4     -3.57e-4   0.56e-4   
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[O3].adp_33                 0.00521     0.005205  0.000062   
  U₁₁, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_11                 0.00386      0.00386   0.00015   
  U₁₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_13                 1.80e-4       1.8e-4    1.1e-4   2.1% ↑
  U₂₂, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_22                 0.00396      0.00396   0.00014   0.1% ↓
  U₃₃, Å²         structures[cosio_300k].atom_site_aniso[Si].adp_33                 0.00278      0.00278   0.00012   0.1% ↑
  x               structures[cosio_300k].atom_sites[Co2].fract_x                    0.27656     0.276559  0.000091   
  z               structures[cosio_300k].atom_sites[Co2].fract_z                    0.99133      0.99133   0.00019   
  x               structures[cosio_300k].atom_sites[O1].fract_x                     0.09206     0.092062  0.000045   
  z               structures[cosio_300k].atom_sites[O1].fract_z                     0.76709     0.767087  0.000075   
  x               structures[cosio_300k].atom_sites[O2].fract_x                     0.44869     0.448692  0.000038   
  z               structures[cosio_300k].atom_sites[O2].fract_z                     0.21555     0.215555  0.000085   
  x               structures[cosio_300k].atom_sites[O3].fract_x                     0.16419     0.164189  0.000030   
  y               structures[cosio_300k].atom_sites[O3].fract_y                     0.03360     0.033602  0.000047   
  z               structures[cosio_300k].atom_sites[O3].fract_z                     0.28170     0.281705  0.000053   
  x               structures[cosio_300k].atom_sites[Si].fract_x                     0.09488     0.094875  0.000055   
  z               structures[cosio_300k].atom_sites[Si].fract_z                     0.42815     0.428146  0.000093   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_11                 0.00244      0.00244   0.00015   0.2% ↑
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_12                -1.50e-4      -1.5e-4    1.1e-4   1.3% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_13                 5.00e-5         5e-5     11e-5   4.3% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_22                 0.00101      0.00101   0.00024   0.3% ↑
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_23                -1.20e-4      -1.2e-4    1.3e-4   3.5% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co1].adp_33                 0.00167      0.00167   0.00015   0.1% ↑
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_11                 0.00176      0.00176   0.00015   0.1% ↑
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_13                -1.70e-4      -1.7e-4    1.1e-4   2.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_22                 0.00159      0.00159   0.00023   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Co2].adp_33                 0.00184      0.00184   0.00015   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_11                  0.00346     0.003460  0.000072   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_13                  4.80e-5       4.8e-5    5.4e-5   0.5% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_22                  0.00296      0.00296   0.00012   0.2% ↓
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O1].adp_33                  0.00201     0.002010  0.000073   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_11                  0.00223     0.002226  0.000070   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_13                  5.10e-5       5.1e-5    5.7e-5   0.5% ↑
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_22                  0.00290      0.00290   0.00012   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O2].adp_33                  0.00294     0.002941  0.000072   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_11                  0.00351     0.003514  0.000053   
  U₁₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_12                  7.07e-4      7.07e-4   0.35e-4   0.1% ↓
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_13                  1.62e-4      1.62e-4   0.43e-4   0.1% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_22                  0.00221     0.002207  0.000082   
  U₂₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_23                 -1.57e-4     -1.57e-4   0.45e-4   
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[O3].adp_33                  0.00308     0.003080  0.000052   
  U₁₁, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_11                  0.00181     0.001810  0.000090   
  U₁₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_13                 -3.60e-5      -3.6e-5    6.9e-5   0.3% ↓
  U₂₂, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_22                  0.00112      0.00112   0.00015   0.1% ↑
  U₃₃, Å²         structures[cosio_55k].atom_site_aniso[Si].adp_33                  0.00154     0.001541  0.000092   
  x               structures[cosio_55k].atom_sites[Co2].fract_x                     0.27602     0.276023  0.000055   
  z               structures[cosio_55k].atom_sites[Co2].fract_z                     0.99134      0.99134   0.00013   
  x               structures[cosio_55k].atom_sites[O1].fract_x                      0.09184     0.091844  0.000027   
  z               structures[cosio_55k].atom_sites[O1].fract_z                      0.76740     0.767395  0.000056   
  x               structures[cosio_55k].atom_sites[O2].fract_x                      0.44849     0.448486  0.000023   
  z               structures[cosio_55k].atom_sites[O2].fract_z                      0.21578     0.215778  0.000059   
  x               structures[cosio_55k].atom_sites[O3].fract_x                      0.16428     0.164276  0.000017   
  y               structures[cosio_55k].atom_sites[O3].fract_y                      0.03324     0.033241  0.000038   
  z               structures[cosio_55k].atom_sites[O3].fract_z                      0.28116     0.281158  0.000040   
  x               structures[cosio_55k].atom_sites[Si].fract_x                      0.09489     0.094886  0.000034   
  z               structures[cosio_55k].atom_sites[Si].fract_z                      0.42823     0.428231  0.000071   

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
    python -m edi report sc-neut-cwl_cosio-heidi --output sc-neut-cwl_cosio-heidi.html
    ```
