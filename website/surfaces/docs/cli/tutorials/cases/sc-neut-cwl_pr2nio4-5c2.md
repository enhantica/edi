# Single-crystal fit: Pr₂NiO₄, 5C2

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

Fit the layered nickelate Pr₂NiO₄ to constant-wavelength neutron single-crystal data from 5C2 at
LLB, with anisotropic displacements.

The project is the catalogue case `sc-neut-cwl_pr2nio4-5c2`, the one the command line and the
app's Examples open.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data sc-neut-cwl_pr2nio4-5c2
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-cwl_pr2nio4-5c2
    ```

## Start with nothing free

The project marks what its finished fit frees. Remove every `()`, so the stages below free one group at a time.

In `experiments/llb_5c2.edi`, remove the `()` from every value; they now read:

```edi
pr2nio4 4
```

In `structures/pr2nio4.edi`, remove the `()` from every value; they now read:

```edi
Pr Pr 0 0 0.362 i 8 1 0 Bani
O2 O 0 0 0.176 i 8 0.722965 0 Bani
```

The same for every other row (6 more).

## Scale

The scale brings the calculated intensities to the measured ones.

In `experiments/llb_5c2.edi`, add `()` after the values the stage frees:

```edi
pr2nio4 4()
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_pr2nio4-5c2 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_pr2nio4-5c2 --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_pr2nio4-5c2, 198 pts fitted / 198 loaded, 1 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                       115.85      6415.49
      1      0.077      49.30      1161.93   81.9% ↓
  done · converged · 1 iters · reduced χ² 1161.93 · wR(F²) 49.30 % · 0.09 s

  refined parameters (1 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[pr2nio4].scale                 4        1.814     0.074   54.6% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## Positions

The coordinates each site's symmetry leaves free.

In `structures/pr2nio4.edi`, add `()` after the values the stage frees:

```edi
Pr Pr 0 0 0.362() i 8 1 0 Bani
O2 O 0 0 0.176() i 8 0.722965 0 Bani
```

The same for every other row (1 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_pr2nio4-5c2 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_pr2nio4-5c2 --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_pr2nio4-5c2, 198 pts fitted / 198 loaded, 6 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        49.30      1192.18
      1      0.082      46.64      1067.00   10.5% ↓
      2      0.091      46.63      1066.25   0.1% ↓
      3      0.100      46.61      1065.55   0.1% ↓
      4      0.110      46.60      1065.20   
      5      0.119      46.60      1064.86   
      6      0.128      46.59      1064.67   
      7      0.137      46.59      1064.48   
      8      0.147      46.59      1064.37   
      9      0.157      46.58      1064.26   
     10      0.166      46.58      1064.19   
     11      0.176      46.58      1064.13   
     12      0.185      46.58      1064.09   
     13      0.195      46.58      1064.05   
     14      0.204      46.58      1064.02   
     15      0.214      46.58      1063.99   
     16      0.224      46.58      1063.98   
     17      0.232      46.58      1063.96   
     18      0.242      46.58      1063.95   
     19      0.251      46.58      1063.94   
     20      0.261      46.58      1063.93   
     21      0.273      46.58      1063.93   
  done · converged · 21 iters · reduced χ² 1063.93 · wR(F²) 46.58 % · 0.28 s

  refined parameters (6 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[pr2nio4].scale             1.814        1.889     0.075   4.1% ↑
  z               structure.atom_sites[O2].fract_z                      0.17600       0.1742    0.0011   1.0% ↓
  x               structure.atom_sites[Od].fract_x                      0.07500        0.053     0.011   28.9% ↓
  y               structure.atom_sites[Od].fract_y                      0.07500        0.068     0.012   9.4% ↓
  z               structure.atom_sites[Od].fract_z                      0.17500       0.1728    0.0039   1.3% ↓
  z               structure.atom_sites[Pr].fract_z                      0.36200      0.36027   0.00078   0.5% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## The interstitial displacement

The isotropic displacement of the interstitial oxygen Od.

In `structures/pr2nio4.edi`, add `()` after the values the stage frees:

```edi
Od O 0.053() 0.068() 0.1728() p 32 0.074654 0() Biso
```

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_pr2nio4-5c2 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_pr2nio4-5c2 --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_pr2nio4-5c2, 198 pts fitted / 198 loaded, 7 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        46.58      1069.50
      1      0.076      46.51      1066.71   0.3% ↓
      2      0.087      46.51      1066.70   
  done · converged · 2 iters · reduced χ² 1066.70 · wR(F²) 46.51 % · 0.10 s

  refined parameters (7 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[pr2nio4].scale             1.889        1.887     0.075   0.1% ↓
  z               structure.atom_sites[O2].fract_z                      0.17420       0.1744    0.0011   0.1% ↑
  B iso, Å²       structure.atom_sites[Od].adp_iso                        0.000        -0.34      0.48 ! 
  x               structure.atom_sites[Od].fract_x                      0.05300       0.0529    0.0091   0.1% ↓
  y               structure.atom_sites[Od].fract_y                      0.06800       0.0664    0.0097   2.4% ↓
  z               structure.atom_sites[Od].fract_z                      0.17280       0.1723    0.0034   0.3% ↓
  z               structure.atom_sites[Pr].fract_z                      0.36027      0.36001   0.00086   0.1% ↓

  - start   the value before the fit
  - value   the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest
  - s.u.    its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
  - !       a poorly determined or strongly correlated parameter:
      structure.atom_sites[Od].adp_iso: s.u. larger than the value
```

## Anisotropic displacements

Last, the tensors, each with the components its site symmetry leaves free.

In `structures/pr2nio4.edi`, add `()` after the values the stage frees:

```edi
Pr 0() 0() 0() 0 0 0
Ni 0() 0() 0() 0 0 0
```

The same for every other row (3 more).

=== "Standalone executable"

    ```console
    edi fit sc-neut-cwl_pr2nio4-5c2 --verbosity full
    ```

=== "Python package"

    ```console
    python -m edi fit sc-neut-cwl_pr2nio4-5c2 --verbosity full
    ```

```text
edi fit: project sc-neut-cwl_pr2nio4-5c2, 198 pts fitted / 198 loaded, 23 free
   iter   time (s) wR(F²) (%)  reduced χ²   change
                        46.51      1164.23
      1      0.102       4.29         9.89   99.2% ↓
      2      0.114       4.27         9.79   0.9% ↓
      3      0.126       4.26         9.76   0.3% ↓
      4      0.138       4.26         9.75   0.1% ↓
      5      0.150       4.26         9.75   
      6      0.162       4.26         9.75   
      7      0.176       4.26         9.75   
  done · converged · 7 iters · reduced χ² 9.75 · wR(F²) 4.26 % · 0.19 s

  refined parameters (23 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[pr2nio4].scale             1.887        4.022     0.029   113.2% ↑
  B₁₁, Å²         structure.atom_site_aniso[Ni].adp_11                    0.000        0.315     0.020   
  B₂₂, Å²         structure.atom_site_aniso[Ni].adp_22                    0.000        0.334     0.019   
  B₃₃, Å²         structure.atom_site_aniso[Ni].adp_33                    0.000        0.938     0.018   
  B₁₁, Å²         structure.atom_site_aniso[O1].adp_11                    0.000        0.581     0.028   
  B₁₂, Å²         structure.atom_site_aniso[O1].adp_12                    0.000       -0.164     0.017   
  B₂₂, Å²         structure.atom_site_aniso[O1].adp_22                    0.000        0.585     0.027   
  B₃₃, Å²         structure.atom_site_aniso[O1].adp_33                    0.000        2.570     0.032   
  B₁₁, Å²         structure.atom_site_aniso[O2].adp_11                    0.000        2.124     0.068   
  B₂₂, Å²         structure.atom_site_aniso[O2].adp_22                    0.000        2.175     0.065   
  B₃₃, Å²         structure.atom_site_aniso[O2].adp_33                    0.000        0.297     0.033   
  B₁₁, Å²         structure.atom_site_aniso[Oi].adp_11                    0.000         1.27      0.38   
  B₂₂, Å²         structure.atom_site_aniso[Oi].adp_22                    0.000         1.37      0.36   
  B₃₃, Å²         structure.atom_site_aniso[Oi].adp_33                    0.000         0.62      0.23   
  B₁₁, Å²         structure.atom_site_aniso[Pr].adp_11                    0.000        0.821     0.031   
  B₂₂, Å²         structure.atom_site_aniso[Pr].adp_22                    0.000        0.833     0.030   
  B₃₃, Å²         structure.atom_site_aniso[Pr].adp_33                    0.000        0.519     0.024   
  z               structure.atom_sites[O2].fract_z                      0.17440     0.173833  0.000095   0.3% ↓
  B iso, Å²       structure.atom_sites[Od].adp_iso                       -0.340         2.57      0.16   857.2% ↑
  x               structure.atom_sites[Od].fract_x                      0.05290       0.0796    0.0022   50.4% ↑
  y               structure.atom_sites[Od].fract_y                      0.06640       0.0740    0.0019   11.5% ↑
  z               structure.atom_sites[Od].fract_z                      0.17230      0.17352   0.00069   0.7% ↑
  z               structure.atom_sites[Pr].fract_z                      0.36001     0.359740  0.000076   0.1% ↓

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
    python -m edi report sc-neut-cwl_pr2nio4-5c2 --output sc-neut-cwl_pr2nio4-5c2.html
    ```
