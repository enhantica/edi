# Rietveld fit: LiNiO₂, ECHIDNA

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit the layered oxide LiNiO₂ to constant-wavelength neutron powder data from ECHIDNA at ANSTO.
Li and Ni mix between two sites, held to full occupancy by constraints, and the profile has
Finger-Cox-Jephcoat asymmetry.

It builds the catalogue case `pd-neut-cwl_lmo-echidna` step by step: the same project the command
line fits and the app's Examples open. Li and Ni share their sites through five relations
(displacements and occupancies).

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p pd-neut-cwl_lmo-echidna/structures pd-neut-cwl_lmo-echidna/experiments pd-neut-cwl_lmo-echidna/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name pd-neut-cwl_lmo-echidna
_metadata.title "LiNiO₂ [R-3m] · ECHIDNA @ ANSTO"
_metadata.description "Layered oxide · Li/Ni site mixing · Occupancy constraints · TCH × FCJ asymmetry"
_metadata.authors .
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_lmo-echidna-lmo
    mv data/pd-neut-cwl_lmo-echidna-lmo.edi pd-neut-cwl_lmo-echidna/structures/lmo.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_lmo-echidna-lmo
    mv data/pd-neut-cwl_lmo-echidna-lmo.edi pd-neut-cwl_lmo-echidna/structures/lmo.edi
    ```

## Define the experiment

Download the experiment into `experiments`: the file declares the instrument, the peak profile, the background, the structures it links and the measured data.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_lmo-echidna-echidna
    mv data/pd-neut-cwl_lmo-echidna-echidna.edi pd-neut-cwl_lmo-echidna/experiments/echidna.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_lmo-echidna-echidna
    mv data/pd-neut-cwl_lmo-echidna-echidna.edi pd-neut-cwl_lmo-echidna/experiments/echidna.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_minimizer.type crysta
_minimizer.max_iterations 1000

_fitting_mode.type single

loop_
_alias.id
_alias.parameter_unique_name
biso_Li1 lmo.atom_site.Li1.adp_iso
biso_Li2 lmo.atom_site.Li2.adp_iso
biso_Ni1 lmo.atom_site.Ni1.adp_iso
biso_Ni2 lmo.atom_site.Ni2.adp_iso
occ_Li1 lmo.atom_site.Li1.occupancy
occ_Li2 lmo.atom_site.Li2.occupancy
occ_Ni1 lmo.atom_site.Ni1.occupancy
occ_Ni2 lmo.atom_site.Ni2.occupancy

loop_
_constraint.id
_constraint.expression
1 "biso_Ni1 = biso_Li1"
2 "biso_Li2 = biso_Ni2"
3 "occ_Ni1 = 1 - occ_Li1"
4 "occ_Li2 = 1 - occ_Li1"
5 "occ_Ni2 = occ_Li1"

_edi.schema_version 3
```

## Scale, 2θ zero and cell

The scale, the zero shift and the two cell lengths put the peaks in place and at the right
height.

In `experiments/echidna.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0()
lmo 10() 1.0
```

In `structures/lmo.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 2.88()
_cell.length_c 14.18()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lmo-echidna, 3002 pts fitted / 3200 loaded, 4 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       29.38        81.99
      1      0.051      8.05         6.16   92.5% ↓
      2      0.059      8.05         6.16   
  done · converged · 2 iters · reduced χ² 6.16 · Rwp 8.05 % · 0.06 s

  refined parameters (4 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.0000      -0.0430    0.0017   
  scale           experiment.linked_structures[lmo].scale                    10       17.518     0.046   75.2% ↑
  a, Å            structure.cell.length_a                                2.8800     2.875275  0.000033   0.2% ↓
  c, Å            structure.cell.length_c                               14.1800     14.18421   0.00030   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Sample displacement and transparency

The sample sits a little off the diffractometer axis and the beam goes into it; both shift the
peaks with angle, unlike the zero.

In `experiments/echidna.edi`, add these lines, free with `()`; a value left out reads as zero:

```edi
_instrument.calib_sample_displacement 0()
_instrument.calib_sample_transparency 0()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lmo-echidna, 3002 pts fitted / 3200 loaded, 6 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        8.05         6.16
      1      0.050      8.04         6.14   0.3% ↓
  done · converged · 1 iters · reduced χ² 6.14 · Rwp 8.04 % · 0.05 s

  refined parameters (6 free):
  name                     parameter                                               start        value      s.u.   change
  Sample displacement, deg experiment.instrument.calib_sample_displacement        0.0000       0.0198    0.0067   
  Sample transparency, deg experiment.instrument.calib_sample_transparency        0.0000       0.0157    0.0086   
  2θ offset, deg           experiment.instrument.calib_twotheta_offset           -0.0430       -0.071     0.012   65.0% ↓
  scale                    experiment.linked_structures[lmo].scale                17.518       17.515     0.046   
  a, Å                     structure.cell.length_a                                2.8753     2.875002  0.000099   
  c, Å                     structure.cell.length_c                               14.1842     14.18268   0.00060   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

The nine background points follow the level between the peaks.

In `experiments/echidna.edi`, add `()` after the values the stage frees:

```edi
1 12 550()
2 30 550()
```

The same for every other row (7 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lmo-echidna, 3002 pts fitted / 3200 loaded, 15 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        8.04         6.16
      1      0.056      6.46         3.98   35.4% ↓
  done · converged · 1 iters · reduced χ² 3.98 · Rwp 6.46 % · 0.06 s

  refined parameters (15 free):
  name                     parameter                                               start        value      s.u.   change
  intensity                experiment.background[1].intensity                        550        558.1       5.1   1.5% ↑
  intensity                experiment.background[2].intensity                        550        545.5       3.6   0.8% ↓
  intensity                experiment.background[3].intensity                        550        576.5       3.6   4.8% ↑
  intensity                experiment.background[4].intensity                        550        563.5       3.7   2.5% ↑
  intensity                experiment.background[5].intensity                        550        562.0       3.7   2.2% ↑
  intensity                experiment.background[6].intensity                        550        598.2       3.5   8.8% ↑
  intensity                experiment.background[7].intensity                        550        630.1       4.1   14.6% ↑
  intensity                experiment.background[8].intensity                        550        619.5       4.6   12.6% ↑
  intensity                experiment.background[9].intensity                        550        631.6       7.5   14.8% ↑
  Sample displacement, deg experiment.instrument.calib_sample_displacement        0.0198       0.0143    0.0056   27.5% ↓
  Sample transparency, deg experiment.instrument.calib_sample_transparency        0.0157       0.0090    0.0071   42.5% ↓
  2θ offset, deg           experiment.instrument.calib_twotheta_offset           -0.0710      -0.0613    0.0096   13.7% ↑
  scale                    experiment.linked_structures[lmo].scale                17.515       17.095     0.039   2.4% ↓
  a, Å                     structure.cell.length_a                                2.8750     2.875120  0.000082   
  c, Å                     structure.cell.length_c                               14.1827     14.18259   0.00050   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

In `experiments/echidna.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.1()
_peak.broad_gauss_v -0.3()
_peak.broad_gauss_w 0.4()
_peak.broad_lorentz_y 0.1()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lmo-echidna, 3002 pts fitted / 3200 loaded, 19 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        6.46         3.99
      1      0.058      6.39         3.90   2.2% ↓
  done · converged · 1 iters · reduced χ² 3.90 · Rwp 6.39 % · 0.06 s

  refined parameters (19 free):
  name                     parameter                                               start        value      s.u.   change
  intensity                experiment.background[1].intensity                      558.1        561.7       5.0   0.6% ↑
  intensity                experiment.background[2].intensity                      545.5        547.2       3.6   0.3% ↑
  intensity                experiment.background[3].intensity                      576.5        581.5       3.6   0.9% ↑
  intensity                experiment.background[4].intensity                      563.5        571.2       3.8   1.4% ↑
  intensity                experiment.background[5].intensity                        562        566.0       3.7   0.7% ↑
  intensity                experiment.background[6].intensity                      598.2        600.6       3.5   0.4% ↑
  intensity                experiment.background[7].intensity                      630.1        638.3       4.2   1.3% ↑
  intensity                experiment.background[8].intensity                      619.5        629.9       4.7   1.7% ↑
  intensity                experiment.background[9].intensity                      631.6        650.6       7.8   3.0% ↑
  Sample displacement, deg experiment.instrument.calib_sample_displacement        0.0143       0.0144    0.0054   0.6% ↑
  Sample transparency, deg experiment.instrument.calib_sample_transparency        0.0090       0.0093    0.0070 ! 3.9% ↑
  2θ offset, deg           experiment.instrument.calib_twotheta_offset           -0.0613      -0.0615    0.0095 ! 0.3% ↓
  scale                    experiment.linked_structures[lmo].scale                17.095       16.861     0.052   1.4% ↓
  U, deg²                  experiment.peak.broad_gauss_u                             0.1       0.0970    0.0033   3.0% ↓
  V, deg²                  experiment.peak.broad_gauss_v                            -0.3      -0.2819    0.0093   6.0% ↑
  W, deg²                  experiment.peak.broad_gauss_w                             0.4       0.4008    0.0070   0.2% ↑
  Y, deg                   experiment.peak.broad_lorentz_y                           0.1       0.0843    0.0026   15.7% ↓
  a, Å                     structure.cell.length_a                                2.8751     2.875111  0.000080   
  c, Å                     structure.cell.length_c                               14.1826     14.18272   0.00049   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.instrument.calib_sample_transparency: strongly correlated with 2θ offset (echidna) (r = -0.95)
      experiment.instrument.calib_twotheta_offset: strongly correlated with Sample transparency (echidna) (r = -0.95)
```

## Oxygen position

O's height along c is the only coordinate the symmetry leaves free.

In `structures/lmo.edi`, add `()` after the values the stage frees:

```edi
O O 0 0 0.26() c 6 1 0.5 Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lmo-echidna, 3002 pts fitted / 3200 loaded, 20 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        6.39         3.90
      1      0.054      6.20         3.67   6.0% ↓
  done · converged · 1 iters · reduced χ² 3.67 · Rwp 6.20 % · 0.06 s

  refined parameters (20 free):
  name                     parameter                                               start        value      s.u.   change
  intensity                experiment.background[1].intensity                      561.7        565.4       4.9   0.7% ↑
  intensity                experiment.background[2].intensity                      547.2        547.9       3.5   0.1% ↑
  intensity                experiment.background[3].intensity                      581.5        580.2       3.5   0.2% ↓
  intensity                experiment.background[4].intensity                      571.2        575.1       3.7   0.7% ↑
  intensity                experiment.background[5].intensity                        566        567.0       3.6   0.2% ↑
  intensity                experiment.background[6].intensity                      600.6        599.3       3.4   0.2% ↓
  intensity                experiment.background[7].intensity                      638.3        643.4       4.1   0.8% ↑
  intensity                experiment.background[8].intensity                      629.9        627.1       4.6   0.4% ↓
  intensity                experiment.background[9].intensity                      650.6        645.3       7.6   0.8% ↓
  Sample displacement, deg experiment.instrument.calib_sample_displacement        0.0144       0.0169    0.0052   17.1% ↑
  Sample transparency, deg experiment.instrument.calib_sample_transparency        0.0093       0.0111    0.0069 ! 19.1% ↑
  2θ offset, deg           experiment.instrument.calib_twotheta_offset           -0.0615      -0.0648    0.0092 ! 5.3% ↓
  scale                    experiment.linked_structures[lmo].scale                16.861       16.777     0.051   0.5% ↓
  U, deg²                  experiment.peak.broad_gauss_u                           0.097       0.1005    0.0031   3.6% ↑
  V, deg²                  experiment.peak.broad_gauss_v                         -0.2819      -0.2902    0.0089   2.9% ↓
  W, deg²                  experiment.peak.broad_gauss_w                          0.4008       0.4070    0.0068   1.5% ↑
  Y, deg                   experiment.peak.broad_lorentz_y                        0.0843       0.0801    0.0026   5.0% ↓
  z                        structure.atom_sites[O].fract_z                       0.26000     0.259221  0.000055   0.3% ↓
  a, Å                     structure.cell.length_a                                2.8751     2.875043  0.000077   
  c, Å                     structure.cell.length_c                               14.1827     14.18260   0.00046   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.instrument.calib_sample_transparency: strongly correlated with 2θ offset (echidna) (r = -0.95)
      experiment.instrument.calib_twotheta_offset: strongly correlated with Sample transparency (echidna) (r = -0.95)
```

## Displacements

Li1's, Ni2's and O's; Ni1 and Li2 follow by the relations.

In `structures/lmo.edi`, add `()` after the values the stage frees:

```edi
O O 0 0 0.259221() c 6 1 0.5() Biso
Li1 Li 0 0 0.5 b 3 0.95 0.5() Biso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lmo-echidna, 3002 pts fitted / 3200 loaded, 23 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        6.20         3.67
      1      0.063      5.31         2.70   26.6% ↓
      2      0.075      5.31         2.70   
  done · converged · 2 iters · reduced χ² 2.70 · Rwp 5.31 % · 0.08 s

  refined parameters (23 free):
  name                     parameter                                               start        value      s.u.   change
  intensity                experiment.background[1].intensity                      565.4        563.0       4.2   0.4% ↓
  intensity                experiment.background[2].intensity                      547.9        549.5       3.0   0.3% ↑
  intensity                experiment.background[3].intensity                      580.2        577.0       3.1   0.5% ↓
  intensity                experiment.background[4].intensity                      575.1        576.7       3.2   0.3% ↑
  intensity                experiment.background[5].intensity                        567        569.8       3.2   0.5% ↑
  intensity                experiment.background[6].intensity                      599.3        593.7       2.9   0.9% ↓
  intensity                experiment.background[7].intensity                      643.4        642.5       3.6   0.1% ↓
  intensity                experiment.background[8].intensity                      627.1        630.6       4.1   0.6% ↑
  intensity                experiment.background[9].intensity                      645.3        640.8       6.7   0.7% ↓
  Sample displacement, deg experiment.instrument.calib_sample_displacement        0.0169       0.0287    0.0045   69.7% ↑
  Sample transparency, deg experiment.instrument.calib_sample_transparency        0.0111       0.0240    0.0059 ! 116.5% ↑
  2θ offset, deg           experiment.instrument.calib_twotheta_offset           -0.0648      -0.0846    0.0079 ! 30.6% ↓
  scale                    experiment.linked_structures[lmo].scale                16.777       17.100     0.065   1.9% ↑
  U, deg²                  experiment.peak.broad_gauss_u                          0.1005       0.1011    0.0027   0.5% ↑
  V, deg²                  experiment.peak.broad_gauss_v                         -0.2902      -0.2950    0.0077   1.7% ↓
  W, deg²                  experiment.peak.broad_gauss_w                           0.407       0.4119    0.0059   1.2% ↑
  Y, deg                   experiment.peak.broad_lorentz_y                        0.0801       0.0791    0.0023   1.2% ↓
  B iso, Å²                structure.atom_sites[Li1].adp_iso                       0.500         1.03      0.15   105.3% ↑
  B iso, Å²                structure.atom_sites[Ni2].adp_iso                       0.500        0.213     0.018   57.4% ↓
  B iso, Å²                structure.atom_sites[O].adp_iso                         0.500        1.054     0.033   110.8% ↑
  z                        structure.atom_sites[O].fract_z                       0.25922     0.259037  0.000082   0.1% ↓
  a, Å                     structure.cell.length_a                                2.8750     2.874852  0.000067   
  c, Å                     structure.cell.length_c                               14.1826     14.18174   0.00040   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.instrument.calib_sample_transparency: strongly correlated with 2θ offset (echidna) (r = -0.95)
      experiment.instrument.calib_twotheta_offset: strongly correlated with Sample transparency (echidna) (r = -0.95)
```

## Li/Ni mixing

Last, Li1's occupancy, which sets how much Ni sits on the Li site; it moves with the
displacements, so it comes after them.

In `structures/lmo.edi`, add `()` after the values the stage frees:

```edi
Li1 Li 0 0 0.5 b 3 0.95() 1.03() Biso
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lmo-echidna --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lmo-echidna, 3002 pts fitted / 3200 loaded, 24 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        5.31         2.70
      1      0.058      4.99         2.39   11.5% ↓
  done · converged · 1 iters · reduced χ² 2.39 · Rwp 4.99 % · 0.06 s

  refined parameters (24 free):
  name                     parameter                                               start        value      s.u.   change
  intensity                experiment.background[1].intensity                        563        559.0       4.0   0.7% ↓
  intensity                experiment.background[2].intensity                      549.5        547.2       2.8   0.4% ↓
  intensity                experiment.background[3].intensity                        577        574.6       2.9   0.4% ↓
  intensity                experiment.background[4].intensity                      576.7        577.9       3.0   0.2% ↑
  intensity                experiment.background[5].intensity                      569.8        568.2       3.0   0.3% ↓
  intensity                experiment.background[6].intensity                      593.7        594.6       2.7   0.2% ↑
  intensity                experiment.background[7].intensity                      642.5        645.4       3.4   0.5% ↑
  intensity                experiment.background[8].intensity                      630.6        627.6       3.8   0.5% ↓
  intensity                experiment.background[9].intensity                      640.8        640.6       6.3   
  Sample displacement, deg experiment.instrument.calib_sample_displacement        0.0287       0.0263    0.0042   8.3% ↓
  Sample transparency, deg experiment.instrument.calib_sample_transparency        0.0240       0.0226    0.0055 ! 5.8% ↓
  2θ offset, deg           experiment.instrument.calib_twotheta_offset           -0.0846      -0.0817    0.0073 ! 3.4% ↑
  scale                    experiment.linked_structures[lmo].scale                  17.1       15.860     0.086   7.3% ↓
  U, deg²                  experiment.peak.broad_gauss_u                          0.1011       0.1038    0.0026   2.7% ↑
  V, deg²                  experiment.peak.broad_gauss_v                          -0.295      -0.3050    0.0072   3.4% ↓
  W, deg²                  experiment.peak.broad_gauss_w                          0.4119       0.4195    0.0056   1.9% ↑
  Y, deg                   experiment.peak.broad_lorentz_y                        0.0791       0.0787    0.0022   0.6% ↓
  B iso, Å²                structure.atom_sites[Li1].adp_iso                       1.030         1.47      0.12   43.2% ↑
  occ                      structure.atom_sites[Li1].occupancy                    0.9500       0.9851    0.0019   3.7% ↑
  B iso, Å²                structure.atom_sites[Ni2].adp_iso                       0.213        0.319     0.016   49.9% ↑
  B iso, Å²                structure.atom_sites[O].adp_iso                         1.054        0.781     0.027   25.9% ↓
  z                        structure.atom_sites[O].fract_z                       0.25904     0.258776  0.000068   0.1% ↓
  a, Å                     structure.cell.length_a                                2.8749     2.874880  0.000063   
  c, Å                     structure.cell.length_c                               14.1817     14.18191   0.00037   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      experiment.instrument.calib_sample_transparency: strongly correlated with 2θ offset (echidna) (r = -0.95)
      experiment.instrument.calib_twotheta_offset: strongly correlated with Sample transparency (echidna) (r = -0.95)
```

## Report

Write the HTML report of the fitted project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-neut-cwl_lmo-echidna --output pd-neut-cwl_lmo-echidna.html
    ```
