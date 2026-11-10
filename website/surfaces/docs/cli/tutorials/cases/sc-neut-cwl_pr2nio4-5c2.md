# Single-crystal fit: Pr₂NiO₄, 5C2

The same staged fit as the Python tutorial, on the command line. The command line fits whatever the project marks free with `()` after a value, so each stage marks its parameters in the project's files with a text editor and runs `edi fit`, which writes the fitted values back into the project for the next stage.

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
      1      0.042      49.30      1161.93   81.9% ↓
      2      0.055      49.30      1161.93   
  done · converged · 2 iters · reduced χ² 1161.93 · wR(F²) 49.30 % · 0.07 s

  refined parameters (1 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[pr2nio4].scale                 4        1.814     0.074   54.6% ↓

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
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
      1      0.043      47.49      1106.20   7.2% ↓
      2      0.084      46.77      1072.93   3.0% ↓
      3      0.106      46.69      1069.03   0.4% ↓
      4      0.118      46.64      1067.00   0.2% ↓
      5      0.136      46.63      1066.25   0.1% ↓
      6      0.168      46.61      1065.55   0.1% ↓
      7      0.199      46.60      1065.20   
      8      0.221      46.60      1064.86   
      9      0.234      46.59      1064.67   
     10      0.257      46.59      1064.48   
     11      0.267      46.59      1064.37   
     12      0.275      46.58      1064.26   
     13      0.294      46.58      1064.19   
     14      0.304      46.58      1064.13   
     15      0.313      46.58      1064.09   
     16      0.326      46.58      1064.05   
     17      0.335      46.58      1064.02   
     18      0.345      46.58      1063.99   
     19      0.357      46.58      1063.98   
     20      0.368      46.58      1063.96   
     21      0.397      46.58      1063.95   
     22      0.406      46.58      1063.94   
     23      0.418      46.58      1063.93   
  done · converged · 23 iters · reduced χ² 1063.93 · wR(F²) 46.58 % · 0.44 s

  refined parameters (6 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[pr2nio4].scale             1.814        1.887     0.075   4.0% ↑
  z               structure.atom_sites[O2].fract_z                      0.17600       0.1742    0.0011   1.0% ↓
  x               structure.atom_sites[Od].fract_x                      0.07500        0.053     0.011   29.9% ↓
  y               structure.atom_sites[Od].fract_y                      0.07500        0.067     0.011   10.6% ↓
  z               structure.atom_sites[Od].fract_z                      0.17500       0.1727    0.0039   1.3% ↓
  z               structure.atom_sites[Pr].fract_z                      0.36200      0.36026   0.00078   0.5% ↓

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
```

## The interstitial displacement

The isotropic displacement of the interstitial oxygen Od.

In `structures/pr2nio4.edi`, add `()` after the values the stage frees:

```edi
Od O 0.053() 0.067() 0.1727() p 32 0.074654 0() Biso
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
                        46.58      1069.49
      1      0.018      46.53      1067.18   0.2% ↓
      2      0.027      46.52      1066.73   
      3      0.039      46.51      1066.70   
  done · converged · 3 iters · reduced χ² 1066.70 · wR(F²) 46.51 % · 0.07 s

  refined parameters (7 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[pr2nio4].scale             1.887        1.887     0.075   
  z               structure.atom_sites[O2].fract_z                      0.17420       0.1744    0.0011   0.1% ↑
  B iso, Å²       structure.atom_sites[Od].adp_iso                        0.000        -0.34      0.48   
  x               structure.atom_sites[Od].fract_x                      0.05300       0.0531    0.0091   0.1% ↑
  y               structure.atom_sites[Od].fract_y                      0.06700       0.0664    0.0097   0.9% ↓
  z               structure.atom_sites[Od].fract_z                      0.17270       0.1723    0.0033   0.2% ↓
  z               structure.atom_sites[Pr].fract_z                      0.36026      0.36001   0.00086   0.1% ↓

  - start   the value before the fit
  - value   the fitted value
  - s.u.    its standard uncertainty
  - change  how far the fit moved it, in % of the start: ↑ up, ↓ down
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
                        46.51      1164.22
      1      0.044      16.34       143.71   87.7% ↓
      2      0.063       4.77        12.26   91.5% ↓
      3      0.077       4.34        10.14   17.3% ↓
      4      0.089       4.29         9.88   2.5% ↓
      5      0.100       4.27         9.79   0.9% ↓
      6      0.112       4.26         9.76   0.3% ↓
      7      0.136       4.26         9.75   0.1% ↓
      8      0.164       4.26         9.75   
      9      0.180       4.26         9.75   
  done · converged · 9 iters · reduced χ² 9.75 · wR(F²) 4.26 % · 0.21 s

  refined parameters (23 free):
  name            parameter                                               start        value      s.u.   change
  scale           experiment.linked_structures[pr2nio4].scale             1.887        4.022     0.029   113.1% ↑
  B₁₁, Å²         structure.atom_site_aniso[Ni].adp_11                    0.000        0.315     0.020   
  B₂₂, Å²         structure.atom_site_aniso[Ni].adp_22                    0.000        0.334     0.019   
  B₃₃, Å²         structure.atom_site_aniso[Ni].adp_33                    0.000        0.938     0.018   
  B₁₁, Å²         structure.atom_site_aniso[O1].adp_11                    0.000        0.581     0.028   
  B₁₂, Å²         structure.atom_site_aniso[O1].adp_12                    0.000       -0.164     0.017   
  B₂₂, Å²         structure.atom_site_aniso[O1].adp_22                    0.000        0.585     0.027   
  B₃₃, Å²         structure.atom_site_aniso[O1].adp_33                    0.000        2.570     0.032   
  B₁₁, Å²         structure.atom_site_aniso[O2].adp_11                    0.000        2.126     0.068   
  B₂₂, Å²         structure.atom_site_aniso[O2].adp_22                    0.000        2.172     0.065   
  B₃₃, Å²         structure.atom_site_aniso[O2].adp_33                    0.000        0.297     0.033   
  B₁₁, Å²         structure.atom_site_aniso[Oi].adp_11                    0.000         1.27      0.38   
  B₂₂, Å²         structure.atom_site_aniso[Oi].adp_22                    0.000         1.37      0.36   
  B₃₃, Å²         structure.atom_site_aniso[Oi].adp_33                    0.000         0.62      0.23   
  B₁₁, Å²         structure.atom_site_aniso[Pr].adp_11                    0.000        0.822     0.031   
  B₂₂, Å²         structure.atom_site_aniso[Pr].adp_22                    0.000        0.833     0.030   
  B₃₃, Å²         structure.atom_site_aniso[Pr].adp_33                    0.000        0.519     0.024   
  z               structure.atom_sites[O2].fract_z                      0.17440     0.173833  0.000095   0.3% ↓
  B iso, Å²       structure.atom_sites[Od].adp_iso                       -0.340         2.57      0.16   857.1% ↑
  x               structure.atom_sites[Od].fract_x                      0.05310       0.0795    0.0022   49.7% ↑
  y               structure.atom_sites[Od].fract_y                      0.06640       0.0741    0.0019   11.6% ↑
  z               structure.atom_sites[Od].fract_z                      0.17230      0.17352   0.00069   0.7% ↑
  z               structure.atom_sites[Pr].fract_z                      0.36001     0.359739  0.000076   0.1% ↓

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
    python -m edi report sc-neut-cwl_pr2nio4-5c2 --output sc-neut-cwl_pr2nio4-5c2.html
    ```
