# La₀.₅Ba₀.₅CoO₃ on HRPT

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage. The Python tutorial builds this project by hand; here the command line starts from its starting project instead, since building a project by hand on the command line is planned for a later release.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_lbco-hrpt
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_lbco-hrpt
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/hrpt.edi`, remove the `()` from every value; they now read:

```edi
_instrument.calib_twotheta_offset 0.3
_peak.broad_gauss_u 0.08
_peak.broad_gauss_v -0.1
_peak.broad_gauss_w 0.1
_peak.broad_lorentz_y 0.08
1 10 160
2 30 160
```

The same for every other row (4 more).

In `structures/lbco.edi`, remove the `()` from every value; they now read:

```edi
_cell.length_a 3.88
La La 0 0 0 a 1 0.5 0.5 Biso
Co Co 0.5 0.5 0.5 b 1 1 0.5 Biso
```

The same for every other row (1 more).

## Scale, 2θ zero and cell

The scale sets the overall height of the pattern, and the zero shift and the cell length put the
peaks where they are measured, so they come first.

In `experiments/hrpt.edi`, add `()` after the values the stage frees:

```edi
_instrument.calib_twotheta_offset 0.3()
lbco 9() 1.0
```

In `structures/lbco.edi`, add `()` after the values the stage frees:

```edi
_cell.length_a 3.88()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lbco-hrpt, 3098 pts fitted / 3098 loaded, 3 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       53.67        71.20
      1      0.037     12.52         3.87   94.6% ↓
      2      0.044     12.52         3.87   
  done · converged · 2 iters · reduced χ² 3.87 · Rwp 12.52 % · 0.05 s

  refined parameters (3 free):
  name            parameter                                               start        value      s.u.   change
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.3000       0.6209    0.0019   107.0% ↑
  scale           experiment.linked_structures[lbco].scale                    9        7.259     0.037   19.3% ↓
  a, Å            structure.cell.length_a                                3.8800     3.890816  0.000061   0.3% ↑

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Background

With the peaks in place, the five background points follow the level between them.

In `experiments/hrpt.edi`, add `()` after the values the stage frees:

```edi
1 10 160()
2 30 160()
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lbco-hrpt, 3098 pts fitted / 3098 loaded, 8 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       12.52         3.88
      1      0.052     10.91         2.95   24.0% ↓
  done · converged · 1 iters · reduced χ² 2.95 · Rwp 10.91 % · 0.06 s

  refined parameters (8 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[1].intensity                        160        168.1       2.1   5.1% ↑
  intensity       experiment.background[2].intensity                        160        168.2       1.5   5.1% ↑
  intensity       experiment.background[3].intensity                        160        172.0       1.1   7.5% ↑
  intensity       experiment.background[4].intensity                        160       174.14      0.95   8.8% ↑
  intensity       experiment.background[5].intensity                        160        176.4       1.3   10.2% ↑
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.6209       0.6213    0.0017   0.1% ↑
  scale           experiment.linked_structures[lbco].scale                7.259        7.083     0.033   2.4% ↓
  a, Å            structure.cell.length_a                                3.8908     3.890834  0.000055   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Peak widths

The profile terms now fit the widths and shapes of the peaks.

In `experiments/hrpt.edi`, add `()` after the values the stage frees:

```edi
_peak.broad_gauss_u 0.08()
_peak.broad_gauss_v -0.1()
_peak.broad_gauss_w 0.1()
_peak.broad_lorentz_y 0.08()
```

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lbco-hrpt, 3098 pts fitted / 3098 loaded, 12 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       10.91         2.95
      1      0.046     10.73         2.86   3.2% ↓
  done · converged · 1 iters · reduced χ² 2.86 · Rwp 10.73 % · 0.05 s

  refined parameters (12 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[1].intensity                      168.1        168.5       2.1   0.2% ↑
  intensity       experiment.background[2].intensity                      168.2        167.5       1.5   0.4% ↓
  intensity       experiment.background[3].intensity                        172        170.8       1.1   0.7% ↓
  intensity       experiment.background[4].intensity                     174.14       173.05      0.97   0.6% ↓
  intensity       experiment.background[5].intensity                      176.4        175.4       1.4   0.6% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.6213       0.6211    0.0017   
  scale           experiment.linked_structures[lbco].scale                7.083        7.207     0.041   1.7% ↑
  U, deg²         experiment.peak.broad_gauss_u                            0.08       0.0818    0.0048   2.3% ↑
  V, deg²         experiment.peak.broad_gauss_v                            -0.1       -0.105     0.011   5.4% ↓
  W, deg²         experiment.peak.broad_gauss_w                             0.1       0.1090    0.0052   9.0% ↑
  Y, deg          experiment.peak.broad_lorentz_y                          0.08       0.0885    0.0033   10.6% ↑
  a, Å            structure.cell.length_a                                3.8908     3.890841  0.000056   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Displacements

Every atom sits on a special position of P m -3 m, so there are no coordinates to fit. The
displacements change the peak intensities with angle and come last.

In `structures/lbco.edi`, add `()` after the values the stage frees:

```edi
La La 0 0 0 a 1 0.5 0.5() Biso
Ba Ba 0 0 0 a 1 0.5 0.5() Biso
```

The same for every other row (2 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lbco-hrpt, 3098 pts fitted / 3098 loaded, 16 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       10.73         2.86
      1      0.049      7.23         1.30   54.7% ↓
      2      0.059      7.23         1.30   
  done · converged · 2 iters · reduced χ² 1.30 · Rwp 7.23 % · 0.06 s

  refined parameters (16 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[1].intensity                      168.5        169.6       1.4   0.6% ↑
  intensity       experiment.background[2].intensity                      167.5        165.0       1.0   1.5% ↓
  intensity       experiment.background[3].intensity                      170.8       166.99      0.74   2.2% ↓
  intensity       experiment.background[4].intensity                     173.05       175.89      0.66   1.6% ↑
  intensity       experiment.background[5].intensity                      175.4       171.24      0.94   2.4% ↓
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.6211       0.6204    0.0011   0.1% ↓
  scale           experiment.linked_structures[lbco].scale                7.207        9.132     0.065   26.7% ↑
  U, deg²         experiment.peak.broad_gauss_u                          0.0818       0.0826    0.0032   1.0% ↑
  V, deg²         experiment.peak.broad_gauss_v                          -0.105      -0.1176    0.0068   12.0% ↓
  W, deg²         experiment.peak.broad_gauss_w                           0.109       0.1213    0.0033   11.3% ↑
  Y, deg          experiment.peak.broad_lorentz_y                        0.0885       0.0839    0.0022   5.2% ↓
  B iso, Å²       structure.atom_sites[Ba].adp_iso                        0.500            1        43 ! 4.6% ↑
  B iso, Å²       structure.atom_sites[Co].adp_iso                        0.500        0.211     0.061   57.8% ↓
  B iso, Å²       structure.atom_sites[La].adp_iso                        0.500            1        26 ! 2.0% ↑
  B iso, Å²       structure.atom_sites[O].adp_iso                         0.500        1.392     0.017   178.3% ↑
  a, Å            structure.cell.length_a                                3.8908     3.890791  0.000039   

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      structure.atom_sites[Ba].adp_iso: s.u. larger than the value; strongly correlated with La B iso (lbco) (r = -1.00)
      structure.atom_sites[La].adp_iso: s.u. larger than the value; strongly correlated with Ba B iso (lbco) (r = -1.00)
```

## Constrain La and Ba

The correlations show the displacements of La and Ba moving together almost exactly, with
opposite signs: they share one site and scatter neutrons similarly, so the pattern cannot tell
them apart, and their s.u. are large. Give each an alias and constrain Ba's to follow La's, then
fit again. Ba's displacement is no longer fitted on its own.

In `analysis/analysis.edi`, add these rows to its alias and constraint loops:

```edi
biso_La lbco.atom_site.La.adp_iso
biso_Ba lbco.atom_site.Ba.adp_iso
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_lbco-hrpt --verbosity full
    ```

```text
edi fit: project pd-neut-cwl_lbco-hrpt, 3098 pts fitted / 3098 loaded, 15 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                        8.28         1.70
      1      0.047      7.23         1.30   23.7% ↓
  done · converged · 1 iters · reduced χ² 1.30 · Rwp 7.23 % · 0.05 s

  refined parameters (15 free):
  name            parameter                                               start        value      s.u.   change
  intensity       experiment.background[1].intensity                      169.6        169.6       1.4   
  intensity       experiment.background[2].intensity                        165        165.0       1.0   
  intensity       experiment.background[3].intensity                     166.99       166.99      0.74   
  intensity       experiment.background[4].intensity                     175.89       175.89      0.65   
  intensity       experiment.background[5].intensity                     171.24       171.24      0.92   
  2θ offset, deg  experiment.instrument.calib_twotheta_offset            0.6204       0.6204    0.0011   
  scale           experiment.linked_structures[lbco].scale                9.132        9.132     0.054   
  U, deg²         experiment.peak.broad_gauss_u                          0.0826       0.0826    0.0032   
  V, deg²         experiment.peak.broad_gauss_v                         -0.1176      -0.1176    0.0067   
  W, deg²         experiment.peak.broad_gauss_w                          0.1213       0.1213    0.0033   
  Y, deg          experiment.peak.broad_lorentz_y                        0.0839       0.0839    0.0022   
  B iso, Å²       structure.atom_sites[Co].adp_iso                        0.211        0.211     0.056   0.1% ↑
  B iso, Å²       structure.atom_sites[La].adp_iso                        1.000        0.515     0.028   48.5% ↓
  B iso, Å²       structure.atom_sites[O].adp_iso                         1.392        1.392     0.017   
  a, Å            structure.cell.length_a                                3.8908     3.890791  0.000039   

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
    python -m edi report pd-neut-cwl_lbco-hrpt --output pd-neut-cwl_lbco-hrpt.html
    ```
