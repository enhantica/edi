# Rietveld fit: Si, SEPD

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit silicon to time-of-flight neutron powder data from SEPD at Argonne, with the Jorgensen-Von
Dreele profile.

It builds the catalogue case `pd-neut-tof_si-sepd` step by step: the same project the command
line fits and the app's Examples open.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p pd-neut-tof_si-sepd/structures pd-neut-tof_si-sepd/experiments pd-neut-tof_si-sepd/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name pd-neut-tof_si-sepd
_metadata.title "Silicon [Fd-3m] · SEPD @ Argonne"
_metadata.description "Silicon standard · Jorgensen–Von Dreele profile · Time-of-flight neutron powder data"
_metadata.authors .
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_si-sepd-si
    mv data/pd-neut-tof_si-sepd-si.edi pd-neut-tof_si-sepd/structures/si.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_si-sepd-si
    mv data/pd-neut-tof_si-sepd-si.edi pd-neut-tof_si-sepd/structures/si.edi
    ```

## Define the experiment

Download the experiment into `experiments`: the file declares the instrument, the peak profile, the background, the structures it links and the measured data.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_si-sepd-sepd
    mv data/pd-neut-tof_si-sepd-sepd.edi pd-neut-tof_si-sepd/experiments/sepd.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_si-sepd-sepd
    mv data/pd-neut-tof_si-sepd-sepd.edi pd-neut-tof_si-sepd/experiments/sepd.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_minimizer.type crysta
_minimizer.max_iterations 1000

_fitting_mode.type single

_edi.schema_version 3
```

## Cell, scale and time-of-flight calibration

Set the background to its automatic estimate in the experiment file: each fit places its points first, by the arPLS method, a smooth curve under the pattern that ignores the peaks.

In `experiments/sepd.edi`, set:

```edi
_background_estimate.mode auto
_background_estimate.n_points 14
```

In `experiments/sepd.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
si 600() 1.0
```

In `structures/si.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 5.431()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_si-sepd --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_si-sepd --verbosity full
    ```

```text
edi fit: project pd-neut-tof_si-sepd, 5600 pts fitted / 5600 loaded, 3 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       52.36       204.71
      1      0.076     10.45         8.16   96.0% ↓
      2      0.088     10.45         8.16   
  done · converged · 2 iters · reduced χ² 8.16 · Rwp 10.45 % · 0.10 s

  refined parameters (3 free):
  name            parameter                                               start        value      s.u.   change
  TOF offset, µs  experiment.instrument.calib_d_to_tof_offset                 0       -8.808     0.086   
  scale           experiment.linked_structures[si].scale                    600        373.4       1.1   37.8% ↓
  a, Å            structure.cell.length_a                                5.4310     5.430922  0.000062   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

The estimated points are a starting point; fit them now that the peaks are in place.

In `experiments/sepd.edi`, set:

```edi
_background_estimate.mode manual
```

In `experiments/sepd.edi`, add `()` after the values the stage frees:

```edi
1 2000 212.567()
2 9035 117.617()
```

The same for every other row (12 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_si-sepd --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_si-sepd --verbosity full
    ```

```text
edi fit: project pd-neut-tof_si-sepd, 5600 pts fitted / 5600 loaded, 17 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       10.45         8.18
      1      0.124      7.45         4.16   49.1% ↓
  done · converged · 1 iters · reduced χ² 4.16 · Rwp 7.45 % · 0.13 s

  refined parameters (17 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                    191.17        184.5       7.2   3.5% ↓
  intensity       experiment.background[11].intensity                    131.69        160.6       5.1   21.9% ↑
  intensity       experiment.background[12].intensity                    143.56        180.8       6.9   26.0% ↑
  intensity       experiment.background[13].intensity                    115.18          193        16   67.8% ↑
  intensity       experiment.background[14].intensity                    177.06          210        27   18.6% ↑
  intensity       experiment.background[1].intensity                     212.57       201.47      0.43   5.2% ↓
  intensity       experiment.background[2].intensity                     117.62       106.29      0.43   9.6% ↓
  intensity       experiment.background[3].intensity                     163.05       129.43      0.85   20.6% ↓
  intensity       experiment.background[4].intensity                     120.31        119.8       1.6   0.5% ↓
  intensity       experiment.background[5].intensity                     186.02        134.7       2.4   27.6% ↓
  intensity       experiment.background[6].intensity                     121.96        130.6       1.4   7.1% ↑
  intensity       experiment.background[7].intensity                     134.65        141.5       2.3   5.1% ↑
  intensity       experiment.background[8].intensity                     156.32        148.7       9.1   4.9% ↓
  intensity       experiment.background[9].intensity                     272.06          154        20   43.6% ↓
  TOF offset, µs  experiment.instrument.calib_d_to_tof_offset            -8.808       -8.851     0.060   0.5% ↓
  scale           experiment.linked_structures[si].scale                  373.4       384.69      0.78   3.0% ↑
  a, Å            structure.cell.length_a                                5.4309     5.430953  0.000043   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Gaussian widths

The background stays free while the widths join. diffraction-lib fixes it for this step and
leaves it fixed; here the fit reaches the same result with it free, as every other case does.
The Gaussian terms come first.

In `experiments/sepd.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_0 3()
_peak.broad_gauss_sigma_1 30()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_si-sepd --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_si-sepd --verbosity full
    ```

```text
edi fit: project pd-neut-tof_si-sepd, 5600 pts fitted / 5600 loaded, 19 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        7.45         4.16
      1      0.109      7.42         4.13   0.8% ↓
  done · converged · 1 iters · reduced χ² 4.13 · Rwp 7.42 % · 0.12 s

  refined parameters (19 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     184.5        184.4       7.1   0.1% ↓
  intensity       experiment.background[11].intensity                     160.6        160.6       5.1   
  intensity       experiment.background[12].intensity                     180.8        180.8       6.9   
  intensity       experiment.background[13].intensity                       193          193        16   0.2% ↑
  intensity       experiment.background[14].intensity                       210          210        27   
  intensity       experiment.background[1].intensity                     201.47       201.35      0.43   0.1% ↓
  intensity       experiment.background[2].intensity                     106.29       106.36      0.43   0.1% ↑
  intensity       experiment.background[3].intensity                     129.43       129.54      0.85   0.1% ↑
  intensity       experiment.background[4].intensity                      119.8        119.7       1.6   0.1% ↓
  intensity       experiment.background[5].intensity                      134.7        135.4       2.4   0.5% ↑
  intensity       experiment.background[6].intensity                      130.6        130.5       1.4   
  intensity       experiment.background[7].intensity                      141.5        141.5       2.3   
  intensity       experiment.background[8].intensity                      148.7        148.2       9.1   0.3% ↓
  intensity       experiment.background[9].intensity                        154          162        20   5.1% ↑
  TOF offset, µs  experiment.instrument.calib_d_to_tof_offset            -8.851       -8.831     0.061   0.2% ↑
  scale           experiment.linked_structures[si].scale                 384.69       384.79      0.79   
  σ₀², µs²        experiment.peak.broad_gauss_sigma_0                         3         4.90      0.38   63.2% ↑
  σ₁², µs²/Å²     experiment.peak.broad_gauss_sigma_1                        30        26.84      0.53   10.5% ↓
  a, Å            structure.cell.length_a                                5.4310     5.430915  0.000044   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Lorentzian width

Then the Lorentzian term.

In `experiments/sepd.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_lorentz_gamma_1 3()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_si-sepd --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_si-sepd --verbosity full
    ```

```text
edi fit: project pd-neut-tof_si-sepd, 5600 pts fitted / 5600 loaded, 20 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        7.42         4.13
      1      0.116      7.28         3.97   3.7% ↓
  done · converged · 1 iters · reduced χ² 3.97 · Rwp 7.28 % · 0.13 s

  refined parameters (20 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     184.4        184.5       7.0   0.1% ↑
  intensity       experiment.background[11].intensity                     160.6        160.6       5.0   
  intensity       experiment.background[12].intensity                     180.8        180.8       6.8   
  intensity       experiment.background[13].intensity                       193          193        15   0.2% ↑
  intensity       experiment.background[14].intensity                       210          210        26   
  intensity       experiment.background[1].intensity                     201.35       201.77      0.42   0.2% ↑
  intensity       experiment.background[2].intensity                     106.36       107.98      0.43   1.5% ↑
  intensity       experiment.background[3].intensity                     129.54       131.15      0.84   1.2% ↑
  intensity       experiment.background[4].intensity                      119.7        119.1       1.6   0.5% ↓
  intensity       experiment.background[5].intensity                      135.4        146.8       2.5   8.4% ↑
  intensity       experiment.background[6].intensity                      130.5        129.1       1.4   1.1% ↓
  intensity       experiment.background[7].intensity                      141.5        142.5       2.2   0.7% ↑
  intensity       experiment.background[8].intensity                      148.2        155.1       8.9   4.6% ↑
  intensity       experiment.background[9].intensity                        162          248        20   53.2% ↑
  TOF offset, µs  experiment.instrument.calib_d_to_tof_offset            -8.831       -8.841     0.060   0.1% ↓
  scale           experiment.linked_structures[si].scale                 384.79       378.69      0.88   1.6% ↓
  σ₀², µs²        experiment.peak.broad_gauss_sigma_0                       4.9         5.00      0.38   2.0% ↑
  σ₁², µs²/Å²     experiment.peak.broad_gauss_sigma_1                     26.84        34.17      0.75   27.3% ↑
  γ₁, µs/Å        experiment.peak.broad_lorentz_gamma_1                       3        1.694     0.090   43.5% ↓
  a, Å            structure.cell.length_a                                5.4309     5.430939  0.000043   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Displacement

In `structures/si.edi`, add `()` after the values the stage frees:

```edi
Si Si 0.125 0.125 0.125 a 8 1 0.5() Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_si-sepd --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_si-sepd --verbosity full
    ```

```text
edi fit: project pd-neut-tof_si-sepd, 5600 pts fitted / 5600 loaded, 21 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        7.28         3.98
      1      0.122      7.28         3.97   0.2% ↓
  done · converged · 1 iters · reduced χ² 3.97 · Rwp 7.28 % · 0.13 s

  refined parameters (21 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     184.5        184.7       7.0   0.1% ↑
  intensity       experiment.background[11].intensity                     160.6        160.6       5.0   
  intensity       experiment.background[12].intensity                     180.8        180.8       6.8   
  intensity       experiment.background[13].intensity                       193          193        15   0.2% ↑
  intensity       experiment.background[14].intensity                       210          210        26   
  intensity       experiment.background[1].intensity                     201.77       202.71      0.49   0.5% ↑
  intensity       experiment.background[2].intensity                     107.98       107.85      0.43   0.1% ↓
  intensity       experiment.background[3].intensity                     131.15       131.16      0.84   
  intensity       experiment.background[4].intensity                      119.1        119.1       1.6   
  intensity       experiment.background[5].intensity                      146.8        146.5       2.5   0.2% ↓
  intensity       experiment.background[6].intensity                      129.1        129.2       1.4   
  intensity       experiment.background[7].intensity                      142.5        142.5       2.2   
  intensity       experiment.background[8].intensity                      155.1        155.6       8.9   0.3% ↑
  intensity       experiment.background[9].intensity                        248          244        20   1.5% ↓
  TOF offset, µs  experiment.instrument.calib_d_to_tof_offset            -8.841       -8.869     0.060   0.3% ↓
  scale           experiment.linked_structures[si].scale                 378.69        381.6       1.2   0.8% ↑
  σ₀², µs²        experiment.peak.broad_gauss_sigma_0                         5         4.33      0.41   13.5% ↓
  σ₁², µs²/Å²     experiment.peak.broad_gauss_sigma_1                     34.17        34.73      0.76   1.6% ↑
  γ₁, µs/Å        experiment.peak.broad_lorentz_gamma_1                   1.694        1.671     0.090   1.3% ↓
  B iso, Å²       structure.atom_sites[Si].adp_iso                        0.500       0.5164    0.0044   3.3% ↑
  a, Å            structure.cell.length_a                                5.4309     5.430957  0.000044   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak decay

The back-to-back exponential decay terms β₀ and β₁.

In `experiments/sepd.edi`, add `()` after the values the stage frees:

```edi
_peak.decay_beta_0 0.04()
_peak.decay_beta_1 0.01()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_si-sepd --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_si-sepd --verbosity full
    ```

```text
edi fit: project pd-neut-tof_si-sepd, 5600 pts fitted / 5600 loaded, 23 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        7.28         3.97
      1      0.103      7.18         3.86   2.7% ↓
      2      0.125      7.18         3.86   
  done · converged · 2 iters · reduced χ² 3.86 · Rwp 7.18 % · 0.14 s

  refined parameters (23 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     184.7        184.7       6.9   
  intensity       experiment.background[11].intensity                     160.6        160.6       4.9   
  intensity       experiment.background[12].intensity                     180.8        180.8       6.7   
  intensity       experiment.background[13].intensity                       193          193        15   0.2% ↑
  intensity       experiment.background[14].intensity                       210          210        26   
  intensity       experiment.background[1].intensity                     202.71       203.66      0.48   0.5% ↑
  intensity       experiment.background[2].intensity                     107.85       108.22      0.43   0.3% ↑
  intensity       experiment.background[3].intensity                     131.16       130.64      0.83   0.4% ↓
  intensity       experiment.background[4].intensity                      119.1        119.3       1.5   0.1% ↑
  intensity       experiment.background[5].intensity                      146.5        144.3       2.5   1.5% ↓
  intensity       experiment.background[6].intensity                      129.2        129.4       1.4   0.2% ↑
  intensity       experiment.background[7].intensity                      142.5        142.3       2.2   0.1% ↓
  intensity       experiment.background[8].intensity                      155.6        153.7       8.8   1.2% ↓
  intensity       experiment.background[9].intensity                        244          225        20   7.7% ↓
  TOF offset, µs  experiment.instrument.calib_d_to_tof_offset            -8.869       -8.346     0.085   5.9% ↑
  scale           experiment.linked_structures[si].scale                  381.6        382.7       1.2   0.3% ↑
  σ₀², µs²        experiment.peak.broad_gauss_sigma_0                      4.33         5.51      0.46   27.3% ↑
  σ₁², µs²/Å²     experiment.peak.broad_gauss_sigma_1                     34.73        34.19      0.77   1.5% ↓
  γ₁, µs/Å        experiment.peak.broad_lorentz_gamma_1                   1.671        1.955     0.096   17.0% ↑
  β₀              experiment.peak.decay_beta_0                             0.04      0.04017   0.00024   0.4% ↑
  β₁              experiment.peak.decay_beta_1                             0.01      0.01247   0.00023   24.7% ↑
  B iso, Å²       structure.atom_sites[Si].adp_iso                        0.516       0.5277    0.0045   2.2% ↑
  a, Å            structure.cell.length_a                                5.4310     5.430824  0.000062   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Your own measured data

The command line fits the files of a project. To start from a measured-data file on your own disk, create the experiment in the Python package with `add_from_data_path`, or in the app with **Load ▾ Measured data From file…**, and save the project; creating one from a data file on the command line comes in a later version.

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-neut-tof_si-sepd --output pd-neut-tof_si-sepd.html
    ```
