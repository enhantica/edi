# Two-phase fit: La₀.₅Ba₀.₅CoO₃ and Si, McStas

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_lbco-si-mcstas
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_lbco-si-mcstas
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/mcstas.edi`, remove the `()` from every value; they now read:

```edi
_peak.rise_alpha_1 0.01
_peak.decay_beta_0 0.006
_peak.decay_beta_1 0.004
_peak.broad_gauss_sigma_0 50000
_peak.broad_gauss_sigma_1 -50000
_peak.broad_gauss_sigma_2 20000
1 45000 0.23
2 50000 0.23
```

The same for every other row (13 more).

In `structures/lbco.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 3.8909
Co Co 0.5 0.5 0.5 b 1 1 0.5 Biso
O O 0 0.5 0.5 c 3 1 0.5 Biso
```

In `structures/si.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 5.43
```

## Scales and cells

Both phases' scales and cells put the peaks in place and at the right height; the DIFC stays
fixed, as in diffraction-lib's tutorial.

In `experiments/mcstas.edi`, add `()` after the values the stage frees:

```edi
lbco 4() 0.8892011305507715()
si 0.2() 0.11079886944922841()
```

In `structures/lbco.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 3.8909()
```

In `structures/si.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 5.43()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

```text
edi fit: project pd-neut-tof_lbco-si-mcstas, 633 pts fitted / 1000 loaded, 4 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       50.18       398.16
      1      0.104     26.83       113.82   71.4% ↓
      2      0.212     23.13        84.56   25.7% ↓
      3      0.295     23.12        84.52   
      4      0.385     23.12        84.52   
  done · converged · 4 iters · reduced χ² 84.52 · Rwp 23.12 % · 0.43 s

  refined parameters (4 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[lbco].scale                    4        31.87      0.59   696.8% ↑
  scale           experiment.linked_structures[si].scale                    0.2        0.346     0.035   72.9% ↑
  a, Å            structures[lbco].cell.length_a                         3.8909      3.89041   0.00024   
  a, Å            structures[si].cell.length_a                           5.4300       5.4314    0.0024   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

In `experiments/mcstas.edi`, add `()` after the values the stage frees:

```edi
1 45000 0.23()
2 50000 0.23()
```

The same for every other row (11 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

```text
edi fit: project pd-neut-tof_lbco-si-mcstas, 633 pts fitted / 1000 loaded, 17 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       23.12        86.31
      1      0.149     21.09        71.82   16.8% ↓
      2      0.241     21.09        71.82   
      3      0.383     21.09        71.82   
  done · converged · 3 iters · reduced χ² 71.82 · Rwp 21.09 % · 0.45 s

  refined parameters (17 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                      0.23        0.319     0.011   38.6% ↑
  intensity       experiment.background[11].intensity                      0.23        0.196     0.011   14.6% ↓
  intensity       experiment.background[12].intensity                      0.23        0.216     0.013   6.1% ↓
  intensity       experiment.background[13].intensity                      0.23        0.233     0.037   1.2% ↑
  intensity       experiment.background[1].intensity                       0.23        0.258     0.039   12.0% ↑
  intensity       experiment.background[2].intensity                       0.23        0.234     0.038   1.6% ↑
  intensity       experiment.background[3].intensity                       0.23        0.286     0.023   24.3% ↑
  intensity       experiment.background[4].intensity                       0.23        0.253     0.018   10.1% ↑
  intensity       experiment.background[5].intensity                       0.23        0.281     0.017   22.4% ↑
  intensity       experiment.background[6].intensity                       0.23        0.245     0.013   6.5% ↑
  intensity       experiment.background[7].intensity                       0.23        0.246     0.015   6.9% ↑
  intensity       experiment.background[8].intensity                       0.23       0.2344    0.0099   1.9% ↑
  intensity       experiment.background[9].intensity                       0.23       0.2505    0.0094   8.9% ↑
  scale           experiment.linked_structures[lbco].scale                31.87        31.05      0.55   2.6% ↓
  scale           experiment.linked_structures[si].scale                  0.346        0.231     0.035   33.1% ↓
  a, Å            structures[lbco].cell.length_a                         3.8904      3.89039   0.00022   
  a, Å            structures[si].cell.length_a                           5.4314       5.4331    0.0033   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

In `experiments/mcstas.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_0 50000()
_peak.broad_gauss_sigma_1 -50000()
_peak.broad_gauss_sigma_2 20000()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

```text
edi fit: project pd-neut-tof_lbco-si-mcstas, 633 pts fitted / 1000 loaded, 20 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       21.09        72.17
      1      0.154     21.05        71.92   0.4% ↓
      2      0.243     21.05        71.87   0.1% ↓
      3      0.325     21.04        71.81   0.1% ↓
      4      0.407     21.03        71.75   0.1% ↓
      5      0.500     21.02        71.69   0.1% ↓
      6      0.580     21.01        71.62   0.1% ↓
      7      0.658     20.99        71.51   0.2% ↓
      8      0.737     20.97        71.33   0.3% ↓
      9      0.814     20.93        71.09   0.3% ↓
     10      0.890     20.90        70.86   0.3% ↓
     11      0.965     20.88        70.75   0.2% ↓
     12      1.040     20.88        70.73   
     13      1.172     20.88        70.73   
  done · converged · 13 iters · reduced χ² 70.73 · Rwp 20.88 % · 1.22 s

  refined parameters (20 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     0.319        0.323     0.011   1.2% ↑
  intensity       experiment.background[11].intensity                     0.196        0.196     0.010   0.1% ↑
  intensity       experiment.background[12].intensity                     0.216        0.216     0.013   
  intensity       experiment.background[13].intensity                     0.233        0.233     0.037   0.2% ↓
  intensity       experiment.background[1].intensity                      0.258        0.268     0.039   3.8% ↑
  intensity       experiment.background[2].intensity                      0.234        0.246     0.038   5.0% ↑
  intensity       experiment.background[3].intensity                      0.286        0.289     0.022   0.9% ↑
  intensity       experiment.background[4].intensity                      0.253        0.253     0.017   0.1% ↓
  intensity       experiment.background[5].intensity                      0.281        0.281     0.017   
  intensity       experiment.background[6].intensity                      0.245        0.245     0.013   0.2% ↓
  intensity       experiment.background[7].intensity                      0.246        0.249     0.015   1.3% ↑
  intensity       experiment.background[8].intensity                     0.2344       0.2341    0.0098   0.1% ↓
  intensity       experiment.background[9].intensity                     0.2505       0.2504    0.0093   
  scale           experiment.linked_structures[lbco].scale                31.05        30.88      0.55   0.6% ↓
  scale           experiment.linked_structures[si].scale                  0.231        0.216     0.033   6.7% ↓
  σ₀², µs²        experiment.peak.broad_gauss_sigma_0                    5.00e4     2.0300e4  0.9800e4   59.3% ↓
  σ₁², µs²/Å²     experiment.peak.broad_gauss_sigma_1                   -5.00e4     -5.000e3  14.000e3   89.8% ↑
  σ₂², µs²/Å⁴     experiment.peak.broad_gauss_sigma_2                    2.00e4      3.900e3   4.700e3   80.6% ↓
  a, Å            structures[lbco].cell.length_a                         3.8904      3.89039   0.00022   
  a, Å            structures[si].cell.length_a                           5.4331       5.4334    0.0029   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Rise and decay

In `experiments/mcstas.edi`, add `()` after the values the stage frees:

```edi
_peak.rise_alpha_1 0.01()
_peak.decay_beta_0 0.006()
_peak.decay_beta_1 0.004()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

```text
edi fit: project pd-neut-tof_lbco-si-mcstas, 633 pts fitted / 1000 loaded, 23 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       20.88        71.08
      1      0.079     20.86        70.93   0.2% ↓
      2      0.100     20.86        70.93   
      3      0.126     20.86        70.92   
      4      0.150     20.86        70.92   
      5      0.212     20.86        70.92   
  done · converged · 5 iters · reduced χ² 70.92 · Rwp 20.86 % · 0.23 s

  refined parameters (23 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     0.323        0.322     0.011   0.2% ↓
  intensity       experiment.background[11].intensity                     0.196        0.196     0.010   0.1% ↑
  intensity       experiment.background[12].intensity                     0.216        0.216     0.013   
  intensity       experiment.background[13].intensity                     0.233        0.233     0.037   0.1% ↓
  intensity       experiment.background[1].intensity                      0.268        0.269     0.039   0.5% ↑
  intensity       experiment.background[2].intensity                      0.246        0.248     0.038   0.7% ↑
  intensity       experiment.background[3].intensity                      0.289        0.289     0.023   
  intensity       experiment.background[4].intensity                      0.253        0.253     0.017   
  intensity       experiment.background[5].intensity                      0.281        0.281     0.017   0.1% ↑
  intensity       experiment.background[6].intensity                      0.245        0.244     0.013   0.2% ↓
  intensity       experiment.background[7].intensity                      0.249        0.249     0.016   0.2% ↑
  intensity       experiment.background[8].intensity                     0.2341       0.2336    0.0098   0.2% ↓
  intensity       experiment.background[9].intensity                     0.2504       0.2507    0.0093   0.1% ↑
  scale           experiment.linked_structures[lbco].scale                30.88        30.89      0.56   
  scale           experiment.linked_structures[si].scale                  0.216        0.218     0.033   0.8% ↑
  σ₀², µs²        experiment.peak.broad_gauss_sigma_0                    2.03e4     2.1000e4  1.0000e4   3.1% ↑
  σ₁², µs²/Å²     experiment.peak.broad_gauss_sigma_1                   -5.00e3     -5.000e3  15.000e3   5.3% ↑
  σ₂², µs²/Å⁴     experiment.peak.broad_gauss_sigma_2                    3.90e3      3.500e3   4.700e3   9.4% ↓
  β₀              experiment.peak.decay_beta_0                            0.006      0.00547   0.00062   8.8% ↓
  β₁              experiment.peak.decay_beta_1                            0.004       0.0049    0.0014   23.1% ↑
  α₁              experiment.peak.rise_alpha_1                             0.01       0.0104    0.0012   3.9% ↑
  a, Å            structures[lbco].cell.length_a                         3.8904      3.89008   0.00061   
  a, Å            structures[si].cell.length_a                           5.4334       5.4329    0.0029   

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Displacements

Co's and O's; La's, Ba's and Si's stay fixed, as the case's project keeps them.

In `structures/lbco.edi`, add `()` after the values the stage frees:

```edi
Co Co 0.5 0.5 0.5 b 1 1 0.5() Biso
O O 0 0.5 0.5 c 3 1 0.5() Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_lbco-si-mcstas --verbosity full
    ```

```text
edi fit: project pd-neut-tof_lbco-si-mcstas, 633 pts fitted / 1000 loaded, 25 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       20.86        71.16
      1      0.074      7.45         9.08   87.2% ↓
      2      0.095      6.22         6.33   30.3% ↓
      3      0.116      5.98         5.84   7.7% ↓
      4      0.136      5.72         5.36   8.3% ↓
      5      0.156      5.52         4.99   6.8% ↓
      6      0.176      5.43         4.83   3.4% ↓
      7      0.197      5.38         4.73   2.0% ↓
      8      0.217      5.31         4.61   2.6% ↓
      9      0.237      5.22         4.45   3.4% ↓
     10      0.257      5.13         4.30   3.3% ↓
     11      0.277      5.07         4.20   2.2% ↓
     12      0.297      5.05         4.17   0.9% ↓
     13      0.318      5.04         4.16   0.2% ↓
     14      0.339      5.04         4.16   
     15      0.409      5.04         4.16   
  done · converged · 15 iters · reduced χ² 4.16 · Rwp 5.04 % · 0.43 s

  refined parameters (25 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[10].intensity                     0.322       0.2405    0.0029   25.3% ↓
  intensity       experiment.background[11].intensity                     0.196       0.2246    0.0025   14.6% ↑
  intensity       experiment.background[12].intensity                     0.216       0.2211    0.0030   2.4% ↑
  intensity       experiment.background[13].intensity                     0.233       0.2249    0.0089   3.5% ↓
  intensity       experiment.background[1].intensity                      0.269       0.2706    0.0093   0.6% ↑
  intensity       experiment.background[2].intensity                      0.248       0.2618    0.0091   5.5% ↑
  intensity       experiment.background[3].intensity                      0.289       0.2743    0.0054   5.1% ↓
  intensity       experiment.background[4].intensity                      0.253       0.2574    0.0042   1.7% ↑
  intensity       experiment.background[5].intensity                      0.281       0.2494    0.0041   11.3% ↓
  intensity       experiment.background[6].intensity                      0.244       0.2423    0.0032   0.7% ↓
  intensity       experiment.background[7].intensity                      0.249       0.2408    0.0038   3.3% ↓
  intensity       experiment.background[8].intensity                     0.2336       0.2376    0.0024   1.7% ↑
  intensity       experiment.background[9].intensity                     0.2507       0.2379    0.0023   5.1% ↓
  scale           experiment.linked_structures[lbco].scale                30.89        42.53      0.34   37.7% ↑
  scale           experiment.linked_structures[si].scale                  0.218       0.3088    0.0089   41.7% ↑
  σ₀², µs²        experiment.peak.broad_gauss_sigma_0                    2.10e4     4.4600e4  0.3500e4   112.4% ↑
  σ₁², µs²/Å²     experiment.peak.broad_gauss_sigma_1                   -5.00e3    -5.2900e4  0.4500e4   957.7% ↓
  σ₂², µs²/Å⁴     experiment.peak.broad_gauss_sigma_2                    3.50e3     2.3500e4  0.1400e4   570.3% ↑
  β₀              experiment.peak.decay_beta_0                          0.00547      0.00543   0.00015   0.8% ↓
  β₁              experiment.peak.decay_beta_1                           0.0049      0.00412   0.00032   16.0% ↓
  α₁              experiment.peak.rise_alpha_1                           0.0104      0.00989   0.00025   4.9% ↓
  B iso, Å²       structures[lbco].atom_sites[Co].adp_iso                 0.500        0.388     0.096   22.5% ↓
  B iso, Å²       structures[lbco].atom_sites[O].adp_iso                  0.500        2.347     0.032   369.4% ↑
  a, Å            structures[lbco].cell.length_a                         3.8901      3.89027   0.00015   
  a, Å            structures[si].cell.length_a                           5.4329      5.43249   0.00064   

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
    python -m edi report pd-neut-tof_lbco-si-mcstas --output pd-neut-tof_lbco-si-mcstas.html
    ```
