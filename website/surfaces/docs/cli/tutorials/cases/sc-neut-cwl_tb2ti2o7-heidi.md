# Single-crystal fit: Tb₂Ti₂O₇, HEiDi

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit the pyrochlore Tb₂Ti₂O₇ to constant-wavelength neutron single-crystal data from HEiDi at
MLZ, with anisotropic displacements and Becker-Coppens extinction.

It builds the catalogue case `sc-neut-cwl_tb2ti2o7-heidi` step by step: the same project the
command line fits and the app's Examples open.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p sc-neut-cwl_tb2ti2o7-heidi/structures sc-neut-cwl_tb2ti2o7-heidi/experiments sc-neut-cwl_tb2ti2o7-heidi/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name             sc-neut-cwl_tb2ti2o7-heidi
_metadata.title "Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)"
_metadata.description "Single crystal · Anisotropic displacements and extinction from a rough start"
_metadata.authors .
_metadata.created          "22 Oct 2026 18:00:00"
_metadata.last_modified    "22 Oct 2026 18:00:00"
_metadata.timestamp        ?
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data sc-neut-cwl_tb2ti2o7-heidi-tb2ti2o7
    mv data/sc-neut-cwl_tb2ti2o7-heidi-tb2ti2o7.edi sc-neut-cwl_tb2ti2o7-heidi/structures/tb2ti2o7.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-cwl_tb2ti2o7-heidi-tb2ti2o7
    mv data/sc-neut-cwl_tb2ti2o7-heidi-tb2ti2o7.edi sc-neut-cwl_tb2ti2o7-heidi/structures/tb2ti2o7.edi
    ```

## Define the experiment

Download the experiment into `experiments`: the file declares the instrument, the peak profile, the background, the structures it links and the measured data.

=== "Standalone executable"

    ```console
    edi download-data sc-neut-cwl_tb2ti2o7-heidi-heidi
    mv data/sc-neut-cwl_tb2ti2o7-heidi-heidi.edi sc-neut-cwl_tb2ti2o7-heidi/experiments/heidi.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-cwl_tb2ti2o7-heidi-heidi
    mv data/sc-neut-cwl_tb2ti2o7-heidi-heidi.edi sc-neut-cwl_tb2ti2o7-heidi/experiments/heidi.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_fitting_mode.type single

_edi.schema_version 3
```

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
      1      0.062      19.62        58.90   22.1% ↓
  done · converged · 1 iters · reduced χ² 58.90 · wR(F²) 19.62 % · 0.07 s

  refined parameters (1 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[tb2ti2o7].scale                4        4.477     0.061   11.9% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
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
      1      0.084      14.74        33.42   43.5% ↓
  done · converged · 1 iters · reduced χ² 33.42 · wR(F²) 14.74 % · 0.10 s

  refined parameters (2 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[tb2ti2o7].scale            4.477        4.555     0.046   1.7% ↑
  x               structure.atom_sites[O1].fract_x                      0.33000      0.32803   0.00015   0.6% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
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
      1      0.098       6.09         5.93   82.9% ↓
  done · converged · 1 iters · reduced χ² 5.93 · wR(F²) 6.09 % · 0.11 s

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
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
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
      1      0.095       2.90         1.35   77.4% ↓
      2      0.106       2.88         1.33   1.6% ↓
      3      0.117       2.88         1.33   
      4      0.128       2.88         1.33   
      5      0.145       2.88         1.33   
      6      0.155       2.88         1.33   
      7      0.169       2.88         1.33   
      8      0.182       2.88         1.33   
  done · converged · 8 iters · reduced χ² 1.33 · wR(F²) 2.88 % · 0.20 s

  refined parameters (12 free):
  name                 parameter                                               start        value      s.u.   change
  Domain radius, μm    experiment.extinction.domain_radius                        25          3.0       1.9   87.9% ↓
  Mosaic spread, rad⁻¹ experiment.extinction.mosaic_spread                         0      2.730e3   0.095e3   
  scale                experiment.linked_structures[tb2ti2o7].scale            5.269        5.900     0.036   12.0% ↑
  U₁₁, Å²              structure.atom_site_aniso[O1].adp_11                  0.00632      0.00742   0.00012   17.4% ↑
  U₂₂, Å²              structure.atom_site_aniso[O1].adp_22                  0.00434     0.005533  0.000084   27.5% ↑
  U₂₃, Å²              structure.atom_site_aniso[O1].adp_23                  0.00192     0.001927  0.000087   0.3% ↑
  U₁₁, Å²              structure.atom_site_aniso[O2].adp_11                  0.00332      0.00442   0.00012   33.2% ↑
  U₁₁, Å²              structure.atom_site_aniso[Tb].adp_11                  0.00578     0.006965  0.000084   20.5% ↑
  U₁₂, Å²              structure.atom_site_aniso[Tb].adp_12                 -0.00234    -0.002266  0.000075   3.1% ↑
  U₁₁, Å²              structure.atom_site_aniso[Ti].adp_11                  0.00515      0.00617   0.00014   19.8% ↑
  U₁₂, Å²              structure.atom_site_aniso[Ti].adp_12                 -6.20e-4      -2.7e-4    1.7e-4   55.7% ↑
  x                    structure.atom_sites[O1].fract_x                      0.32796     0.327981  0.000032   

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
    python -m edi report sc-neut-cwl_tb2ti2o7-heidi --output sc-neut-cwl_tb2ti2o7-heidi.html
    ```
