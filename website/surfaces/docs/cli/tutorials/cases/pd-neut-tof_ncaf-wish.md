# Joint fit: Na₂Ca₃Al₂F₁₄, WISH

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit Na₂Ca₃Al₂F₁₄ to time-of-flight neutron powder data from WISH at ISIS, all five detector bank
pairs at once. Each bank has its own calibration and profile; the structure is shared.

It builds the catalogue case `pd-neut-tof_ncaf-wish` step by step: the same project the command
line fits and the app's Examples open.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p pd-neut-tof_ncaf-wish/structures pd-neut-tof_ncaf-wish/experiments pd-neut-tof_ncaf-wish/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name pd-neut-tof_ncaf-wish
_metadata.title "Na₂Ca₃Al₂F₁₄ [I2₁3] · WISH @ ISIS"
_metadata.description "All five detector bank pairs fitted jointly · Jorgensen–Von Dreele profile · Per-bank calibration"
_metadata.authors .
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_ncaf-wish-ncaf
    mv data/pd-neut-tof_ncaf-wish-ncaf.edi pd-neut-tof_ncaf-wish/structures/ncaf.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_ncaf-wish-ncaf
    mv data/pd-neut-tof_ncaf-wish-ncaf.edi pd-neut-tof_ncaf-wish/structures/ncaf.edi
    ```

## Define the experiments

Download the experiments into `experiments`: each file declares its instrument, peak profile, background, the structures it links and its measured data.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_ncaf-wish-wish_1_10
    mv data/pd-neut-tof_ncaf-wish-wish_1_10.edi pd-neut-tof_ncaf-wish/experiments/wish_1_10.edi
    edi download-data pd-neut-tof_ncaf-wish-wish_2_9
    mv data/pd-neut-tof_ncaf-wish-wish_2_9.edi pd-neut-tof_ncaf-wish/experiments/wish_2_9.edi
    edi download-data pd-neut-tof_ncaf-wish-wish_3_8
    mv data/pd-neut-tof_ncaf-wish-wish_3_8.edi pd-neut-tof_ncaf-wish/experiments/wish_3_8.edi
    edi download-data pd-neut-tof_ncaf-wish-wish_4_7
    mv data/pd-neut-tof_ncaf-wish-wish_4_7.edi pd-neut-tof_ncaf-wish/experiments/wish_4_7.edi
    edi download-data pd-neut-tof_ncaf-wish-wish_5_6
    mv data/pd-neut-tof_ncaf-wish-wish_5_6.edi pd-neut-tof_ncaf-wish/experiments/wish_5_6.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_ncaf-wish-wish_1_10
    mv data/pd-neut-tof_ncaf-wish-wish_1_10.edi pd-neut-tof_ncaf-wish/experiments/wish_1_10.edi
    python -m edi download-data pd-neut-tof_ncaf-wish-wish_2_9
    mv data/pd-neut-tof_ncaf-wish-wish_2_9.edi pd-neut-tof_ncaf-wish/experiments/wish_2_9.edi
    python -m edi download-data pd-neut-tof_ncaf-wish-wish_3_8
    mv data/pd-neut-tof_ncaf-wish-wish_3_8.edi pd-neut-tof_ncaf-wish/experiments/wish_3_8.edi
    python -m edi download-data pd-neut-tof_ncaf-wish-wish_4_7
    mv data/pd-neut-tof_ncaf-wish-wish_4_7.edi pd-neut-tof_ncaf-wish/experiments/wish_4_7.edi
    python -m edi download-data pd-neut-tof_ncaf-wish-wish_5_6
    mv data/pd-neut-tof_ncaf-wish-wish_5_6.edi pd-neut-tof_ncaf-wish/experiments/wish_5_6.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_minimizer.type crysta
_minimizer.max_iterations 1000
_minimizer.chi_square_tolerance 0.0001

_fitting_mode.type joint

loop_
_joint_fit.experiment_id
_joint_fit.weight
wish_1_10 1
wish_2_9 1
wish_3_8 1
wish_4_7 1
wish_5_6 1

_edi.schema_version 3
```

## Scales and time-of-flight calibration

Each bank's scale and DIFC offset and linear term put its peaks in place and at the right
height.

In `experiments/wish_1_10.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
_instrument.calib_d_to_tof_linear 4985.32()
ncaf 40() 1.0
```

In `experiments/wish_2_9.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
_instrument.calib_d_to_tof_linear 10389.9()
ncaf 40() 1.0
```

In `experiments/wish_3_8.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
_instrument.calib_d_to_tof_linear 15105.5()
ncaf 40() 1.0
```

In `experiments/wish_4_7.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
_instrument.calib_d_to_tof_linear 18660.1()
ncaf 40() 1.0
```

In `experiments/wish_5_6.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
_instrument.calib_d_to_tof_linear 20772.9()
ncaf 40() 1.0
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ncaf-wish, 5 banks (wish_1_10, wish_2_9, wish_3_8, wish_4_7, wish_5_6), 18973 pts fitted / 20475 loaded, 15 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       29.77       140.86
      1      0.364     19.91        62.98   55.3% ↓
      2      0.407     19.90        62.95   
      3      0.462     19.90        62.95   
      4      0.518     19.90        62.95   
      5      0.575     19.90        62.95   
      6      0.657     19.90        62.95   
  done · converged · 6 iters · reduced χ² 62.95 · Rwp 19.90 % · 0.71 s

  per-bank Rwp (%):   wish_1_10 8.20   wish_2_9 19.90   wish_3_8 20.38   wish_4_7 20.84   wish_5_6 20.34

  refined parameters (15 free):
  name             parameter                                                       start        value      s.u.   change
  TOF linear, µs/Å experiments[wish_1_10].instrument.calib_d_to_tof_linear        4.99e3     4.9854e3  0.0022e3   
  TOF offset, µs   experiments[wish_1_10].instrument.calib_d_to_tof_offset             0         13.9       8.2   
  scale            experiments[wish_1_10].linked_structures[ncaf].scale               40        31.64      0.61   20.9% ↓
  TOF linear, µs/Å experiments[wish_2_9].instrument.calib_d_to_tof_linear         1.04e4   1.038968e40.000049e4   
  TOF offset, µs   experiments[wish_2_9].instrument.calib_d_to_tof_offset              0         13.8       1.2   
  scale            experiments[wish_2_9].linked_structures[ncaf].scale                40        32.64      0.20   18.4% ↓
  TOF linear, µs/Å experiments[wish_3_8].instrument.calib_d_to_tof_linear         1.51e4   1.510335e40.000038e4   
  TOF offset, µs   experiments[wish_3_8].instrument.calib_d_to_tof_offset              0       -10.36      0.69   
  scale            experiments[wish_3_8].linked_structures[ncaf].scale                40        33.30      0.15   16.7% ↓
  TOF linear, µs/Å experiments[wish_4_7].instrument.calib_d_to_tof_linear         1.87e4   1.865808e40.000033e4   
  TOF offset, µs   experiments[wish_4_7].instrument.calib_d_to_tof_offset              0       -13.05      0.53   
  scale            experiments[wish_4_7].linked_structures[ncaf].scale                40        32.94      0.14   17.7% ↓
  TOF linear, µs/Å experiments[wish_5_6].instrument.calib_d_to_tof_linear         2.08e4   2.077090e40.000030e4   
  TOF offset, µs   experiments[wish_5_6].instrument.calib_d_to_tof_offset              0       -11.29      0.44   
  scale            experiments[wish_5_6].linked_structures[ncaf].scale                40        33.13      0.14   17.2% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

Each bank's background points; bank 1-10's first and last stay fixed, as its source has them.

In `experiments/wish_1_10.edi`, add `()` after the values the stage frees:

```edi
2 7099.4761 210()
3 8008.2271 210()
```

The same for every other row (32 more).

In `experiments/wish_2_9.edi`, add `()` after the values the stage frees:

```edi
1 7246.0732 220()
2 9265.5195 220()
```

The same for every other row (20 more).

In `experiments/wish_3_8.edi`, add `()` after the values the stage frees:

```edi
1 9089.7529 240()
2 11580.4033 240()
```

The same for every other row (20 more).

In `experiments/wish_4_7.edi`, add `()` after the values the stage frees:

```edi
1 9089.7529 250()
2 10671.6523 250()
```

The same for every other row (26 more).

In `experiments/wish_5_6.edi`, add `()` after the values the stage frees:

```edi
1 11136.874 260()
2 13313.3877 260()
```

The same for every other row (26 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ncaf-wish, 5 banks (wish_1_10, wish_2_9, wish_3_8, wish_4_7, wish_5_6), 18973 pts fitted / 20475 loaded, 149 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       19.90        63.39
      1      1.023     13.97        31.21   50.8% ↓
  done · converged · 1 iters · reduced χ² 31.21 · Rwp 13.97 % · 1.21 s

  per-bank Rwp (%):   wish_1_10 6.08   wish_2_9 13.72   wish_3_8 14.60   wish_4_7 14.47   wish_5_6 14.27

  refined parameters (149 free):
  name             parameter                                                       start        value      s.u.   change
  intensity        experiments[wish_1_10].background[10].intensity                   210          230        33   9.7% ↑
  intensity        experiments[wish_1_10].background[11].intensity                   210          255        23   21.4% ↑
  intensity        experiments[wish_1_10].background[12].intensity                   210          246        21   17.1% ↑
  intensity        experiments[wish_1_10].background[13].intensity                   210          224        17   6.4% ↑
  intensity        experiments[wish_1_10].background[14].intensity                   210          258        14   22.9% ↑
  intensity        experiments[wish_1_10].background[15].intensity                   210        247.3       9.2   17.7% ↑
  intensity        experiments[wish_1_10].background[16].intensity                   210        227.2       7.3   8.2% ↑
  intensity        experiments[wish_1_10].background[17].intensity                   210        236.8       5.9   12.8% ↑
  intensity        experiments[wish_1_10].background[18].intensity                   210        226.7       5.2   7.9% ↑
  intensity        experiments[wish_1_10].background[19].intensity                   210        223.4       5.2   6.4% ↑
  intensity        experiments[wish_1_10].background[20].intensity                   210        219.8       5.1   4.7% ↑
  intensity        experiments[wish_1_10].background[21].intensity                   210        223.6       3.8   6.5% ↑
  intensity        experiments[wish_1_10].background[22].intensity                   210        216.6       3.7   3.1% ↑
  intensity        experiments[wish_1_10].background[23].intensity                   210        216.8       4.3   3.2% ↑
  intensity        experiments[wish_1_10].background[24].intensity                   210        213.5       4.7   1.7% ↑
  intensity        experiments[wish_1_10].background[25].intensity                   210        216.2       5.3   3.0% ↑
  intensity        experiments[wish_1_10].background[26].intensity                   210        213.0       6.0   1.4% ↑
  intensity        experiments[wish_1_10].background[27].intensity                   210        212.4       7.1   1.1% ↑
  intensity        experiments[wish_1_10].background[28].intensity                   210        212.6       8.2   1.2% ↑
  intensity        experiments[wish_1_10].background[29].intensity                   210        211.3       9.9   0.6% ↑
  intensity        experiments[wish_1_10].background[2].intensity                    210          110       130 ! 48.7% ↓
  intensity        experiments[wish_1_10].background[30].intensity                   210          211        13   0.5% ↑
  intensity        experiments[wish_1_10].background[31].intensity                   210          223        16   6.2% ↑
  intensity        experiments[wish_1_10].background[32].intensity                   210          210        21   0.2% ↑
  intensity        experiments[wish_1_10].background[33].intensity                   210          222        31   5.8% ↑
  intensity        experiments[wish_1_10].background[34].intensity                   210          255        48   21.4% ↑
  intensity        experiments[wish_1_10].background[35].intensity                   210          120        63   43.0% ↓
  intensity        experiments[wish_1_10].background[3].intensity                    210          161        81   23.5% ↓
  intensity        experiments[wish_1_10].background[4].intensity                    210          120        79   42.8% ↓
  intensity        experiments[wish_1_10].background[5].intensity                    210          322        95   53.5% ↑
  intensity        experiments[wish_1_10].background[6].intensity                    210          259        64   23.5% ↑
  intensity        experiments[wish_1_10].background[7].intensity                    210          234        66   11.2% ↑
  intensity        experiments[wish_1_10].background[8].intensity                    210          229        54   9.0% ↑
  intensity        experiments[wish_1_10].background[9].intensity                    210          239        40   13.7% ↑
  TOF linear, µs/Å experiments[wish_1_10].instrument.calib_d_to_tof_linear        4.99e3     4.9851e3  0.0016e3   
  TOF offset, µs   experiments[wish_1_10].instrument.calib_d_to_tof_offset          13.9         14.5       6.1   4.1% ↑
  scale            experiments[wish_1_10].linked_structures[ncaf].scale            31.64        30.36      0.47   4.0% ↓
  intensity        experiments[wish_2_9].background[10].intensity                    220        286.9       5.5   30.4% ↑
  intensity        experiments[wish_2_9].background[11].intensity                    220        284.6       5.4   29.3% ↑
  intensity        experiments[wish_2_9].background[12].intensity                    220        267.7       4.0   21.7% ↑
  intensity        experiments[wish_2_9].background[13].intensity                    220        259.4       3.3   17.9% ↑
  intensity        experiments[wish_2_9].background[14].intensity                    220        251.7       3.0   14.4% ↑
  intensity        experiments[wish_2_9].background[15].intensity                    220        232.1       2.9   5.5% ↑
  intensity        experiments[wish_2_9].background[16].intensity                    220        222.7       3.5   1.2% ↑
  intensity        experiments[wish_2_9].background[17].intensity                    220        219.9       4.7   0.1% ↓
  intensity        experiments[wish_2_9].background[18].intensity                    220        227.1       6.4   3.2% ↑
  intensity        experiments[wish_2_9].background[19].intensity                    220        218.4       8.7   0.7% ↓
  intensity        experiments[wish_2_9].background[1].intensity                     220          125        83   43.1% ↓
  intensity        experiments[wish_2_9].background[20].intensity                    220          220        14   0.1% ↑
  intensity        experiments[wish_2_9].background[21].intensity                    220          219        23   0.6% ↓
  intensity        experiments[wish_2_9].background[22].intensity                    220          164        55   25.3% ↓
  intensity        experiments[wish_2_9].background[2].intensity                     220          222        63   0.7% ↑
  intensity        experiments[wish_2_9].background[3].intensity                     220          348        44   58.2% ↑
  intensity        experiments[wish_2_9].background[4].intensity                     220          391        27   77.5% ↑
  intensity        experiments[wish_2_9].background[5].intensity                     220          355        20   61.5% ↑
  intensity        experiments[wish_2_9].background[6].intensity                     220          345        17   56.9% ↑
  intensity        experiments[wish_2_9].background[7].intensity                     220          393        14   78.5% ↑
  intensity        experiments[wish_2_9].background[8].intensity                     220          417        11   89.6% ↑
  intensity        experiments[wish_2_9].background[9].intensity                     220        404.8       7.6   84.0% ↑
  TOF linear, µs/Å experiments[wish_2_9].instrument.calib_d_to_tof_linear         1.04e4   1.038973e40.000036e4   
  TOF offset, µs   experiments[wish_2_9].instrument.calib_d_to_tof_offset           13.8        13.26      0.84   3.9% ↓
  scale            experiments[wish_2_9].linked_structures[ncaf].scale             32.64        30.86      0.15   5.4% ↓
  intensity        experiments[wish_3_8].background[10].intensity                    240        376.4       5.1   56.8% ↑
  intensity        experiments[wish_3_8].background[11].intensity                    240        343.2       4.7   43.0% ↑
  intensity        experiments[wish_3_8].background[12].intensity                    240        298.4       4.0   24.3% ↑
  intensity        experiments[wish_3_8].background[13].intensity                    240        264.9       3.6   10.4% ↑
  intensity        experiments[wish_3_8].background[14].intensity                    240        257.0       3.6   7.1% ↑
  intensity        experiments[wish_3_8].background[15].intensity                    240        242.5       3.8   1.0% ↑
  intensity        experiments[wish_3_8].background[16].intensity                    240        250.9       4.3   4.5% ↑
  intensity        experiments[wish_3_8].background[17].intensity                    240        239.5       5.2   0.2% ↓
  intensity        experiments[wish_3_8].background[18].intensity                    240        245.9       7.5   2.5% ↑
  intensity        experiments[wish_3_8].background[19].intensity                    240          240        11   
  intensity        experiments[wish_3_8].background[1].intensity                     240          330        61   37.5% ↑
  intensity        experiments[wish_3_8].background[20].intensity                    240          236        15   1.8% ↓
  intensity        experiments[wish_3_8].background[21].intensity                    240          239        25   0.5% ↓
  intensity        experiments[wish_3_8].background[22].intensity                    240          243        58   1.1% ↑
  intensity        experiments[wish_3_8].background[2].intensity                     240          430        40   79.2% ↑
  intensity        experiments[wish_3_8].background[3].intensity                     240          392        27   63.2% ↑
  intensity        experiments[wish_3_8].background[4].intensity                     240          455        19   89.8% ↑
  intensity        experiments[wish_3_8].background[5].intensity                     240          396        12   64.9% ↑
  intensity        experiments[wish_3_8].background[6].intensity                     240        382.0       9.0   59.2% ↑
  intensity        experiments[wish_3_8].background[7].intensity                     240        360.5       8.0   50.2% ↑
  intensity        experiments[wish_3_8].background[8].intensity                     240        341.4       6.7   42.2% ↑
  intensity        experiments[wish_3_8].background[9].intensity                     240        354.1       5.8   47.5% ↑
  TOF linear, µs/Å experiments[wish_3_8].instrument.calib_d_to_tof_linear         1.51e4   1.510341e40.000028e4   
  TOF offset, µs   experiments[wish_3_8].instrument.calib_d_to_tof_offset         -10.36       -10.70      0.52   3.3% ↓
  scale            experiments[wish_3_8].linked_structures[ncaf].scale              33.3        31.56      0.11   5.2% ↓
  intensity        experiments[wish_4_7].background[10].intensity                    250        367.9       9.5   47.2% ↑
  intensity        experiments[wish_4_7].background[11].intensity                    250        417.3       8.3   66.9% ↑
  intensity        experiments[wish_4_7].background[12].intensity                    250        381.3       6.9   52.5% ↑
  intensity        experiments[wish_4_7].background[13].intensity                    250        367.8       6.2   47.1% ↑
  intensity        experiments[wish_4_7].background[14].intensity                    250        350.8       5.5   40.3% ↑
  intensity        experiments[wish_4_7].background[15].intensity                    250        306.9       5.4   22.7% ↑
  intensity        experiments[wish_4_7].background[16].intensity                    250        402.7       6.3   61.1% ↑
  intensity        experiments[wish_4_7].background[17].intensity                    250        328.9       5.2   31.6% ↑
  intensity        experiments[wish_4_7].background[18].intensity                    250        330.0       4.3   32.0% ↑
  intensity        experiments[wish_4_7].background[19].intensity                    250        264.5       4.1   5.8% ↑
  intensity        experiments[wish_4_7].background[1].intensity                     250          378        69   51.4% ↑
  intensity        experiments[wish_4_7].background[20].intensity                    250        268.3       4.9   7.3% ↑
  intensity        experiments[wish_4_7].background[21].intensity                    250        252.8       5.2   1.1% ↑
  intensity        experiments[wish_4_7].background[22].intensity                    250        264.7       4.9   5.9% ↑
  intensity        experiments[wish_4_7].background[23].intensity                    250        258.7       5.3   3.5% ↑
  intensity        experiments[wish_4_7].background[24].intensity                    250        263.5       6.4   5.4% ↑
  intensity        experiments[wish_4_7].background[25].intensity                    250        262.2       8.0   4.9% ↑
  intensity        experiments[wish_4_7].background[26].intensity                    250          255        11   1.9% ↑
  intensity        experiments[wish_4_7].background[27].intensity                    250          264        19   5.4% ↑
  intensity        experiments[wish_4_7].background[28].intensity                    250          238        47   4.9% ↓
  intensity        experiments[wish_4_7].background[2].intensity                     250          452        51   80.7% ↑
  intensity        experiments[wish_4_7].background[3].intensity                     250          419        39   67.7% ↑
  intensity        experiments[wish_4_7].background[4].intensity                     250          476        32   90.4% ↑
  intensity        experiments[wish_4_7].background[5].intensity                     250          493        24   97.0% ↑
  intensity        experiments[wish_4_7].background[6].intensity                     250          411        19   64.6% ↑
  intensity        experiments[wish_4_7].background[7].intensity                     250          445        17   78.0% ↑
  intensity        experiments[wish_4_7].background[8].intensity                     250          399        15   59.4% ↑
  intensity        experiments[wish_4_7].background[9].intensity                     250          492        15   97.0% ↑
  TOF linear, µs/Å experiments[wish_4_7].instrument.calib_d_to_tof_linear         1.87e4   1.865806e40.000025e4   
  TOF offset, µs   experiments[wish_4_7].instrument.calib_d_to_tof_offset         -13.05       -13.17      0.40   0.9% ↓
  scale            experiments[wish_4_7].linked_structures[ncaf].scale             32.94       30.877     0.099   6.3% ↓
  intensity        experiments[wish_5_6].background[10].intensity                    260          474        17   82.4% ↑
  intensity        experiments[wish_5_6].background[11].intensity                    260          465        12   78.8% ↑
  intensity        experiments[wish_5_6].background[12].intensity                    260        361.8       7.9   39.2% ↑
  intensity        experiments[wish_5_6].background[13].intensity                    260        414.5       7.2   59.4% ↑
  intensity        experiments[wish_5_6].background[14].intensity                    260        378.4       5.9   45.5% ↑
  intensity        experiments[wish_5_6].background[15].intensity                    260        366.1       5.2   40.8% ↑
  intensity        experiments[wish_5_6].background[16].intensity                    260        340.8       4.9   31.1% ↑
  intensity        experiments[wish_5_6].background[17].intensity                    260        328.3       4.7   26.3% ↑
  intensity        experiments[wish_5_6].background[18].intensity                    260        344.3       4.8   32.4% ↑
  intensity        experiments[wish_5_6].background[19].intensity                    260        317.9       4.7   22.3% ↑
  intensity        experiments[wish_5_6].background[1].intensity                     260          503        42   93.6% ↑
  intensity        experiments[wish_5_6].background[20].intensity                    260        286.3       4.9   10.1% ↑
  intensity        experiments[wish_5_6].background[21].intensity                    260        262.3       5.0   0.9% ↑
  intensity        experiments[wish_5_6].background[22].intensity                    260        269.8       5.2   3.8% ↑
  intensity        experiments[wish_5_6].background[23].intensity                    260        265.4       5.5   2.1% ↑
  intensity        experiments[wish_5_6].background[24].intensity                    260        261.7       6.7   0.7% ↑
  intensity        experiments[wish_5_6].background[25].intensity                    260        275.1       8.1   5.8% ↑
  intensity        experiments[wish_5_6].background[26].intensity                    260        270.9       7.8   4.2% ↑
  intensity        experiments[wish_5_6].background[27].intensity                    260        276.6       9.9   6.4% ↑
  intensity        experiments[wish_5_6].background[28].intensity                    260          255        21   1.9% ↓
  intensity        experiments[wish_5_6].background[2].intensity                     260          437        32   68.1% ↑
  intensity        experiments[wish_5_6].background[3].intensity                     260          377        56   45.0% ↑
  intensity        experiments[wish_5_6].background[4].intensity                     260          480        26   84.7% ↑
  intensity        experiments[wish_5_6].background[5].intensity                     260          505        23   94.4% ↑
  intensity        experiments[wish_5_6].background[6].intensity                     260          467        19   79.7% ↑
  intensity        experiments[wish_5_6].background[7].intensity                     260          405        15   55.7% ↑
  intensity        experiments[wish_5_6].background[8].intensity                     260          454        14   74.5% ↑
  intensity        experiments[wish_5_6].background[9].intensity                     260          384        13   47.5% ↑
  TOF linear, µs/Å experiments[wish_5_6].instrument.calib_d_to_tof_linear         2.08e4   2.077095e40.000023e4   
  TOF offset, µs   experiments[wish_5_6].instrument.calib_d_to_tof_offset         -11.29       -11.45      0.33   1.4% ↓
  scale            experiments[wish_5_6].linked_structures[ncaf].scale             33.13       30.983     0.098   6.5% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[wish_1_10].background[2].intensity: s.u. larger than the value
```

## Peak asymmetry

Each bank's back-to-back exponentials, the terms its data determine; bank 1-10 keeps its
instrument values.

In `experiments/wish_2_9.edi`, add `()` after the values the stage frees:

```edi
_peak.rise_alpha_0 0.053()
_peak.rise_alpha_1 0.031()
_peak.decay_beta_0 0.0061()
_peak.decay_beta_1 0.096()
```

In `experiments/wish_3_8.edi`, add `()` after the values the stage frees:

```edi
_peak.rise_alpha_0 -0.016()
_peak.rise_alpha_1 0.16()
_peak.decay_beta_0 0.0069()
_peak.decay_beta_1 0.032()
```

In `experiments/wish_4_7.edi`, add `()` after the values the stage frees:

```edi
_peak.rise_alpha_0 -0.015()
_peak.rise_alpha_1 0.16()
_peak.decay_beta_0 0.0074()
_peak.decay_beta_1 0.017()
```

In `experiments/wish_5_6.edi`, add `()` after the values the stage frees:

```edi
_peak.rise_alpha_0 -0.012()
_peak.rise_alpha_1 0.14()
_peak.decay_beta_0 0.0077()
_peak.decay_beta_1 0.012()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ncaf-wish, 5 banks (wish_1_10, wish_2_9, wish_3_8, wish_4_7, wish_5_6), 18973 pts fitted / 20475 loaded, 165 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.97        31.24
      1      1.106     10.41        17.36   44.4% ↓
      2      1.220     10.30        17.00   2.1% ↓
      3      1.337     10.26        16.85   0.9% ↓
      4      1.457     10.24        16.80   0.3% ↓
      5      1.592     10.23        16.78   0.1% ↓
      6      1.729     10.23        16.77   
      7      1.854     10.23        16.77   
      8      1.989     10.23        16.77   
      9      2.149     10.23        16.77   
     10      2.265     10.23        16.77   
     11      2.393     10.23        16.77   
     12      2.601     10.23        16.77   
  done · converged · 12 iters · reduced χ² 16.77 · Rwp 10.23 % · 2.82 s

  per-bank Rwp (%):   wish_1_10 6.08   wish_2_9 9.21   wish_3_8 10.49   wish_4_7 10.60   wish_5_6 10.89

  refined parameters (165 free):
  name             parameter                                                       start        value      s.u.   change
  intensity        experiments[wish_1_10].background[10].intensity                   230          230        24   0.1% ↑
  intensity        experiments[wish_1_10].background[11].intensity                   255          255        17   
  intensity        experiments[wish_1_10].background[12].intensity                   246          246        15   
  intensity        experiments[wish_1_10].background[13].intensity                   224          224        12   0.2% ↓
  intensity        experiments[wish_1_10].background[14].intensity                   258        258.0       9.8   
  intensity        experiments[wish_1_10].background[15].intensity                 247.3        247.3       6.8   
  intensity        experiments[wish_1_10].background[16].intensity                 227.2        227.2       5.4   
  intensity        experiments[wish_1_10].background[17].intensity                 236.8        236.8       4.3   
  intensity        experiments[wish_1_10].background[18].intensity                 226.7        226.7       3.8   
  intensity        experiments[wish_1_10].background[19].intensity                 223.4        223.4       3.8   
  intensity        experiments[wish_1_10].background[20].intensity                 219.8        219.8       3.7   
  intensity        experiments[wish_1_10].background[21].intensity                 223.6        223.6       2.8   
  intensity        experiments[wish_1_10].background[22].intensity                 216.6        216.6       2.7   
  intensity        experiments[wish_1_10].background[23].intensity                 216.8        216.8       3.2   
  intensity        experiments[wish_1_10].background[24].intensity                 213.5        213.5       3.5   
  intensity        experiments[wish_1_10].background[25].intensity                 216.2        216.2       3.9   
  intensity        experiments[wish_1_10].background[26].intensity                   213        213.0       4.4   
  intensity        experiments[wish_1_10].background[27].intensity                 212.4        212.4       5.2   
  intensity        experiments[wish_1_10].background[28].intensity                 212.6        212.6       6.0   
  intensity        experiments[wish_1_10].background[29].intensity                 211.3        211.3       7.3   
  intensity        experiments[wish_1_10].background[2].intensity                    110          108        89   2.0% ↓
  intensity        experiments[wish_1_10].background[30].intensity                   211        211.0       9.0   
  intensity        experiments[wish_1_10].background[31].intensity                   223          223        12   
  intensity        experiments[wish_1_10].background[32].intensity                   210          210        16   0.2% ↑
  intensity        experiments[wish_1_10].background[33].intensity                   222          222        23   0.1% ↑
  intensity        experiments[wish_1_10].background[34].intensity                   255          255        35   
  intensity        experiments[wish_1_10].background[35].intensity                   120          120        46   0.3% ↓
  intensity        experiments[wish_1_10].background[3].intensity                    161          161        59   0.2% ↓
  intensity        experiments[wish_1_10].background[4].intensity                    120          120        58   
  intensity        experiments[wish_1_10].background[5].intensity                    322          322        70   0.1% ↑
  intensity        experiments[wish_1_10].background[6].intensity                    259          259        47   0.2% ↑
  intensity        experiments[wish_1_10].background[7].intensity                    234          234        48   0.2% ↓
  intensity        experiments[wish_1_10].background[8].intensity                    229          229        40   0.1% ↓
  intensity        experiments[wish_1_10].background[9].intensity                    239          239        30   0.1% ↓
  TOF linear, µs/Å experiments[wish_1_10].instrument.calib_d_to_tof_linear        4.99e3     4.9851e3  0.0012e3   
  TOF offset, µs   experiments[wish_1_10].instrument.calib_d_to_tof_offset          14.5         14.5       4.5   0.2% ↓
  scale            experiments[wish_1_10].linked_structures[ncaf].scale            30.36        30.36      0.34   
  intensity        experiments[wish_2_9].background[10].intensity                  286.9        264.8       4.1   7.7% ↓
  intensity        experiments[wish_2_9].background[11].intensity                  284.6        272.7       4.0   4.2% ↓
  intensity        experiments[wish_2_9].background[12].intensity                  267.7        259.5       2.9   3.1% ↓
  intensity        experiments[wish_2_9].background[13].intensity                  259.4        250.8       2.4   3.3% ↓
  intensity        experiments[wish_2_9].background[14].intensity                  251.7        239.1       2.2   5.0% ↓
  intensity        experiments[wish_2_9].background[15].intensity                  232.1        227.6       2.1   1.9% ↓
  intensity        experiments[wish_2_9].background[16].intensity                  222.7        217.4       2.6   2.4% ↓
  intensity        experiments[wish_2_9].background[17].intensity                  219.9        220.7       3.4   0.3% ↑
  intensity        experiments[wish_2_9].background[18].intensity                  227.1        222.8       4.7   1.9% ↓
  intensity        experiments[wish_2_9].background[19].intensity                  218.4        220.0       6.4   0.7% ↑
  intensity        experiments[wish_2_9].background[1].intensity                     125          104        61   16.8% ↓
  intensity        experiments[wish_2_9].background[20].intensity                    220        219.5       9.7   0.2% ↓
  intensity        experiments[wish_2_9].background[21].intensity                    219          219        17   
  intensity        experiments[wish_2_9].background[22].intensity                    164          164        41   0.1% ↑
  intensity        experiments[wish_2_9].background[2].intensity                     222          193        46   13.1% ↓
  intensity        experiments[wish_2_9].background[3].intensity                     348          308        32   11.4% ↓
  intensity        experiments[wish_2_9].background[4].intensity                     391          367        20   6.0% ↓
  intensity        experiments[wish_2_9].background[5].intensity                     355          320        15   9.8% ↓
  intensity        experiments[wish_2_9].background[6].intensity                     345          323        12   6.4% ↓
  intensity        experiments[wish_2_9].background[7].intensity                     393          335        10   14.8% ↓
  intensity        experiments[wish_2_9].background[8].intensity                     417        387.7       7.9   7.0% ↓
  intensity        experiments[wish_2_9].background[9].intensity                   404.8        357.2       5.7   11.8% ↓
  TOF linear, µs/Å experiments[wish_2_9].instrument.calib_d_to_tof_linear         1.04e4   1.040109e40.000050e4   0.1% ↑
  TOF offset, µs   experiments[wish_2_9].instrument.calib_d_to_tof_offset          13.26        -2.63      0.95   119.8% ↓
  scale            experiments[wish_2_9].linked_structures[ncaf].scale             30.86        33.75      0.13   9.4% ↑
  β₀               experiments[wish_2_9].peak.decay_beta_0                        0.0061     0.005005  0.000046   17.9% ↓
  β₁               experiments[wish_2_9].peak.decay_beta_1                         0.096       0.0798    0.0017   16.8% ↓
  α₀               experiments[wish_2_9].peak.rise_alpha_0                         0.053     -0.00418   0.00054   107.9% ↓
  α₁               experiments[wish_2_9].peak.rise_alpha_1                         0.031       0.0815    0.0021   162.9% ↑
  intensity        experiments[wish_3_8].background[10].intensity                  376.4        347.5       3.8   7.7% ↓
  intensity        experiments[wish_3_8].background[11].intensity                  343.2        313.3       3.5   8.7% ↓
  intensity        experiments[wish_3_8].background[12].intensity                  298.4        272.0       3.0   8.8% ↓
  intensity        experiments[wish_3_8].background[13].intensity                  264.9        257.6       2.6   2.7% ↓
  intensity        experiments[wish_3_8].background[14].intensity                    257        253.5       2.6   1.4% ↓
  intensity        experiments[wish_3_8].background[15].intensity                  242.5        233.6       2.8   3.7% ↓
  intensity        experiments[wish_3_8].background[16].intensity                  250.9        244.9       3.2   2.4% ↓
  intensity        experiments[wish_3_8].background[17].intensity                  239.5        237.3       3.8   0.9% ↓
  intensity        experiments[wish_3_8].background[18].intensity                  245.9        238.5       5.5   3.0% ↓
  intensity        experiments[wish_3_8].background[19].intensity                    240        242.2       7.5   0.9% ↑
  intensity        experiments[wish_3_8].background[1].intensity                     330          318        45   3.7% ↓
  intensity        experiments[wish_3_8].background[20].intensity                    236          236        11   0.1% ↑
  intensity        experiments[wish_3_8].background[21].intensity                    239          230        18   3.8% ↓
  intensity        experiments[wish_3_8].background[22].intensity                    243          237        42   2.6% ↓
  intensity        experiments[wish_3_8].background[2].intensity                     430          387        29   9.9% ↓
  intensity        experiments[wish_3_8].background[3].intensity                     392          365        20   6.9% ↓
  intensity        experiments[wish_3_8].background[4].intensity                     455          397        14   12.6% ↓
  intensity        experiments[wish_3_8].background[5].intensity                     396        360.6       8.9   8.9% ↓
  intensity        experiments[wish_3_8].background[6].intensity                     382        347.2       6.7   9.1% ↓
  intensity        experiments[wish_3_8].background[7].intensity                   360.5        321.2       5.9   10.9% ↓
  intensity        experiments[wish_3_8].background[8].intensity                   341.4        316.8       5.0   7.2% ↓
  intensity        experiments[wish_3_8].background[9].intensity                   354.1        302.2       4.4   14.7% ↓
  TOF linear, µs/Å experiments[wish_3_8].instrument.calib_d_to_tof_linear         1.51e4   1.510844e40.000037e4   
  TOF offset, µs   experiments[wish_3_8].instrument.calib_d_to_tof_offset          -10.7       -15.94      0.63   49.0% ↓
  scale            experiments[wish_3_8].linked_structures[ncaf].scale             31.56       34.145     0.089   8.2% ↑
  β₀               experiments[wish_3_8].peak.decay_beta_0                        0.0069     0.006021  0.000038   12.7% ↓
  β₁               experiments[wish_3_8].peak.decay_beta_1                         0.032      0.02170   0.00049   32.2% ↓
  α₀               experiments[wish_3_8].peak.rise_alpha_0                        -0.016     -0.00968   0.00040   39.5% ↑
  α₁               experiments[wish_3_8].peak.rise_alpha_1                          0.16       0.0967    0.0015   39.5% ↓
  intensity        experiments[wish_4_7].background[10].intensity                  367.9        343.0       7.0   6.8% ↓
  intensity        experiments[wish_4_7].background[11].intensity                  417.3        383.5       6.1   8.1% ↓
  intensity        experiments[wish_4_7].background[12].intensity                  381.3        344.3       5.1   9.7% ↓
  intensity        experiments[wish_4_7].background[13].intensity                  367.8        328.0       4.6   10.8% ↓
  intensity        experiments[wish_4_7].background[14].intensity                  350.8        325.5       4.1   7.2% ↓
  intensity        experiments[wish_4_7].background[15].intensity                  306.9        279.5       4.0   8.9% ↓
  intensity        experiments[wish_4_7].background[16].intensity                  402.7        343.0       4.8   14.8% ↓
  intensity        experiments[wish_4_7].background[17].intensity                  328.9        315.6       3.8   4.0% ↓
  intensity        experiments[wish_4_7].background[18].intensity                    330        303.1       3.2   8.2% ↓
  intensity        experiments[wish_4_7].background[19].intensity                  264.5        251.2       3.0   5.0% ↓
  intensity        experiments[wish_4_7].background[1].intensity                     378          369        51   2.4% ↓
  intensity        experiments[wish_4_7].background[20].intensity                  268.3        262.3       3.6   2.2% ↓
  intensity        experiments[wish_4_7].background[21].intensity                  252.8        245.8       3.8   2.8% ↓
  intensity        experiments[wish_4_7].background[22].intensity                  264.7        263.7       3.6   0.4% ↓
  intensity        experiments[wish_4_7].background[23].intensity                  258.7        249.7       3.9   3.5% ↓
  intensity        experiments[wish_4_7].background[24].intensity                  263.5        259.9       4.7   1.4% ↓
  intensity        experiments[wish_4_7].background[25].intensity                  262.2        260.3       5.9   0.7% ↓
  intensity        experiments[wish_4_7].background[26].intensity                    255        249.5       7.7   2.1% ↓
  intensity        experiments[wish_4_7].background[27].intensity                    264          255        14   3.4% ↓
  intensity        experiments[wish_4_7].background[28].intensity                    238          244        35   2.4% ↑
  intensity        experiments[wish_4_7].background[2].intensity                     452          424        37   6.1% ↓
  intensity        experiments[wish_4_7].background[3].intensity                     419          401        28   4.2% ↓
  intensity        experiments[wish_4_7].background[4].intensity                     476          416        24   12.5% ↓
  intensity        experiments[wish_4_7].background[5].intensity                     493          453        18   8.1% ↓
  intensity        experiments[wish_4_7].background[6].intensity                     411          375        14   8.7% ↓
  intensity        experiments[wish_4_7].background[7].intensity                     445          395        13   11.2% ↓
  intensity        experiments[wish_4_7].background[8].intensity                     399          364        11   8.9% ↓
  intensity        experiments[wish_4_7].background[9].intensity                     492          395        11   19.7% ↓
  TOF linear, µs/Å experiments[wish_4_7].instrument.calib_d_to_tof_linear         1.87e4   1.866337e40.000033e4   
  TOF offset, µs   experiments[wish_4_7].instrument.calib_d_to_tof_offset         -13.17       -19.14      0.52   45.3% ↓
  scale            experiments[wish_4_7].linked_structures[ncaf].scale            30.877       33.523     0.084   8.6% ↑
  β₀               experiments[wish_4_7].peak.decay_beta_0                        0.0074     0.006578  0.000033   11.1% ↓
  β₁               experiments[wish_4_7].peak.decay_beta_1                         0.017      0.00936   0.00024   45.0% ↓
  α₀               experiments[wish_4_7].peak.rise_alpha_0                        -0.015     -0.01025   0.00053   31.7% ↑
  α₁               experiments[wish_4_7].peak.rise_alpha_1                          0.16       0.1018    0.0016   36.4% ↓
  intensity        experiments[wish_5_6].background[10].intensity                    474          371        13   21.7% ↓
  intensity        experiments[wish_5_6].background[11].intensity                    465        391.2       8.9   15.9% ↓
  intensity        experiments[wish_5_6].background[12].intensity                  361.8        337.4       5.8   6.7% ↓
  intensity        experiments[wish_5_6].background[13].intensity                  414.5        381.7       5.3   7.9% ↓
  intensity        experiments[wish_5_6].background[14].intensity                  378.4        344.1       4.4   9.1% ↓
  intensity        experiments[wish_5_6].background[15].intensity                  366.1        329.5       3.9   10.0% ↓
  intensity        experiments[wish_5_6].background[16].intensity                  340.8        318.7       3.6   6.5% ↓
  intensity        experiments[wish_5_6].background[17].intensity                  328.3        289.3       3.5   11.9% ↓
  intensity        experiments[wish_5_6].background[18].intensity                  344.3        323.9       3.5   5.9% ↓
  intensity        experiments[wish_5_6].background[19].intensity                  317.9        298.7       3.4   6.0% ↓
  intensity        experiments[wish_5_6].background[1].intensity                     503          475        31   5.6% ↓
  intensity        experiments[wish_5_6].background[20].intensity                  286.3        266.2       3.6   7.0% ↓
  intensity        experiments[wish_5_6].background[21].intensity                  262.3        254.7       3.7   2.9% ↓
  intensity        experiments[wish_5_6].background[22].intensity                  269.8        264.2       3.8   2.1% ↓
  intensity        experiments[wish_5_6].background[23].intensity                  265.4        260.2       4.1   2.0% ↓
  intensity        experiments[wish_5_6].background[24].intensity                  261.7        261.9       4.9   0.1% ↑
  intensity        experiments[wish_5_6].background[25].intensity                  275.1        262.0       6.0   4.8% ↓
  intensity        experiments[wish_5_6].background[26].intensity                  270.9        269.8       5.8   0.4% ↓
  intensity        experiments[wish_5_6].background[27].intensity                  276.6        271.5       7.3   1.8% ↓
  intensity        experiments[wish_5_6].background[28].intensity                    255          259        16   1.7% ↑
  intensity        experiments[wish_5_6].background[2].intensity                     437          412        23   5.7% ↓
  intensity        experiments[wish_5_6].background[3].intensity                     377          377        41   
  intensity        experiments[wish_5_6].background[4].intensity                     480          435        19   9.3% ↓
  intensity        experiments[wish_5_6].background[5].intensity                     505          446        17   11.8% ↓
  intensity        experiments[wish_5_6].background[6].intensity                     467          427        14   8.5% ↓
  intensity        experiments[wish_5_6].background[7].intensity                     405          372        11   8.1% ↓
  intensity        experiments[wish_5_6].background[8].intensity                     454          394        10   13.2% ↓
  intensity        experiments[wish_5_6].background[9].intensity                     384        377.7       9.4   1.6% ↓
  TOF linear, µs/Å experiments[wish_5_6].instrument.calib_d_to_tof_linear         2.08e4   2.077510e40.000031e4   
  TOF offset, µs   experiments[wish_5_6].instrument.calib_d_to_tof_offset         -11.45       -16.64      0.46   45.4% ↓
  scale            experiments[wish_5_6].linked_structures[ncaf].scale            30.983       33.583     0.083   8.4% ↑
  β₀               experiments[wish_5_6].peak.decay_beta_0                        0.0077     0.006825  0.000031   11.4% ↓
  β₁               experiments[wish_5_6].peak.decay_beta_1                         0.012      0.00599   0.00017   50.1% ↓
  α₀               experiments[wish_5_6].peak.rise_alpha_0                        -0.012     -0.00907   0.00073   24.4% ↑
  α₁               experiments[wish_5_6].peak.rise_alpha_1                          0.14       0.0991    0.0018   29.2% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Gaussian widths

The Gaussian width terms the banks' data determine.

In `experiments/wish_2_9.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_1 34()
_peak.broad_gauss_sigma_2 11()
```

In `experiments/wish_3_8.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_1 30()
_peak.broad_gauss_sigma_2 8.3()
```

In `experiments/wish_4_7.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_1 14()
_peak.broad_gauss_sigma_2 8.9()
```

In `experiments/wish_5_6.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_2 7.7()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ncaf-wish, 5 banks (wish_1_10, wish_2_9, wish_3_8, wish_4_7, wish_5_6), 18973 pts fitted / 20475 loaded, 172 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       10.23        16.78
      1      1.003     10.00        16.02   4.5% ↓
      2      1.134     10.00        16.02   
      3      1.265     10.00        16.02   
      4      1.399     10.00        16.02   
      5      1.549     10.00        16.02   
      6      1.707     10.00        16.02   
      7      1.843     10.00        16.01   
      8      1.977      9.99        16.00   0.1% ↓
      9      2.108      9.99        15.98   0.2% ↓
     10      2.247      9.98        15.96   0.1% ↓
     11      2.385      9.97        15.93   0.2% ↓
     12      2.553      9.97        15.93   
     13      2.753      9.97        15.93   
  done · converged · 13 iters · reduced χ² 15.93 · Rwp 9.97 % · 2.98 s

  per-bank Rwp (%):   wish_1_10 6.08   wish_2_9 8.65   wish_3_8 10.15   wish_4_7 10.36   wish_5_6 10.77

  refined parameters (172 free):
  name             parameter                                                       start        value      s.u.   change
  intensity        experiments[wish_1_10].background[10].intensity                   230          230        24   0.1% ↑
  intensity        experiments[wish_1_10].background[11].intensity                   255          255        17   
  intensity        experiments[wish_1_10].background[12].intensity                   246          246        15   
  intensity        experiments[wish_1_10].background[13].intensity                   224          224        12   0.2% ↓
  intensity        experiments[wish_1_10].background[14].intensity                   258        258.0       9.5   
  intensity        experiments[wish_1_10].background[15].intensity                 247.3        247.3       6.6   
  intensity        experiments[wish_1_10].background[16].intensity                 227.2        227.2       5.3   
  intensity        experiments[wish_1_10].background[17].intensity                 236.8        236.8       4.2   
  intensity        experiments[wish_1_10].background[18].intensity                 226.7        226.7       3.7   
  intensity        experiments[wish_1_10].background[19].intensity                 223.4        223.4       3.7   
  intensity        experiments[wish_1_10].background[20].intensity                 219.8        219.8       3.6   
  intensity        experiments[wish_1_10].background[21].intensity                 223.6        223.6       2.7   
  intensity        experiments[wish_1_10].background[22].intensity                 216.6        216.6       2.7   
  intensity        experiments[wish_1_10].background[23].intensity                 216.8        216.8       3.1   
  intensity        experiments[wish_1_10].background[24].intensity                 213.5        213.5       3.4   
  intensity        experiments[wish_1_10].background[25].intensity                 216.2        216.2       3.8   
  intensity        experiments[wish_1_10].background[26].intensity                   213        213.0       4.3   
  intensity        experiments[wish_1_10].background[27].intensity                 212.4        212.4       5.1   
  intensity        experiments[wish_1_10].background[28].intensity                 212.6        212.6       5.9   
  intensity        experiments[wish_1_10].background[29].intensity                 211.3        211.3       7.1   
  intensity        experiments[wish_1_10].background[2].intensity                    108          108        86   0.2% ↓
  intensity        experiments[wish_1_10].background[30].intensity                   211        211.0       8.8   
  intensity        experiments[wish_1_10].background[31].intensity                   223          223        12   
  intensity        experiments[wish_1_10].background[32].intensity                   210          210        15   0.2% ↑
  intensity        experiments[wish_1_10].background[33].intensity                   222          222        23   0.1% ↑
  intensity        experiments[wish_1_10].background[34].intensity                   255          255        35   
  intensity        experiments[wish_1_10].background[35].intensity                   120          120        45   0.3% ↓
  intensity        experiments[wish_1_10].background[3].intensity                    161          161        58   0.2% ↓
  intensity        experiments[wish_1_10].background[4].intensity                    120          120        56   
  intensity        experiments[wish_1_10].background[5].intensity                    322          322        68   0.1% ↑
  intensity        experiments[wish_1_10].background[6].intensity                    259          259        46   0.2% ↑
  intensity        experiments[wish_1_10].background[7].intensity                    234          234        47   0.2% ↓
  intensity        experiments[wish_1_10].background[8].intensity                    229          229        39   0.1% ↓
  intensity        experiments[wish_1_10].background[9].intensity                    239          239        29   0.1% ↓
  TOF linear, µs/Å experiments[wish_1_10].instrument.calib_d_to_tof_linear        4.99e3     4.9851e3  0.0012e3   
  TOF offset, µs   experiments[wish_1_10].instrument.calib_d_to_tof_offset          14.5         14.5       4.3   0.2% ↓
  scale            experiments[wish_1_10].linked_structures[ncaf].scale            30.36        30.36      0.33   
  intensity        experiments[wish_2_9].background[10].intensity                  264.8        268.7       4.0   1.5% ↑
  intensity        experiments[wish_2_9].background[11].intensity                  272.7        275.1       3.9   0.9% ↑
  intensity        experiments[wish_2_9].background[12].intensity                  259.5        260.9       2.9   0.5% ↑
  intensity        experiments[wish_2_9].background[13].intensity                  250.8        252.7       2.4   0.8% ↑
  intensity        experiments[wish_2_9].background[14].intensity                  239.1        241.9       2.2   1.2% ↑
  intensity        experiments[wish_2_9].background[15].intensity                  227.6        227.8       2.1   0.1% ↑
  intensity        experiments[wish_2_9].background[16].intensity                  217.4        217.5       2.5   0.1% ↑
  intensity        experiments[wish_2_9].background[17].intensity                  220.7        220.4       3.3   0.1% ↓
  intensity        experiments[wish_2_9].background[18].intensity                  222.8        221.4       4.6   0.6% ↓
  intensity        experiments[wish_2_9].background[19].intensity                    220        220.6       6.2   0.3% ↑
  intensity        experiments[wish_2_9].background[1].intensity                     104           96        59   7.5% ↓
  intensity        experiments[wish_2_9].background[20].intensity                  219.5        219.3       9.5   0.1% ↓
  intensity        experiments[wish_2_9].background[21].intensity                    219          219        17   
  intensity        experiments[wish_2_9].background[22].intensity                    164          164        40   0.1% ↑
  intensity        experiments[wish_2_9].background[2].intensity                     193          205        45   6.3% ↑
  intensity        experiments[wish_2_9].background[3].intensity                     308          278        32   9.7% ↓
  intensity        experiments[wish_2_9].background[4].intensity                     367          359        19   2.1% ↓
  intensity        experiments[wish_2_9].background[5].intensity                     320          315        14   1.4% ↓
  intensity        experiments[wish_2_9].background[6].intensity                     323          322        12   0.3% ↓
  intensity        experiments[wish_2_9].background[7].intensity                     335        339.4       9.8   1.3% ↑
  intensity        experiments[wish_2_9].background[8].intensity                   387.7        391.8       7.7   1.1% ↑
  intensity        experiments[wish_2_9].background[9].intensity                   357.2        367.3       5.6   2.8% ↑
  TOF linear, µs/Å experiments[wish_2_9].instrument.calib_d_to_tof_linear         1.04e4   1.038768e40.000066e4   0.1% ↓
  TOF offset, µs   experiments[wish_2_9].instrument.calib_d_to_tof_offset          -2.63         19.5       1.5   842.0% ↑
  scale            experiments[wish_2_9].linked_structures[ncaf].scale             33.75        33.52      0.12   0.7% ↓
  σ₁², µs²/Å²      experiments[wish_2_9].peak.broad_gauss_sigma_1                     34           52        14   51.5% ↑
  σ₂², µs²/Å⁴      experiments[wish_2_9].peak.broad_gauss_sigma_2                     11        25.73      0.99   133.9% ↑
  β₀               experiments[wish_2_9].peak.decay_beta_0                      0.005005     0.005370  0.000061   7.3% ↑
  β₁               experiments[wish_2_9].peak.decay_beta_1                        0.0798       0.0797    0.0021   0.1% ↓
  α₀               experiments[wish_2_9].peak.rise_alpha_0                      -0.00418       0.0573    0.0049   1.47e3 % ↑
  α₁               experiments[wish_2_9].peak.rise_alpha_1                        0.0815      -0.0185    0.0064   122.7% ↓
  intensity        experiments[wish_3_8].background[10].intensity                  347.5        351.5       3.7   1.2% ↑
  intensity        experiments[wish_3_8].background[11].intensity                  313.3        318.4       3.4   1.6% ↑
  intensity        experiments[wish_3_8].background[12].intensity                    272        275.8       3.0   1.4% ↑
  intensity        experiments[wish_3_8].background[13].intensity                  257.6        258.5       2.6   0.4% ↑
  intensity        experiments[wish_3_8].background[14].intensity                  253.5        253.7       2.6   0.1% ↑
  intensity        experiments[wish_3_8].background[15].intensity                  233.6        234.9       2.7   0.6% ↑
  intensity        experiments[wish_3_8].background[16].intensity                  244.9        245.4       3.1   0.2% ↑
  intensity        experiments[wish_3_8].background[17].intensity                  237.3        237.5       3.7   0.1% ↑
  intensity        experiments[wish_3_8].background[18].intensity                  238.5        238.6       5.4   
  intensity        experiments[wish_3_8].background[19].intensity                  242.2        242.3       7.3   
  intensity        experiments[wish_3_8].background[1].intensity                     318          319        44   0.4% ↑
  intensity        experiments[wish_3_8].background[20].intensity                    236          236        11   0.2% ↓
  intensity        experiments[wish_3_8].background[21].intensity                    230          234        18   1.7% ↑
  intensity        experiments[wish_3_8].background[22].intensity                    237          234        41   1.2% ↓
  intensity        experiments[wish_3_8].background[2].intensity                     387          388        28   0.2% ↑
  intensity        experiments[wish_3_8].background[3].intensity                     365          365        19   0.1% ↓
  intensity        experiments[wish_3_8].background[4].intensity                     397          397        14   0.1% ↑
  intensity        experiments[wish_3_8].background[5].intensity                   360.6        360.3       8.6   0.1% ↓
  intensity        experiments[wish_3_8].background[6].intensity                   347.2        348.1       6.5   0.2% ↑
  intensity        experiments[wish_3_8].background[7].intensity                   321.2        322.3       5.8   0.4% ↑
  intensity        experiments[wish_3_8].background[8].intensity                   316.8        318.3       4.8   0.5% ↑
  intensity        experiments[wish_3_8].background[9].intensity                   302.2        307.5       4.3   1.7% ↑
  TOF linear, µs/Å experiments[wish_3_8].instrument.calib_d_to_tof_linear         1.51e4   1.510705e40.000044e4   
  TOF offset, µs   experiments[wish_3_8].instrument.calib_d_to_tof_offset         -15.94       -16.31      0.69   2.3% ↓
  scale            experiments[wish_3_8].linked_structures[ncaf].scale            34.145       33.985     0.087   0.5% ↓
  σ₁², µs²/Å²      experiments[wish_3_8].peak.broad_gauss_sigma_1                     30         55.4       7.1   84.7% ↑
  σ₂², µs²/Å⁴      experiments[wish_3_8].peak.broad_gauss_sigma_2                    8.3         18.5       1.1   122.8% ↑
  β₀               experiments[wish_3_8].peak.decay_beta_0                      0.006021     0.006318  0.000043   4.9% ↑
  β₁               experiments[wish_3_8].peak.decay_beta_1                        0.0217      0.02048   0.00053   5.6% ↓
  α₀               experiments[wish_3_8].peak.rise_alpha_0                      -0.00968     -0.01093   0.00087   12.9% ↓
  α₁               experiments[wish_3_8].peak.rise_alpha_1                        0.0967       0.1185    0.0038   22.6% ↑
  intensity        experiments[wish_4_7].background[10].intensity                    343        343.2       6.8   0.1% ↑
  intensity        experiments[wish_4_7].background[11].intensity                  383.5        384.7       6.0   0.3% ↑
  intensity        experiments[wish_4_7].background[12].intensity                  344.3        345.9       5.0   0.5% ↑
  intensity        experiments[wish_4_7].background[13].intensity                    328        329.8       4.5   0.5% ↑
  intensity        experiments[wish_4_7].background[14].intensity                  325.5        327.4       4.0   0.6% ↑
  intensity        experiments[wish_4_7].background[15].intensity                  279.5        281.4       3.9   0.7% ↑
  intensity        experiments[wish_4_7].background[16].intensity                    343        349.7       4.7   1.9% ↑
  intensity        experiments[wish_4_7].background[17].intensity                  315.6        317.4       3.7   0.6% ↑
  intensity        experiments[wish_4_7].background[18].intensity                  303.1        306.7       3.1   1.2% ↑
  intensity        experiments[wish_4_7].background[19].intensity                  251.2        252.5       3.0   0.5% ↑
  intensity        experiments[wish_4_7].background[1].intensity                     369          370        49   0.3% ↑
  intensity        experiments[wish_4_7].background[20].intensity                  262.3        262.7       3.5   0.2% ↑
  intensity        experiments[wish_4_7].background[21].intensity                  245.8        246.3       3.7   0.2% ↑
  intensity        experiments[wish_4_7].background[22].intensity                  263.7        263.5       3.5   0.1% ↓
  intensity        experiments[wish_4_7].background[23].intensity                  249.7        250.4       3.8   0.3% ↑
  intensity        experiments[wish_4_7].background[24].intensity                  259.9        260.0       4.6   
  intensity        experiments[wish_4_7].background[25].intensity                  260.3        260.2       5.7   
  intensity        experiments[wish_4_7].background[26].intensity                  249.5        250.0       7.5   0.2% ↑
  intensity        experiments[wish_4_7].background[27].intensity                    255          254        14   0.3% ↓
  intensity        experiments[wish_4_7].background[28].intensity                    244          244        34   0.1% ↑
  intensity        experiments[wish_4_7].background[2].intensity                     424          425        37   0.3% ↑
  intensity        experiments[wish_4_7].background[3].intensity                     401          402        28   0.2% ↑
  intensity        experiments[wish_4_7].background[4].intensity                     416          417        23   0.2% ↑
  intensity        experiments[wish_4_7].background[5].intensity                     453          453        18   
  intensity        experiments[wish_4_7].background[6].intensity                     375          375        14   0.1% ↑
  intensity        experiments[wish_4_7].background[7].intensity                     395          395        12   0.1% ↓
  intensity        experiments[wish_4_7].background[8].intensity                     364          364        11   0.1% ↑
  intensity        experiments[wish_4_7].background[9].intensity                     395          397        11   0.4% ↑
  TOF linear, µs/Å experiments[wish_4_7].instrument.calib_d_to_tof_linear         1.87e4   1.866214e40.000039e4   
  TOF offset, µs   experiments[wish_4_7].instrument.calib_d_to_tof_offset         -19.14       -19.00      0.56   0.7% ↑
  scale            experiments[wish_4_7].linked_structures[ncaf].scale            33.523       33.405     0.082   0.4% ↓
  σ₁², µs²/Å²      experiments[wish_4_7].peak.broad_gauss_sigma_1                     14         21.7       5.6   55.0% ↑
  σ₂², µs²/Å⁴      experiments[wish_4_7].peak.broad_gauss_sigma_2                    8.9         19.7       1.2   121.0% ↑
  β₀               experiments[wish_4_7].peak.decay_beta_0                      0.006578     0.006780  0.000036   3.1% ↑
  β₁               experiments[wish_4_7].peak.decay_beta_1                       0.00936      0.00888   0.00025   5.1% ↓
  α₀               experiments[wish_4_7].peak.rise_alpha_0                      -0.01025      -0.0095    0.0011   7.1% ↑
  α₁               experiments[wish_4_7].peak.rise_alpha_1                        0.1018       0.1155    0.0034   13.4% ↑
  intensity        experiments[wish_5_6].background[10].intensity                    371          371        12   
  intensity        experiments[wish_5_6].background[11].intensity                  391.2        392.4       8.7   0.3% ↑
  intensity        experiments[wish_5_6].background[12].intensity                  337.4        337.7       5.7   0.1% ↑
  intensity        experiments[wish_5_6].background[13].intensity                  381.7        382.5       5.2   0.2% ↑
  intensity        experiments[wish_5_6].background[14].intensity                  344.1        345.2       4.3   0.3% ↑
  intensity        experiments[wish_5_6].background[15].intensity                  329.5        330.8       3.8   0.4% ↑
  intensity        experiments[wish_5_6].background[16].intensity                  318.7        319.8       3.5   0.3% ↑
  intensity        experiments[wish_5_6].background[17].intensity                  289.3        291.9       3.5   0.9% ↑
  intensity        experiments[wish_5_6].background[18].intensity                  323.9        325.7       3.4   0.5% ↑
  intensity        experiments[wish_5_6].background[19].intensity                  298.7        300.5       3.4   0.6% ↑
  intensity        experiments[wish_5_6].background[1].intensity                     475          475        30   
  intensity        experiments[wish_5_6].background[20].intensity                  266.2        267.7       3.5   0.6% ↑
  intensity        experiments[wish_5_6].background[21].intensity                  254.7        255.1       3.6   0.1% ↑
  intensity        experiments[wish_5_6].background[22].intensity                  264.2        264.4       3.7   0.1% ↑
  intensity        experiments[wish_5_6].background[23].intensity                  260.2        260.3       4.0   
  intensity        experiments[wish_5_6].background[24].intensity                  261.9        261.8       4.8   0.1% ↓
  intensity        experiments[wish_5_6].background[25].intensity                    262        262.8       5.8   0.3% ↑
  intensity        experiments[wish_5_6].background[26].intensity                  269.8        269.7       5.6   
  intensity        experiments[wish_5_6].background[27].intensity                  271.5        271.5       7.1   
  intensity        experiments[wish_5_6].background[28].intensity                    259          259        15   0.2% ↑
  intensity        experiments[wish_5_6].background[2].intensity                     412          412        23   0.1% ↑
  intensity        experiments[wish_5_6].background[3].intensity                     377          377        40   
  intensity        experiments[wish_5_6].background[4].intensity                     435          435        19   
  intensity        experiments[wish_5_6].background[5].intensity                     446          445        17   0.2% ↓
  intensity        experiments[wish_5_6].background[6].intensity                     427          428        14   0.1% ↑
  intensity        experiments[wish_5_6].background[7].intensity                     372          372        11   
  intensity        experiments[wish_5_6].background[8].intensity                     394        394.1       9.8   
  intensity        experiments[wish_5_6].background[9].intensity                   377.7        378.5       9.2   0.2% ↑
  TOF linear, µs/Å experiments[wish_5_6].instrument.calib_d_to_tof_linear         2.08e4   2.077460e40.000035e4   
  TOF offset, µs   experiments[wish_5_6].instrument.calib_d_to_tof_offset         -16.64       -16.72      0.50   0.5% ↓
  scale            experiments[wish_5_6].linked_structures[ncaf].scale            33.583       33.506     0.081   0.2% ↓
  σ₂², µs²/Å⁴      experiments[wish_5_6].peak.broad_gauss_sigma_2                    7.7        15.41      0.79   100.2% ↑
  β₀               experiments[wish_5_6].peak.decay_beta_0                      0.006825     0.006956  0.000033   1.9% ↑
  β₁               experiments[wish_5_6].peak.decay_beta_1                       0.00599      0.00573   0.00016   4.3% ↓
  α₀               experiments[wish_5_6].peak.rise_alpha_0                      -0.00907      -0.0075    0.0011   17.7% ↑
  α₁               experiments[wish_5_6].peak.rise_alpha_1                        0.0991       0.1037    0.0023   4.6% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Lorentzian width

Bank 2-9's Lorentzian term.

In `experiments/wish_2_9.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_lorentz_gamma_1 1()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ncaf-wish, 5 banks (wish_1_10, wish_2_9, wish_3_8, wish_4_7, wish_5_6), 18973 pts fitted / 20475 loaded, 173 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        9.97        15.93
      1      0.732      9.97        15.93   
  done · converged · 1 iters · reduced χ² 15.93 · Rwp 9.97 % · 1.01 s

  per-bank Rwp (%):   wish_1_10 6.08   wish_2_9 8.65   wish_3_8 10.15   wish_4_7 10.36   wish_5_6 10.77

  refined parameters (173 free):
  name             parameter                                                       start        value      s.u.   change
  intensity        experiments[wish_1_10].background[10].intensity                   230          230        24   0.1% ↑
  intensity        experiments[wish_1_10].background[11].intensity                   255          255        17   
  intensity        experiments[wish_1_10].background[12].intensity                   246          246        15   
  intensity        experiments[wish_1_10].background[13].intensity                   224          224        12   0.2% ↓
  intensity        experiments[wish_1_10].background[14].intensity                   258        258.0       9.5   
  intensity        experiments[wish_1_10].background[15].intensity                 247.3        247.3       6.6   
  intensity        experiments[wish_1_10].background[16].intensity                 227.2        227.2       5.3   
  intensity        experiments[wish_1_10].background[17].intensity                 236.8        236.8       4.2   
  intensity        experiments[wish_1_10].background[18].intensity                 226.7        226.7       3.7   
  intensity        experiments[wish_1_10].background[19].intensity                 223.4        223.4       3.7   
  intensity        experiments[wish_1_10].background[20].intensity                 219.8        219.8       3.6   
  intensity        experiments[wish_1_10].background[21].intensity                 223.6        223.6       2.7   
  intensity        experiments[wish_1_10].background[22].intensity                 216.6        216.6       2.7   
  intensity        experiments[wish_1_10].background[23].intensity                 216.8        216.8       3.1   
  intensity        experiments[wish_1_10].background[24].intensity                 213.5        213.5       3.4   
  intensity        experiments[wish_1_10].background[25].intensity                 216.2        216.2       3.8   
  intensity        experiments[wish_1_10].background[26].intensity                   213        213.0       4.3   
  intensity        experiments[wish_1_10].background[27].intensity                 212.4        212.4       5.1   
  intensity        experiments[wish_1_10].background[28].intensity                 212.6        212.6       5.9   
  intensity        experiments[wish_1_10].background[29].intensity                 211.3        211.3       7.1   
  intensity        experiments[wish_1_10].background[2].intensity                    108          108        86   0.2% ↓
  intensity        experiments[wish_1_10].background[30].intensity                   211        211.0       8.8   
  intensity        experiments[wish_1_10].background[31].intensity                   223          223        12   
  intensity        experiments[wish_1_10].background[32].intensity                   210          210        15   0.2% ↑
  intensity        experiments[wish_1_10].background[33].intensity                   222          222        23   0.1% ↑
  intensity        experiments[wish_1_10].background[34].intensity                   255          255        35   
  intensity        experiments[wish_1_10].background[35].intensity                   120          120        45   0.3% ↓
  intensity        experiments[wish_1_10].background[3].intensity                    161          161        58   0.2% ↓
  intensity        experiments[wish_1_10].background[4].intensity                    120          120        56   
  intensity        experiments[wish_1_10].background[5].intensity                    322          322        68   0.1% ↑
  intensity        experiments[wish_1_10].background[6].intensity                    259          259        46   0.2% ↑
  intensity        experiments[wish_1_10].background[7].intensity                    234          234        47   0.2% ↓
  intensity        experiments[wish_1_10].background[8].intensity                    229          229        39   0.1% ↓
  intensity        experiments[wish_1_10].background[9].intensity                    239          239        29   0.1% ↓
  TOF linear, µs/Å experiments[wish_1_10].instrument.calib_d_to_tof_linear        4.99e3     4.9851e3  0.0012e3   
  TOF offset, µs   experiments[wish_1_10].instrument.calib_d_to_tof_offset          14.5         14.5       4.3   0.2% ↓
  scale            experiments[wish_1_10].linked_structures[ncaf].scale            30.36        30.36      0.33   
  intensity        experiments[wish_2_9].background[10].intensity                  268.7        268.6       4.0   
  intensity        experiments[wish_2_9].background[11].intensity                  275.1        275.1       3.9   
  intensity        experiments[wish_2_9].background[12].intensity                  260.9        260.8       2.9   
  intensity        experiments[wish_2_9].background[13].intensity                  252.7        252.6       2.4   
  intensity        experiments[wish_2_9].background[14].intensity                  241.9        241.9       2.2   
  intensity        experiments[wish_2_9].background[15].intensity                  227.8        227.8       2.1   
  intensity        experiments[wish_2_9].background[16].intensity                  217.5        217.5       2.5   
  intensity        experiments[wish_2_9].background[17].intensity                  220.4        220.4       3.3   
  intensity        experiments[wish_2_9].background[18].intensity                  221.4        221.4       4.6   
  intensity        experiments[wish_2_9].background[19].intensity                  220.6        220.6       6.2   
  intensity        experiments[wish_2_9].background[1].intensity                      96           96        59   0.1% ↑
  intensity        experiments[wish_2_9].background[20].intensity                  219.3        219.3       9.5   
  intensity        experiments[wish_2_9].background[21].intensity                    219          219        17   
  intensity        experiments[wish_2_9].background[22].intensity                    164          164        40   0.1% ↑
  intensity        experiments[wish_2_9].background[2].intensity                     205          205        45   
  intensity        experiments[wish_2_9].background[3].intensity                     278          278        32   
  intensity        experiments[wish_2_9].background[4].intensity                     359          359        19   
  intensity        experiments[wish_2_9].background[5].intensity                     315          315        14   0.1% ↑
  intensity        experiments[wish_2_9].background[6].intensity                     322          322        12   
  intensity        experiments[wish_2_9].background[7].intensity                   339.4          339        10   0.1% ↓
  intensity        experiments[wish_2_9].background[8].intensity                   391.8        391.6       7.9   0.1% ↓
  intensity        experiments[wish_2_9].background[9].intensity                   367.3        367.0       6.0   0.1% ↓
  TOF linear, µs/Å experiments[wish_2_9].instrument.calib_d_to_tof_linear         1.04e4   1.038767e40.000067e4   
  TOF offset, µs   experiments[wish_2_9].instrument.calib_d_to_tof_offset           19.5         19.5       1.5   0.1% ↓
  scale            experiments[wish_2_9].linked_structures[ncaf].scale             33.52        33.53      0.16   
  σ₁², µs²/Å²      experiments[wish_2_9].peak.broad_gauss_sigma_1                     52           52        14   0.7% ↓
  σ₂², µs²/Å⁴      experiments[wish_2_9].peak.broad_gauss_sigma_2                  25.73         25.6       1.1   0.4% ↓
  γ₁, µs/Å         experiments[wish_2_9].peak.broad_lorentz_gamma_1                    1         1.09      0.68   9.0% ↑
  β₀               experiments[wish_2_9].peak.decay_beta_0                       0.00537     0.005371  0.000063   
  β₁               experiments[wish_2_9].peak.decay_beta_1                        0.0797       0.0798    0.0022   0.2% ↑
  α₀               experiments[wish_2_9].peak.rise_alpha_0                        0.0573       0.0576    0.0055   0.5% ↑
  α₁               experiments[wish_2_9].peak.rise_alpha_1                       -0.0185      -0.0186    0.0066   0.6% ↓
  intensity        experiments[wish_3_8].background[10].intensity                  351.5        351.5       3.7   
  intensity        experiments[wish_3_8].background[11].intensity                  318.4        318.4       3.4   
  intensity        experiments[wish_3_8].background[12].intensity                  275.8        275.8       3.0   
  intensity        experiments[wish_3_8].background[13].intensity                  258.5        258.5       2.6   
  intensity        experiments[wish_3_8].background[14].intensity                  253.7        253.7       2.6   
  intensity        experiments[wish_3_8].background[15].intensity                  234.9        234.9       2.7   
  intensity        experiments[wish_3_8].background[16].intensity                  245.4        245.4       3.1   
  intensity        experiments[wish_3_8].background[17].intensity                  237.5        237.5       3.7   
  intensity        experiments[wish_3_8].background[18].intensity                  238.6        238.6       5.4   
  intensity        experiments[wish_3_8].background[19].intensity                  242.3        242.3       7.3   
  intensity        experiments[wish_3_8].background[1].intensity                     319          319        44   0.1% ↑
  intensity        experiments[wish_3_8].background[20].intensity                    236          236        11   0.2% ↓
  intensity        experiments[wish_3_8].background[21].intensity                    234          234        18   0.1% ↓
  intensity        experiments[wish_3_8].background[22].intensity                    234          234        41   
  intensity        experiments[wish_3_8].background[2].intensity                     388          388        28   
  intensity        experiments[wish_3_8].background[3].intensity                     365          365        19   0.1% ↓
  intensity        experiments[wish_3_8].background[4].intensity                     397          397        14   0.1% ↑
  intensity        experiments[wish_3_8].background[5].intensity                   360.3        360.3       8.6   
  intensity        experiments[wish_3_8].background[6].intensity                   348.1        348.1       6.5   
  intensity        experiments[wish_3_8].background[7].intensity                   322.3        322.3       5.8   
  intensity        experiments[wish_3_8].background[8].intensity                   318.3        318.3       4.8   
  intensity        experiments[wish_3_8].background[9].intensity                   307.5        307.5       4.3   
  TOF linear, µs/Å experiments[wish_3_8].instrument.calib_d_to_tof_linear         1.51e4   1.510705e40.000044e4   
  TOF offset, µs   experiments[wish_3_8].instrument.calib_d_to_tof_offset         -16.31       -16.31      0.69   
  scale            experiments[wish_3_8].linked_structures[ncaf].scale            33.985       33.985     0.087   
  σ₁², µs²/Å²      experiments[wish_3_8].peak.broad_gauss_sigma_1                   55.4         55.4       7.1   
  σ₂², µs²/Å⁴      experiments[wish_3_8].peak.broad_gauss_sigma_2                   18.5         18.5       1.1   
  β₀               experiments[wish_3_8].peak.decay_beta_0                      0.006318     0.006318  0.000043   
  β₁               experiments[wish_3_8].peak.decay_beta_1                       0.02048      0.02048   0.00053   
  α₀               experiments[wish_3_8].peak.rise_alpha_0                      -0.01093     -0.01093   0.00087   
  α₁               experiments[wish_3_8].peak.rise_alpha_1                        0.1185       0.1185    0.0038   
  intensity        experiments[wish_4_7].background[10].intensity                  343.2        343.2       6.8   
  intensity        experiments[wish_4_7].background[11].intensity                  384.7        384.7       6.0   
  intensity        experiments[wish_4_7].background[12].intensity                  345.9        345.9       5.0   
  intensity        experiments[wish_4_7].background[13].intensity                  329.8        329.8       4.5   
  intensity        experiments[wish_4_7].background[14].intensity                  327.4        327.4       4.0   
  intensity        experiments[wish_4_7].background[15].intensity                  281.4        281.4       3.9   
  intensity        experiments[wish_4_7].background[16].intensity                  349.7        349.7       4.7   
  intensity        experiments[wish_4_7].background[17].intensity                  317.4        317.4       3.7   
  intensity        experiments[wish_4_7].background[18].intensity                  306.7        306.7       3.1   
  intensity        experiments[wish_4_7].background[19].intensity                  252.5        252.5       3.0   
  intensity        experiments[wish_4_7].background[1].intensity                     370          370        49   
  intensity        experiments[wish_4_7].background[20].intensity                  262.7        262.7       3.5   
  intensity        experiments[wish_4_7].background[21].intensity                  246.3        246.3       3.7   
  intensity        experiments[wish_4_7].background[22].intensity                  263.5        263.5       3.5   
  intensity        experiments[wish_4_7].background[23].intensity                  250.4        250.4       3.8   
  intensity        experiments[wish_4_7].background[24].intensity                    260        260.0       4.6   
  intensity        experiments[wish_4_7].background[25].intensity                  260.2        260.2       5.7   
  intensity        experiments[wish_4_7].background[26].intensity                    250        250.0       7.5   
  intensity        experiments[wish_4_7].background[27].intensity                    254          254        14   
  intensity        experiments[wish_4_7].background[28].intensity                    244          244        34   0.1% ↑
  intensity        experiments[wish_4_7].background[2].intensity                     425          425        37   0.1% ↑
  intensity        experiments[wish_4_7].background[3].intensity                     402          402        28   
  intensity        experiments[wish_4_7].background[4].intensity                     417          417        23   
  intensity        experiments[wish_4_7].background[5].intensity                     453          453        18   
  intensity        experiments[wish_4_7].background[6].intensity                     375          375        14   0.1% ↑
  intensity        experiments[wish_4_7].background[7].intensity                     395          395        12   0.1% ↓
  intensity        experiments[wish_4_7].background[8].intensity                     364          364        11   0.1% ↑
  intensity        experiments[wish_4_7].background[9].intensity                     397          397        11   0.1% ↓
  TOF linear, µs/Å experiments[wish_4_7].instrument.calib_d_to_tof_linear         1.87e4   1.866213e40.000039e4   
  TOF offset, µs   experiments[wish_4_7].instrument.calib_d_to_tof_offset            -19       -19.00      0.56   
  scale            experiments[wish_4_7].linked_structures[ncaf].scale            33.405       33.405     0.082   
  σ₁², µs²/Å²      experiments[wish_4_7].peak.broad_gauss_sigma_1                   21.7         21.7       5.6   0.1% ↑
  σ₂², µs²/Å⁴      experiments[wish_4_7].peak.broad_gauss_sigma_2                   19.7         19.7       1.2   0.2% ↓
  β₀               experiments[wish_4_7].peak.decay_beta_0                       0.00678     0.006780  0.000036   
  β₁               experiments[wish_4_7].peak.decay_beta_1                       0.00888      0.00888   0.00025   
  α₀               experiments[wish_4_7].peak.rise_alpha_0                       -0.0095      -0.0095    0.0011   0.2% ↓
  α₁               experiments[wish_4_7].peak.rise_alpha_1                        0.1155       0.1155    0.0034   
  intensity        experiments[wish_5_6].background[10].intensity                    371          371        12   
  intensity        experiments[wish_5_6].background[11].intensity                  392.4        392.4       8.7   
  intensity        experiments[wish_5_6].background[12].intensity                  337.7        337.7       5.7   
  intensity        experiments[wish_5_6].background[13].intensity                  382.5        382.5       5.2   
  intensity        experiments[wish_5_6].background[14].intensity                  345.2        345.2       4.3   
  intensity        experiments[wish_5_6].background[15].intensity                  330.8        330.8       3.8   
  intensity        experiments[wish_5_6].background[16].intensity                  319.8        319.8       3.5   
  intensity        experiments[wish_5_6].background[17].intensity                  291.9        291.9       3.5   
  intensity        experiments[wish_5_6].background[18].intensity                  325.7        325.7       3.4   
  intensity        experiments[wish_5_6].background[19].intensity                  300.5        300.5       3.4   
  intensity        experiments[wish_5_6].background[1].intensity                     475          475        30   
  intensity        experiments[wish_5_6].background[20].intensity                  267.7        267.7       3.5   
  intensity        experiments[wish_5_6].background[21].intensity                  255.1        255.1       3.6   
  intensity        experiments[wish_5_6].background[22].intensity                  264.4        264.4       3.7   
  intensity        experiments[wish_5_6].background[23].intensity                  260.3        260.3       4.0   
  intensity        experiments[wish_5_6].background[24].intensity                  261.8        261.8       4.8   
  intensity        experiments[wish_5_6].background[25].intensity                  262.8        262.8       5.8   
  intensity        experiments[wish_5_6].background[26].intensity                  269.7        269.7       5.6   
  intensity        experiments[wish_5_6].background[27].intensity                  271.5        271.5       7.1   
  intensity        experiments[wish_5_6].background[28].intensity                    259          259        15   0.2% ↑
  intensity        experiments[wish_5_6].background[2].intensity                     412          412        23   0.1% ↑
  intensity        experiments[wish_5_6].background[3].intensity                     377          377        40   
  intensity        experiments[wish_5_6].background[4].intensity                     435          435        19   
  intensity        experiments[wish_5_6].background[5].intensity                     445          445        17   
  intensity        experiments[wish_5_6].background[6].intensity                     428          428        14   0.1% ↓
  intensity        experiments[wish_5_6].background[7].intensity                     372          372        11   
  intensity        experiments[wish_5_6].background[8].intensity                   394.1        394.1       9.8   
  intensity        experiments[wish_5_6].background[9].intensity                   378.5        378.5       9.2   
  TOF linear, µs/Å experiments[wish_5_6].instrument.calib_d_to_tof_linear         2.08e4   2.077460e40.000035e4   
  TOF offset, µs   experiments[wish_5_6].instrument.calib_d_to_tof_offset         -16.72       -16.72      0.50   
  scale            experiments[wish_5_6].linked_structures[ncaf].scale            33.506       33.506     0.081   
  σ₂², µs²/Å⁴      experiments[wish_5_6].peak.broad_gauss_sigma_2                  15.41        15.41      0.79   
  β₀               experiments[wish_5_6].peak.decay_beta_0                      0.006956     0.006956  0.000033   
  β₁               experiments[wish_5_6].peak.decay_beta_1                       0.00573      0.00573   0.00016   
  α₀               experiments[wish_5_6].peak.rise_alpha_0                       -0.0075      -0.0075    0.0011   0.5% ↑
  α₁               experiments[wish_5_6].peak.rise_alpha_1                        0.1037       0.1037    0.0023   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Absorption

Banks 2-9 to 5-6 each fit their absorption.

In `experiments/wish_2_9.edi`, add `()` after the values the stage frees:

```edi
_absorption.abscor1 0()
```

In `experiments/wish_3_8.edi`, add `()` after the values the stage frees:

```edi
_absorption.abscor1 0()
```

In `experiments/wish_4_7.edi`, add `()` after the values the stage frees:

```edi
_absorption.abscor1 0()
```

In `experiments/wish_5_6.edi`, add `()` after the values the stage frees:

```edi
_absorption.abscor1 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ncaf-wish, 5 banks (wish_1_10, wish_2_9, wish_3_8, wish_4_7, wish_5_6), 18973 pts fitted / 20475 loaded, 177 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        9.97        15.94
      1      1.285      9.91        15.74   1.2% ↓
      2      1.443      9.91        15.74   
      3      1.685      9.91        15.74   
  done · converged · 3 iters · reduced χ² 15.74 · Rwp 9.91 % · 1.95 s

  per-bank Rwp (%):   wish_1_10 6.08   wish_2_9 8.53   wish_3_8 10.15   wish_4_7 10.32   wish_5_6 10.66

  refined parameters (177 free):
  name             parameter                                                       start        value      s.u.   change
  intensity        experiments[wish_1_10].background[10].intensity                   230          230        24   0.1% ↑
  intensity        experiments[wish_1_10].background[11].intensity                   255          255        17   
  intensity        experiments[wish_1_10].background[12].intensity                   246          246        15   
  intensity        experiments[wish_1_10].background[13].intensity                   224          224        12   0.2% ↓
  intensity        experiments[wish_1_10].background[14].intensity                   258        258.0       9.5   
  intensity        experiments[wish_1_10].background[15].intensity                 247.3        247.3       6.6   
  intensity        experiments[wish_1_10].background[16].intensity                 227.2        227.2       5.2   
  intensity        experiments[wish_1_10].background[17].intensity                 236.8        236.8       4.2   
  intensity        experiments[wish_1_10].background[18].intensity                 226.7        226.7       3.7   
  intensity        experiments[wish_1_10].background[19].intensity                 223.4        223.4       3.7   
  intensity        experiments[wish_1_10].background[20].intensity                 219.8        219.8       3.6   
  intensity        experiments[wish_1_10].background[21].intensity                 223.6        223.6       2.7   
  intensity        experiments[wish_1_10].background[22].intensity                 216.6        216.6       2.7   
  intensity        experiments[wish_1_10].background[23].intensity                 216.8        216.8       3.1   
  intensity        experiments[wish_1_10].background[24].intensity                 213.5        213.5       3.4   
  intensity        experiments[wish_1_10].background[25].intensity                 216.2        216.2       3.8   
  intensity        experiments[wish_1_10].background[26].intensity                   213        213.0       4.3   
  intensity        experiments[wish_1_10].background[27].intensity                 212.4        212.4       5.1   
  intensity        experiments[wish_1_10].background[28].intensity                 212.6        212.6       5.8   
  intensity        experiments[wish_1_10].background[29].intensity                 211.3        211.3       7.0   
  intensity        experiments[wish_1_10].background[2].intensity                    108          108        86   0.2% ↓
  intensity        experiments[wish_1_10].background[30].intensity                   211        211.0       8.7   
  intensity        experiments[wish_1_10].background[31].intensity                   223          223        12   
  intensity        experiments[wish_1_10].background[32].intensity                   210          210        15   0.2% ↑
  intensity        experiments[wish_1_10].background[33].intensity                   222          222        22   0.1% ↑
  intensity        experiments[wish_1_10].background[34].intensity                   255          255        34   
  intensity        experiments[wish_1_10].background[35].intensity                   120          120        45   0.3% ↓
  intensity        experiments[wish_1_10].background[3].intensity                    161          161        58   0.2% ↓
  intensity        experiments[wish_1_10].background[4].intensity                    120          120        56   
  intensity        experiments[wish_1_10].background[5].intensity                    322          322        68   0.1% ↑
  intensity        experiments[wish_1_10].background[6].intensity                    259          259        45   0.2% ↑
  intensity        experiments[wish_1_10].background[7].intensity                    234          234        47   0.2% ↓
  intensity        experiments[wish_1_10].background[8].intensity                    229          229        39   0.1% ↓
  intensity        experiments[wish_1_10].background[9].intensity                    239          239        29   0.1% ↓
  TOF linear, µs/Å experiments[wish_1_10].instrument.calib_d_to_tof_linear        4.99e3     4.9851e3  0.0012e3   
  TOF offset, µs   experiments[wish_1_10].instrument.calib_d_to_tof_offset          14.5         14.5       4.3   0.2% ↓
  scale            experiments[wish_1_10].linked_structures[ncaf].scale            30.36        30.36      0.33   
  ABSCOR1, Å⁻¹     experiments[wish_2_9].absorption.abscor1                       0.0000       0.0144    0.0019   
  intensity        experiments[wish_2_9].background[10].intensity                  268.6        265.8       4.0   1.1% ↓
  intensity        experiments[wish_2_9].background[11].intensity                  275.1        274.0       3.9   0.4% ↓
  intensity        experiments[wish_2_9].background[12].intensity                  260.8        260.3       2.9   0.2% ↓
  intensity        experiments[wish_2_9].background[13].intensity                  252.6        252.7       2.4   
  intensity        experiments[wish_2_9].background[14].intensity                  241.9        242.3       2.2   0.2% ↑
  intensity        experiments[wish_2_9].background[15].intensity                  227.8        228.6       2.1   0.3% ↑
  intensity        experiments[wish_2_9].background[16].intensity                  217.5        218.3       2.5   0.4% ↑
  intensity        experiments[wish_2_9].background[17].intensity                  220.4        220.7       3.3   0.1% ↑
  intensity        experiments[wish_2_9].background[18].intensity                  221.4        223.5       4.6   0.9% ↑
  intensity        experiments[wish_2_9].background[19].intensity                  220.6        219.8       6.2   0.4% ↓
  intensity        experiments[wish_2_9].background[1].intensity                      96           76        59   21.3% ↓
  intensity        experiments[wish_2_9].background[20].intensity                  219.3        219.7       9.4   0.2% ↑
  intensity        experiments[wish_2_9].background[21].intensity                    219          219        17   0.1% ↓
  intensity        experiments[wish_2_9].background[22].intensity                    164          164        39   0.1% ↑
  intensity        experiments[wish_2_9].background[2].intensity                     205          191        45   6.8% ↓
  intensity        experiments[wish_2_9].background[3].intensity                     278          255        32   8.4% ↓
  intensity        experiments[wish_2_9].background[4].intensity                     359          347        19   3.2% ↓
  intensity        experiments[wish_2_9].background[5].intensity                     315          301        14   4.3% ↓
  intensity        experiments[wish_2_9].background[6].intensity                     322          313        12   2.7% ↓
  intensity        experiments[wish_2_9].background[7].intensity                     339          323        11   4.8% ↓
  intensity        experiments[wish_2_9].background[8].intensity                   391.6        383.9       7.9   2.0% ↓
  intensity        experiments[wish_2_9].background[9].intensity                     367        358.5       6.1   2.3% ↓
  TOF linear, µs/Å experiments[wish_2_9].instrument.calib_d_to_tof_linear         1.04e4   1.038837e40.000067e4   
  TOF offset, µs   experiments[wish_2_9].instrument.calib_d_to_tof_offset           19.5         18.5       1.5   5.3% ↓
  scale            experiments[wish_2_9].linked_structures[ncaf].scale             33.53        36.28      0.40   8.2% ↑
  σ₁², µs²/Å²      experiments[wish_2_9].peak.broad_gauss_sigma_1                     52           40        14   22.4% ↓
  σ₂², µs²/Å⁴      experiments[wish_2_9].peak.broad_gauss_sigma_2                   25.6         25.7       1.1   0.3% ↑
  γ₁, µs/Å         experiments[wish_2_9].peak.broad_lorentz_gamma_1                 1.09         1.35      0.69   24.2% ↑
  β₀               experiments[wish_2_9].peak.decay_beta_0                      0.005371     0.005445  0.000064   1.4% ↑
  β₁               experiments[wish_2_9].peak.decay_beta_1                        0.0798       0.0745    0.0021   6.6% ↓
  α₀               experiments[wish_2_9].peak.rise_alpha_0                        0.0576       0.0537    0.0047   6.7% ↓
  α₁               experiments[wish_2_9].peak.rise_alpha_1                       -0.0186      -0.0166    0.0059   10.7% ↑
  ABSCOR1, Å⁻¹     experiments[wish_3_8].absorption.abscor1                       0.0000        -7e-4     13e-4   
  intensity        experiments[wish_3_8].background[10].intensity                  351.5        351.7       3.7   
  intensity        experiments[wish_3_8].background[11].intensity                  318.4        318.5       3.4   
  intensity        experiments[wish_3_8].background[12].intensity                  275.8        275.8       2.9   
  intensity        experiments[wish_3_8].background[13].intensity                  258.5        258.5       2.6   
  intensity        experiments[wish_3_8].background[14].intensity                  253.7        253.7       2.6   
  intensity        experiments[wish_3_8].background[15].intensity                  234.9        234.8       2.7   
  intensity        experiments[wish_3_8].background[16].intensity                  245.4        245.3       3.1   
  intensity        experiments[wish_3_8].background[17].intensity                  237.5        237.5       3.7   
  intensity        experiments[wish_3_8].background[18].intensity                  238.6        238.4       5.3   0.1% ↓
  intensity        experiments[wish_3_8].background[19].intensity                  242.3        242.3       7.2   
  intensity        experiments[wish_3_8].background[1].intensity                     319          320        44   0.3% ↑
  intensity        experiments[wish_3_8].background[20].intensity                    236          236        11   0.2% ↓
  intensity        experiments[wish_3_8].background[21].intensity                    234          234        18   0.2% ↓
  intensity        experiments[wish_3_8].background[22].intensity                    234          234        41   0.2% ↓
  intensity        experiments[wish_3_8].background[2].intensity                     388          389        28   0.2% ↑
  intensity        experiments[wish_3_8].background[3].intensity                     365          365        19   0.1% ↑
  intensity        experiments[wish_3_8].background[4].intensity                     397          398        14   0.3% ↑
  intensity        experiments[wish_3_8].background[5].intensity                   360.3        361.0       8.6   0.2% ↑
  intensity        experiments[wish_3_8].background[6].intensity                   348.1        348.6       6.5   0.1% ↑
  intensity        experiments[wish_3_8].background[7].intensity                   322.3        322.9       5.8   0.2% ↑
  intensity        experiments[wish_3_8].background[8].intensity                   318.3        318.6       4.8   0.1% ↑
  intensity        experiments[wish_3_8].background[9].intensity                   307.5        307.9       4.3   0.1% ↑
  TOF linear, µs/Å experiments[wish_3_8].instrument.calib_d_to_tof_linear         1.51e4   1.510701e40.000044e4   
  TOF offset, µs   experiments[wish_3_8].instrument.calib_d_to_tof_offset         -16.31       -16.24      0.69   0.5% ↑
  scale            experiments[wish_3_8].linked_structures[ncaf].scale            33.985        33.84      0.26   0.4% ↓
  σ₁², µs²/Å²      experiments[wish_3_8].peak.broad_gauss_sigma_1                   55.4         55.6       7.0   0.4% ↑
  σ₂², µs²/Å⁴      experiments[wish_3_8].peak.broad_gauss_sigma_2                   18.5         18.5       1.1   0.1% ↓
  β₀               experiments[wish_3_8].peak.decay_beta_0                      0.006318     0.006313  0.000043   0.1% ↓
  β₁               experiments[wish_3_8].peak.decay_beta_1                       0.02048      0.02061   0.00054   0.7% ↑
  α₀               experiments[wish_3_8].peak.rise_alpha_0                      -0.01093     -0.01097   0.00087   0.4% ↓
  α₁               experiments[wish_3_8].peak.rise_alpha_1                        0.1185       0.1187    0.0038   0.2% ↑
  ABSCOR1, Å⁻¹     experiments[wish_4_7].absorption.abscor1                       0.0000      -0.0072    0.0012   
  intensity        experiments[wish_4_7].background[10].intensity                  343.2        348.2       6.8   1.5% ↑
  intensity        experiments[wish_4_7].background[11].intensity                  384.7        389.5       6.0   1.3% ↑
  intensity        experiments[wish_4_7].background[12].intensity                  345.9        350.7       5.0   1.4% ↑
  intensity        experiments[wish_4_7].background[13].intensity                  329.8        334.3       4.5   1.4% ↑
  intensity        experiments[wish_4_7].background[14].intensity                  327.4        329.5       4.0   0.6% ↑
  intensity        experiments[wish_4_7].background[15].intensity                  281.4        283.4       3.9   0.7% ↑
  intensity        experiments[wish_4_7].background[16].intensity                  349.7        352.0       4.6   0.7% ↑
  intensity        experiments[wish_4_7].background[17].intensity                  317.4        317.6       3.7   0.1% ↑
  intensity        experiments[wish_4_7].background[18].intensity                  306.7        306.7       3.1   
  intensity        experiments[wish_4_7].background[19].intensity                  252.5        251.9       2.9   0.2% ↓
  intensity        experiments[wish_4_7].background[1].intensity                     370          375        49   1.4% ↑
  intensity        experiments[wish_4_7].background[20].intensity                  262.7        262.3       3.5   0.2% ↓
  intensity        experiments[wish_4_7].background[21].intensity                  246.3        245.6       3.7   0.3% ↓
  intensity        experiments[wish_4_7].background[22].intensity                  263.5        263.3       3.5   0.1% ↓
  intensity        experiments[wish_4_7].background[23].intensity                  250.4        249.2       3.8   0.5% ↓
  intensity        experiments[wish_4_7].background[24].intensity                    260        259.2       4.6   0.3% ↓
  intensity        experiments[wish_4_7].background[25].intensity                  260.2        259.9       5.7   0.1% ↓
  intensity        experiments[wish_4_7].background[26].intensity                    250        248.6       7.5   0.5% ↓
  intensity        experiments[wish_4_7].background[27].intensity                    254          252        14   1.0% ↓
  intensity        experiments[wish_4_7].background[28].intensity                    244          246        34   0.8% ↑
  intensity        experiments[wish_4_7].background[2].intensity                     425          434        36   2.2% ↑
  intensity        experiments[wish_4_7].background[3].intensity                     402          408        28   1.5% ↑
  intensity        experiments[wish_4_7].background[4].intensity                     417          430        23   3.2% ↑
  intensity        experiments[wish_4_7].background[5].intensity                     453          462        18   1.9% ↑
  intensity        experiments[wish_4_7].background[6].intensity                     375          383        14   2.1% ↑
  intensity        experiments[wish_4_7].background[7].intensity                     395          405        12   2.4% ↑
  intensity        experiments[wish_4_7].background[8].intensity                     364          370        11   1.8% ↑
  intensity        experiments[wish_4_7].background[9].intensity                     397          413        11   3.9% ↑
  TOF linear, µs/Å experiments[wish_4_7].instrument.calib_d_to_tof_linear         1.87e4   1.866176e40.000038e4   
  TOF offset, µs   experiments[wish_4_7].instrument.calib_d_to_tof_offset            -19       -18.33      0.55   3.5% ↑
  scale            experiments[wish_4_7].linked_structures[ncaf].scale            33.405        31.87      0.25   4.6% ↓
  σ₁², µs²/Å²      experiments[wish_4_7].peak.broad_gauss_sigma_1                   21.7         22.8       5.6   5.1% ↑
  σ₂², µs²/Å⁴      experiments[wish_4_7].peak.broad_gauss_sigma_2                   19.7         19.7       1.2   0.1% ↓
  β₀               experiments[wish_4_7].peak.decay_beta_0                       0.00678     0.006736  0.000036   0.7% ↓
  β₁               experiments[wish_4_7].peak.decay_beta_1                       0.00888      0.00968   0.00027   9.0% ↑
  α₀               experiments[wish_4_7].peak.rise_alpha_0                       -0.0095      -0.0098    0.0011   3.0% ↓
  α₁               experiments[wish_4_7].peak.rise_alpha_1                        0.1155       0.1167    0.0034   1.0% ↑
  ABSCOR1, Å⁻¹     experiments[wish_5_6].absorption.abscor1                       0.0000      -0.0135    0.0012 ! 
  intensity        experiments[wish_5_6].background[10].intensity                    371          401        12   8.2% ↑
  intensity        experiments[wish_5_6].background[11].intensity                  392.4        415.4       8.8   5.9% ↑
  intensity        experiments[wish_5_6].background[12].intensity                  337.7        346.4       5.7   2.6% ↑
  intensity        experiments[wish_5_6].background[13].intensity                  382.5        391.0       5.2   2.2% ↑
  intensity        experiments[wish_5_6].background[14].intensity                  345.2        353.0       4.3   2.3% ↑
  intensity        experiments[wish_5_6].background[15].intensity                  330.8        337.9       3.8   2.2% ↑
  intensity        experiments[wish_5_6].background[16].intensity                  319.8        322.8       3.5   0.9% ↑
  intensity        experiments[wish_5_6].background[17].intensity                  291.9        294.9       3.4   1.0% ↑
  intensity        experiments[wish_5_6].background[18].intensity                  325.7        326.1       3.4   0.1% ↑
  intensity        experiments[wish_5_6].background[19].intensity                  300.5        300.1       3.3   0.1% ↓
  intensity        experiments[wish_5_6].background[1].intensity                     475          491        30   3.3% ↑
  intensity        experiments[wish_5_6].background[20].intensity                  267.7        266.2       3.5   0.6% ↓
  intensity        experiments[wish_5_6].background[21].intensity                  255.1        253.9       3.6   0.5% ↓
  intensity        experiments[wish_5_6].background[22].intensity                  264.4        263.3       3.7   0.4% ↓
  intensity        experiments[wish_5_6].background[23].intensity                  260.3        258.8       3.9   0.6% ↓
  intensity        experiments[wish_5_6].background[24].intensity                  261.8        261.6       4.7   0.1% ↓
  intensity        experiments[wish_5_6].background[25].intensity                  262.8        258.6       5.8   1.6% ↓
  intensity        experiments[wish_5_6].background[26].intensity                  269.7        269.1       5.6   0.2% ↓
  intensity        experiments[wish_5_6].background[27].intensity                  271.5        269.2       7.1   0.8% ↓
  intensity        experiments[wish_5_6].background[28].intensity                    259          261        15   0.9% ↑
  intensity        experiments[wish_5_6].background[2].intensity                     412          426        23   3.5% ↑
  intensity        experiments[wish_5_6].background[3].intensity                     377          385        40   2.2% ↑
  intensity        experiments[wish_5_6].background[4].intensity                     435          455        19   4.7% ↑
  intensity        experiments[wish_5_6].background[5].intensity                     445          469        17   5.5% ↑
  intensity        experiments[wish_5_6].background[6].intensity                     428          444        14   3.7% ↑
  intensity        experiments[wish_5_6].background[7].intensity                     372          385        11   3.5% ↑
  intensity        experiments[wish_5_6].background[8].intensity                   394.1        415.8       9.9   5.5% ↑
  intensity        experiments[wish_5_6].background[9].intensity                   378.5        382.7       9.1   1.1% ↑
  TOF linear, µs/Å experiments[wish_5_6].instrument.calib_d_to_tof_linear         2.08e4   2.077404e40.000033e4   
  TOF offset, µs   experiments[wish_5_6].instrument.calib_d_to_tof_offset         -16.72       -15.66      0.47   6.3% ↑
  scale            experiments[wish_5_6].linked_structures[ncaf].scale            33.506        30.55      0.26 ! 8.8% ↓
  σ₂², µs²/Å⁴      experiments[wish_5_6].peak.broad_gauss_sigma_2                  15.41        15.43      0.77   0.1% ↑
  β₀               experiments[wish_5_6].peak.decay_beta_0                      0.006956     0.006880  0.000034   1.1% ↓
  β₁               experiments[wish_5_6].peak.decay_beta_1                       0.00573      0.00688   0.00019   20.1% ↑
  α₀               experiments[wish_5_6].peak.rise_alpha_0                       -0.0075     -0.00795   0.00094   6.1% ↓
  α₁               experiments[wish_5_6].peak.rise_alpha_1                        0.1037       0.1051    0.0022   1.3% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[wish_5_6].absorption.abscor1: strongly correlated with ncaf scale (wish_5_6) (r = 0.96)
      experiments[wish_5_6].linked_structures[ncaf].scale: strongly correlated with ABSCOR1 (wish_5_6) (r = 0.96)
```

## Atom positions

The coordinates the cubic symmetry leaves free.

In `structures/ncaf.edi`, add `()` after the values the stage frees:

```edi
Ca1 Ca 0.47() 0 0.25 b 12 1 0.5 Biso
Al1 Al 0.25() 0.25 0.25 a 8 1 0.5 Biso
```

The same for every other row (4 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ncaf-wish, 5 banks (wish_1_10, wish_2_9, wish_3_8, wish_4_7, wish_5_6), 18973 pts fitted / 20475 loaded, 187 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        9.91        15.75
      1      1.484      8.07        10.43   33.8% ↓
      2      1.708      8.07        10.43   
      3      1.989      8.07        10.43   
  done · converged · 3 iters · reduced χ² 10.43 · Rwp 8.07 % · 2.37 s

  per-bank Rwp (%):   wish_1_10 4.95   wish_2_9 6.68   wish_3_8 8.27   wish_4_7 8.54   wish_5_6 8.66

  refined parameters (187 free):
  name             parameter                                                       start        value      s.u.   change
  intensity        experiments[wish_1_10].background[10].intensity                   230          201        19   12.4% ↓
  intensity        experiments[wish_1_10].background[11].intensity                   255          253        14   0.6% ↓
  intensity        experiments[wish_1_10].background[12].intensity                   246          225        12   8.3% ↓
  intensity        experiments[wish_1_10].background[13].intensity                   224        217.9       9.3   2.7% ↓
  intensity        experiments[wish_1_10].background[14].intensity                   258        231.8       7.8   10.2% ↓
  intensity        experiments[wish_1_10].background[15].intensity                 247.3        235.8       5.4   4.7% ↓
  intensity        experiments[wish_1_10].background[16].intensity                 227.2        238.0       4.3   4.7% ↑
  intensity        experiments[wish_1_10].background[17].intensity                 236.8        240.0       3.4   1.4% ↑
  intensity        experiments[wish_1_10].background[18].intensity                 226.7        226.5       3.0   0.1% ↓
  intensity        experiments[wish_1_10].background[19].intensity                 223.4        221.4       3.0   0.9% ↓
  intensity        experiments[wish_1_10].background[20].intensity                 219.8        229.3       3.0   4.3% ↑
  intensity        experiments[wish_1_10].background[21].intensity                 223.6        224.9       2.2   0.6% ↑
  intensity        experiments[wish_1_10].background[22].intensity                 216.6        216.2       2.2   0.2% ↓
  intensity        experiments[wish_1_10].background[23].intensity                 216.8        216.9       2.5   0.1% ↑
  intensity        experiments[wish_1_10].background[24].intensity                 213.5        213.5       2.8   
  intensity        experiments[wish_1_10].background[25].intensity                 216.2        216.2       3.1   
  intensity        experiments[wish_1_10].background[26].intensity                   213        213.0       3.5   
  intensity        experiments[wish_1_10].background[27].intensity                 212.4        212.4       4.1   
  intensity        experiments[wish_1_10].background[28].intensity                 212.6        212.6       4.7   
  intensity        experiments[wish_1_10].background[29].intensity                 211.3        211.3       5.7   
  intensity        experiments[wish_1_10].background[2].intensity                    108           65        70 ! 40.2% ↓
  intensity        experiments[wish_1_10].background[30].intensity                   211        211.0       7.1   
  intensity        experiments[wish_1_10].background[31].intensity                   223        222.9       9.0   
  intensity        experiments[wish_1_10].background[32].intensity                   210          210        13   0.2% ↑
  intensity        experiments[wish_1_10].background[33].intensity                   222          222        18   0.1% ↑
  intensity        experiments[wish_1_10].background[34].intensity                   255          255        28   
  intensity        experiments[wish_1_10].background[35].intensity                   120          120        37   0.3% ↓
  intensity        experiments[wish_1_10].background[3].intensity                    161          117        47   27.5% ↓
  intensity        experiments[wish_1_10].background[4].intensity                    120           79        46   33.9% ↓
  intensity        experiments[wish_1_10].background[5].intensity                    322          248        55   22.8% ↓
  intensity        experiments[wish_1_10].background[6].intensity                    259          176        37   31.9% ↓
  intensity        experiments[wish_1_10].background[7].intensity                    234          126        38   46.1% ↓
  intensity        experiments[wish_1_10].background[8].intensity                    229          221        32   3.4% ↓
  intensity        experiments[wish_1_10].background[9].intensity                    239          208        23   12.9% ↓
  TOF linear, µs/Å experiments[wish_1_10].instrument.calib_d_to_tof_linear        4.99e3    4.98540e3 0.00090e3   
  TOF offset, µs   experiments[wish_1_10].instrument.calib_d_to_tof_offset          14.5         13.2       3.1   8.6% ↓
  scale            experiments[wish_1_10].linked_structures[ncaf].scale            30.36        37.71      0.36   24.2% ↑
  ABSCOR1, Å⁻¹     experiments[wish_2_9].absorption.abscor1                       0.0144      -0.0313    0.0017   317.4% ↓
  intensity        experiments[wish_2_9].background[10].intensity                  265.8        281.0       3.3   5.7% ↑
  intensity        experiments[wish_2_9].background[11].intensity                    274        266.2       3.2   2.8% ↓
  intensity        experiments[wish_2_9].background[12].intensity                  260.3        259.0       2.3   0.5% ↓
  intensity        experiments[wish_2_9].background[13].intensity                  252.7        253.3       2.0   0.2% ↑
  intensity        experiments[wish_2_9].background[14].intensity                  242.3        237.5       1.8   2.0% ↓
  intensity        experiments[wish_2_9].background[15].intensity                  228.6        227.9       1.7   0.3% ↓
  intensity        experiments[wish_2_9].background[16].intensity                  218.3        221.4       2.1   1.4% ↑
  intensity        experiments[wish_2_9].background[17].intensity                  220.7        219.7       2.7   0.5% ↓
  intensity        experiments[wish_2_9].background[18].intensity                  223.5        224.2       3.8   0.3% ↑
  intensity        experiments[wish_2_9].background[19].intensity                  219.8        219.5       5.1   0.1% ↓
  intensity        experiments[wish_2_9].background[1].intensity                      76          129        48   69.1% ↑
  intensity        experiments[wish_2_9].background[20].intensity                  219.7        219.8       7.7   
  intensity        experiments[wish_2_9].background[21].intensity                    219          219        14   0.1% ↓
  intensity        experiments[wish_2_9].background[22].intensity                    164          164        32   0.1% ↑
  intensity        experiments[wish_2_9].background[2].intensity                     191          207        37   8.4% ↑
  intensity        experiments[wish_2_9].background[3].intensity                     255          320        26   25.7% ↑
  intensity        experiments[wish_2_9].background[4].intensity                     347          367        16   5.7% ↑
  intensity        experiments[wish_2_9].background[5].intensity                     301          333        12   10.7% ↑
  intensity        experiments[wish_2_9].background[6].intensity                     313        323.9       9.5   3.5% ↑
  intensity        experiments[wish_2_9].background[7].intensity                     323        363.4       8.2   12.5% ↑
  intensity        experiments[wish_2_9].background[8].intensity                   383.9        391.3       6.4   1.9% ↑
  intensity        experiments[wish_2_9].background[9].intensity                   358.5        343.5       5.1   4.2% ↓
  TOF linear, µs/Å experiments[wish_2_9].instrument.calib_d_to_tof_linear         1.04e4   1.038811e40.000062e4   
  TOF offset, µs   experiments[wish_2_9].instrument.calib_d_to_tof_offset           18.5         17.6       1.3   4.7% ↓
  scale            experiments[wish_2_9].linked_structures[ncaf].scale             36.28        29.96      0.29   17.4% ↓
  σ₁², µs²/Å²      experiments[wish_2_9].peak.broad_gauss_sigma_1                     40           67        12   66.6% ↑
  σ₂², µs²/Å⁴      experiments[wish_2_9].peak.broad_gauss_sigma_2                   25.7        23.45      0.93   8.7% ↓
  γ₁, µs/Å         experiments[wish_2_9].peak.broad_lorentz_gamma_1                 1.35         1.86      0.55   37.8% ↑
  β₀               experiments[wish_2_9].peak.decay_beta_0                      0.005445     0.005335  0.000051   2.0% ↓
  β₁               experiments[wish_2_9].peak.decay_beta_1                        0.0745       0.0823    0.0019   10.5% ↑
  α₀               experiments[wish_2_9].peak.rise_alpha_0                        0.0537       0.0544    0.0056   1.3% ↑
  α₁               experiments[wish_2_9].peak.rise_alpha_1                       -0.0166      -0.0053    0.0071   68.2% ↑
  ABSCOR1, Å⁻¹     experiments[wish_3_8].absorption.abscor1                     -7.00e-4      -0.0223    0.0011   3.08e3 % ↓
  intensity        experiments[wish_3_8].background[10].intensity                  351.7        353.8       3.0   0.6% ↑
  intensity        experiments[wish_3_8].background[11].intensity                  318.5        300.1       2.8   5.8% ↓
  intensity        experiments[wish_3_8].background[12].intensity                  275.8        284.7       2.4   3.2% ↑
  intensity        experiments[wish_3_8].background[13].intensity                  258.5        254.1       2.1   1.7% ↓
  intensity        experiments[wish_3_8].background[14].intensity                  253.7        253.9       2.1   0.1% ↑
  intensity        experiments[wish_3_8].background[15].intensity                  234.8        235.5       2.2   0.3% ↑
  intensity        experiments[wish_3_8].background[16].intensity                  245.3        240.6       2.5   1.9% ↓
  intensity        experiments[wish_3_8].background[17].intensity                  237.5        239.3       3.0   0.8% ↑
  intensity        experiments[wish_3_8].background[18].intensity                  238.4        242.8       4.4   1.9% ↑
  intensity        experiments[wish_3_8].background[19].intensity                  242.3        241.0       5.9   0.5% ↓
  intensity        experiments[wish_3_8].background[1].intensity                     320          342        36   6.9% ↑
  intensity        experiments[wish_3_8].background[20].intensity                    236        235.8       8.3   0.1% ↓
  intensity        experiments[wish_3_8].background[21].intensity                    234          236        15   0.8% ↑
  intensity        experiments[wish_3_8].background[22].intensity                    234          239        34   2.2% ↑
  intensity        experiments[wish_3_8].background[2].intensity                     389          417        23   7.2% ↑
  intensity        experiments[wish_3_8].background[3].intensity                     365          378        16   3.6% ↑
  intensity        experiments[wish_3_8].background[4].intensity                     398          427        11   7.3% ↑
  intensity        experiments[wish_3_8].background[5].intensity                     361        383.4       7.0   6.2% ↑
  intensity        experiments[wish_3_8].background[6].intensity                   348.6        369.6       5.3   6.0% ↑
  intensity        experiments[wish_3_8].background[7].intensity                   322.9        342.8       4.7   6.2% ↑
  intensity        experiments[wish_3_8].background[8].intensity                   318.6        325.8       4.0   2.2% ↑
  intensity        experiments[wish_3_8].background[9].intensity                   307.9        335.2       3.5   8.9% ↑
  TOF linear, µs/Å experiments[wish_3_8].instrument.calib_d_to_tof_linear         1.51e4   1.510566e40.000036e4   
  TOF offset, µs   experiments[wish_3_8].instrument.calib_d_to_tof_offset         -16.24       -13.46      0.57   17.1% ↑
  scale            experiments[wish_3_8].linked_structures[ncaf].scale             33.84        29.99      0.20   11.4% ↓
  σ₁², µs²/Å²      experiments[wish_3_8].peak.broad_gauss_sigma_1                   55.6         64.3       5.9   15.6% ↑
  σ₂², µs²/Å⁴      experiments[wish_3_8].peak.broad_gauss_sigma_2                   18.5        17.01      0.91   8.0% ↓
  β₀               experiments[wish_3_8].peak.decay_beta_0                      0.006313     0.006116  0.000036   3.1% ↓
  β₁               experiments[wish_3_8].peak.decay_beta_1                       0.02061      0.02531   0.00050   22.8% ↑
  α₀               experiments[wish_3_8].peak.rise_alpha_0                      -0.01097     -0.01165   0.00076   6.2% ↓
  α₁               experiments[wish_3_8].peak.rise_alpha_1                        0.1187       0.1216    0.0033   2.4% ↑
  ABSCOR1, Å⁻¹     experiments[wish_4_7].absorption.abscor1                      -0.0072     -0.01936   0.00092 ! 168.9% ↓
  intensity        experiments[wish_4_7].background[10].intensity                  348.2        386.1       5.5   10.9% ↑
  intensity        experiments[wish_4_7].background[11].intensity                  389.5        368.7       4.9   5.3% ↓
  intensity        experiments[wish_4_7].background[12].intensity                  350.7        382.9       4.1   9.2% ↑
  intensity        experiments[wish_4_7].background[13].intensity                  334.3        346.4       3.7   3.6% ↑
  intensity        experiments[wish_4_7].background[14].intensity                  329.5        327.7       3.3   0.6% ↓
  intensity        experiments[wish_4_7].background[15].intensity                  283.4        306.8       3.2   8.3% ↑
  intensity        experiments[wish_4_7].background[16].intensity                    352        357.9       3.8   1.7% ↑
  intensity        experiments[wish_4_7].background[17].intensity                  317.6        318.4       3.0   0.2% ↑
  intensity        experiments[wish_4_7].background[18].intensity                  306.7        292.8       2.5   4.5% ↓
  intensity        experiments[wish_4_7].background[19].intensity                  251.9        260.5       2.4   3.4% ↑
  intensity        experiments[wish_4_7].background[1].intensity                     375          387        40   3.1% ↑
  intensity        experiments[wish_4_7].background[20].intensity                  262.3        256.6       2.9   2.2% ↓
  intensity        experiments[wish_4_7].background[21].intensity                  245.6        245.4       3.0   0.1% ↓
  intensity        experiments[wish_4_7].background[22].intensity                  263.3        263.4       2.9   
  intensity        experiments[wish_4_7].background[23].intensity                  249.2        250.2       3.1   0.4% ↑
  intensity        experiments[wish_4_7].background[24].intensity                  259.2        257.2       3.7   0.8% ↓
  intensity        experiments[wish_4_7].background[25].intensity                  259.9        257.3       4.7   1.0% ↓
  intensity        experiments[wish_4_7].background[26].intensity                  248.6        253.9       6.1   2.1% ↑
  intensity        experiments[wish_4_7].background[27].intensity                    252          258        11   2.5% ↑
  intensity        experiments[wish_4_7].background[28].intensity                    246          241        28   1.9% ↓
  intensity        experiments[wish_4_7].background[2].intensity                     434          445        30   2.6% ↑
  intensity        experiments[wish_4_7].background[3].intensity                     408          419        23   2.8% ↑
  intensity        experiments[wish_4_7].background[4].intensity                     430          458        19   6.6% ↑
  intensity        experiments[wish_4_7].background[5].intensity                     462          465        14   0.6% ↑
  intensity        experiments[wish_4_7].background[6].intensity                     383          407        11   6.3% ↑
  intensity        experiments[wish_4_7].background[7].intensity                     405        407.9       9.7   0.7% ↑
  intensity        experiments[wish_4_7].background[8].intensity                     370        384.2       8.5   3.8% ↑
  intensity        experiments[wish_4_7].background[9].intensity                     413        444.7       8.5   7.7% ↑
  TOF linear, µs/Å experiments[wish_4_7].instrument.calib_d_to_tof_linear         1.87e4   1.866085e40.000031e4   
  TOF offset, µs   experiments[wish_4_7].instrument.calib_d_to_tof_offset         -18.33       -16.62      0.44   9.3% ↑
  scale            experiments[wish_4_7].linked_structures[ncaf].scale             31.87        29.42      0.19 ! 7.7% ↓
  σ₁², µs²/Å²      experiments[wish_4_7].peak.broad_gauss_sigma_1                   22.8         28.0       4.7   23.0% ↑
  σ₂², µs²/Å⁴      experiments[wish_4_7].peak.broad_gauss_sigma_2                   19.7        18.79      0.97   4.6% ↓
  β₀               experiments[wish_4_7].peak.decay_beta_0                      0.006736     0.006636  0.000030   1.5% ↓
  β₁               experiments[wish_4_7].peak.decay_beta_1                       0.00968      0.01178   0.00024   21.7% ↑
  α₀               experiments[wish_4_7].peak.rise_alpha_0                       -0.0098     -0.01055   0.00091   7.6% ↓
  α₁               experiments[wish_4_7].peak.rise_alpha_1                        0.1167       0.1197    0.0029   2.6% ↑
  ABSCOR1, Å⁻¹     experiments[wish_5_6].absorption.abscor1                      -0.0135     -0.01693   0.00093 ! 25.4% ↓
  intensity        experiments[wish_5_6].background[10].intensity                    401        430.2       9.7   7.3% ↑
  intensity        experiments[wish_5_6].background[11].intensity                  415.4        429.5       7.2   3.4% ↑
  intensity        experiments[wish_5_6].background[12].intensity                  346.4        376.1       4.7   8.6% ↑
  intensity        experiments[wish_5_6].background[13].intensity                    391        365.6       4.3   6.5% ↓
  intensity        experiments[wish_5_6].background[14].intensity                    353        378.3       3.5   7.2% ↑
  intensity        experiments[wish_5_6].background[15].intensity                  337.9        344.1       3.1   1.8% ↑
  intensity        experiments[wish_5_6].background[16].intensity                  322.8        324.6       2.9   0.5% ↑
  intensity        experiments[wish_5_6].background[17].intensity                  294.9        312.0       2.8   5.8% ↑
  intensity        experiments[wish_5_6].background[18].intensity                  326.1        324.6       2.8   0.5% ↓
  intensity        experiments[wish_5_6].background[19].intensity                  300.1        286.0       2.7   4.7% ↓
  intensity        experiments[wish_5_6].background[1].intensity                     491          499        25   1.6% ↑
  intensity        experiments[wish_5_6].background[20].intensity                  266.2        273.9       2.9   2.9% ↑
  intensity        experiments[wish_5_6].background[21].intensity                  253.9        256.6       2.9   1.1% ↑
  intensity        experiments[wish_5_6].background[22].intensity                  263.3        260.1       3.0   1.2% ↓
  intensity        experiments[wish_5_6].background[23].intensity                  258.8        260.2       3.2   0.5% ↑
  intensity        experiments[wish_5_6].background[24].intensity                  261.6        261.9       3.9   0.1% ↑
  intensity        experiments[wish_5_6].background[25].intensity                  258.6        261.9       4.7   1.3% ↑
  intensity        experiments[wish_5_6].background[26].intensity                  269.1        268.1       4.6   0.4% ↓
  intensity        experiments[wish_5_6].background[27].intensity                  269.2        268.0       5.8   0.4% ↓
  intensity        experiments[wish_5_6].background[28].intensity                    261          262        13   0.6% ↑
  intensity        experiments[wish_5_6].background[2].intensity                     426          425        19   0.2% ↓
  intensity        experiments[wish_5_6].background[3].intensity                     385          386        32   0.3% ↑
  intensity        experiments[wish_5_6].background[4].intensity                     455          481        15   5.8% ↑
  intensity        experiments[wish_5_6].background[5].intensity                     469          460        14   2.0% ↓
  intensity        experiments[wish_5_6].background[6].intensity                     444          449        12   1.1% ↑
  intensity        experiments[wish_5_6].background[7].intensity                     385        398.1       8.3   3.4% ↑
  intensity        experiments[wish_5_6].background[8].intensity                   415.8        413.3       8.0   0.6% ↓
  intensity        experiments[wish_5_6].background[9].intensity                   382.7        377.8       7.5   1.3% ↓
  TOF linear, µs/Å experiments[wish_5_6].instrument.calib_d_to_tof_linear         2.08e4   2.077363e40.000027e4   
  TOF offset, µs   experiments[wish_5_6].instrument.calib_d_to_tof_offset         -15.66       -14.93      0.38   4.7% ↑
  scale            experiments[wish_5_6].linked_structures[ncaf].scale             30.55        29.69      0.21 ! 2.8% ↓
  σ₂², µs²/Å⁴      experiments[wish_5_6].peak.broad_gauss_sigma_2                  15.43        15.84      0.63   2.7% ↑
  β₀               experiments[wish_5_6].peak.decay_beta_0                       0.00688     0.006868  0.000028   0.2% ↓
  β₁               experiments[wish_5_6].peak.decay_beta_1                       0.00688      0.00776   0.00016   12.8% ↑
  α₀               experiments[wish_5_6].peak.rise_alpha_0                      -0.00795     -0.00811   0.00078   2.0% ↓
  α₁               experiments[wish_5_6].peak.rise_alpha_1                        0.1051       0.1066    0.0019   1.4% ↑
  x                structure.atom_sites[Al1].fract_x                             0.25000      0.25292   0.00026   1.2% ↑
  x                structure.atom_sites[Ca1].fract_x                             0.47000      0.46663   0.00016   0.7% ↓
  x                structure.atom_sites[F1].fract_x                              0.14000     0.137172  0.000099   2.0% ↓
  y                structure.atom_sites[F1].fract_y                              0.31000     0.304832  0.000096   1.7% ↓
  z                structure.atom_sites[F1].fract_z                              0.12000      0.11899   0.00012   0.8% ↓
  x                structure.atom_sites[F2].fract_x                              0.36000      0.36238   0.00014   0.7% ↑
  y                structure.atom_sites[F2].fract_y                              0.36000      0.36343   0.00011   1.0% ↑
  z                structure.atom_sites[F2].fract_z                              0.19000      0.18614   0.00011   2.0% ↓
  x                structure.atom_sites[F3].fract_x                              0.46000     0.461473  0.000072   0.3% ↑
  x                structure.atom_sites[Na1].fract_x                             0.09000      0.08396   0.00014   6.7% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[wish_1_10].background[2].intensity: s.u. larger than the value
      experiments[wish_4_7].absorption.abscor1: strongly correlated with ncaf scale (wish_4_7) (r = 0.95)
      experiments[wish_4_7].linked_structures[ncaf].scale: strongly correlated with ABSCOR1 (wish_4_7) (r = 0.95)
      experiments[wish_5_6].absorption.abscor1: strongly correlated with ncaf scale (wish_5_6) (r = 0.96)
      experiments[wish_5_6].linked_structures[ncaf].scale: strongly correlated with ABSCOR1 (wish_5_6) (r = 0.96)
```

## Displacements

In `structures/ncaf.edi`, add `()` after the values the stage frees:

```edi
Ca1 Ca 0.46663() 0 0.25 b 12 1 0.5() Biso
F1 F 0.137172() 0.304832() 0.11899() c 24 1 0.5() Biso
```

The same for every other row (2 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ncaf-wish --verbosity full
    ```

```text
edi fit: joint project pd-neut-tof_ncaf-wish, 5 banks (wish_1_10, wish_2_9, wish_3_8, wish_4_7, wish_5_6), 18973 pts fitted / 20475 loaded, 193 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        8.07        10.43
      1      9.361      7.69         9.50   9.0% ↓
      2     10.462      7.69         9.50   
  done · converged · 2 iters · reduced χ² 9.50 · Rwp 7.69 % · 11.45 s

  per-bank Rwp (%):   wish_1_10 4.65   wish_2_9 6.44   wish_3_8 7.89   wish_4_7 8.10   wish_5_6 8.28

  refined parameters (193 free):
  name             parameter                                                       start        value      s.u.   change
  intensity        experiments[wish_1_10].background[10].intensity                   201          212        19   5.3% ↑
  intensity        experiments[wish_1_10].background[11].intensity                   253          256        13   1.0% ↑
  intensity        experiments[wish_1_10].background[12].intensity                   225          231        12   2.7% ↑
  intensity        experiments[wish_1_10].background[13].intensity                 217.9        220.9       8.9   1.4% ↑
  intensity        experiments[wish_1_10].background[14].intensity                 231.8        232.5       7.4   0.3% ↑
  intensity        experiments[wish_1_10].background[15].intensity                 235.8        237.4       5.1   0.7% ↑
  intensity        experiments[wish_1_10].background[16].intensity                   238        234.7       4.1   1.4% ↓
  intensity        experiments[wish_1_10].background[17].intensity                   240        238.8       3.3   0.5% ↓
  intensity        experiments[wish_1_10].background[18].intensity                 226.5        226.7       2.9   0.1% ↑
  intensity        experiments[wish_1_10].background[19].intensity                 221.4        221.7       2.9   0.1% ↑
  intensity        experiments[wish_1_10].background[20].intensity                 229.3        227.6       2.9   0.7% ↓
  intensity        experiments[wish_1_10].background[21].intensity                 224.9        224.7       2.1   0.1% ↓
  intensity        experiments[wish_1_10].background[22].intensity                 216.2        216.3       2.1   
  intensity        experiments[wish_1_10].background[23].intensity                 216.9        216.9       2.4   
  intensity        experiments[wish_1_10].background[24].intensity                 213.5        213.5       2.6   
  intensity        experiments[wish_1_10].background[25].intensity                 216.2        216.2       3.0   
  intensity        experiments[wish_1_10].background[26].intensity                   213        213.0       3.3   
  intensity        experiments[wish_1_10].background[27].intensity                 212.4        212.4       3.9   
  intensity        experiments[wish_1_10].background[28].intensity                 212.6        212.6       4.5   
  intensity        experiments[wish_1_10].background[29].intensity                 211.3        211.3       5.5   
  intensity        experiments[wish_1_10].background[2].intensity                     65          119        67   83.5% ↑
  intensity        experiments[wish_1_10].background[30].intensity                   211        211.0       6.8   
  intensity        experiments[wish_1_10].background[31].intensity                 222.9        222.9       8.6   
  intensity        experiments[wish_1_10].background[32].intensity                   210          210        12   0.2% ↑
  intensity        experiments[wish_1_10].background[33].intensity                   222          222        18   0.1% ↑
  intensity        experiments[wish_1_10].background[34].intensity                   255          255        27   
  intensity        experiments[wish_1_10].background[35].intensity                   120          120        35   0.3% ↓
  intensity        experiments[wish_1_10].background[3].intensity                    117          147        45   25.4% ↑
  intensity        experiments[wish_1_10].background[4].intensity                     79          125        44   58.2% ↑
  intensity        experiments[wish_1_10].background[5].intensity                    248          292        53   17.7% ↑
  intensity        experiments[wish_1_10].background[6].intensity                    176          204        35   15.7% ↑
  intensity        experiments[wish_1_10].background[7].intensity                    126          171        36   36.0% ↑
  intensity        experiments[wish_1_10].background[8].intensity                    221          236        30   6.8% ↑
  intensity        experiments[wish_1_10].background[9].intensity                    208          217        22   4.2% ↑
  TOF linear, µs/Å experiments[wish_1_10].instrument.calib_d_to_tof_linear        4.99e3    4.98527e3 0.00089e3   
  TOF offset, µs   experiments[wish_1_10].instrument.calib_d_to_tof_offset          13.2         13.7       3.2   3.6% ↑
  scale            experiments[wish_1_10].linked_structures[ncaf].scale            37.71        37.07      0.35   1.7% ↓
  ABSCOR1, Å⁻¹     experiments[wish_2_9].absorption.abscor1                      -0.0313      -0.0039    0.0019   87.5% ↑
  intensity        experiments[wish_2_9].background[10].intensity                    281        281.6       3.1   0.2% ↑
  intensity        experiments[wish_2_9].background[11].intensity                  266.2        265.4       3.1   0.3% ↓
  intensity        experiments[wish_2_9].background[12].intensity                    259        259.4       2.2   0.2% ↑
  intensity        experiments[wish_2_9].background[13].intensity                  253.3        253.7       1.9   0.2% ↑
  intensity        experiments[wish_2_9].background[14].intensity                  237.5        237.4       1.8   
  intensity        experiments[wish_2_9].background[15].intensity                  227.9        227.9       1.6   
  intensity        experiments[wish_2_9].background[16].intensity                  221.4        221.1       2.0   0.1% ↓
  intensity        experiments[wish_2_9].background[17].intensity                  219.7        220.3       2.6   0.3% ↑
  intensity        experiments[wish_2_9].background[18].intensity                  224.2        226.2       3.6   0.9% ↑
  intensity        experiments[wish_2_9].background[19].intensity                  219.5        218.8       4.8   0.3% ↓
  intensity        experiments[wish_2_9].background[1].intensity                     129          250        46   94.2% ↑
  intensity        experiments[wish_2_9].background[20].intensity                  219.8        220.1       7.3   0.1% ↑
  intensity        experiments[wish_2_9].background[21].intensity                    219          219        13   0.2% ↓
  intensity        experiments[wish_2_9].background[22].intensity                    164          164        31   0.2% ↑
  intensity        experiments[wish_2_9].background[2].intensity                     207          270        35   30.5% ↑
  intensity        experiments[wish_2_9].background[3].intensity                     320          378        25   18.1% ↑
  intensity        experiments[wish_2_9].background[4].intensity                     367          385        15   4.9% ↑
  intensity        experiments[wish_2_9].background[5].intensity                     333          338        11   1.4% ↑
  intensity        experiments[wish_2_9].background[6].intensity                   323.9        332.2       9.1   2.6% ↑
  intensity        experiments[wish_2_9].background[7].intensity                   363.4        366.5       7.8   0.8% ↑
  intensity        experiments[wish_2_9].background[8].intensity                   391.3        392.1       6.1   0.2% ↑
  intensity        experiments[wish_2_9].background[9].intensity                   343.5        342.2       4.9   0.4% ↓
  TOF linear, µs/Å experiments[wish_2_9].instrument.calib_d_to_tof_linear         1.04e4   1.038975e40.000083e4   
  TOF offset, µs   experiments[wish_2_9].instrument.calib_d_to_tof_offset           17.6         13.8       1.6   21.6% ↓
  scale            experiments[wish_2_9].linked_structures[ncaf].scale             29.96        36.18      0.40   20.8% ↑
  σ₁², µs²/Å²      experiments[wish_2_9].peak.broad_gauss_sigma_1                     67           71        12   5.4% ↑
  σ₂², µs²/Å⁴      experiments[wish_2_9].peak.broad_gauss_sigma_2                  23.45        22.97      0.90   2.0% ↓
  γ₁, µs/Å         experiments[wish_2_9].peak.broad_lorentz_gamma_1                 1.86         1.69      0.55   9.1% ↓
  β₀               experiments[wish_2_9].peak.decay_beta_0                      0.005335     0.005325  0.000049   0.2% ↓
  β₁               experiments[wish_2_9].peak.decay_beta_1                        0.0823       0.0823    0.0018   
  α₀               experiments[wish_2_9].peak.rise_alpha_0                        0.0544       0.0407    0.0068   25.3% ↓
  α₁               experiments[wish_2_9].peak.rise_alpha_1                       -0.0053        0.024     0.011   553.9% ↑
  ABSCOR1, Å⁻¹     experiments[wish_3_8].absorption.abscor1                      -0.0223       0.0011    0.0013 ! 105.0% ↑
  intensity        experiments[wish_3_8].background[10].intensity                  353.8        353.4       2.9   0.1% ↓
  intensity        experiments[wish_3_8].background[11].intensity                  300.1        298.4       2.7   0.6% ↓
  intensity        experiments[wish_3_8].background[12].intensity                  284.7        283.4       2.3   0.4% ↓
  intensity        experiments[wish_3_8].background[13].intensity                  254.1        253.7       2.0   0.2% ↓
  intensity        experiments[wish_3_8].background[14].intensity                  253.9        254.3       2.0   0.2% ↑
  intensity        experiments[wish_3_8].background[15].intensity                  235.5        235.3       2.1   0.1% ↓
  intensity        experiments[wish_3_8].background[16].intensity                  240.6        240.6       2.4   
  intensity        experiments[wish_3_8].background[17].intensity                  239.3        239.3       2.9   
  intensity        experiments[wish_3_8].background[18].intensity                  242.8        242.9       4.2   0.1% ↑
  intensity        experiments[wish_3_8].background[19].intensity                    241        241.1       5.6   
  intensity        experiments[wish_3_8].background[1].intensity                     342          441        34   28.9% ↑
  intensity        experiments[wish_3_8].background[20].intensity                  235.8        235.3       7.9   0.2% ↓
  intensity        experiments[wish_3_8].background[21].intensity                    236          239        14   1.3% ↑
  intensity        experiments[wish_3_8].background[22].intensity                    239          246        32   2.8% ↑
  intensity        experiments[wish_3_8].background[2].intensity                     417          512        22   22.9% ↑
  intensity        experiments[wish_3_8].background[3].intensity                     378          417        15   10.3% ↑
  intensity        experiments[wish_3_8].background[4].intensity                     427          474        11   11.1% ↑
  intensity        experiments[wish_3_8].background[5].intensity                   383.4        407.5       6.8   6.3% ↑
  intensity        experiments[wish_3_8].background[6].intensity                   369.6        377.5       5.1   2.1% ↑
  intensity        experiments[wish_3_8].background[7].intensity                   342.8        346.1       4.6   1.0% ↑
  intensity        experiments[wish_3_8].background[8].intensity                   325.8        331.8       3.8   1.8% ↑
  intensity        experiments[wish_3_8].background[9].intensity                   335.2        335.9       3.4   0.2% ↑
  TOF linear, µs/Å experiments[wish_3_8].instrument.calib_d_to_tof_linear         1.51e4   1.510528e40.000037e4   
  TOF offset, µs   experiments[wish_3_8].instrument.calib_d_to_tof_offset         -13.46       -12.72      0.62   5.5% ↑
  scale            experiments[wish_3_8].linked_structures[ncaf].scale             29.99        37.35      0.34 ! 24.6% ↑
  σ₁², µs²/Å²      experiments[wish_3_8].peak.broad_gauss_sigma_1                   64.3         62.4       5.7   3.0% ↓
  σ₂², µs²/Å⁴      experiments[wish_3_8].peak.broad_gauss_sigma_2                  17.01        16.85      0.90   0.9% ↓
  β₀               experiments[wish_3_8].peak.decay_beta_0                      0.006116     0.005990  0.000036   2.1% ↓
  β₁               experiments[wish_3_8].peak.decay_beta_1                       0.02531      0.02767   0.00053   9.3% ↑
  α₀               experiments[wish_3_8].peak.rise_alpha_0                      -0.01165     -0.01216   0.00074   4.4% ↓
  α₁               experiments[wish_3_8].peak.rise_alpha_1                        0.1216       0.1230    0.0032   1.1% ↑
  ABSCOR1, Å⁻¹     experiments[wish_4_7].absorption.abscor1                      -0.0194       0.0044    0.0013 ! 122.9% ↑
  intensity        experiments[wish_4_7].background[10].intensity                  386.1        396.0       5.3   2.6% ↑
  intensity        experiments[wish_4_7].background[11].intensity                  368.7        391.3       4.7   6.1% ↑
  intensity        experiments[wish_4_7].background[12].intensity                  382.9        384.8       4.0   0.5% ↑
  intensity        experiments[wish_4_7].background[13].intensity                  346.4        349.1       3.6   0.8% ↑
  intensity        experiments[wish_4_7].background[14].intensity                  327.7        331.6       3.1   1.2% ↑
  intensity        experiments[wish_4_7].background[15].intensity                  306.8        308.6       3.1   0.6% ↑
  intensity        experiments[wish_4_7].background[16].intensity                  357.9        355.2       3.6   0.7% ↓
  intensity        experiments[wish_4_7].background[17].intensity                  318.4        317.6       2.9   0.3% ↓
  intensity        experiments[wish_4_7].background[18].intensity                  292.8        289.9       2.4   1.0% ↓
  intensity        experiments[wish_4_7].background[19].intensity                  260.5        259.8       2.3   0.3% ↓
  intensity        experiments[wish_4_7].background[1].intensity                     387          488        38   26.1% ↑
  intensity        experiments[wish_4_7].background[20].intensity                  256.6        255.7       2.7   0.4% ↓
  intensity        experiments[wish_4_7].background[21].intensity                  245.4        245.6       2.9   0.1% ↑
  intensity        experiments[wish_4_7].background[22].intensity                  263.4        263.8       2.7   0.2% ↑
  intensity        experiments[wish_4_7].background[23].intensity                  250.2        250.3       3.0   
  intensity        experiments[wish_4_7].background[24].intensity                  257.2        257.6       3.6   0.1% ↑
  intensity        experiments[wish_4_7].background[25].intensity                  257.3        257.4       4.4   
  intensity        experiments[wish_4_7].background[26].intensity                  253.9        254.5       5.8   0.3% ↑
  intensity        experiments[wish_4_7].background[27].intensity                    258          260        11   0.6% ↑
  intensity        experiments[wish_4_7].background[28].intensity                    241          240        26   0.2% ↓
  intensity        experiments[wish_4_7].background[2].intensity                     445          566        28   27.1% ↑
  intensity        experiments[wish_4_7].background[3].intensity                     419          494        22   17.8% ↑
  intensity        experiments[wish_4_7].background[4].intensity                     458          559        18   22.0% ↑
  intensity        experiments[wish_4_7].background[5].intensity                     465          529        14   13.8% ↑
  intensity        experiments[wish_4_7].background[6].intensity                     407          445        11   9.4% ↑
  intensity        experiments[wish_4_7].background[7].intensity                   407.9        459.6       9.4   12.7% ↑
  intensity        experiments[wish_4_7].background[8].intensity                   384.2        412.5       8.1   7.4% ↑
  intensity        experiments[wish_4_7].background[9].intensity                   444.7        510.9       8.2   14.9% ↑
  TOF linear, µs/Å experiments[wish_4_7].instrument.calib_d_to_tof_linear         1.87e4   1.865999e40.000032e4   
  TOF offset, µs   experiments[wish_4_7].instrument.calib_d_to_tof_offset         -16.62       -15.06      0.49   9.4% ↑
  scale            experiments[wish_4_7].linked_structures[ncaf].scale             29.42        37.93      0.38 ! 28.9% ↑
  σ₁², µs²/Å²      experiments[wish_4_7].peak.broad_gauss_sigma_1                     28         29.3       4.6   4.8% ↑
  σ₂², µs²/Å⁴      experiments[wish_4_7].peak.broad_gauss_sigma_2                  18.79        18.20      0.98   3.1% ↓
  β₀               experiments[wish_4_7].peak.decay_beta_0                      0.006636     0.006428  0.000030   3.1% ↓
  β₁               experiments[wish_4_7].peak.decay_beta_1                       0.01178      0.01467   0.00029   24.6% ↑
  α₀               experiments[wish_4_7].peak.rise_alpha_0                      -0.01055     -0.01160   0.00089   10.0% ↓
  α₁               experiments[wish_4_7].peak.rise_alpha_1                        0.1197       0.1228    0.0029   2.6% ↑
  ABSCOR1, Å⁻¹     experiments[wish_5_6].absorption.abscor1                      -0.0169       0.0100    0.0014 ! 159.0% ↑
  intensity        experiments[wish_5_6].background[10].intensity                  430.2        477.7       9.3   11.0% ↑
  intensity        experiments[wish_5_6].background[11].intensity                  429.5        484.2       7.0   12.7% ↑
  intensity        experiments[wish_5_6].background[12].intensity                  376.1        381.6       4.5   1.5% ↑
  intensity        experiments[wish_5_6].background[13].intensity                  365.6        386.1       4.1   5.6% ↑
  intensity        experiments[wish_5_6].background[14].intensity                  378.3        378.1       3.5   0.1% ↓
  intensity        experiments[wish_5_6].background[15].intensity                  344.1        344.0       3.0   
  intensity        experiments[wish_5_6].background[16].intensity                  324.6        327.2       2.8   0.8% ↑
  intensity        experiments[wish_5_6].background[17].intensity                    312        309.7       2.7   0.7% ↓
  intensity        experiments[wish_5_6].background[18].intensity                  324.6        322.7       2.7   0.6% ↓
  intensity        experiments[wish_5_6].background[19].intensity                    286        283.7       2.6   0.8% ↓
  intensity        experiments[wish_5_6].background[1].intensity                     499          613        24   22.8% ↑
  intensity        experiments[wish_5_6].background[20].intensity                  273.9        271.8       2.8   0.8% ↓
  intensity        experiments[wish_5_6].background[21].intensity                  256.6        257.2       2.8   0.2% ↑
  intensity        experiments[wish_5_6].background[22].intensity                  260.1        259.4       2.9   0.3% ↓
  intensity        experiments[wish_5_6].background[23].intensity                  260.2        261.2       3.1   0.4% ↑
  intensity        experiments[wish_5_6].background[24].intensity                  261.9        262.2       3.7   0.1% ↑
  intensity        experiments[wish_5_6].background[25].intensity                  261.9        263.0       4.5   0.4% ↑
  intensity        experiments[wish_5_6].background[26].intensity                  268.1        268.5       4.4   0.1% ↑
  intensity        experiments[wish_5_6].background[27].intensity                    268        269.1       5.5   0.4% ↑
  intensity        experiments[wish_5_6].background[28].intensity                    262          261        12   0.2% ↓
  intensity        experiments[wish_5_6].background[2].intensity                     425          512        18   20.5% ↑
  intensity        experiments[wish_5_6].background[3].intensity                     386          474        31   22.7% ↑
  intensity        experiments[wish_5_6].background[4].intensity                     481          561        15   16.5% ↑
  intensity        experiments[wish_5_6].background[5].intensity                     460          551        13   19.8% ↑
  intensity        experiments[wish_5_6].background[6].intensity                     449          509        11   13.3% ↑
  intensity        experiments[wish_5_6].background[7].intensity                   398.1        434.5       7.9   9.1% ↑
  intensity        experiments[wish_5_6].background[8].intensity                   413.3        465.2       7.9   12.6% ↑
  intensity        experiments[wish_5_6].background[9].intensity                   377.8        400.5       7.2   6.0% ↑
  TOF linear, µs/Å experiments[wish_5_6].instrument.calib_d_to_tof_linear         2.08e4   2.077292e40.000028e4   
  TOF offset, µs   experiments[wish_5_6].instrument.calib_d_to_tof_offset         -14.93       -13.71      0.42   8.2% ↑
  scale            experiments[wish_5_6].linked_structures[ncaf].scale             29.69        39.76      0.45 ! 33.9% ↑
  σ₂², µs²/Å⁴      experiments[wish_5_6].peak.broad_gauss_sigma_2                  15.84        15.71      0.61   0.8% ↓
  β₀               experiments[wish_5_6].peak.decay_beta_0                      0.006868     0.006673  0.000027   2.8% ↓
  β₁               experiments[wish_5_6].peak.decay_beta_1                       0.00776      0.01007   0.00020   29.7% ↑
  α₀               experiments[wish_5_6].peak.rise_alpha_0                      -0.00811     -0.00950   0.00078   17.1% ↓
  α₁               experiments[wish_5_6].peak.rise_alpha_1                        0.1066       0.1102    0.0019   3.4% ↑
  B iso, Å²        structure.atom_sites[Al1].adp_iso                               0.500        0.913     0.047   82.7% ↑
  x                structure.atom_sites[Al1].fract_x                             0.25292      0.25196   0.00029   0.4% ↓
  B iso, Å²        structure.atom_sites[Ca1].adp_iso                               0.500        1.016     0.046   103.3% ↑
  x                structure.atom_sites[Ca1].fract_x                             0.46663      0.46646   0.00017   
  B iso, Å²        structure.atom_sites[F1].adp_iso                                0.500        1.015     0.034   103.0% ↑
  x                structure.atom_sites[F1].fract_x                              0.13717      0.13758   0.00012   0.3% ↑
  y                structure.atom_sites[F1].fract_y                              0.30483      0.30553   0.00011   0.2% ↑
  z                structure.atom_sites[F1].fract_z                              0.11899      0.11961   0.00013   0.5% ↑
  B iso, Å²        structure.atom_sites[F2].adp_iso                                0.500        1.526     0.040   205.2% ↑
  x                structure.atom_sites[F2].fract_x                              0.36238      0.36229   0.00016   
  y                structure.atom_sites[F2].fract_y                              0.36343      0.36316   0.00013   0.1% ↓
  z                structure.atom_sites[F2].fract_z                              0.18614      0.18696   0.00013   0.4% ↑
  B iso, Å²        structure.atom_sites[F3].adp_iso                                0.500        1.026     0.047   105.2% ↑
  x                structure.atom_sites[F3].fract_x                              0.46147     0.461083  0.000073   0.1% ↓
  B iso, Å²        structure.atom_sites[Na1].adp_iso                               0.500        2.353     0.096   370.5% ↑
  x                structure.atom_sites[Na1].fract_x                             0.08396      0.08517   0.00016   1.4% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[wish_3_8].absorption.abscor1: strongly correlated with ncaf scale (wish_3_8) (r = 0.95)
      experiments[wish_3_8].linked_structures[ncaf].scale: strongly correlated with ABSCOR1 (wish_3_8) (r = 0.95)
      experiments[wish_4_7].absorption.abscor1: strongly correlated with ncaf scale (wish_4_7) (r = 0.95)
      experiments[wish_4_7].linked_structures[ncaf].scale: strongly correlated with ABSCOR1 (wish_4_7) (r = 0.95)
      experiments[wish_5_6].absorption.abscor1: strongly correlated with ncaf scale (wish_5_6) (r = 0.96)
      experiments[wish_5_6].linked_structures[ncaf].scale: strongly correlated with ABSCOR1 (wish_5_6) (r = 0.96)
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-neut-tof_ncaf-wish --output pd-neut-tof_ncaf-wish.html
    ```
