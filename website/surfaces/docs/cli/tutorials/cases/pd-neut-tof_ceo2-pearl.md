# Calibration fit: CeO₂, PEARL

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_ceo2-pearl
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_ceo2-pearl
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/pearl.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_d_to_tof_offset 0
_instrument.calib_d_to_tof_linear 4680
_instrument.calib_d_to_tof_quadratic 1.7621
_peak.rise_alpha_1 0.3
_peak.decay_beta_0 0.03
_peak.decay_beta_1 0.03
_peak.broad_gauss_sigma_1 80
_peak.broad_gauss_sigma_2 4
_peak.broad_lorentz_gamma_1 5
_absorption.abscor1 0
1 0 2200
2 1 0
```

The same for every other row (5 more).

In `structures/ceo2.edi`, remove the `()` from every value; they now read:

```edi
Ce Ce 0 0 0 a 4 1 0.5 Biso
O O 0.25 0.25 0.25 c 8 1 0.5 Biso
```

## Scale and time-of-flight calibration

CeO₂ is the calibration standard, so its cell stays fixed and the DIFC terms put the peaks in
place.

In `experiments/pearl.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
_instrument.calib_d_to_tof_linear 4680()
_instrument.calib_d_to_tof_quadratic 1.7621()
ceo2 2000() 1.0
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

```text
edi fit: project pd-neut-tof_ceo2-pearl, 2237 pts fitted / 2524 loaded, 4 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       14.20        27.73
      1      0.006     13.04        23.36   15.8% ↓
      2      0.010     13.03        23.34   0.1% ↓
      3      0.015     13.03        23.34   
      4      0.022     13.03        23.34   
  done · converged · 4 iters · reduced χ² 23.34 · Rwp 13.03 % · 0.03 s

  refined parameters (4 free):
  name                 parameter                                               start        value      s.u.   change
  TOF linear, µs/Å     experiment.instrument.calib_d_to_tof_linear            4.68e3    4.67987e3 0.00089e3   
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset                 0         1.59      0.51   
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic         1.7621         1.53      0.34   13.2% ↓
  scale                experiment.linked_structures[ceo2].scale               2.00e3      2.183e3   0.011e3   9.1% ↑

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

The six polynomial terms follow the level between the peaks.

In `experiments/pearl.edi`, add `()` after the values the stage frees:

```edi
1 0 2200()
2 1 0()
```

The same for every other row (4 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

```text
edi fit: project pd-neut-tof_ceo2-pearl, 2237 pts fitted / 2524 loaded, 10 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.03        23.41
      1      0.009      6.73         6.24   73.4% ↓
      2      0.015      6.73         6.24   
      3      0.025      6.73         6.24   
  done · converged · 3 iters · reduced χ² 6.24 · Rwp 6.73 % · 0.03 s

  refined parameters (10 free):
  name                 parameter                                               start        value      s.u.   change
  coefficient          experiment.background[1].coef                          2.20e3     2.2034e3  0.0084e3   0.2% ↑
  coefficient          experiment.background[2].coef                               0          213        28   
  coefficient          experiment.background[3].coef                               0          363        82   
  coefficient          experiment.background[4].coef                               0     -2.018e3   0.069e3   
  coefficient          experiment.background[5].coef                               0      2.120e3   0.150e3   
  coefficient          experiment.background[6].coef                               0         -650        77   
  TOF linear, µs/Å     experiment.instrument.calib_d_to_tof_linear            4.68e3    4.67926e3 0.00048e3   
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              1.59         2.04      0.27   28.1% ↑
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic           1.53         1.71      0.18   12.0% ↑
  scale                experiment.linked_structures[ceo2].scale               2.18e3     2.1171e3  0.0056e3   3.0% ↓

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Gaussian widths

The Gaussian terms that grow with d spacing.

In `experiments/pearl.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_1 80()
_peak.broad_gauss_sigma_2 4()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

```text
edi fit: project pd-neut-tof_ceo2-pearl, 2237 pts fitted / 2524 loaded, 12 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        6.73         6.24
      1      0.008      6.28         5.44   12.9% ↓
      2      0.012      6.27         5.43   0.1% ↓
      3      0.019      6.27         5.43   
  done · converged · 3 iters · reduced χ² 5.43 · Rwp 6.27 % · 0.02 s

  refined parameters (12 free):
  name                 parameter                                               start        value      s.u.   change
  coefficient          experiment.background[1].coef                          2.20e3     2.1917e3  0.0078e3   0.5% ↓
  coefficient          experiment.background[2].coef                             213          220        26   3.4% ↑
  coefficient          experiment.background[3].coef                             363          359        77   1.1% ↓
  coefficient          experiment.background[4].coef                         -2.02e3     -2.040e3   0.064e3   1.1% ↓
  coefficient          experiment.background[5].coef                          2.12e3      2.130e3   0.140e3   0.4% ↑
  coefficient          experiment.background[6].coef                            -650         -646        72   0.6% ↑
  TOF linear, µs/Å     experiment.instrument.calib_d_to_tof_linear            4.68e3    4.67955e3 0.00047e3   
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              2.04         1.85      0.27   9.1% ↓
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic           1.71         1.73      0.18   1.3% ↑
  scale                experiment.linked_structures[ceo2].scale               2.12e3     2.1338e3  0.0053e3   0.8% ↑
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                        80         91.0       2.0   13.7% ↑
  σ₂², µs²/Å⁴          experiment.peak.broad_gauss_sigma_2                         4         7.71      0.64   92.7% ↑

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Lorentzian width

The Lorentzian term that grows with d spacing.

In `experiments/pearl.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_lorentz_gamma_1 5()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

```text
edi fit: project pd-neut-tof_ceo2-pearl, 2237 pts fitted / 2524 loaded, 13 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        6.27         5.43
      1      0.010      6.19         5.30   2.5% ↓
      2      0.016      6.19         5.30   
      3      0.024      6.19         5.30   
  done · converged · 3 iters · reduced χ² 5.30 · Rwp 6.19 % · 0.03 s

  refined parameters (13 free):
  name                 parameter                                               start        value      s.u.   change
  coefficient          experiment.background[1].coef                          2.19e3     2.1708e3  0.0082e3   1.0% ↓
  coefficient          experiment.background[2].coef                             220          218        26   0.7% ↓
  coefficient          experiment.background[3].coef                             359          369        76   2.7% ↑
  coefficient          experiment.background[4].coef                         -2.04e3     -2.044e3   0.064e3   0.2% ↓
  coefficient          experiment.background[5].coef                          2.13e3      2.140e3   0.140e3   0.6% ↑
  coefficient          experiment.background[6].coef                            -646         -653        71   1.1% ↓
  TOF linear, µs/Å     experiment.instrument.calib_d_to_tof_linear            4.68e3    4.67957e3 0.00046e3   
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              1.85         1.84      0.27   0.4% ↓
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic           1.73         1.72      0.18   0.8% ↓
  scale                experiment.linked_structures[ceo2].scale               2.13e3     2.1588e3  0.0062e3   1.2% ↑
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                        91         80.2       2.5   11.8% ↓
  σ₂², µs²/Å⁴          experiment.peak.broad_gauss_sigma_2                      7.71         7.04      0.63   8.7% ↓
  γ₁, µs/Å             experiment.peak.broad_lorentz_gamma_1                       5         6.35      0.18   27.0% ↑

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Rise and decay

The back-to-back exponentials that shape each time-of-flight peak.

In `experiments/pearl.edi`, add `()` after the values the stage frees:

```edi
_peak.rise_alpha_1 0.3()
_peak.decay_beta_0 0.03()
_peak.decay_beta_1 0.03()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

```text
edi fit: project pd-neut-tof_ceo2-pearl, 2237 pts fitted / 2524 loaded, 16 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        6.19         5.30
      1      0.010      6.02         5.01   5.6% ↓
      2      0.014      5.67         4.45   11.1% ↓
      3      0.018      5.67         4.44   0.3% ↓
      4      0.025      5.67         4.44   
  done · converged · 4 iters · reduced χ² 4.44 · Rwp 5.67 % · 0.03 s

  refined parameters (16 free):
  name                 parameter                                               start        value      s.u.   change
  coefficient          experiment.background[1].coef                          2.17e3     2.1736e3  0.0076e3   0.1% ↑
  coefficient          experiment.background[2].coef                             218          214        24   2.1% ↓
  coefficient          experiment.background[3].coef                             369          416        70   12.6% ↑
  coefficient          experiment.background[4].coef                         -2.04e3     -2.042e3   0.059e3   0.1% ↑
  coefficient          experiment.background[5].coef                          2.14e3      2.080e3   0.130e3   2.6% ↓
  coefficient          experiment.background[6].coef                            -653         -628        65   3.9% ↑
  TOF linear, µs/Å     experiment.instrument.calib_d_to_tof_linear            4.68e3    4.67823e3 0.00055e3   
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              1.84         3.06      0.24   66.2% ↑
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic           1.72         1.74      0.17   0.9% ↑
  scale                experiment.linked_structures[ceo2].scale               2.16e3     2.1482e3  0.0059e3   0.5% ↓
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                      80.2         78.1       3.3   2.7% ↓
  σ₂², µs²/Å⁴          experiment.peak.broad_gauss_sigma_2                      7.04         4.68      0.62   33.6% ↓
  γ₁, µs/Å             experiment.peak.broad_lorentz_gamma_1                    6.35         4.49      0.24   29.3% ↓
  β₀                   experiment.peak.decay_beta_0                             0.03      0.02514   0.00023   16.2% ↓
  β₁                   experiment.peak.decay_beta_1                             0.03      0.02858   0.00061   4.7% ↓
  α₁                   experiment.peak.rise_alpha_1                              0.3        0.228     0.022   24.0% ↓

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Displacements

In `structures/ceo2.edi`, add `()` after the values the stage frees:

```edi
Ce Ce 0 0 0 a 4 1 0.5() Biso
O O 0.25 0.25 0.25 c 8 1 0.5() Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

```text
edi fit: project pd-neut-tof_ceo2-pearl, 2237 pts fitted / 2524 loaded, 18 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        5.67         4.44
      1      0.019      5.30         3.88   12.5% ↓
      2      0.023      5.29         3.88   0.2% ↓
      3      0.029      5.29         3.88   
      4      0.037      5.29         3.88   
  done · converged · 4 iters · reduced χ² 3.88 · Rwp 5.29 % · 0.04 s

  refined parameters (18 free):
  name                 parameter                                               start        value      s.u.   change
  coefficient          experiment.background[1].coef                          2.17e3     2.1718e3  0.0071e3   0.1% ↓
  coefficient          experiment.background[2].coef                             214          211        23   1.2% ↓
  coefficient          experiment.background[3].coef                             416          394        65   5.3% ↓
  coefficient          experiment.background[4].coef                         -2.04e3     -1.922e3   0.056e3   5.9% ↑
  coefficient          experiment.background[5].coef                          2.08e3      1.950e3   0.120e3   6.1% ↓
  coefficient          experiment.background[6].coef                            -628         -587        61   6.5% ↑
  TOF linear, µs/Å     experiment.instrument.calib_d_to_tof_linear            4.68e3    4.67788e3 0.00056e3   
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              3.06         3.05      0.22   0.2% ↓
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic           1.74         1.76      0.16   1.1% ↑
  scale                experiment.linked_structures[ceo2].scale               2.15e3     2.1143e3  0.0066e3   1.6% ↓
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                      78.1         83.7       3.4   7.2% ↑
  σ₂², µs²/Å⁴          experiment.peak.broad_gauss_sigma_2                      4.68         3.56      0.58   23.9% ↓
  γ₁, µs/Å             experiment.peak.broad_lorentz_gamma_1                    4.49         4.91      0.23   9.5% ↑
  β₀                   experiment.peak.decay_beta_0                          0.02514      0.02546   0.00023   1.3% ↑
  β₁                   experiment.peak.decay_beta_1                          0.02858      0.02904   0.00058   1.6% ↑
  α₁                   experiment.peak.rise_alpha_1                            0.228        0.255     0.031   12.0% ↑
  B iso, Å²            structure.atom_sites[Ce].adp_iso                        0.500        0.302     0.011   39.7% ↓
  B iso, Å²            structure.atom_sites[O].adp_iso                         0.500       0.4950    0.0075   1.0% ↓

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Absorption

Absorption weakens the intensities with time of flight, as the displacements do, so it comes
after them, on its own.

In `experiments/pearl.edi`, add `()` after the values the stage frees:

```edi
_absorption.abscor1 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_ceo2-pearl --verbosity full
    ```

```text
edi fit: project pd-neut-tof_ceo2-pearl, 2237 pts fitted / 2524 loaded, 19 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        5.29         3.88
      1      0.025      5.29         3.88   
      2      0.036      5.29         3.88   
  done · converged · 2 iters · reduced χ² 3.88 · Rwp 5.29 % · 0.04 s

  refined parameters (19 free):
  name                 parameter                                               start        value      s.u.   change
  ABSCOR1, Å⁻¹         experiment.absorption.abscor1                          0.0000         3e-4     25e-4   
  coefficient          experiment.background[1].coef                          2.17e3     2.1717e3  0.0071e3   
  coefficient          experiment.background[2].coef                             211          212        23   0.5% ↑
  coefficient          experiment.background[3].coef                             394          394        65   0.1% ↓
  coefficient          experiment.background[4].coef                         -1.92e3     -1.924e3   0.057e3   0.1% ↓
  coefficient          experiment.background[5].coef                          1.95e3      1.960e3   0.120e3   0.3% ↑
  coefficient          experiment.background[6].coef                            -587         -588        62   0.2% ↓
  TOF linear, µs/Å     experiment.instrument.calib_d_to_tof_linear            4.68e3    4.67788e3 0.00056e3   
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              3.05         3.05      0.22   0.1% ↑
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic           1.76         1.76      0.16   0.1% ↑
  scale                experiment.linked_structures[ceo2].scale               2.11e3      2.118e3   0.025e3   0.2% ↑
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                      83.7         83.7       3.4   
  σ₂², µs²/Å⁴          experiment.peak.broad_gauss_sigma_2                      3.56         3.56      0.58   0.1% ↑
  γ₁, µs/Å             experiment.peak.broad_lorentz_gamma_1                    4.91         4.91      0.23   0.1% ↑
  β₀                   experiment.peak.decay_beta_0                          0.02546      0.02546   0.00023   
  β₁                   experiment.peak.decay_beta_1                          0.02904      0.02902   0.00059   0.1% ↓
  α₁                   experiment.peak.rise_alpha_1                            0.255        0.255     0.031   
  B iso, Å²            structure.atom_sites[Ce].adp_iso                        0.302        0.302     0.013   0.1% ↑
  B iso, Å²            structure.atom_sites[O].adp_iso                         0.495        0.496     0.011   0.2% ↑

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
    python -m edi report pd-neut-tof_ceo2-pearl --output pd-neut-tof_ceo2-pearl.html
    ```
