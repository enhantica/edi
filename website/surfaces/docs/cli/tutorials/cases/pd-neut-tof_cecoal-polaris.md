# Rietveld fit: CeCoAl₃, POLARIS

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit CeCoAl₃ to time-of-flight neutron powder data from POLARIS at ISIS: structure and profile,
with a 24-term Chebyshev background.

It builds the catalogue case `pd-neut-tof_cecoal-polaris` step by step: the same project the
command line fits and the app's Examples open.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p pd-neut-tof_cecoal-polaris/structures pd-neut-tof_cecoal-polaris/experiments pd-neut-tof_cecoal-polaris/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name pd-neut-tof_cecoal-polaris
_metadata.title "CeCoAl₃ [Pmma] · POLARIS @ ISIS"
_metadata.description "Structure and time-of-flight profile fit · 24-term Chebyshev background"
_metadata.authors .
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_cecoal-polaris-cecoal
    mv data/pd-neut-tof_cecoal-polaris-cecoal.edi pd-neut-tof_cecoal-polaris/structures/cecoal.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_cecoal-polaris-cecoal
    mv data/pd-neut-tof_cecoal-polaris-cecoal.edi pd-neut-tof_cecoal-polaris/structures/cecoal.edi
    ```

## Define the experiment

Download the experiment into `experiments`: the file declares the instrument, the peak profile, the background, the structures it links and the measured data.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-tof_cecoal-polaris-polaris
    mv data/pd-neut-tof_cecoal-polaris-polaris.edi pd-neut-tof_cecoal-polaris/experiments/polaris.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-tof_cecoal-polaris-polaris
    mv data/pd-neut-tof_cecoal-polaris-polaris.edi pd-neut-tof_cecoal-polaris/experiments/polaris.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_minimizer.type crysta
_minimizer.max_iterations 1000
_minimizer.chi_square_tolerance 0.0001

_fitting_mode.type single

_edi.schema_version 3
```

## Scale, time-of-flight calibration and cell

The scale, the DIFC offset and its quadratic term, and the three cell lengths put the peaks in
place and at the right height.

In `experiments/polaris.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_d_to_tof_offset 0()
_instrument.calib_d_to_tof_quadratic -1.92194()
cecoal 20000() 1.0
```

In `structures/cecoal.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 7.65()
_cell.length_b 4.05()
_cell.length_c 6.91()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

```text
edi fit: project pd-neut-tof_cecoal-polaris, 3692 pts fitted / 3693 loaded, 6 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       11.38        84.57
      1      0.227      4.13        11.13   86.8% ↓
  done · converged · 1 iters · reduced χ² 11.13 · Rwp 4.13 % · 0.25 s

  refined parameters (6 free):
  name                 parameter                                               start        value      s.u.   change
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset                 0         2.75      0.74 ! 
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic       -1.92194        -2.45      0.42 ! 27.7% ↓
  scale                experiment.linked_structures[cecoal].scale             2.00e4     1.3185e4  0.0048e4   34.1% ↓
  a, Å                 structure.cell.length_a                                7.6500       7.6529    0.0015 ! 
  b, Å                 structure.cell.length_b                                4.0500      4.05244   0.00079 ! 0.1% ↑
  c, Å                 structure.cell.length_c                                6.9100       6.9072    0.0014 ! 

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.instrument.calib_d_to_tof_offset: strongly correlated with a (cecoal) (r = -0.95)
      experiment.instrument.calib_d_to_tof_quadratic: strongly correlated with b (cecoal) (r = -0.96)
      structure.cell.length_a: strongly correlated with TOF offset (polaris) (r = -0.95)
      structure.cell.length_b: strongly correlated with TOF quadratic (polaris) (r = -0.96)
      structure.cell.length_c: strongly correlated with TOF quadratic (polaris) (r = -0.95)
```

## Background

The first twelve polynomial terms (orders 0 to 11) follow the level between the peaks; the
higher ones stay at zero.

In `experiments/polaris.edi`, add `()` after the values the stage frees:

```edi
1 0 25000()
2 1 0()
```

The same for every other row (10 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

```text
edi fit: project pd-neut-tof_cecoal-polaris, 3692 pts fitted / 3693 loaded, 18 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        4.13        11.17
      1      0.251      2.31         3.51   68.5% ↓
  done · converged · 1 iters · reduced χ² 3.51 · Rwp 2.31 % · 0.28 s

  refined parameters (18 free):
  name                 parameter                                               start        value      s.u.   change
  coefficient          experiment.background[10].coef                              0          710       160   
  coefficient          experiment.background[11].coef                              0          530       110   
  coefficient          experiment.background[12].coef                              0          145        49   
  coefficient          experiment.background[1].coef                          2.50e4     2.6720e4  0.0170e4 ! 6.9% ↑
  coefficient          experiment.background[2].coef                               0      4.530e3   0.310e3 ! 
  coefficient          experiment.background[3].coef                               0      2.960e3   0.290e3 ! 
  coefficient          experiment.background[4].coef                               0          -50       270 ! 
  coefficient          experiment.background[5].coef                               0          600       260 ! 
  coefficient          experiment.background[6].coef                               0          380       250 ! 
  coefficient          experiment.background[7].coef                               0          400       230   
  coefficient          experiment.background[8].coef                               0          260       220   
  coefficient          experiment.background[9].coef                               0          480       200   
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              2.75         3.15      0.36 ! 14.6% ↑
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic          -2.45        -2.28      0.20 ! 6.8% ↑
  scale                experiment.linked_structures[cecoal].scale             1.32e4     1.5493e4  0.0047e4   17.5% ↑
  a, Å                 structure.cell.length_a                                7.6529      7.65237   0.00072 ! 
  b, Å                 structure.cell.length_b                                4.0524      4.05206   0.00038 ! 
  c, Å                 structure.cell.length_c                                6.9072      6.90639   0.00065 ! 

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.background[1].coef: strongly correlated with 2 coefficient (polaris) (r = 0.99)
      experiment.background[2].coef: strongly correlated with 1 coefficient (polaris) (r = 0.99)
      experiment.background[3].coef: strongly correlated with 2 coefficient (polaris) (r = 0.96)
      experiment.background[4].coef: strongly correlated with 3 coefficient (polaris) (r = 0.96)
      experiment.background[5].coef: strongly correlated with 4 coefficient (polaris) (r = 0.96)
      experiment.background[6].coef: strongly correlated with 5 coefficient (polaris) (r = 0.95)
      experiment.instrument.calib_d_to_tof_offset: strongly correlated with a (cecoal) (r = -0.95)
      experiment.instrument.calib_d_to_tof_quadratic: strongly correlated with b (cecoal) (r = -0.96)
      structure.cell.length_a: strongly correlated with TOF offset (polaris) (r = -0.95)
      structure.cell.length_b: strongly correlated with TOF quadratic (polaris) (r = -0.96)
      structure.cell.length_c: strongly correlated with TOF quadratic (polaris) (r = -0.95)
```

## Peak widths

In `experiments/polaris.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_sigma_1 40()
_peak.broad_lorentz_gamma_1 5()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

```text
edi fit: project pd-neut-tof_cecoal-polaris, 3692 pts fitted / 3693 loaded, 20 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        2.31         3.51
      1      0.289      2.31         3.51   0.3% ↓
  done · converged · 1 iters · reduced χ² 3.51 · Rwp 2.31 % · 0.32 s

  refined parameters (20 free):
  name                 parameter                                               start        value      s.u.   change
  coefficient          experiment.background[10].coef                            710          730       160   2.6% ↑
  coefficient          experiment.background[11].coef                            530          550       110   3.1% ↑
  coefficient          experiment.background[12].coef                            145          155        50   7.2% ↑
  coefficient          experiment.background[1].coef                          2.67e4     2.6780e4  0.0170e4 ! 0.2% ↑
  coefficient          experiment.background[2].coef                          4.53e3      4.550e3   0.310e3 ! 0.4% ↑
  coefficient          experiment.background[3].coef                          2.96e3      2.940e3   0.290e3 ! 0.7% ↓
  coefficient          experiment.background[4].coef                             -50          -70       270 ! 37.2% ↓
  coefficient          experiment.background[5].coef                             600          590       260 ! 1.8% ↓
  coefficient          experiment.background[6].coef                             380          410       250 ! 7.4% ↑
  coefficient          experiment.background[7].coef                             400          440       230   11.2% ↑
  coefficient          experiment.background[8].coef                             260          290       220   13.2% ↑
  coefficient          experiment.background[9].coef                             480          490       200   3.0% ↑
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              3.15         3.15      0.36 ! 
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic          -2.28        -2.27      0.20 ! 0.4% ↑
  scale                experiment.linked_structures[cecoal].scale             1.55e4     1.5350e4  0.0085e4   0.9% ↓
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                        40         46.2       2.3   15.5% ↑
  γ₁, µs/Å             experiment.peak.broad_lorentz_gamma_1                       5         4.19      0.33   16.3% ↓
  a, Å                 structure.cell.length_a                                7.6524      7.65234   0.00072 ! 
  b, Å                 structure.cell.length_b                                4.0521      4.05207   0.00038 ! 
  c, Å                 structure.cell.length_c                                6.9064      6.90639   0.00065 ! 

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.background[1].coef: strongly correlated with 2 coefficient (polaris) (r = 0.97)
      experiment.background[2].coef: strongly correlated with 1 coefficient (polaris) (r = 0.97)
      experiment.background[3].coef: strongly correlated with 2 coefficient (polaris) (r = 0.96)
      experiment.background[4].coef: strongly correlated with 3 coefficient (polaris) (r = 0.96)
      experiment.background[5].coef: strongly correlated with 4 coefficient (polaris) (r = 0.96)
      experiment.background[6].coef: strongly correlated with 5 coefficient (polaris) (r = 0.95)
      experiment.instrument.calib_d_to_tof_offset: strongly correlated with a (cecoal) (r = -0.95)
      experiment.instrument.calib_d_to_tof_quadratic: strongly correlated with b (cecoal) (r = -0.96)
      structure.cell.length_a: strongly correlated with TOF offset (polaris) (r = -0.95)
      structure.cell.length_b: strongly correlated with TOF quadratic (polaris) (r = -0.96)
      structure.cell.length_c: strongly correlated with TOF quadratic (polaris) (r = -0.95)
```

## Atom positions

The coordinates the symmetry leaves free.

In `structures/cecoal.edi`, add `()` after the values the stage frees:

```edi
Ce Ce 0.25 0 0.38() e 2 1 0.5 Biso
Co Co 0.25 0 0.81() e 2 1 0.5 Biso
```

The same for every other row (2 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

```text
edi fit: project pd-neut-tof_cecoal-polaris, 3692 pts fitted / 3693 loaded, 25 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        2.31         3.51
      1      0.303      2.14         3.00   14.5% ↓
  done · converged · 1 iters · reduced χ² 3.00 · Rwp 2.14 % · 0.33 s

  refined parameters (25 free):
  name                 parameter                                               start        value      s.u.   change
  coefficient          experiment.background[10].coef                            730          600       150   17.6% ↓
  coefficient          experiment.background[11].coef                            550          480       110   13.2% ↓
  coefficient          experiment.background[12].coef                            155          125        46   19.1% ↓
  coefficient          experiment.background[1].coef                          2.68e4     2.6680e4  0.0160e4 ! 0.4% ↓
  coefficient          experiment.background[2].coef                          4.55e3      4.460e3   0.290e3 ! 2.0% ↓
  coefficient          experiment.background[3].coef                          2.94e3      2.910e3   0.270e3 ! 1.0% ↓
  coefficient          experiment.background[4].coef                             -70          -90       250 ! 32.5% ↓
  coefficient          experiment.background[5].coef                             590          570       240 ! 3.6% ↓
  coefficient          experiment.background[6].coef                             410          350       230 ! 15.6% ↓
  coefficient          experiment.background[7].coef                             440          350       220   21.4% ↓
  coefficient          experiment.background[8].coef                             290          140       200   53.4% ↓
  coefficient          experiment.background[9].coef                             490          330       180   33.3% ↓
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              3.15         3.50      0.33 ! 11.2% ↑
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic          -2.27        -2.10      0.19 ! 7.6% ↑
  scale                experiment.linked_structures[cecoal].scale             1.53e4     1.5487e4  0.0080e4   0.9% ↑
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                      46.2         44.9       2.1   2.8% ↓
  γ₁, µs/Å             experiment.peak.broad_lorentz_gamma_1                    4.19         4.46      0.31   6.5% ↑
  z                    structure.atom_sites[Al2].fract_z                     0.04000      0.04309   0.00022   7.7% ↑
  x                    structure.atom_sites[Al3].fract_x                     0.07000      0.06978   0.00015   0.3% ↓
  z                    structure.atom_sites[Al3].fract_z                     0.70000      0.70136   0.00017   0.2% ↑
  z                    structure.atom_sites[Ce].fract_z                      0.38000      0.38253   0.00017   0.7% ↑
  z                    structure.atom_sites[Co].fract_z                      0.81000      0.81482   0.00034   0.6% ↑
  a, Å                 structure.cell.length_a                                7.6523      7.65166   0.00066 ! 
  b, Å                 structure.cell.length_b                                4.0521      4.05166   0.00036 ! 
  c, Å                 structure.cell.length_c                                6.9064      6.90582   0.00060 ! 

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.background[1].coef: strongly correlated with 2 coefficient (polaris) (r = 0.97)
      experiment.background[2].coef: strongly correlated with 1 coefficient (polaris) (r = 0.97)
      experiment.background[3].coef: strongly correlated with 2 coefficient (polaris) (r = 0.96)
      experiment.background[4].coef: strongly correlated with 3 coefficient (polaris) (r = 0.96)
      experiment.background[5].coef: strongly correlated with 4 coefficient (polaris) (r = 0.96)
      experiment.background[6].coef: strongly correlated with 5 coefficient (polaris) (r = 0.95)
      experiment.instrument.calib_d_to_tof_offset: strongly correlated with a (cecoal) (r = -0.95)
      experiment.instrument.calib_d_to_tof_quadratic: strongly correlated with b (cecoal) (r = -0.96)
      structure.cell.length_a: strongly correlated with TOF offset (polaris) (r = -0.95)
      structure.cell.length_b: strongly correlated with TOF quadratic (polaris) (r = -0.96)
      structure.cell.length_c: strongly correlated with TOF quadratic (polaris) (r = -0.95)
```

## Displacements

In `structures/cecoal.edi`, add `()` after the values the stage frees:

```edi
Ce Ce 0.25 0 0.38253() e 2 1 0.5() Biso
Co Co 0.25 0 0.81482() e 2 1 0.5() Biso
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

```text
edi fit: project pd-neut-tof_cecoal-polaris, 3692 pts fitted / 3693 loaded, 30 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        2.14         3.01
      1      0.292      2.10         2.89   3.7% ↓
  done · converged · 1 iters · reduced χ² 2.89 · Rwp 2.10 % · 0.32 s

  refined parameters (30 free):
  name                 parameter                                               start        value      s.u.   change
  coefficient          experiment.background[10].coef                            600          650       150   7.5% ↑
  coefficient          experiment.background[11].coef                            480          530       100   9.6% ↑
  coefficient          experiment.background[12].coef                            125          159        45   27.5% ↑
  coefficient          experiment.background[1].coef                          2.67e4     2.6690e4  0.0150e4 ! 
  coefficient          experiment.background[2].coef                          4.46e3      4.540e3   0.280e3 ! 1.7% ↑
  coefficient          experiment.background[3].coef                          2.91e3      2.880e3   0.260e3 ! 1.2% ↓
  coefficient          experiment.background[4].coef                             -90          -60       250 ! 38.4% ↑
  coefficient          experiment.background[5].coef                             570          580       240 ! 2.0% ↑
  coefficient          experiment.background[6].coef                             350          390       220   11.6% ↑
  coefficient          experiment.background[7].coef                             350          390       210   12.8% ↑
  coefficient          experiment.background[8].coef                             140          180       200   31.5% ↑
  coefficient          experiment.background[9].coef                             330          350       180   7.4% ↑
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset               3.5         3.57      0.32 ! 1.9% ↑
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic           -2.1        -2.04      0.18 ! 2.9% ↑
  scale                experiment.linked_structures[cecoal].scale             1.55e4     1.5355e4  0.0096e4   0.9% ↓
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                      44.9         45.4       2.1   1.0% ↑
  γ₁, µs/Å             experiment.peak.broad_lorentz_gamma_1                    4.46         4.40      0.31   1.4% ↓
  B iso, Å²            structure.atom_sites[Al1].adp_iso                       0.500        0.605     0.020   21.0% ↑
  B iso, Å²            structure.atom_sites[Al2].adp_iso                       0.500        0.564     0.021   12.8% ↑
  z                    structure.atom_sites[Al2].fract_z                     0.04309      0.04322   0.00023   0.3% ↑
  B iso, Å²            structure.atom_sites[Al3].adp_iso                       0.500        0.469     0.014   6.2% ↓
  x                    structure.atom_sites[Al3].fract_x                     0.06978      0.06958   0.00015   0.3% ↓
  z                    structure.atom_sites[Al3].fract_z                     0.70136      0.70167   0.00017   
  B iso, Å²            structure.atom_sites[Ce].adp_iso                        0.500        0.440     0.016   12.0% ↓
  z                    structure.atom_sites[Ce].fract_z                      0.38253      0.38235   0.00017   
  B iso, Å²            structure.atom_sites[Co].adp_iso                        0.500        0.334     0.024   33.2% ↓
  z                    structure.atom_sites[Co].fract_z                      0.81482      0.81532   0.00033   0.1% ↑
  a, Å                 structure.cell.length_a                                7.6517      7.65141   0.00065 ! 
  b, Å                 structure.cell.length_b                                4.0517      4.05156   0.00035 ! 
  c, Å                 structure.cell.length_c                                6.9058      6.90570   0.00059 ! 

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.background[1].coef: strongly correlated with 2 coefficient (polaris) (r = 0.97)
      experiment.background[2].coef: strongly correlated with 1 coefficient (polaris) (r = 0.97)
      experiment.background[3].coef: strongly correlated with 4 coefficient (polaris) (r = 0.95)
      experiment.background[4].coef: strongly correlated with 5 coefficient (polaris) (r = 0.96)
      experiment.background[5].coef: strongly correlated with 4 coefficient (polaris) (r = 0.96)
      experiment.instrument.calib_d_to_tof_offset: strongly correlated with a (cecoal) (r = -0.95)
      experiment.instrument.calib_d_to_tof_quadratic: strongly correlated with b (cecoal) (r = -0.96)
      structure.cell.length_a: strongly correlated with TOF offset (polaris) (r = -0.95)
      structure.cell.length_b: strongly correlated with TOF quadratic (polaris) (r = -0.96)
      structure.cell.length_c: strongly correlated with TOF quadratic (polaris) (r = -0.95)
```

## Absorption

Absorption weakens the intensities with time of flight, as the displacements do with angle, so
it comes after them, on its own.

In `experiments/polaris.edi`, add `()` after the values the stage frees:

```edi
_absorption.abscor1 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

```text
edi fit: project pd-neut-tof_cecoal-polaris, 3692 pts fitted / 3693 loaded, 31 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        2.10         2.90
      1      0.260      2.08         2.86   1.3% ↓
      2      0.312      2.08         2.86   
  done · converged · 2 iters · reduced χ² 2.86 · Rwp 2.08 % · 0.34 s

  refined parameters (31 free):
  name                 parameter                                               start        value      s.u.   change
  ABSCOR1, Å⁻¹         experiment.absorption.abscor1                          0.0000       0.0176    0.0027   
  coefficient          experiment.background[10].coef                            650          670       150   2.5% ↑
  coefficient          experiment.background[11].coef                            530          529        99   0.1% ↓
  coefficient          experiment.background[12].coef                            159          161        45   1.3% ↑
  coefficient          experiment.background[1].coef                          2.67e4     2.6770e4  0.0150e4 ! 0.3% ↑
  coefficient          experiment.background[2].coef                          4.54e3      4.580e3   0.280e3 ! 0.8% ↑
  coefficient          experiment.background[3].coef                          2.88e3      2.910e3   0.260e3 ! 1.0% ↑
  coefficient          experiment.background[4].coef                             -60         -210       250 ! 250.8% ↓
  coefficient          experiment.background[5].coef                             580          590       230 ! 0.9% ↑
  coefficient          experiment.background[6].coef                             390          420       220   7.1% ↑
  coefficient          experiment.background[7].coef                             390          460       210   16.9% ↑
  coefficient          experiment.background[8].coef                             180          250       200   39.3% ↑
  coefficient          experiment.background[9].coef                             350          390       180   11.8% ↑
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              3.57         3.58      0.33 ! 0.2% ↑
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic          -2.04        -2.03      0.19 ! 0.4% ↑
  scale                experiment.linked_structures[cecoal].scale             1.54e4     1.7050e4  0.0290e4   11.0% ↑
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                      45.4         46.0       2.1   1.4% ↑
  γ₁, µs/Å             experiment.peak.broad_lorentz_gamma_1                     4.4         4.32      0.31   1.7% ↓
  B iso, Å²            structure.atom_sites[Al1].adp_iso                       0.605        0.677     0.023   11.8% ↑
  B iso, Å²            structure.atom_sites[Al2].adp_iso                       0.564        0.638     0.024   13.0% ↑
  z                    structure.atom_sites[Al2].fract_z                     0.04322      0.04315   0.00022   0.2% ↓
  B iso, Å²            structure.atom_sites[Al3].adp_iso                       0.469        0.536     0.018   14.2% ↑
  x                    structure.atom_sites[Al3].fract_x                     0.06958      0.06962   0.00014   0.1% ↑
  z                    structure.atom_sites[Al3].fract_z                     0.70167      0.70173   0.00017   
  B iso, Å²            structure.atom_sites[Ce].adp_iso                        0.440        0.510     0.019   15.8% ↑
  z                    structure.atom_sites[Ce].fract_z                      0.38235      0.38228   0.00017   
  B iso, Å²            structure.atom_sites[Co].adp_iso                        0.334        0.389     0.025   16.4% ↑
  z                    structure.atom_sites[Co].fract_z                      0.81532      0.81553   0.00033   
  a, Å                 structure.cell.length_a                                7.6514      7.65141   0.00065 ! 
  b, Å                 structure.cell.length_b                                4.0516      4.05155   0.00035 ! 
  c, Å                 structure.cell.length_c                                6.9057      6.90565   0.00059 ! 

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.background[1].coef: strongly correlated with 2 coefficient (polaris) (r = 0.97)
      experiment.background[2].coef: strongly correlated with 1 coefficient (polaris) (r = 0.97)
      experiment.background[3].coef: strongly correlated with 2 coefficient (polaris) (r = 0.95)
      experiment.background[4].coef: strongly correlated with 5 coefficient (polaris) (r = 0.95)
      experiment.background[5].coef: strongly correlated with 4 coefficient (polaris) (r = 0.95)
      experiment.instrument.calib_d_to_tof_offset: strongly correlated with a (cecoal) (r = -0.95)
      experiment.instrument.calib_d_to_tof_quadratic: strongly correlated with b (cecoal) (r = -0.96)
      structure.cell.length_a: strongly correlated with TOF offset (polaris) (r = -0.95)
      structure.cell.length_b: strongly correlated with TOF quadratic (polaris) (r = -0.96)
      structure.cell.length_c: strongly correlated with TOF quadratic (polaris) (r = -0.95)
```

## Al3 occupancy

Last, Al3's occupancy, which moves with its displacement.

In `structures/cecoal.edi`, add `()` after the values the stage frees:

```edi
Al3 Al 0.06962() 0.5 0.70173() j 4 1() 0.536() Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-tof_cecoal-polaris --verbosity full
    ```

```text
edi fit: project pd-neut-tof_cecoal-polaris, 3692 pts fitted / 3693 loaded, 32 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        2.08         2.86
      1      0.301      2.08         2.85   0.2% ↓
  done · converged · 1 iters · reduced χ² 2.85 · Rwp 2.08 % · 0.34 s

  refined parameters (32 free):
  name                 parameter                                               start        value      s.u.   change
  ABSCOR1, Å⁻¹         experiment.absorption.abscor1                          0.0176       0.0174    0.0027   1.2% ↓
  coefficient          experiment.background[10].coef                            670          650       150   2.4% ↓
  coefficient          experiment.background[11].coef                            529          507        99   4.1% ↓
  coefficient          experiment.background[12].coef                            161          147        45   8.5% ↓
  coefficient          experiment.background[1].coef                          2.68e4     2.6760e4  0.0150e4 ! 
  coefficient          experiment.background[2].coef                          4.58e3      4.570e3   0.280e3 ! 0.3% ↓
  coefficient          experiment.background[3].coef                          2.91e3      2.900e3   0.260e3 ! 0.2% ↓
  coefficient          experiment.background[4].coef                            -210         -200       250 ! 2.8% ↑
  coefficient          experiment.background[5].coef                             590          590       230 ! 0.4% ↑
  coefficient          experiment.background[6].coef                             420          420       220   0.8% ↓
  coefficient          experiment.background[7].coef                             460          450       210   2.9% ↓
  coefficient          experiment.background[8].coef                             250          240       200   2.2% ↓
  coefficient          experiment.background[9].coef                             390          390       180   0.1% ↓
  TOF offset, µs       experiment.instrument.calib_d_to_tof_offset              3.58         3.63      0.33 ! 1.3% ↑
  TOF quadratic, µs/Å² experiment.instrument.calib_d_to_tof_quadratic          -2.03        -2.01      0.19 ! 0.9% ↑
  scale                experiment.linked_structures[cecoal].scale             1.71e4     1.6820e4  0.0300e4   1.4% ↓
  σ₁², µs²/Å²          experiment.peak.broad_gauss_sigma_1                        46         46.2       2.1   0.4% ↑
  γ₁, µs/Å             experiment.peak.broad_lorentz_gamma_1                    4.32         4.30      0.31   0.4% ↓
  B iso, Å²            structure.atom_sites[Al1].adp_iso                       0.677        0.656     0.024   3.0% ↓
  B iso, Å²            structure.atom_sites[Al2].adp_iso                       0.638        0.617     0.025   3.2% ↓
  z                    structure.atom_sites[Al2].fract_z                     0.04315      0.04310   0.00022   0.1% ↓
  B iso, Å²            structure.atom_sites[Al3].adp_iso                       0.536        0.575     0.023   7.3% ↑
  x                    structure.atom_sites[Al3].fract_x                     0.06962      0.06958   0.00014   0.1% ↓
  z                    structure.atom_sites[Al3].fract_z                     0.70173      0.70168   0.00017   
  occ                  structure.atom_sites[Al3].occupancy                    1.0000       1.0199    0.0075   2.0% ↑
  B iso, Å²            structure.atom_sites[Ce].adp_iso                        0.510        0.491     0.020   3.8% ↓
  z                    structure.atom_sites[Ce].fract_z                      0.38228      0.38225   0.00017   
  B iso, Å²            structure.atom_sites[Co].adp_iso                        0.389        0.370     0.026   4.9% ↓
  z                    structure.atom_sites[Co].fract_z                      0.81553      0.81556   0.00033   
  a, Å                 structure.cell.length_a                                7.6514      7.65132   0.00065 ! 
  b, Å                 structure.cell.length_b                                4.0515      4.05150   0.00035 ! 
  c, Å                 structure.cell.length_c                                6.9056      6.90557   0.00059 ! 

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.background[1].coef: strongly correlated with 2 coefficient (polaris) (r = 0.97)
      experiment.background[2].coef: strongly correlated with 1 coefficient (polaris) (r = 0.97)
      experiment.background[3].coef: strongly correlated with 2 coefficient (polaris) (r = 0.95)
      experiment.background[4].coef: strongly correlated with 5 coefficient (polaris) (r = 0.95)
      experiment.background[5].coef: strongly correlated with 4 coefficient (polaris) (r = 0.95)
      experiment.instrument.calib_d_to_tof_offset: strongly correlated with a (cecoal) (r = -0.95)
      experiment.instrument.calib_d_to_tof_quadratic: strongly correlated with b (cecoal) (r = -0.96)
      structure.cell.length_a: strongly correlated with TOF offset (polaris) (r = -0.95)
      structure.cell.length_b: strongly correlated with TOF quadratic (polaris) (r = -0.96)
      structure.cell.length_c: strongly correlated with TOF quadratic (polaris) (r = -0.95)
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-neut-tof_cecoal-polaris --output pd-neut-tof_cecoal-polaris.html
    ```
