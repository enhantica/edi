# Joint fit: PbSO₄, neutron and X-ray

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit PbSO₄ to two patterns at once, the Rietveld round robin's neutron pattern from D1A at ILL
and its laboratory X-ray pattern: one structure, two experiments.

It builds the catalogue case `pd-neut-xray-cwl_pbso4-d1a-lab` step by step: the same project the
command line fits and the app's Examples open.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p pd-neut-xray-cwl_pbso4-d1a-lab/structures pd-neut-xray-cwl_pbso4-d1a-lab/experiments pd-neut-xray-cwl_pbso4-d1a-lab/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name pd-neut-xray-cwl_pbso4-d1a-lab
_metadata.title "PbSO₄ [Pnma] · D1A @ ILL and laboratory X-ray"
_metadata.description "Rietveld round-robin data · Neutron and X-ray patterns fitted jointly"
_metadata.authors .
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-xray-cwl_pbso4-d1a-lab-pbso4
    mv data/pd-neut-xray-cwl_pbso4-d1a-lab-pbso4.edi pd-neut-xray-cwl_pbso4-d1a-lab/structures/pbso4.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-xray-cwl_pbso4-d1a-lab-pbso4
    mv data/pd-neut-xray-cwl_pbso4-d1a-lab-pbso4.edi pd-neut-xray-cwl_pbso4-d1a-lab/structures/pbso4.edi
    ```

## Define the experiments

Download the experiments into `experiments`: each file declares its instrument, peak profile, background, the structures it links and its measured data.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-xray-cwl_pbso4-d1a-lab-d1a
    mv data/pd-neut-xray-cwl_pbso4-d1a-lab-d1a.edi pd-neut-xray-cwl_pbso4-d1a-lab/experiments/d1a.edi
    edi download-data pd-neut-xray-cwl_pbso4-d1a-lab-lab
    mv data/pd-neut-xray-cwl_pbso4-d1a-lab-lab.edi pd-neut-xray-cwl_pbso4-d1a-lab/experiments/lab.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-xray-cwl_pbso4-d1a-lab-d1a
    mv data/pd-neut-xray-cwl_pbso4-d1a-lab-d1a.edi pd-neut-xray-cwl_pbso4-d1a-lab/experiments/d1a.edi
    python -m edi download-data pd-neut-xray-cwl_pbso4-d1a-lab-lab
    mv data/pd-neut-xray-cwl_pbso4-d1a-lab-lab.edi pd-neut-xray-cwl_pbso4-d1a-lab/experiments/lab.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_minimizer.type crysta
_minimizer.max_iterations 1000

_fitting_mode.type joint

loop_
_joint_fit.experiment_id
_joint_fit.weight
d1a 0.5
lab 0.5

_edi.schema_version 3
```

## Scales, 2θ zeros and cell

In `experiments/d1a.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
pbso4 1.5() 1.0
```

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
pbso4 0.001() 1.0
```

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 8.47()
_cell.length_b 5.39()
_cell.length_c 6.95()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

```text
edi fit: joint project pd-neut-xray-cwl_pbso4-d1a-lab, 2 banks (d1a, lab), 8709 pts fitted / 8911 loaded, 7 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       64.60       241.50
      1      0.216     27.86        44.92   81.4% ↓
      2      0.243     27.34        43.27   3.7% ↓
      3      0.266     26.85        41.73   3.6% ↓
      4      0.288     26.38        40.29   3.4% ↓
      5      0.309     25.95        38.96   3.3% ↓
      6      0.330     25.50        37.63   3.4% ↓
      7      0.351     25.02        36.23   3.7% ↓
      8      0.371     24.52        34.79   4.0% ↓
      9      0.392     24.01        33.36   4.1% ↓
     10      0.414     23.47        31.88   4.4% ↓
     11      0.435     22.90        30.36   4.8% ↓
     12      0.455     22.34        28.88   4.9% ↓
     13      0.476     21.80        27.51   4.7% ↓
     14      0.497     21.31        26.28   4.5% ↓
     15      0.517     20.89        25.26   3.9% ↓
     16      0.538     20.57        24.49   3.0% ↓
     17      0.559     20.35        23.96   2.2% ↓
     18      0.582     20.21        23.63   1.4% ↓
     19      0.603     20.12        23.44   0.8% ↓
     20      0.630     20.08        23.33   0.5% ↓
     21      0.651     20.05        23.27   0.2% ↓
     22      0.672     20.04        23.24   0.1% ↓
     23      0.692     20.03        23.23   0.1% ↓
     24      0.713     20.03        23.22   
     25      0.733     20.03        23.22   
     26      0.754     20.03        23.22   
     27      0.775     20.03        23.21   
     28      0.796     20.03        23.21   
     29      0.817     20.03        23.21   
     30      0.839     20.03        23.21   
     31      0.882     20.03        23.21   
  done · converged · 31 iters · reduced χ² 23.21 · Rwp 20.03 % · 0.91 s

  per-bank Rwp (%):   d1a 14.11   lab 32.19

  refined parameters (7 free):
  name            parameter                                                 start        value      s.u.   change
  2θ offset, deg  experiments[d1a].instrument.calib_twotheta_offset        0.0000      -0.0353    0.0017   
  scale           experiments[d1a].linked_structures[pbso4].scale             1.5       1.1947    0.0054   20.4% ↓
  2θ offset, deg  experiments[lab].instrument.calib_twotheta_offset        0.0000     -0.06203   0.00066   
  scale           experiments[lab].linked_structures[pbso4].scale           0.001     6.410e-4  0.043e-4   35.9% ↓
  a, Å            structure.cell.length_a                                  8.4700      8.47728   0.00013   0.1% ↑
  b, Å            structure.cell.length_b                                  5.3900     5.396294  0.000080   0.1% ↑
  c, Å            structure.cell.length_c                                  6.9500      6.95673   0.00011   0.1% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Backgrounds

D1A's points and the laboratory pattern's Chebyshev terms.

In `experiments/d1a.edi`, add `()` after the values the stage frees:

```edi
1 11 200()
2 15 200()
```

The same for every other row (6 more).

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
1 0 140()
2 1 0()
```

The same for every other row (4 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

```text
edi fit: joint project pd-neut-xray-cwl_pbso4-d1a-lab, 2 banks (d1a, lab), 8709 pts fitted / 8911 loaded, 21 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       20.03        23.25
      1      0.222     19.11        21.17   9.0% ↓
      2      0.267     19.11        21.17   
  done · converged · 2 iters · reduced χ² 21.17 · Rwp 19.11 % · 0.30 s

  per-bank Rwp (%):   d1a 13.27   lab 30.98

  refined parameters (21 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiments[d1a].background[1].intensity                    200          210        13   4.8% ↑
  intensity       experiments[d1a].background[2].intensity                    200        197.3       9.0   1.4% ↓
  intensity       experiments[d1a].background[3].intensity                    200        194.7       5.7   2.6% ↓
  intensity       experiments[d1a].background[4].intensity                    200        195.0       3.8   2.5% ↓
  intensity       experiments[d1a].background[5].intensity                    200        229.0       3.1   14.5% ↑
  intensity       experiments[d1a].background[6].intensity                    200        206.1       1.9   3.1% ↑
  intensity       experiments[d1a].background[7].intensity                    200        241.3       2.4   20.6% ↑
  intensity       experiments[d1a].background[8].intensity                    200        188.9       5.1   5.5% ↓
  2θ offset, deg  experiments[d1a].instrument.calib_twotheta_offset       -0.0353      -0.0342    0.0017   3.1% ↑
  scale           experiments[d1a].linked_structures[pbso4].scale          1.1947       1.1255    0.0063   5.8% ↓
  coefficient     experiments[lab].background[1].coef                         140        157.9       1.7   12.8% ↑
  coefficient     experiments[lab].background[2].coef                           0         31.9       2.7   
  coefficient     experiments[lab].background[3].coef                           0          3.6       2.5   
  coefficient     experiments[lab].background[4].coef                           0         23.4       2.4   
  coefficient     experiments[lab].background[5].coef                           0        -15.9       2.2   
  coefficient     experiments[lab].background[6].coef                           0         -2.9       2.1   
  2θ offset, deg  experiments[lab].instrument.calib_twotheta_offset       -0.0620     -0.06190   0.00065   0.2% ↑
  scale           experiments[lab].linked_structures[pbso4].scale         6.41e-4     6.195e-4  0.045e-4   3.3% ↓
  a, Å            structure.cell.length_a                                  8.4773      8.47734   0.00013   
  b, Å            structure.cell.length_b                                  5.3963     5.396287  0.000080   
  c, Å            structure.cell.length_c                                  6.9567      6.95680   0.00011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

In `experiments/d1a.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.2()
_peak.broad_gauss_v -0.5()
_peak.broad_gauss_w 0.4()
_peak.mixing_eta_0 0.5()
```

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.02()
_peak.broad_gauss_v -0.02()
_peak.broad_gauss_w 0.008()
_peak.mixing_eta_0 0.5()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

```text
edi fit: joint project pd-neut-xray-cwl_pbso4-d1a-lab, 2 banks (d1a, lab), 8709 pts fitted / 8911 loaded, 29 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       19.11        21.19
      1      0.286     11.62         7.84   63.0% ↓
      2      0.317     11.49         7.66   2.3% ↓
      3      0.350     11.42         7.57   1.1% ↓
      4      0.385     11.40         7.54   0.4% ↓
      5      0.417     11.39         7.53   0.1% ↓
      6      0.451     11.39         7.53   
      7      0.481     11.39         7.53   
      8      0.514     11.39         7.53   
      9      0.549     11.39         7.53   
     10      0.605     11.39         7.53   
  done · converged · 10 iters · reduced χ² 7.53 · Rwp 11.39 % · 0.66 s

  per-bank Rwp (%):   d1a 8.65   lab 17.39

  refined parameters (29 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiments[d1a].background[1].intensity                    210        209.5       7.7   0.3% ↓
  intensity       experiments[d1a].background[2].intensity                  197.3        197.4       5.4   
  intensity       experiments[d1a].background[3].intensity                  194.7        194.3       3.4   0.2% ↓
  intensity       experiments[d1a].background[4].intensity                    195        194.4       2.3   0.3% ↓
  intensity       experiments[d1a].background[5].intensity                    229        219.0       2.3   4.4% ↓
  intensity       experiments[d1a].background[6].intensity                  206.1        199.6       1.2   3.2% ↓
  intensity       experiments[d1a].background[7].intensity                  241.3        221.2       1.8   8.3% ↓
  intensity       experiments[d1a].background[8].intensity                  188.9        187.4       3.2   0.8% ↓
  2θ offset, deg  experiments[d1a].instrument.calib_twotheta_offset       -0.0342      -0.1028    0.0017   200.6% ↓
  scale           experiments[d1a].linked_structures[pbso4].scale          1.1255       1.2193    0.0062   8.3% ↑
  U, deg²         experiments[d1a].peak.broad_gauss_u                         0.2       0.1676    0.0061 ! 16.2% ↓
  V, deg²         experiments[d1a].peak.broad_gauss_v                        -0.5       -0.370     0.014 ! 25.9% ↑
  W, deg²         experiments[d1a].peak.broad_gauss_w                         0.4       0.3683    0.0074   7.9% ↓
  Eta0            experiments[d1a].peak.mixing_eta_0                          0.5        0.427     0.014   14.7% ↓
  coefficient     experiments[lab].background[1].coef                       157.9        107.5       1.2   31.9% ↓
  coefficient     experiments[lab].background[2].coef                        31.9         31.8       1.7   0.3% ↓
  coefficient     experiments[lab].background[3].coef                         3.6         21.4       1.5   494.9% ↑
  coefficient     experiments[lab].background[4].coef                        23.4         13.0       1.5   44.5% ↓
  coefficient     experiments[lab].background[5].coef                       -15.9        -10.5       1.3   34.1% ↑
  coefficient     experiments[lab].background[6].coef                        -2.9         -1.7       1.3   43.0% ↑
  2θ offset, deg  experiments[lab].instrument.calib_twotheta_offset       -0.0619     -0.07973   0.00059   28.8% ↓
  scale           experiments[lab].linked_structures[pbso4].scale         6.20e-4     8.587e-4  0.038e-4   38.6% ↑
  U, deg²         experiments[lab].peak.broad_gauss_u                        0.02        0.301     0.013 ! 1.40e3 % ↑
  V, deg²         experiments[lab].peak.broad_gauss_v                       -0.02      -0.1836    0.0091 ! 818.2% ↓
  W, deg²         experiments[lab].peak.broad_gauss_w                       0.008       0.0371    0.0017 ! 364.2% ↑
  Eta0            experiments[lab].peak.mixing_eta_0                          0.5        0.695     0.014   39.0% ↑
  a, Å            structure.cell.length_a                                  8.4773      8.47195   0.00016   0.1% ↓
  b, Å            structure.cell.length_b                                  5.3963      5.39297   0.00010   0.1% ↓
  c, Å            structure.cell.length_c                                  6.9568      6.95311   0.00014   0.1% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[d1a].peak.broad_gauss_u: strongly correlated with V (d1a) (r = -0.96)
      experiments[d1a].peak.broad_gauss_v: strongly correlated with U (d1a) (r = -0.96)
      experiments[lab].peak.broad_gauss_u: strongly correlated with V (lab) (r = -0.97)
      experiments[lab].peak.broad_gauss_v: strongly correlated with W (lab) (r = -0.98)
      experiments[lab].peak.broad_gauss_w: strongly correlated with V (lab) (r = -0.98)
```

## Peak asymmetry, D1A

The D1A pattern's four Bérar-Baldinozzi terms.

In `experiments/d1a.edi`, add `()` after the values the stage frees:

```edi
_peak.asym_beba_a0 0()
_peak.asym_beba_b0 0()
_peak.asym_beba_a1 0()
_peak.asym_beba_b1 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

```text
edi fit: joint project pd-neut-xray-cwl_pbso4-d1a-lab, 2 banks (d1a, lab), 8709 pts fitted / 8911 loaded, 33 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.39         7.53
      1      0.330      9.65         5.40   28.2% ↓
      2      0.360      9.64         5.39   0.2% ↓
      3      0.392      9.64         5.39   
      4      0.420      9.64         5.39   
      5      0.453      9.64         5.39   
      6      0.482      9.64         5.39   
      7      0.527      9.64         5.39   
  done · converged · 7 iters · reduced χ² 5.39 · Rwp 9.64 % · 0.57 s

  per-bank Rwp (%):   d1a 8.03   lab 13.50

  refined parameters (33 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiments[d1a].background[1].intensity                  209.5        209.3       6.6   0.1% ↓
  intensity       experiments[d1a].background[2].intensity                  197.4        197.8       4.5   0.2% ↑
  intensity       experiments[d1a].background[3].intensity                  194.3        192.8       2.9   0.8% ↓
  intensity       experiments[d1a].background[4].intensity                  194.4        198.0       1.9   1.9% ↑
  intensity       experiments[d1a].background[5].intensity                    219        219.3       2.0   0.1% ↑
  intensity       experiments[d1a].background[6].intensity                  199.6        199.6       1.1   
  intensity       experiments[d1a].background[7].intensity                  221.2        221.1       1.6   
  intensity       experiments[d1a].background[8].intensity                  187.4        192.2       2.7   2.6% ↑
  2θ offset, deg  experiments[d1a].instrument.calib_twotheta_offset       -0.1028       0.0133    0.0025   113.0% ↑
  scale           experiments[d1a].linked_structures[pbso4].scale          1.2193       1.2175    0.0053   0.1% ↓
  A₀              experiments[d1a].peak.asym_beba_a0                            0       -0.241     0.030   
  A₁              experiments[d1a].peak.asym_beba_a1                            0       -0.551     0.072 ! 
  B₀              experiments[d1a].peak.asym_beba_b0                            0      -0.0499    0.0053   
  B₁              experiments[d1a].peak.asym_beba_b1                            0        0.036     0.014 ! 
  U, deg²         experiments[d1a].peak.broad_gauss_u                      0.1676       0.2766    0.0071   65.0% ↑
  V, deg²         experiments[d1a].peak.broad_gauss_v                       -0.37       -0.622     0.017   68.1% ↓
  W, deg²         experiments[d1a].peak.broad_gauss_w                      0.3683       0.5163    0.0095   40.2% ↑
  Eta0            experiments[d1a].peak.mixing_eta_0                        0.427        0.392     0.012   8.2% ↓
  coefficient     experiments[lab].background[1].coef                       107.5       112.66      0.96   4.8% ↑
  coefficient     experiments[lab].background[2].coef                        31.8         32.3       1.4   1.5% ↑
  coefficient     experiments[lab].background[3].coef                        21.4         14.5       1.3   32.2% ↓
  coefficient     experiments[lab].background[4].coef                          13         10.8       1.3   16.6% ↓
  coefficient     experiments[lab].background[5].coef                       -10.5         -6.9       1.1   34.5% ↑
  coefficient     experiments[lab].background[6].coef                        -1.7         -6.6       1.1   286.0% ↓
  2θ offset, deg  experiments[lab].instrument.calib_twotheta_offset       -0.0797     -0.04785   0.00056   40.0% ↑
  scale           experiments[lab].linked_structures[pbso4].scale         8.59e-4     8.510e-4  0.031e-4   0.9% ↓
  U, deg²         experiments[lab].peak.broad_gauss_u                       0.301       0.0502    0.0024   83.3% ↓
  V, deg²         experiments[lab].peak.broad_gauss_v                     -0.1836      -0.0227    0.0024   87.6% ↑
  W, deg²         experiments[lab].peak.broad_gauss_w                      0.0371      0.01066   0.00056   71.3% ↓
  Eta0            experiments[lab].peak.mixing_eta_0                        0.695        0.827     0.013   19.0% ↑
  a, Å            structure.cell.length_a                                  8.4719      8.47935   0.00013   0.1% ↑
  b, Å            structure.cell.length_b                                  5.3930     5.397800  0.000083   0.1% ↑
  c, Å            structure.cell.length_c                                  6.9531      6.95925   0.00011   0.1% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[d1a].peak.asym_beba_a1: strongly correlated with B₁ (d1a) (r = 0.96)
      experiments[d1a].peak.asym_beba_b1: strongly correlated with A₁ (d1a) (r = 0.96)
```

## Peak asymmetry, laboratory

The laboratory pattern's first-order terms.

In `experiments/lab.edi`, add `()` after the values the stage frees:

```edi
_peak.asym_beba_a0 0()
_peak.asym_beba_b0 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

```text
edi fit: joint project pd-neut-xray-cwl_pbso4-d1a-lab, 2 banks (d1a, lab), 8709 pts fitted / 8911 loaded, 35 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        9.64         5.39
      1      0.297      9.45         5.19   3.9% ↓
      2      0.336      9.45         5.19   
      3      0.369      9.45         5.19   
      4      0.401      9.45         5.19   
      5      0.466      9.45         5.19   
  done · converged · 5 iters · reduced χ² 5.19 · Rwp 9.45 % · 0.51 s

  per-bank Rwp (%):   d1a 8.09   lab 12.82

  refined parameters (35 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiments[d1a].background[1].intensity                  209.3        209.3       6.4   
  intensity       experiments[d1a].background[2].intensity                  197.8        197.9       4.5   
  intensity       experiments[d1a].background[3].intensity                  192.8        192.6       2.8   0.1% ↓
  intensity       experiments[d1a].background[4].intensity                    198        198.4       1.9   0.2% ↑
  intensity       experiments[d1a].background[5].intensity                  219.3        219.3       1.9   
  intensity       experiments[d1a].background[6].intensity                  199.6       199.72      0.99   0.1% ↑
  intensity       experiments[d1a].background[7].intensity                  221.1        221.0       1.5   
  intensity       experiments[d1a].background[8].intensity                  192.2        193.0       2.7   0.4% ↑
  2θ offset, deg  experiments[d1a].instrument.calib_twotheta_offset        0.0133       0.0225    0.0026   68.8% ↑
  scale           experiments[d1a].linked_structures[pbso4].scale          1.2175       1.2166    0.0053   0.1% ↓
  A₀              experiments[d1a].peak.asym_beba_a0                       -0.241       -0.249     0.030   3.5% ↓
  A₁              experiments[d1a].peak.asym_beba_a1                       -0.551       -0.536     0.071 ! 2.7% ↑
  B₀              experiments[d1a].peak.asym_beba_b0                      -0.0499      -0.0538    0.0053   7.9% ↓
  B₁              experiments[d1a].peak.asym_beba_b1                        0.036        0.051     0.014 ! 40.7% ↑
  U, deg²         experiments[d1a].peak.broad_gauss_u                      0.2766       0.2941    0.0074 ! 6.3% ↑
  V, deg²         experiments[d1a].peak.broad_gauss_v                      -0.622       -0.658     0.017 ! 5.7% ↓
  W, deg²         experiments[d1a].peak.broad_gauss_w                      0.5163       0.5352    0.0098   3.7% ↑
  Eta0            experiments[d1a].peak.mixing_eta_0                        0.392        0.387     0.012   1.3% ↓
  coefficient     experiments[lab].background[1].coef                      112.66       111.96      0.95   0.6% ↓
  coefficient     experiments[lab].background[2].coef                        32.3         31.3       1.4   3.2% ↓
  coefficient     experiments[lab].background[3].coef                        14.5         13.9       1.3   4.0% ↓
  coefficient     experiments[lab].background[4].coef                        10.8         10.9       1.2   0.8% ↑
  coefficient     experiments[lab].background[5].coef                        -6.9         -7.1       1.1   2.6% ↓
  coefficient     experiments[lab].background[6].coef                        -6.6         -6.7       1.1   1.6% ↓
  2θ offset, deg  experiments[lab].instrument.calib_twotheta_offset       -0.0478      -0.0387    0.0014   19.2% ↑
  scale           experiments[lab].linked_structures[pbso4].scale         8.51e-4     8.534e-4  0.030e-4   0.3% ↑
  A₀              experiments[lab].peak.asym_beba_a0                            0       -0.179     0.011   
  B₀              experiments[lab].peak.asym_beba_b0                            0      -0.0317    0.0017   
  U, deg²         experiments[lab].peak.broad_gauss_u                      0.0502       0.0543    0.0024   8.1% ↑
  V, deg²         experiments[lab].peak.broad_gauss_v                     -0.0227      -0.0283    0.0024   24.5% ↓
  W, deg²         experiments[lab].peak.broad_gauss_w                     0.01066      0.01209   0.00056   13.4% ↑
  Eta0            experiments[lab].peak.mixing_eta_0                        0.827        0.820     0.013   0.9% ↓
  a, Å            structure.cell.length_a                                  8.4794      8.48009   0.00015   
  b, Å            structure.cell.length_b                                  5.3978     5.398279  0.000094   
  c, Å            structure.cell.length_c                                  6.9592      6.95985   0.00013   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[d1a].peak.asym_beba_a1: strongly correlated with B₁ (d1a) (r = 0.96)
      experiments[d1a].peak.asym_beba_b1: strongly correlated with A₁ (d1a) (r = 0.96)
      experiments[d1a].peak.broad_gauss_u: strongly correlated with V (d1a) (r = -0.95)
      experiments[d1a].peak.broad_gauss_v: strongly correlated with U (d1a) (r = -0.95)
```

## Atom positions

The neutron and X-ray patterns together see the oxygen as well as the lead, so all free
coordinates fit at once.

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
Pb Pb 0.19() 0.25 0.17() c 4 1 0.5 Biso
S S 0.07() 0.25 0.68() c 4 1 0.5 Biso
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

```text
edi fit: joint project pd-neut-xray-cwl_pbso4-d1a-lab, 2 banks (d1a, lab), 8709 pts fitted / 8911 loaded, 46 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        9.45         5.19
      1      0.332      8.47         4.17   19.7% ↓
      2      0.388      8.47         4.17   
  done · converged · 2 iters · reduced χ² 4.17 · Rwp 8.47 % · 0.43 s

  per-bank Rwp (%):   d1a 6.98   lab 12.01

  refined parameters (46 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiments[d1a].background[1].intensity                  209.3        209.2       5.8   0.1% ↓
  intensity       experiments[d1a].background[2].intensity                  197.9        198.1       4.0   0.1% ↑
  intensity       experiments[d1a].background[3].intensity                  192.6        192.2       2.5   0.2% ↓
  intensity       experiments[d1a].background[4].intensity                  198.4        201.4       1.7   1.5% ↑
  intensity       experiments[d1a].background[5].intensity                  219.3        215.9       1.8   1.6% ↓
  intensity       experiments[d1a].background[6].intensity                 199.72       203.44      0.90   1.9% ↑
  intensity       experiments[d1a].background[7].intensity                    221        214.0       1.4   3.2% ↓
  intensity       experiments[d1a].background[8].intensity                    193        204.3       2.5   5.9% ↑
  2θ offset, deg  experiments[d1a].instrument.calib_twotheta_offset        0.0225       0.0165    0.0025   26.9% ↓
  scale           experiments[d1a].linked_structures[pbso4].scale          1.2166       1.2227    0.0047   0.5% ↑
  A₀              experiments[d1a].peak.asym_beba_a0                       -0.249       -0.233     0.027   6.3% ↑
  A₁              experiments[d1a].peak.asym_beba_a1                       -0.536       -0.676     0.065 ! 26.1% ↓
  B₀              experiments[d1a].peak.asym_beba_b0                      -0.0538      -0.0596    0.0048   10.7% ↓
  B₁              experiments[d1a].peak.asym_beba_b1                        0.051        0.038     0.013 ! 24.6% ↓
  U, deg²         experiments[d1a].peak.broad_gauss_u                      0.2941       0.2890    0.0068   1.7% ↓
  V, deg²         experiments[d1a].peak.broad_gauss_v                      -0.658       -0.629     0.016 ! 4.4% ↑
  W, deg²         experiments[d1a].peak.broad_gauss_w                      0.5352       0.5131    0.0087 ! 4.1% ↓
  Eta0            experiments[d1a].peak.mixing_eta_0                        0.387        0.388     0.011   0.3% ↑
  coefficient     experiments[lab].background[1].coef                      111.96       113.33      0.85   1.2% ↑
  coefficient     experiments[lab].background[2].coef                        31.3         36.0       1.3   15.0% ↑
  coefficient     experiments[lab].background[3].coef                        13.9         17.6       1.2   26.7% ↑
  coefficient     experiments[lab].background[4].coef                        10.9         14.7       1.1   35.1% ↑
  coefficient     experiments[lab].background[5].coef                        -7.1        -5.19      0.96   26.9% ↑
  coefficient     experiments[lab].background[6].coef                        -6.7        -4.88      0.94   27.2% ↑
  2θ offset, deg  experiments[lab].instrument.calib_twotheta_offset       -0.0387      -0.0381    0.0013   1.6% ↑
  scale           experiments[lab].linked_structures[pbso4].scale         8.53e-4     8.581e-4  0.027e-4   0.6% ↑
  A₀              experiments[lab].peak.asym_beba_a0                       -0.179      -0.1744    0.0097   2.6% ↑
  B₀              experiments[lab].peak.asym_beba_b0                      -0.0317      -0.0304    0.0016   4.0% ↑
  U, deg²         experiments[lab].peak.broad_gauss_u                      0.0543       0.0556    0.0022   2.4% ↑
  V, deg²         experiments[lab].peak.broad_gauss_v                     -0.0283      -0.0296    0.0022   4.7% ↓
  W, deg²         experiments[lab].peak.broad_gauss_w                     0.01209      0.01228   0.00050   1.6% ↑
  Eta0            experiments[lab].peak.mixing_eta_0                         0.82        0.829     0.012   1.1% ↑
  x               structure.atom_sites[O1].fract_x                        0.91000      0.90697   0.00025   0.3% ↓
  z               structure.atom_sites[O1].fract_z                        0.60000      0.59632   0.00026   0.6% ↓
  x               structure.atom_sites[O2].fract_x                        0.19000      0.19367   0.00025   1.9% ↑
  z               structure.atom_sites[O2].fract_z                        0.54000      0.54305   0.00030   0.6% ↑
  x               structure.atom_sites[O3].fract_x                        0.08000      0.08058   0.00016   0.7% ↑
  y               structure.atom_sites[O3].fract_y                        0.03000      0.02831   0.00022   5.6% ↓
  z               structure.atom_sites[O3].fract_z                        0.81000      0.80871   0.00020   0.2% ↓
  x               structure.atom_sites[Pb].fract_x                        0.19000     0.187508  0.000087   1.3% ↓
  z               structure.atom_sites[Pb].fract_z                        0.17000      0.16749   0.00012   1.5% ↓
  x               structure.atom_sites[S].fract_x                         0.07000      0.06476   0.00037   7.5% ↓
  z               structure.atom_sites[S].fract_z                         0.68000      0.68260   0.00051   0.4% ↑
  a, Å            structure.cell.length_a                                  8.4801      8.48009   0.00013   
  b, Å            structure.cell.length_b                                  5.3983     5.398368  0.000084   
  c, Å            structure.cell.length_c                                  6.9599      6.95989   0.00011   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiments[d1a].peak.asym_beba_a1: strongly correlated with B₁ (d1a) (r = 0.95)
      experiments[d1a].peak.asym_beba_b1: strongly correlated with A₁ (d1a) (r = 0.95)
      experiments[d1a].peak.broad_gauss_v: strongly correlated with W (d1a) (r = -0.95)
      experiments[d1a].peak.broad_gauss_w: strongly correlated with V (d1a) (r = -0.95)
```

## Displacements

In `structures/pbso4.edi`, add `()` after the values the stage frees:

```edi
Pb Pb 0.187508() 0.25 0.16749() c 4 1 0.5() Biso
S S 0.06476() 0.25 0.68260() c 4 1 0.5() Biso
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-xray-cwl_pbso4-d1a-lab --verbosity full
    ```

```text
edi fit: joint project pd-neut-xray-cwl_pbso4-d1a-lab, 2 banks (d1a, lab), 8709 pts fitted / 8911 loaded, 51 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        8.47         4.17
      1      0.315      5.80         1.96   53.1% ↓
      2      0.374      5.80         1.96   
  done · converged · 2 iters · reduced χ² 1.96 · Rwp 5.80 % · 0.42 s

  per-bank Rwp (%):   d1a 4.50   lab 8.71

  refined parameters (51 free):
  name            parameter                                                 start        value      s.u.   change
  intensity       experiments[d1a].background[1].intensity                  209.2        209.7       4.0   0.2% ↑
  intensity       experiments[d1a].background[2].intensity                  198.1        196.9       2.8   0.6% ↓
  intensity       experiments[d1a].background[3].intensity                  192.2        195.4       1.8   1.6% ↑
  intensity       experiments[d1a].background[4].intensity                  201.4        191.0       1.2   5.1% ↓
  intensity       experiments[d1a].background[5].intensity                  215.9        197.9       1.3   8.3% ↓
  intensity       experiments[d1a].background[6].intensity                 203.44       202.11      0.62   0.7% ↓
  intensity       experiments[d1a].background[7].intensity                    214       251.87      0.99   17.7% ↑
  intensity       experiments[d1a].background[8].intensity                  204.3        239.7       1.7   17.3% ↑
  2θ offset, deg  experiments[d1a].instrument.calib_twotheta_offset        0.0165      -0.0032    0.0018   119.2% ↓
  scale           experiments[d1a].linked_structures[pbso4].scale          1.2227       1.5242    0.0054   24.7% ↑
  A₀              experiments[d1a].peak.asym_beba_a0                       -0.233        0.112     0.023   148.1% ↑
  A₁              experiments[d1a].peak.asym_beba_a1                       -0.676       -1.284     0.053   89.9% ↓
  B₀              experiments[d1a].peak.asym_beba_b0                      -0.0596      -0.0162    0.0040   72.8% ↑
  B₁              experiments[d1a].peak.asym_beba_b1                        0.038       -0.049     0.011   229.9% ↓
  U, deg²         experiments[d1a].peak.broad_gauss_u                       0.289       0.2692    0.0044   6.9% ↓
  V, deg²         experiments[d1a].peak.broad_gauss_v                      -0.629      -0.6392    0.0098   1.6% ↓
  W, deg²         experiments[d1a].peak.broad_gauss_w                      0.5131       0.5408    0.0055   5.4% ↑
  Eta0            experiments[d1a].peak.mixing_eta_0                        0.388       0.3194    0.0074   17.7% ↓
  coefficient     experiments[lab].background[1].coef                      113.33       148.19      0.65   30.8% ↑
  coefficient     experiments[lab].background[2].coef                          36        77.56      0.93   115.4% ↑
  coefficient     experiments[lab].background[3].coef                        17.6        13.03      0.76   26.0% ↓
  coefficient     experiments[lab].background[4].coef                        14.7         5.29      0.74   64.0% ↓
  coefficient     experiments[lab].background[5].coef                       -5.19        -5.87      0.66   13.1% ↓
  coefficient     experiments[lab].background[6].coef                       -4.88       -11.46      0.65   134.8% ↓
  2θ offset, deg  experiments[lab].instrument.calib_twotheta_offset       -0.0381     -0.04168   0.00089   9.4% ↓
  scale           experiments[lab].linked_structures[pbso4].scale         8.58e-4     9.757e-4  0.026e-4   13.7% ↑
  A₀              experiments[lab].peak.asym_beba_a0                      -0.1744      -0.1638    0.0070   6.1% ↑
  B₀              experiments[lab].peak.asym_beba_b0                      -0.0304      -0.0314    0.0010   3.4% ↓
  U, deg²         experiments[lab].peak.broad_gauss_u                      0.0556      0.01922   0.00097   65.4% ↓
  V, deg²         experiments[lab].peak.broad_gauss_v                     -0.0296      -0.0069    0.0012   76.6% ↑
  W, deg²         experiments[lab].peak.broad_gauss_w                     0.01228      0.01123   0.00031   8.6% ↓
  Eta0            experiments[lab].peak.mixing_eta_0                        0.829       0.7056    0.0072   14.9% ↓
  B iso, Å²       structure.atom_sites[O1].adp_iso                          0.500        2.159     0.034   331.9% ↑
  x               structure.atom_sites[O1].fract_x                        0.90697      0.90789   0.00019   0.1% ↑
  z               structure.atom_sites[O1].fract_z                        0.59632      0.59529   0.00020   0.2% ↓
  B iso, Å²       structure.atom_sites[O2].adp_iso                          0.500        1.722     0.032   244.5% ↑
  x               structure.atom_sites[O2].fract_x                        0.19367      0.19423   0.00019   0.3% ↑
  z               structure.atom_sites[O2].fract_z                        0.54305      0.54368   0.00024   0.1% ↑
  B iso, Å²       structure.atom_sites[O3].adp_iso                          0.500        1.523     0.022   204.5% ↑
  x               structure.atom_sites[O3].fract_x                        0.08058      0.08089   0.00012   0.4% ↑
  y               structure.atom_sites[O3].fract_y                        0.02831      0.02730   0.00016   3.6% ↓
  z               structure.atom_sites[O3].fract_z                        0.80871      0.80928   0.00015   0.1% ↑
  B iso, Å²       structure.atom_sites[Pb].adp_iso                          0.500        1.570     0.015   213.9% ↑
  x               structure.atom_sites[Pb].fract_x                        0.18751     0.187686  0.000064   0.1% ↑
  z               structure.atom_sites[Pb].fract_z                        0.16749     0.167392  0.000090   0.1% ↓
  B iso, Å²       structure.atom_sites[S].adp_iso                           0.500        0.706     0.038   41.3% ↑
  x               structure.atom_sites[S].fract_x                         0.06476      0.06488   0.00025   0.2% ↑
  z               structure.atom_sites[S].fract_z                         0.68260      0.68270   0.00033   
  a, Å            structure.cell.length_a                                  8.4801     8.479965  0.000086   
  b, Å            structure.cell.length_b                                  5.3984     5.398120  0.000056   
  c, Å            structure.cell.length_c                                  6.9599     6.959593  0.000073   

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
    python -m edi report pd-neut-xray-cwl_pbso4-d1a-lab --output pd-neut-xray-cwl_pbso4-d1a-lab.html
    ```
