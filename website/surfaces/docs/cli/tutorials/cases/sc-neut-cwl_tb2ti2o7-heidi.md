# Single-crystal fit: Tb₂Ti₂O₇, HEiDi

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data sc-neut-cwl_tb2ti2o7-heidi
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-cwl_tb2ti2o7-heidi
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/heidi.edi`, remove the `()` from every value; they now read:

```edi
_extinction.domain_radius 25
_extinction.mosaic_spread 0
tb2ti2o7 4
```

In `structures/tb2ti2o7.edi`, remove the `()` from every value; they now read:

```edi
O1 O 0.33 0.125 0.125 f 48 1 0.0026 Uani
Tb 0.0026 0.0026 0.0026 0 0 0
```

The same for every other row (3 more).

## Scale

The scale brings the calculated intensities to the measured ones.

In `experiments/heidi.edi`, add `()` after the values the stage frees:

```edi
tb2ti2o7 4()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_tb2ti2o7-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_tb2ti2o7-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_tb2ti2o7-heidi, 220 pts fitted / 220 loaded, 1 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        22.22        75.58
      1      0.010      19.62        58.90   22.1% ↓
      2      0.021      19.62        58.90   
  done · converged · 2 iters · reduced χ² 58.90 · wR(F²) 19.62 % · 0.03 s

  refined parameters (1 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[tb2ti2o7].scale                4        4.477     0.061   11.9% ↑

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## O1's position

The one coordinate the symmetry leaves free.

In `structures/tb2ti2o7.edi`, add `()` after the values the stage frees:

```edi
O1 O 0.33() 0.125 0.125 f 48 1 0.0026 Uani
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_tb2ti2o7-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_tb2ti2o7-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_tb2ti2o7-heidi, 220 pts fitted / 220 loaded, 2 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        19.62        59.17
      1      0.013      14.74        33.42   43.5% ↓
      2      0.076      14.74        33.42   
  done · converged · 2 iters · reduced χ² 33.42 · wR(F²) 14.74 % · 0.10 s

  refined parameters (2 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[tb2ti2o7].scale            4.477        4.555     0.046   1.7% ↑
  x               structure.atom_sites[O1].fract_x                      0.33000      0.32803   0.00015   0.6% ↓

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Anisotropic displacements

In `structures/tb2ti2o7.edi`, add `()` after the values the stage frees:

```edi
Tb 0.0026() 0.0026 0.0026 0() 0 0
Ti 0.0026() 0.0026 0.0026 0() 0 0
```

The same for every other row (2 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_tb2ti2o7-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_tb2ti2o7-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_tb2ti2o7-heidi, 220 pts fitted / 220 loaded, 10 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        14.74        34.69
      1      0.016       6.20         6.13   82.3% ↓
      2      0.028       6.09         5.93   3.3% ↓
      3      0.047       6.09         5.93   
  done · converged · 3 iters · reduced χ² 5.93 · wR(F²) 6.09 % · 0.06 s

  refined parameters (10 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[tb2ti2o7].scale            4.555        5.269     0.041   15.7% ↑
  U₁₁, Å²         structure.atom_site_aniso[O1].adp_11                  0.00260      0.00632   0.00025   143.3% ↑
  U₂₂, Å²         structure.atom_site_aniso[O1].adp_22                  0.00260      0.00434   0.00017   66.9% ↑
  U₂₃, Å²         structure.atom_site_aniso[O1].adp_23                  0.00000      0.00192   0.00019   
  U₁₁, Å²         structure.atom_site_aniso[O2].adp_11                  0.00260      0.00332   0.00023   27.6% ↑
  U₁₁, Å²         structure.atom_site_aniso[Tb].adp_11                  0.00260      0.00578   0.00016   122.2% ↑
  U₁₂, Å²         structure.atom_site_aniso[Tb].adp_12                  0.00000     -0.00234   0.00016   
  U₁₁, Å²         structure.atom_site_aniso[Ti].adp_11                  0.00260      0.00515   0.00027   98.1% ↑
  U₁₂, Å²         structure.atom_site_aniso[Ti].adp_12                  0.00000      -6.2e-4    3.5e-4   
  x               structure.atom_sites[O1].fract_x                      0.32803     0.327960  0.000067   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Extinction

The domain radius and the mosaic spread.

In `experiments/heidi.edi`, add `()` after the values the stage frees:

```edi
_extinction.domain_radius 25()
_extinction.mosaic_spread 0()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_tb2ti2o7-heidi --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_tb2ti2o7-heidi --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_tb2ti2o7-heidi, 220 pts fitted / 220 loaded, 12 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                         6.09         5.98
      1      0.014       3.86         2.40   59.9% ↓
      2      0.026       3.18         1.63   32.1% ↓
      3      0.037       2.97         1.42   13.1% ↓
      4      0.048       2.92         1.38   2.9% ↓
      5      0.069       2.91         1.37   0.7% ↓
      6      0.081       2.88         1.34   2.0% ↓
      7      0.092       2.88         1.33   0.4% ↓
      8      0.103       2.88         1.33   
      9      0.113       2.88         1.33   
     10      0.126       2.88         1.33   
  done · converged · 10 iters · reduced χ² 1.33 · wR(F²) 2.88 % · 0.14 s

  refined parameters (12 free):
  name                 parameter                                               start        value      s.u.   change
  Domain radius, μm    experiment.extinction.domain_radius                        25          3.0       1.8   88.1% ↓
  Mosaic spread, rad⁻¹ experiment.extinction.mosaic_spread                         0      2.733e3   0.093e3   
  scale                experiment.linked_structures[tb2ti2o7].scale            5.269        5.900     0.036   12.0% ↑
  U₁₁, Å²              structure.atom_site_aniso[O1].adp_11                  0.00632      0.00742   0.00012   17.4% ↑
  U₂₂, Å²              structure.atom_site_aniso[O1].adp_22                  0.00434     0.005533  0.000084   27.5% ↑
  U₂₃, Å²              structure.atom_site_aniso[O1].adp_23                  0.00192     0.001926  0.000087   0.3% ↑
  U₁₁, Å²              structure.atom_site_aniso[O2].adp_11                  0.00332      0.00442   0.00012   33.2% ↑
  U₁₁, Å²              structure.atom_site_aniso[Tb].adp_11                  0.00578     0.006965  0.000084   20.5% ↑
  U₁₂, Å²              structure.atom_site_aniso[Tb].adp_12                 -0.00234    -0.002266  0.000075   3.1% ↑
  U₁₁, Å²              structure.atom_site_aniso[Ti].adp_11                  0.00515      0.00617   0.00014   19.8% ↑
  U₁₂, Å²              structure.atom_site_aniso[Ti].adp_12                 -6.20e-4      -2.7e-4    1.7e-4   55.7% ↑
  x                    structure.atom_sites[O1].fract_x                      0.32796     0.327981  0.000032   

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
    python -m edi report sc-neut-cwl_tb2ti2o7-heidi --output sc-neut-cwl_tb2ti2o7-heidi.html
    ```
