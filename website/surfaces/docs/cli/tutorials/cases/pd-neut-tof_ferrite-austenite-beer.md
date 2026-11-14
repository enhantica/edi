# Joint fit: ferrite and austenite, BEER

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Calibrate the BEER instrument at ESS with two McStas-simulated banks of a ferrite and austenite
duplex steel, fitted together: each bank has its own zero and resolution.

It builds the catalogue case `pd-neut-tof_ferrite-austenite-beer` step by step: the same project
the command line fits and the app's Examples open. Austenite's displacement follows ferrite's,
and each phase's scale in bank n2 follows bank s2.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p pd-neut-tof_ferrite-austenite-beer/structures pd-neut-tof_ferrite-austenite-beer/experiments pd-neut-tof_ferrite-austenite-beer/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name pd-neut-tof_ferrite-austenite-beer
_metadata.title "Ferrite [Im-3m] / Austenite [Fm-3m] · BEER @ ESS"
_metadata.description "Instrument calibration · 2 McStas-simulated banks fitted jointly · Per-bank zero and resolution"
_metadata.authors .
```

## Define the structures

Download the structures from EasyDiffraction's collection into `structures`. Each CIF gives its space group, cell and atom sites.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_ferrite-austenite-beer-austenite
    mv data/pd-neut-tof_ferrite-austenite-beer-austenite.edi pd-neut-tof_ferrite-austenite-beer/structures/austenite.edi
    edi download-data pd-neut-tof_ferrite-austenite-beer-ferrite
    mv data/pd-neut-tof_ferrite-austenite-beer-ferrite.edi pd-neut-tof_ferrite-austenite-beer/structures/ferrite.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_ferrite-austenite-beer-austenite
    mv data/pd-neut-tof_ferrite-austenite-beer-austenite.edi pd-neut-tof_ferrite-austenite-beer/structures/austenite.edi
    python -m edi download-data pd-neut-tof_ferrite-austenite-beer-ferrite
    mv data/pd-neut-tof_ferrite-austenite-beer-ferrite.edi pd-neut-tof_ferrite-austenite-beer/structures/ferrite.edi
    ```

## Define the experiments

Download the experiments into `experiments`: each file declares its instrument, peak profile, background, the structures it links and its measured data.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_ferrite-austenite-beer-expt_n2
    mv data/pd-neut-tof_ferrite-austenite-beer-expt_n2.edi pd-neut-tof_ferrite-austenite-beer/experiments/expt_n2.edi
    edi download-data pd-neut-tof_ferrite-austenite-beer-expt_s2
    mv data/pd-neut-tof_ferrite-austenite-beer-expt_s2.edi pd-neut-tof_ferrite-austenite-beer/experiments/expt_s2.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_ferrite-austenite-beer-expt_n2
    mv data/pd-neut-tof_ferrite-austenite-beer-expt_n2.edi pd-neut-tof_ferrite-austenite-beer/experiments/expt_n2.edi
    python -m edi download-data pd-neut-tof_ferrite-austenite-beer-expt_s2
    mv data/pd-neut-tof_ferrite-austenite-beer-expt_s2.edi pd-neut-tof_ferrite-austenite-beer/experiments/expt_s2.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_minimizer.type crysta
_minimizer.max_iterations 1000

_fitting_mode.type joint

loop_
_alias.id
_alias.parameter_unique_name
biso_ferrite ferrite.atom_site.Fe.adp_iso
biso_austenite austenite.atom_site.Fe.adp_iso
s2_ferrite_scale expt_s2.linked_structure.ferrite.scale
s2_austenite_scale expt_s2.linked_structure.austenite.scale
n2_ferrite_scale expt_n2.linked_structure.ferrite.scale
n2_austenite_scale expt_n2.linked_structure.austenite.scale

loop_
_constraint.id
_constraint.expression
1 "biso_austenite = biso_ferrite"
2 "n2_ferrite_scale = s2_ferrite_scale"
3 "n2_austenite_scale = s2_austenite_scale"

loop_
_joint_fit.experiment_id
_joint_fit.weight
expt_n2 0.5
expt_s2 0.5

_edi.schema_version 3
```

## Scales and time-of-flight calibration

Both phases' scales and each bank's DIFC offset put the peaks in place and at the right height.

In `experiments/expt_n2.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
```

In `experiments/expt_s2.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
ferrite 400() 0.49780285149965137()
austenite 100() 0.5021971485003485()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ferrite-austenite-beer --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ferrite-austenite-beer --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ferrite-austenite-beer, 2 banks (expt_n2, expt_s2), 5642 pts fitted / 5998 loaded, 4 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       41.44       229.84
      1      0.145     23.83        76.04   66.9% ↓
      2      0.164     23.83        76.04   
  done · converged · 2 iters · reduced χ² 76.04 · Rwp 23.83 % · 0.18 s

  per-bank Rwp (%):   expt_n2 24.49   expt_s2 23.16

  refined parameters (4 free):
  name            parameter                                                       start        value      s.u.   change
  TOF offset, µs  experiments[expt_n2].instrument.calib_d_to_tof_offset               0        -1.94      0.37   
  TOF offset, µs  experiments[expt_s2].instrument.calib_d_to_tof_offset               0        -9.11      0.37   
  scale           experiments[expt_s2].linked_structures[austenite].scale           100        74.47      0.33   25.5% ↓
  scale           experiments[expt_s2].linked_structures[ferrite].scale             400        301.6       1.6   24.6% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

Each bank's background points; the last, past the end of the data, stays fixed.

In `experiments/expt_n2.edi`, add `()` after the values the stage frees:

```edi
1 40111.8789 0.19()
2 41193.5664 0.19()
```

The same for every other row (28 more).

In `experiments/expt_s2.edi`, add `()` after the values the stage frees:

```edi
1 40111.8789 0.18()
2 41193.5664 0.18()
```

The same for every other row (28 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ferrite-austenite-beer --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ferrite-austenite-beer --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ferrite-austenite-beer, 2 banks (expt_n2, expt_s2), 5642 pts fitted / 5998 loaded, 64 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       23.83        76.86
      1      0.705     18.05        44.10   42.6% ↓
  done · converged · 1 iters · reduced χ² 44.10 · Rwp 18.05 % · 0.75 s

  per-bank Rwp (%):   expt_n2 17.91   expt_s2 18.20

  refined parameters (64 free):
  name            parameter                                                       start        value      s.u.   change
  intensity       experiments[expt_n2].background[10].intensity                    0.19        0.205     0.029   7.9% ↑
  intensity       experiments[expt_n2].background[11].intensity                    0.19        0.193     0.069   1.6% ↑
  intensity       experiments[expt_n2].background[12].intensity                    0.19        0.213     0.038   12.3% ↑
  intensity       experiments[expt_n2].background[13].intensity                    0.19        0.264     0.034   38.9% ↑
  intensity       experiments[expt_n2].background[14].intensity                    0.19        0.295     0.038   55.5% ↑
  intensity       experiments[expt_n2].background[15].intensity                    0.19        0.334     0.044   75.6% ↑
  intensity       experiments[expt_n2].background[16].intensity                    0.19        0.276     0.030   45.0% ↑
  intensity       experiments[expt_n2].background[17].intensity                    0.19        0.254     0.027   33.5% ↑
  intensity       experiments[expt_n2].background[18].intensity                    0.19        0.234     0.019   23.0% ↑
  intensity       experiments[expt_n2].background[19].intensity                    0.19        0.230     0.018   20.8% ↑
  intensity       experiments[expt_n2].background[1].intensity                     0.19       -0.020     0.015   110.7% ↓
  intensity       experiments[expt_n2].background[20].intensity                    0.19        0.179     0.011   5.9% ↓
  intensity       experiments[expt_n2].background[21].intensity                    0.19        0.233     0.012   22.5% ↑
  intensity       experiments[expt_n2].background[22].intensity                    0.19        0.478     0.040   151.8% ↑
  intensity       experiments[expt_n2].background[23].intensity                    0.19        0.506     0.043   166.3% ↑
  intensity       experiments[expt_n2].background[24].intensity                    0.19        0.346     0.024   81.9% ↑
  intensity       experiments[expt_n2].background[25].intensity                    0.19        0.530     0.029   178.9% ↑
  intensity       experiments[expt_n2].background[26].intensity                    0.19        1.010     0.066   431.4% ↑
  intensity       experiments[expt_n2].background[27].intensity                    0.19        1.277     0.097   572.1% ↑
  intensity       experiments[expt_n2].background[28].intensity                    0.19        1.155     0.089   508.1% ↑
  intensity       experiments[expt_n2].background[29].intensity                    0.19        1.040     0.072   447.4% ↑
  intensity       experiments[expt_n2].background[2].intensity                     0.19         0.13      0.16 ! 33.7% ↓
  intensity       experiments[expt_n2].background[30].intensity                    0.19        0.645     0.033   239.3% ↑
  intensity       experiments[expt_n2].background[3].intensity                     0.19         0.09      0.18 ! 50.8% ↓
  intensity       experiments[expt_n2].background[4].intensity                     0.19        0.181     0.096   4.8% ↓
  intensity       experiments[expt_n2].background[5].intensity                     0.19        0.186     0.076   1.9% ↓
  intensity       experiments[expt_n2].background[6].intensity                     0.19        0.060     0.084 ! 68.3% ↓
  intensity       experiments[expt_n2].background[7].intensity                     0.19        0.147     0.041   22.5% ↓
  intensity       experiments[expt_n2].background[8].intensity                     0.19        0.214     0.036   12.7% ↑
  intensity       experiments[expt_n2].background[9].intensity                     0.19        0.195     0.028   2.6% ↑
  TOF offset, µs  experiments[expt_n2].instrument.calib_d_to_tof_offset           -1.94        -1.95      0.28   0.3% ↓
  intensity       experiments[expt_s2].background[10].intensity                    0.18        0.204     0.029   13.4% ↑
  intensity       experiments[expt_s2].background[11].intensity                    0.18        0.175     0.067   2.6% ↓
  intensity       experiments[expt_s2].background[12].intensity                    0.18        0.217     0.038   20.7% ↑
  intensity       experiments[expt_s2].background[13].intensity                    0.18        0.275     0.034   52.7% ↑
  intensity       experiments[expt_s2].background[14].intensity                    0.18        0.300     0.038   66.5% ↑
  intensity       experiments[expt_s2].background[15].intensity                    0.18        0.322     0.043   78.7% ↑
  intensity       experiments[expt_s2].background[16].intensity                    0.18        0.296     0.032   64.2% ↑
  intensity       experiments[expt_s2].background[17].intensity                    0.18        0.257     0.027   43.0% ↑
  intensity       experiments[expt_s2].background[18].intensity                    0.18        0.229     0.019   27.4% ↑
  intensity       experiments[expt_s2].background[19].intensity                    0.18        0.222     0.017   23.1% ↑
  intensity       experiments[expt_s2].background[1].intensity                     0.18      -0.0024      0.13 ! 101.3% ↓
  intensity       experiments[expt_s2].background[20].intensity                    0.18        0.172     0.011   4.6% ↓
  intensity       experiments[expt_s2].background[21].intensity                    0.18        0.239     0.012   32.5% ↑
  intensity       experiments[expt_s2].background[22].intensity                    0.18        0.486     0.041   170.1% ↑
  intensity       experiments[expt_s2].background[23].intensity                    0.18        0.495     0.043   174.8% ↑
  intensity       experiments[expt_s2].background[24].intensity                    0.18        0.342     0.024   90.0% ↑
  intensity       experiments[expt_s2].background[25].intensity                    0.18        0.534     0.029   196.7% ↑
  intensity       experiments[expt_s2].background[26].intensity                    0.18        1.019     0.066   466.2% ↑
  intensity       experiments[expt_s2].background[27].intensity                    0.18        1.284     0.098   613.4% ↑
  intensity       experiments[expt_s2].background[28].intensity                    0.18        1.219     0.092   577.1% ↑
  intensity       experiments[expt_s2].background[29].intensity                    0.18        0.987     0.069   448.4% ↑
  intensity       experiments[expt_s2].background[2].intensity                     0.18         0.10      0.15 ! 41.7% ↓
  intensity       experiments[expt_s2].background[30].intensity                    0.18        0.652     0.032   262.1% ↑
  intensity       experiments[expt_s2].background[3].intensity                     0.18         0.08      0.17 ! 53.2% ↓
  intensity       experiments[expt_s2].background[4].intensity                     0.18        0.183     0.090   1.6% ↑
  intensity       experiments[expt_s2].background[5].intensity                     0.18        0.158     0.074   12.2% ↓
  intensity       experiments[expt_s2].background[6].intensity                     0.18        0.044     0.076 ! 75.6% ↓
  intensity       experiments[expt_s2].background[7].intensity                     0.18        0.154     0.042   14.7% ↓
  intensity       experiments[expt_s2].background[8].intensity                     0.18        0.208     0.036   15.8% ↑
  intensity       experiments[expt_s2].background[9].intensity                     0.18        0.189     0.027   5.1% ↑
  TOF offset, µs  experiments[expt_s2].instrument.calib_d_to_tof_offset           -9.11        -9.13      0.28   0.2% ↓
  scale           experiments[expt_s2].linked_structures[austenite].scale         74.47        74.03      0.26   0.6% ↓
  scale           experiments[expt_s2].linked_structures[ferrite].scale           301.6        300.2       1.3   0.5% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[expt_n2].background[2].intensity: s.u. larger than the value
      experiments[expt_n2].background[3].intensity: s.u. larger than the value
      experiments[expt_n2].background[6].intensity: s.u. larger than the value
      experiments[expt_s2].background[1].intensity: s.u. larger than the value
      experiments[expt_s2].background[2].intensity: s.u. larger than the value
      experiments[expt_s2].background[3].intensity: s.u. larger than the value
      experiments[expt_s2].background[6].intensity: s.u. larger than the value
```

## Peak widths

Each bank's widths.

In `experiments/expt_n2.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_0 900()
_peak.broad_gauss_sigma_1 1000()
_peak.broad_gauss_sigma_2 300()
_peak.broad_lorentz_gamma_0 5()
```

In `experiments/expt_s2.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_0 900()
_peak.broad_gauss_sigma_1 1000()
_peak.broad_gauss_sigma_2 300()
_peak.broad_lorentz_gamma_0 5()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ferrite-austenite-beer --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ferrite-austenite-beer --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ferrite-austenite-beer, 2 banks (expt_n2, expt_s2), 5642 pts fitted / 5998 loaded, 72 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       18.05        44.16
      1      0.773     16.38        36.36   17.7% ↓
  done · converged · 1 iters · reduced χ² 36.36 · Rwp 16.38 % · 0.82 s

  per-bank Rwp (%):   expt_n2 16.15   expt_s2 16.61

  refined parameters (72 free):
  name            parameter                                                       start        value      s.u.   change
  intensity       experiments[expt_n2].background[10].intensity                   0.205        0.207     0.027   1.0% ↑
  intensity       experiments[expt_n2].background[11].intensity                   0.193        0.155     0.063   19.6% ↓
  intensity       experiments[expt_n2].background[12].intensity                   0.213        0.197     0.035   7.4% ↓
  intensity       experiments[expt_n2].background[13].intensity                   0.264        0.248     0.031   6.0% ↓
  intensity       experiments[expt_n2].background[14].intensity                   0.295        0.288     0.034   2.3% ↓
  intensity       experiments[expt_n2].background[15].intensity                   0.334        0.318     0.040   4.9% ↓
  intensity       experiments[expt_n2].background[16].intensity                   0.276        0.275     0.027   0.4% ↓
  intensity       experiments[expt_n2].background[17].intensity                   0.254        0.239     0.025   5.7% ↓
  intensity       experiments[expt_n2].background[18].intensity                   0.234        0.233     0.018   0.4% ↓
  intensity       experiments[expt_n2].background[19].intensity                    0.23        0.221     0.016   3.8% ↓
  intensity       experiments[expt_n2].background[1].intensity                    -0.02       -0.022     0.014   11.9% ↓
  intensity       experiments[expt_n2].background[20].intensity                   0.179       0.1739    0.0098   2.9% ↓
  intensity       experiments[expt_n2].background[21].intensity                   0.233        0.236     0.011   1.3% ↑
  intensity       experiments[expt_n2].background[22].intensity                   0.478        0.424     0.038   11.4% ↓
  intensity       experiments[expt_n2].background[23].intensity                   0.506        0.445     0.041   12.1% ↓
  intensity       experiments[expt_n2].background[24].intensity                   0.346        0.347     0.022   0.2% ↑
  intensity       experiments[expt_n2].background[25].intensity                    0.53        0.531     0.027   0.2% ↑
  intensity       experiments[expt_n2].background[26].intensity                    1.01        0.961     0.062   4.8% ↓
  intensity       experiments[expt_n2].background[27].intensity                   1.277        1.195     0.090   6.5% ↓
  intensity       experiments[expt_n2].background[28].intensity                   1.155        1.089     0.082   5.7% ↓
  intensity       experiments[expt_n2].background[29].intensity                    1.04        0.997     0.066   4.1% ↓
  intensity       experiments[expt_n2].background[2].intensity                     0.13         0.13      0.14 ! 2.6% ↓
  intensity       experiments[expt_n2].background[30].intensity                   0.645        0.647     0.030   0.3% ↑
  intensity       experiments[expt_n2].background[3].intensity                     0.09         0.09      0.17 ! 2.1% ↓
  intensity       experiments[expt_n2].background[4].intensity                    0.181        0.179     0.087   1.2% ↓
  intensity       experiments[expt_n2].background[5].intensity                    0.186        0.183     0.069   1.8% ↓
  intensity       experiments[expt_n2].background[6].intensity                     0.06        0.046     0.077 ! 22.6% ↓
  intensity       experiments[expt_n2].background[7].intensity                    0.147        0.147     0.038   0.3% ↑
  intensity       experiments[expt_n2].background[8].intensity                    0.214        0.206     0.033   3.9% ↓
  intensity       experiments[expt_n2].background[9].intensity                    0.195        0.191     0.026   1.8% ↓
  TOF offset, µs  experiments[expt_n2].instrument.calib_d_to_tof_offset           -1.95        -2.17      0.26   11.1% ↓
  σ₀², µs²        experiments[expt_n2].peak.broad_gauss_sigma_0                     900          281        95   68.8% ↓
  σ₁², µs²/Å²     experiments[expt_n2].peak.broad_gauss_sigma_1                  1.00e3      1.860e3   0.110e3 ! 86.0% ↑
  σ₂², µs²/Å⁴     experiments[expt_n2].peak.broad_gauss_sigma_2                     300          203        24 ! 32.4% ↓
  γ₀, µs          experiments[expt_n2].peak.broad_lorentz_gamma_0                     5         5.86      0.44   17.3% ↑
  intensity       experiments[expt_s2].background[10].intensity                   0.204        0.206     0.026   1.0% ↑
  intensity       experiments[expt_s2].background[11].intensity                   0.175        0.135     0.061   22.6% ↓
  intensity       experiments[expt_s2].background[12].intensity                   0.217        0.201     0.035   7.4% ↓
  intensity       experiments[expt_s2].background[13].intensity                   0.275        0.259     0.031   5.9% ↓
  intensity       experiments[expt_s2].background[14].intensity                     0.3        0.293     0.035   2.4% ↓
  intensity       experiments[expt_s2].background[15].intensity                   0.322        0.304     0.040   5.6% ↓
  intensity       experiments[expt_s2].background[16].intensity                   0.296        0.295     0.029   0.4% ↓
  intensity       experiments[expt_s2].background[17].intensity                   0.257        0.242     0.025   5.9% ↓
  intensity       experiments[expt_s2].background[18].intensity                   0.229        0.229     0.017   0.1% ↓
  intensity       experiments[expt_s2].background[19].intensity                   0.222        0.214     0.016   3.8% ↓
  intensity       experiments[expt_s2].background[1].intensity                  -0.0024      -0.0044      0.12 ! 84.0% ↓
  intensity       experiments[expt_s2].background[20].intensity                   0.172       0.1671    0.0095   2.9% ↓
  intensity       experiments[expt_s2].background[21].intensity                   0.239        0.242     0.011   1.1% ↑
  intensity       experiments[expt_s2].background[22].intensity                   0.486        0.432     0.038   11.1% ↓
  intensity       experiments[expt_s2].background[23].intensity                   0.495        0.435     0.040   12.0% ↓
  intensity       experiments[expt_s2].background[24].intensity                   0.342        0.343     0.022   0.3% ↑
  intensity       experiments[expt_s2].background[25].intensity                   0.534        0.535     0.027   0.2% ↑
  intensity       experiments[expt_s2].background[26].intensity                   1.019        0.971     0.062   4.7% ↓
  intensity       experiments[expt_s2].background[27].intensity                   1.284        1.200     0.091   6.6% ↓
  intensity       experiments[expt_s2].background[28].intensity                   1.219        1.152     0.085   5.5% ↓
  intensity       experiments[expt_s2].background[29].intensity                   0.987        0.947     0.063   4.1% ↓
  intensity       experiments[expt_s2].background[2].intensity                      0.1         0.11      0.14 ! 10.8% ↑
  intensity       experiments[expt_s2].background[30].intensity                   0.652        0.654     0.030   0.3% ↑
  intensity       experiments[expt_s2].background[3].intensity                     0.08         0.07      0.15 ! 11.3% ↓
  intensity       experiments[expt_s2].background[4].intensity                    0.183        0.181     0.081   0.8% ↓
  intensity       experiments[expt_s2].background[5].intensity                    0.158        0.153     0.067   2.9% ↓
  intensity       experiments[expt_s2].background[6].intensity                    0.044        0.029     0.070 ! 35.2% ↓
  intensity       experiments[expt_s2].background[7].intensity                    0.154        0.154     0.038   0.1% ↑
  intensity       experiments[expt_s2].background[8].intensity                    0.208        0.199     0.032   4.4% ↓
  intensity       experiments[expt_s2].background[9].intensity                    0.189        0.186     0.025   1.8% ↓
  TOF offset, µs  experiments[expt_s2].instrument.calib_d_to_tof_offset           -9.13        -9.74      0.26   6.7% ↓
  scale           experiments[expt_s2].linked_structures[austenite].scale         74.03        74.57      0.24   0.7% ↑
  scale           experiments[expt_s2].linked_structures[ferrite].scale           300.2        303.1       1.2   1.0% ↑
  σ₀², µs²        experiments[expt_s2].peak.broad_gauss_sigma_0                     900          276        94   69.3% ↓
  σ₁², µs²/Å²     experiments[expt_s2].peak.broad_gauss_sigma_1                  1.00e3      1.880e3   0.110e3 ! 87.9% ↑
  σ₂², µs²/Å⁴     experiments[expt_s2].peak.broad_gauss_sigma_2                     300          192        23 ! 36.1% ↓
  γ₀, µs          experiments[expt_s2].peak.broad_lorentz_gamma_0                     5         5.91      0.44   18.1% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[expt_n2].background[2].intensity: s.u. larger than the value
      experiments[expt_n2].background[3].intensity: s.u. larger than the value
      experiments[expt_n2].background[6].intensity: s.u. larger than the value
      experiments[expt_n2].peak.broad_gauss_sigma_1: strongly correlated with σ₂² (expt_n2) (r = -0.97)
      experiments[expt_n2].peak.broad_gauss_sigma_2: strongly correlated with σ₁² (expt_n2) (r = -0.97)
      experiments[expt_s2].background[1].intensity: s.u. larger than the value
      experiments[expt_s2].background[2].intensity: s.u. larger than the value
      experiments[expt_s2].background[3].intensity: s.u. larger than the value
      experiments[expt_s2].background[6].intensity: s.u. larger than the value
      experiments[expt_s2].peak.broad_gauss_sigma_1: strongly correlated with σ₂² (expt_s2) (r = -0.97)
      experiments[expt_s2].peak.broad_gauss_sigma_2: strongly correlated with σ₁² (expt_s2) (r = -0.97)
```

## Displacement

Last, ferrite's displacement; austenite's follows it.

In `structures/ferrite.edi`, add `()` after the values the stage frees:

```edi
Fe Fe 0 0 0 a 2 1 0.5() Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ferrite-austenite-beer --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ferrite-austenite-beer --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ferrite-austenite-beer, 2 banks (expt_n2, expt_s2), 5642 pts fitted / 5998 loaded, 73 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       16.38        36.36
      1      0.558      7.13         6.89   81.0% ↓
      2      0.866      7.13         6.89   
  done · converged · 2 iters · reduced χ² 6.89 · Rwp 7.13 % · 0.91 s

  per-bank Rwp (%):   expt_n2 7.06   expt_s2 7.20

  refined parameters (73 free):
  name            parameter                                                       start        value      s.u.   change
  intensity       experiments[expt_n2].background[10].intensity                   0.207        0.199     0.012   3.7% ↓
  intensity       experiments[expt_n2].background[11].intensity                   0.155        0.248     0.028   59.7% ↑
  intensity       experiments[expt_n2].background[12].intensity                   0.197        0.241     0.015   22.1% ↑
  intensity       experiments[expt_n2].background[13].intensity                   0.248        0.283     0.014   14.0% ↑
  intensity       experiments[expt_n2].background[14].intensity                   0.288        0.304     0.015   5.7% ↑
  intensity       experiments[expt_n2].background[15].intensity                   0.318        0.338     0.018   6.4% ↑
  intensity       experiments[expt_n2].background[16].intensity                   0.275        0.278     0.012   1.1% ↑
  intensity       experiments[expt_n2].background[17].intensity                   0.239        0.255     0.011   6.7% ↑
  intensity       experiments[expt_n2].background[18].intensity                   0.233       0.2372    0.0075   1.8% ↑
  intensity       experiments[expt_n2].background[19].intensity                   0.221       0.2242    0.0069   1.4% ↑
  intensity       experiments[expt_n2].background[1].intensity                   -0.022      -0.0185    0.0057   16.1% ↑
  intensity       experiments[expt_n2].background[20].intensity                  0.1739       0.1763    0.0043   1.4% ↑
  intensity       experiments[expt_n2].background[21].intensity                   0.236       0.2348    0.0046   0.5% ↓
  intensity       experiments[expt_n2].background[22].intensity                   0.424        0.427     0.017   0.7% ↑
  intensity       experiments[expt_n2].background[23].intensity                   0.445        0.446     0.018   0.3% ↑
  intensity       experiments[expt_n2].background[24].intensity                   0.347       0.3472    0.0092   
  intensity       experiments[expt_n2].background[25].intensity                   0.531        0.532     0.012   0.2% ↑
  intensity       experiments[expt_n2].background[26].intensity                   0.961        0.946     0.028   1.6% ↓
  intensity       experiments[expt_n2].background[27].intensity                   1.195        1.163     0.040   2.7% ↓
  intensity       experiments[expt_n2].background[28].intensity                   1.089        1.060     0.036   2.7% ↓
  intensity       experiments[expt_n2].background[29].intensity                   0.997        0.977     0.029   2.0% ↓
  intensity       experiments[expt_n2].background[2].intensity                     0.13        0.187     0.061   43.6% ↑
  intensity       experiments[expt_n2].background[30].intensity                   0.647        0.648     0.013   0.2% ↑
  intensity       experiments[expt_n2].background[3].intensity                     0.09        0.207     0.071   129.8% ↑
  intensity       experiments[expt_n2].background[4].intensity                    0.179        0.204     0.038   13.9% ↑
  intensity       experiments[expt_n2].background[5].intensity                    0.183        0.215     0.030   17.3% ↑
  intensity       experiments[expt_n2].background[6].intensity                    0.046        0.255     0.034   454.4% ↑
  intensity       experiments[expt_n2].background[7].intensity                    0.147        0.181     0.017   23.2% ↑
  intensity       experiments[expt_n2].background[8].intensity                    0.206        0.225     0.015   9.3% ↑
  intensity       experiments[expt_n2].background[9].intensity                    0.191        0.205     0.011   7.3% ↑
  TOF offset, µs  experiments[expt_n2].instrument.calib_d_to_tof_offset           -2.17        -2.11      0.13   2.9% ↑
  σ₀², µs²        experiments[expt_n2].peak.broad_gauss_sigma_0                     281          914        60   225.4% ↑
  σ₁², µs²/Å²     experiments[expt_n2].peak.broad_gauss_sigma_1                  1.86e3      1.247e3   0.060e3 ! 33.0% ↓
  σ₂², µs²/Å⁴     experiments[expt_n2].peak.broad_gauss_sigma_2                     203          325        12 ! 60.3% ↑
  γ₀, µs          experiments[expt_n2].peak.broad_lorentz_gamma_0                  5.86         4.98      0.21   15.1% ↓
  intensity       experiments[expt_s2].background[10].intensity                   0.206        0.198     0.012   3.6% ↓
  intensity       experiments[expt_s2].background[11].intensity                   0.135        0.228     0.027   68.7% ↑
  intensity       experiments[expt_s2].background[12].intensity                   0.201        0.245     0.015   21.7% ↑
  intensity       experiments[expt_s2].background[13].intensity                   0.259        0.293     0.014   13.2% ↑
  intensity       experiments[expt_s2].background[14].intensity                   0.293        0.309     0.015   5.3% ↑
  intensity       experiments[expt_s2].background[15].intensity                   0.304        0.326     0.018   7.4% ↑
  intensity       experiments[expt_s2].background[16].intensity                   0.295        0.299     0.013   1.2% ↑
  intensity       experiments[expt_s2].background[17].intensity                   0.242        0.259     0.011   6.9% ↑
  intensity       experiments[expt_s2].background[18].intensity                   0.229       0.2329    0.0074   1.7% ↑
  intensity       experiments[expt_s2].background[19].intensity                   0.214       0.2163    0.0067   1.1% ↑
  intensity       experiments[expt_s2].background[1].intensity                  -0.0044        0.017     0.051 ! 489.2% ↑
  intensity       experiments[expt_s2].background[20].intensity                  0.1671       0.1695    0.0042   1.4% ↑
  intensity       experiments[expt_s2].background[21].intensity                   0.242       0.2405    0.0046   0.6% ↓
  intensity       experiments[expt_s2].background[22].intensity                   0.432        0.435     0.017   0.7% ↑
  intensity       experiments[expt_s2].background[23].intensity                   0.435        0.439     0.018   0.9% ↑
  intensity       experiments[expt_s2].background[24].intensity                   0.343       0.3434    0.0092   0.1% ↑
  intensity       experiments[expt_s2].background[25].intensity                   0.535        0.536     0.012   0.2% ↑
  intensity       experiments[expt_s2].background[26].intensity                   0.971        0.956     0.028   1.5% ↓
  intensity       experiments[expt_s2].background[27].intensity                     1.2        1.170     0.041   2.5% ↓
  intensity       experiments[expt_s2].background[28].intensity                   1.152        1.122     0.037   2.6% ↓
  intensity       experiments[expt_s2].background[29].intensity                   0.947        0.930     0.028   1.7% ↓
  intensity       experiments[expt_s2].background[2].intensity                     0.11        0.150     0.059   36.3% ↑
  intensity       experiments[expt_s2].background[30].intensity                   0.654        0.655     0.013   0.2% ↑
  intensity       experiments[expt_s2].background[3].intensity                     0.07        0.185     0.066   164.1% ↑
  intensity       experiments[expt_s2].background[4].intensity                    0.181        0.198     0.036   9.5% ↑
  intensity       experiments[expt_s2].background[5].intensity                    0.153        0.191     0.029   24.6% ↑
  intensity       experiments[expt_s2].background[6].intensity                    0.029        0.215     0.030   641.7% ↑
  intensity       experiments[expt_s2].background[7].intensity                    0.154        0.189     0.017   22.9% ↑
  intensity       experiments[expt_s2].background[8].intensity                    0.199        0.220     0.014   10.6% ↑
  intensity       experiments[expt_s2].background[9].intensity                    0.186        0.200     0.011   7.3% ↑
  TOF offset, µs  experiments[expt_s2].instrument.calib_d_to_tof_offset           -9.74       -10.31      0.13   5.8% ↓
  scale           experiments[expt_s2].linked_structures[austenite].scale         74.57        95.99      0.20   28.7% ↑
  scale           experiments[expt_s2].linked_structures[ferrite].scale           303.1       402.38      0.96   32.8% ↑
  σ₀², µs²        experiments[expt_s2].peak.broad_gauss_sigma_0                     276          893        59   223.5% ↑
  σ₁², µs²/Å²     experiments[expt_s2].peak.broad_gauss_sigma_1                  1.88e3      1.286e3   0.059e3 ! 31.6% ↓
  σ₂², µs²/Å⁴     experiments[expt_s2].peak.broad_gauss_sigma_2                     192          311        12 ! 62.2% ↑
  γ₀, µs          experiments[expt_s2].peak.broad_lorentz_gamma_0                  5.91         4.99      0.21   15.6% ↓
  B iso, Å²       structures[ferrite].atom_sites[Fe].adp_iso                      0.500       1.7154    0.0089   243.1% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[expt_n2].peak.broad_gauss_sigma_1: strongly correlated with σ₂² (expt_n2) (r = -0.98)
      experiments[expt_n2].peak.broad_gauss_sigma_2: strongly correlated with σ₁² (expt_n2) (r = -0.98)
      experiments[expt_s2].background[1].intensity: s.u. larger than the value
      experiments[expt_s2].peak.broad_gauss_sigma_1: strongly correlated with σ₂² (expt_s2) (r = -0.98)
      experiments[expt_s2].peak.broad_gauss_sigma_2: strongly correlated with σ₁² (expt_s2) (r = -0.98)
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-neut-tof_ferrite-austenite-beer --output pd-neut-tof_ferrite-austenite-beer.html
    ```
