# Rietveld fit: PbSO₄, laboratory X-ray

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit PbSO₄ to the Rietveld round robin's laboratory X-ray pattern, with the Cu K&alpha; doublet
and Bérar-Baldinozzi asymmetry.

It builds the catalogue case `pd-xray-cwl_pbso4-lab` step by step: the same project the command
line fits and the app's Examples open.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p pd-xray-cwl_pbso4-lab/structures pd-xray-cwl_pbso4-lab/experiments pd-xray-cwl_pbso4-lab/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name pd-xray-cwl_pbso4-lab
_metadata.title "PbSO₄ [Pnma] · Laboratory X-ray"
_metadata.description "Rietveld round-robin data · Cu Kα doublet · Bérar-Baldinozzi asymmetry"
_metadata.authors .
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data pd-xray-cwl_pbso4-lab-pbso4
    mv data/pd-xray-cwl_pbso4-lab-pbso4.edi pd-xray-cwl_pbso4-lab/structures/pbso4.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-xray-cwl_pbso4-lab-pbso4
    mv data/pd-xray-cwl_pbso4-lab-pbso4.edi pd-xray-cwl_pbso4-lab/structures/pbso4.edi
    ```

## Define the experiment

Download the experiment into `experiments`: the file declares the instrument, the peak profile, the background, the structures it links and the measured data.

=== "Standalone executable"

    ```console
    edi download-data pd-xray-cwl_pbso4-lab-lab
    mv data/pd-xray-cwl_pbso4-lab-lab.edi pd-xray-cwl_pbso4-lab/experiments/lab.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-xray-cwl_pbso4-lab-lab
    mv data/pd-xray-cwl_pbso4-lab-lab.edi pd-xray-cwl_pbso4-lab/experiments/lab.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_minimizer.type crysta
_minimizer.max_iterations 1000

_fitting_mode.type single

_edi.schema_version 3
```

## Scale and 2θ zero

The 2θ zero first: freed together with the cell from the start, the two pull against each
other and the fit cannot take a step.

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
pbso4 0.001() 1.0
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 2 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                      114.69       551.55
      1      0.112     53.17       118.53   78.5% ↓
      2      0.123     51.27       110.20   7.0% ↓
      3      0.134     49.26       101.75   7.7% ↓
      4      0.145     47.28        93.72   7.9% ↓
      5      0.157     45.50        86.81   7.4% ↓
      6      0.174     44.08        81.48   6.1% ↓
      7      0.190     43.08        77.81   4.5% ↓
      8      0.202     42.43        75.49   3.0% ↓
      9      0.214     42.04        74.09   1.9% ↓
     10      0.225     41.80        73.27   1.1% ↓
     11      0.237     41.67        72.80   0.6% ↓
     12      0.248     41.59        72.54   0.4% ↓
     13      0.261     41.55        72.39   0.2% ↓
     14      0.274     41.53        72.31   0.1% ↓
     15      0.286     41.52        72.27   0.1% ↓
     16      0.298     41.51        72.25   
     17      0.309     41.51        72.23   
     18      0.321     41.50        72.23   
     19      0.333     41.50        72.22   
     20      0.345     41.50        72.22   
     21      0.357     41.50        72.22   
     22      0.369     41.50        72.22   
     23      0.379     41.50        72.22   
     24      0.391     41.50        72.22   
     25      0.416     41.50        72.22   
  done · converged · 25 iters · reduced χ² 72.22 · Rwp 41.50 % · 0.43 s

  refined parameters (2 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0000     -0.10601   0.00045   
  scale           experiment.linked_structures[pbso4].scale               0.001     5.549e-4  0.051e-4   44.5% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Cell

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 8.47()
_cell.length_b 5.39()
_cell.length_c 6.95()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 5 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       41.50        72.26
      1      0.138     32.60        44.59   38.3% ↓
      2      0.153     31.42        41.41   7.1% ↓
      3      0.168     30.72        39.60   4.4% ↓
      4      0.244     30.53        39.10   1.3% ↓
      5      0.265     30.48        38.97   0.3% ↓
      6      0.280     30.42        38.83   0.4% ↓
      7      0.296     30.36        38.68   0.4% ↓
      8      0.312     30.32        38.57   0.3% ↓
      9      0.327     30.29        38.49   0.2% ↓
     10      0.343     30.25        38.40   0.2% ↓
     11      0.359     30.22        38.32   0.2% ↓
     12      0.376     30.20        38.27   0.1% ↓
     13      0.391     30.19        38.22   0.1% ↓
     14      0.416     30.16        38.17   0.1% ↓
     15      0.438     30.13        38.09   0.2% ↓
     16      0.453     30.11        38.03   0.2% ↓
     17      0.468     30.09        37.99   0.1% ↓
     18      0.482     30.08        37.97   
     19      0.496     30.08        37.96   
     20      0.514     30.08        37.96   
     21      0.535     30.08        37.96   
     22      0.556     30.08        37.95   
     23      0.576     30.08        37.95   
     24      0.596     30.08        37.95   
     25      0.629     30.08        37.95   
  done · converged · 25 iters · reduced χ² 37.95 · Rwp 30.08 % · 0.65 s

  refined parameters (5 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.1060     -0.04474   0.00042   57.8% ↑
  scale           experiment.linked_structures[pbso4].scale             5.55e-4     6.419e-4  0.041e-4   15.7% ↑
  a, Å            structure.cell.length_a                                8.4700     8.479620  0.000051 ! 0.1% ↑
  b, Å            structure.cell.length_b                                5.3900     5.398589  0.000078   0.2% ↑
  c, Å            structure.cell.length_c                                6.9500     6.959137  0.000090 ! 0.1% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      structure.cell.length_a: strongly correlated with c (pbso4) (r = -1.00)
      structure.cell.length_c: strongly correlated with a (pbso4) (r = -1.00)
```

## Background

The six Chebyshev terms.

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
1 0 140()
2 1 0()
```

The same for every other row (4 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 11 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       30.08        37.99
      1      0.158     29.27        35.97   5.3% ↓
      2      0.175     29.26        35.97   
      3      0.202     29.26        35.96   
      4      0.224     29.26        35.96   
      5      0.244     29.26        35.96   
      6      0.266     29.26        35.96   
      7      0.283     29.26        35.96   
      8      0.303     29.26        35.95   
      9      0.321     29.24        35.92   0.1% ↓
     10      0.340     29.18        35.75   0.5% ↓
     11      0.358     29.16        35.70   0.1% ↓
     12      0.375     29.15        35.69   
     13      0.391     29.15        35.68   
     14      0.409     29.15        35.68   
     15      0.426     29.15        35.68   
     16      0.441     29.15        35.68   
     17      0.472     29.15        35.68   
  done · converged · 17 iters · reduced χ² 35.68 · Rwp 29.15 % · 0.49 s

  refined parameters (11 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                             140        156.6       1.6   11.9% ↑
  coefficient     experiment.background[2].coef                               0         31.1       2.5   
  coefficient     experiment.background[3].coef                               0          2.6       2.3   
  coefficient     experiment.background[4].coef                               0         22.6       2.2   
  coefficient     experiment.background[5].coef                               0        -15.4       2.0   
  coefficient     experiment.background[6].coef                               0         -2.8       2.0   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0447     -0.04031   0.00064   9.9% ↑
  scale           experiment.linked_structures[pbso4].scale             6.42e-4     6.340e-4  0.042e-4   1.2% ↓
  a, Å            structure.cell.length_a                                8.4796      8.48076   0.00013   
  b, Å            structure.cell.length_b                                5.3986     5.398772  0.000080   
  c, Å            structure.cell.length_c                                6.9591      6.95971   0.00011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.02()
_peak.broad_gauss_v -0.02()
_peak.broad_gauss_w 0.008()
_peak.mixing_eta_0 0.5()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 15 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       29.15        35.71
      1      0.197     13.46         7.62   78.7% ↓
      2      0.216     13.46         7.62   
      3      0.236     13.46         7.62   
      4      0.253     13.46         7.62   
      5      0.290     13.46         7.62   
  done · converged · 5 iters · reduced χ² 7.62 · Rwp 13.46 % · 0.32 s

  refined parameters (15 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                           156.6       111.67      0.98   28.7% ↓
  coefficient     experiment.background[2].coef                            31.1         30.5       1.4   2.0% ↓
  coefficient     experiment.background[3].coef                             2.6         13.2       1.2   408.6% ↑
  coefficient     experiment.background[4].coef                            22.6         10.2       1.1   55.0% ↓
  coefficient     experiment.background[5].coef                           -15.4        -7.18      0.92   53.4% ↑
  coefficient     experiment.background[6].coef                            -2.8        -6.72      0.90   140.1% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0403     -0.04573   0.00048   13.5% ↓
  scale           experiment.linked_structures[pbso4].scale             6.34e-4     8.503e-4  0.026e-4   34.1% ↑
  U, deg²         experiment.peak.broad_gauss_u                            0.02       0.0484    0.0020   141.8% ↑
  V, deg²         experiment.peak.broad_gauss_v                           -0.02      -0.0215    0.0020   7.7% ↓
  W, deg²         experiment.peak.broad_gauss_w                           0.008      0.01047   0.00046   30.9% ↑
  Eta0            experiment.peak.mixing_eta_0                              0.5        0.827     0.011   65.3% ↑
  a, Å            structure.cell.length_a                                8.4808      8.47968   0.00013   
  b, Å            structure.cell.length_b                                5.3988     5.398177  0.000084   
  c, Å            structure.cell.length_c                                6.9597      6.95956   0.00011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak asymmetry

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
_peak.asym_beba_a0 0()
_peak.asym_beba_b0 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 17 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.46         7.62
      1      0.193     12.76         6.84   10.2% ↓
      2      0.218     12.76         6.84   
      3      0.243     12.76         6.84   
      4      0.271     12.76         6.84   
      5      0.294     12.76         6.84   
      6      0.332     12.76         6.84   
  done · converged · 6 iters · reduced χ² 6.84 · Rwp 12.76 % · 0.36 s

  refined parameters (17 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                          111.67       112.16      0.77   0.4% ↑
  coefficient     experiment.background[2].coef                            30.5         31.7       1.1   4.0% ↑
  coefficient     experiment.background[3].coef                            13.2         13.9       1.0   5.4% ↑
  coefficient     experiment.background[4].coef                            10.2        11.18      0.97   9.6% ↑
  coefficient     experiment.background[5].coef                           -7.18        -6.90      0.87   3.9% ↑
  coefficient     experiment.background[6].coef                           -6.72        -6.82      0.85   1.5% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0457      -0.0324    0.0012   29.2% ↑
  scale           experiment.linked_structures[pbso4].scale             8.50e-4     8.533e-4  0.025e-4   0.4% ↑
  A₀              experiment.peak.asym_beba_a0                                0      -0.2155    0.0087   
  B₀              experiment.peak.asym_beba_b0                                0      -0.0344    0.0015   
  U, deg²         experiment.peak.broad_gauss_u                          0.0484       0.0555    0.0020   14.7% ↑
  V, deg²         experiment.peak.broad_gauss_v                         -0.0215      -0.0307    0.0020   43.0% ↓
  W, deg²         experiment.peak.broad_gauss_w                         0.01047      0.01282   0.00046   22.4% ↑
  Eta0            experiment.peak.mixing_eta_0                            0.827        0.820     0.010   0.8% ↓
  a, Å            structure.cell.length_a                                8.4797      8.48072   0.00014   
  b, Å            structure.cell.length_b                                5.3982     5.398856  0.000090   
  c, Å            structure.cell.length_c                                6.9596      6.96041   0.00012   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Lead and sulphur positions

X-rays see the heavy atoms first, so their coordinates come before the oxygens'.

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
Pb Pb 0.19() 0.25 0.17() c 4 1 0.5 Biso
S S 0.07() 0.25 0.68() c 4 1 0.5 Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 21 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       12.76         6.85
      1      0.227     11.93         5.99   12.5% ↓
      2      0.273     11.93         5.99   
  done · converged · 2 iters · reduced χ² 5.99 · Rwp 11.93 % · 0.30 s

  refined parameters (21 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                          112.16       113.25      0.72   1.0% ↑
  coefficient     experiment.background[2].coef                            31.7         35.9       1.1   13.2% ↑
  coefficient     experiment.background[3].coef                            13.9        16.99      0.95   22.3% ↑
  coefficient     experiment.background[4].coef                           11.18        14.62      0.92   30.7% ↑
  coefficient     experiment.background[5].coef                            -6.9        -5.41      0.82   21.6% ↑
  coefficient     experiment.background[6].coef                           -6.82        -5.27      0.80   22.7% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0324      -0.0324    0.0011   
  scale           experiment.linked_structures[pbso4].scale             8.53e-4     8.577e-4  0.023e-4   0.5% ↑
  A₀              experiment.peak.asym_beba_a0                          -0.2155      -0.2056    0.0081   4.6% ↑
  B₀              experiment.peak.asym_beba_b0                          -0.0344      -0.0328    0.0013   4.7% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.0555       0.0566    0.0019   1.9% ↑
  V, deg²         experiment.peak.broad_gauss_v                         -0.0307      -0.0318    0.0018   3.5% ↓
  W, deg²         experiment.peak.broad_gauss_w                         0.01282      0.01293   0.00044   0.8% ↑
  Eta0            experiment.peak.mixing_eta_0                             0.82       0.8287    0.0093   1.1% ↑
  x               structure.atom_sites[Pb].fract_x                      0.19000     0.187750  0.000098   1.2% ↓
  z               structure.atom_sites[Pb].fract_z                      0.17000      0.16779   0.00013   1.3% ↓
  x               structure.atom_sites[S].fract_x                       0.07000      0.06528   0.00056   6.7% ↓
  z               structure.atom_sites[S].fract_z                       0.68000      0.68669   0.00075   1.0% ↑
  a, Å            structure.cell.length_a                                8.4807      8.48070   0.00013   
  b, Å            structure.cell.length_b                                5.3989     5.398877  0.000084   
  c, Å            structure.cell.length_c                                6.9604      6.96043   0.00011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Oxygen positions

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
O1 O 0.91() 0.25 0.6() c 4 1 0.5 Biso
O2 O 0.19() 0.25 0.54() c 4 1 0.5 Biso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 28 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.93         6.00
      1      0.245     11.83         5.90   1.7% ↓
      2      0.295     11.83         5.90   
  done · converged · 2 iters · reduced χ² 5.90 · Rwp 11.83 % · 0.33 s

  refined parameters (28 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                          113.25       112.46      0.73   0.7% ↓
  coefficient     experiment.background[2].coef                            35.9         35.5       1.1   1.2% ↓
  coefficient     experiment.background[3].coef                           16.99        16.98      0.95   0.1% ↓
  coefficient     experiment.background[4].coef                           14.62        14.04      0.92   4.0% ↓
  coefficient     experiment.background[5].coef                           -5.41        -5.43      0.82   0.4% ↓
  coefficient     experiment.background[6].coef                           -5.27        -5.37      0.80   1.9% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0324      -0.0327    0.0011   0.9% ↓
  scale           experiment.linked_structures[pbso4].scale             8.58e-4     8.600e-4  0.023e-4   0.3% ↑
  A₀              experiment.peak.asym_beba_a0                          -0.2056      -0.2020    0.0081   1.8% ↑
  B₀              experiment.peak.asym_beba_b0                          -0.0328      -0.0323    0.0013   1.4% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.0566       0.0560    0.0019   1.0% ↓
  V, deg²         experiment.peak.broad_gauss_v                         -0.0318      -0.0313    0.0018   1.5% ↑
  W, deg²         experiment.peak.broad_gauss_w                         0.01293      0.01288   0.00043   0.4% ↓
  Eta0            experiment.peak.mixing_eta_0                           0.8287       0.8283    0.0093   0.1% ↓
  x               structure.atom_sites[O1].fract_x                      0.91000       0.9062    0.0014   0.4% ↓
  z               structure.atom_sites[O1].fract_z                      0.60000       0.5928    0.0016   1.2% ↓
  x               structure.atom_sites[O2].fract_x                      0.19000       0.1821    0.0016   4.1% ↓
  z               structure.atom_sites[O2].fract_z                      0.54000       0.5530    0.0018   2.4% ↑
  x               structure.atom_sites[O3].fract_x                      0.08000      0.07792   0.00092   2.6% ↓
  y               structure.atom_sites[O3].fract_y                      0.03000       0.0240    0.0014   20.1% ↓
  z               structure.atom_sites[O3].fract_z                      0.81000       0.8141    0.0014   0.5% ↑
  x               structure.atom_sites[Pb].fract_x                      0.18775     0.187854  0.000099   0.1% ↑
  z               structure.atom_sites[Pb].fract_z                      0.16779      0.16791   0.00013   0.1% ↑
  x               structure.atom_sites[S].fract_x                       0.06528      0.06391   0.00059   2.1% ↓
  z               structure.atom_sites[S].fract_z                       0.68669      0.68660   0.00076   
  a, Å            structure.cell.length_a                                8.4807      8.48066   0.00013   
  b, Å            structure.cell.length_b                                5.3989     5.398869  0.000083   
  c, Å            structure.cell.length_c                                6.9604      6.96038   0.00011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Displacements

The correlations after this stage show how far the oxygen displacements can be told apart; the
case keeps them separate.

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
Pb Pb 0.187854() 0.25 0.16791() c 4 1 0.5() Biso
S S 0.06391() 0.25 0.68660() c 4 1 0.5() Biso
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-xray-cwl_pbso4-lab --verbosity full
    ```

```text
edi fit: project pd-xray-cwl_pbso4-lab, 5799 pts fitted / 6001 loaded, 33 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.83         5.90
      1      0.228      8.40         2.98   49.6% ↓
      2      0.263      8.40         2.98   
  done · converged · 2 iters · reduced χ² 2.98 · Rwp 8.40 % · 0.29 s

  refined parameters (33 free):
  name            parameter                                               start        value      s.u.   change
  coefficient     experiment.background[1].coef                          112.46       148.82      0.63   32.3% ↑
  coefficient     experiment.background[2].coef                            35.5        78.71      0.86   121.7% ↑
  coefficient     experiment.background[3].coef                           16.98        12.06      0.67   29.0% ↓
  coefficient     experiment.background[4].coef                           14.04         4.48      0.66   68.1% ↓
  coefficient     experiment.background[5].coef                           -5.43        -6.13      0.58   13.0% ↓
  coefficient     experiment.background[6].coef                           -5.37       -12.30      0.58   129.0% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset           -0.0327     -0.03246   0.00084   0.7% ↑
  scale           experiment.linked_structures[pbso4].scale             8.60e-4     9.810e-4  0.025e-4   14.1% ↑
  A₀              experiment.peak.asym_beba_a0                           -0.202      -0.2063    0.0059   2.1% ↓
  B₀              experiment.peak.asym_beba_b0                          -0.0323     -0.03230   0.00088   
  U, deg²         experiment.peak.broad_gauss_u                           0.056      0.02036   0.00088   63.6% ↓
  V, deg²         experiment.peak.broad_gauss_v                         -0.0313      -0.0100    0.0011   68.1% ↑
  W, deg²         experiment.peak.broad_gauss_w                         0.01288      0.01222   0.00029   5.1% ↓
  Eta0            experiment.peak.mixing_eta_0                           0.8283       0.7103    0.0061   14.2% ↓
  B iso, Å²       structure.atom_sites[O1].adp_iso                        0.500         1.04      0.21   107.0% ↑
  x               structure.atom_sites[O1].fract_x                      0.90620      0.90756   0.00098   0.1% ↑
  z               structure.atom_sites[O1].fract_z                      0.59280       0.5948    0.0012   0.3% ↑
  B iso, Å²       structure.atom_sites[O2].adp_iso                        0.500         1.42      0.21   184.1% ↑
  x               structure.atom_sites[O2].fract_x                      0.18210       0.1866    0.0012   2.5% ↑
  z               structure.atom_sites[O2].fract_z                      0.55300       0.5382    0.0015   2.7% ↓
  B iso, Å²       structure.atom_sites[O3].adp_iso                        0.500         1.28      0.14   156.1% ↑
  x               structure.atom_sites[O3].fract_x                      0.07792      0.07822   0.00067   0.4% ↑
  y               structure.atom_sites[O3].fract_y                      0.02400      0.02559   0.00094   6.6% ↑
  z               structure.atom_sites[O3].fract_z                      0.81410      0.81447   0.00099   
  B iso, Å²       structure.atom_sites[Pb].adp_iso                        0.500        1.605     0.017   221.1% ↑
  x               structure.atom_sites[Pb].fract_x                      0.18785     0.187933  0.000076   
  z               structure.atom_sites[Pb].fract_z                      0.16791      0.16739   0.00012   0.3% ↓
  B iso, Å²       structure.atom_sites[S].adp_iso                         0.500        1.026     0.078   105.2% ↑
  x               structure.atom_sites[S].fract_x                       0.06391      0.06369   0.00044   0.3% ↓
  z               structure.atom_sites[S].fract_z                       0.68660      0.68360   0.00059   0.4% ↓
  a, Å            structure.cell.length_a                                8.4807     8.480763  0.000089   
  b, Å            structure.cell.length_b                                5.3989     5.398867  0.000059   
  c, Å            structure.cell.length_c                                6.9604     6.960385  0.000076   

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
    python -m edi report pd-xray-cwl_pbso4-lab --output pd-xray-cwl_pbso4-lab.html
    ```
