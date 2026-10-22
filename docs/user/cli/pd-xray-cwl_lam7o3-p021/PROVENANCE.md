# pd-xray-cwl_lam7o3-p021 — provenance

A high-entropy perovskite, La(Ti,Cr,Mn,Fe,Co,Ni,Cu)O₃, against a synchrotron X-ray powder pattern
from the P02.1 beamline at PETRA III.

## Sources

- **Model:** diffraction-lib's tutorial `refine-lam7o3-p021` (develop `cb2cda7b`): the Pnma structure
  with seven cations sharing the B site in equal parts, the constraints tying the six other B-site
  displacements to Ti's and O2's to O1's, the wavelength 0.207109 Å, the pseudo-Voigt with
  Thompson-Cox-Hastings broadening (Y fixed at 0, as the tutorial has it), the excluded regions below
  2° and from 15° to 20°, and every parameter the tutorial frees.
- **Data:** `data/hep7c-xray-synchrotron.dat`, dataset `meas-hep7c-xray-synchrotron` of the repository
  `easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669` (path
  `data/measured/hep7c-xray-synchrotron.dat`), sha256
  `9337ae90cff8bba8dec359dc768c937767f8fd6e0305b6c2c916b9f3963d9a01`, licence BSD-3-Clause. The file
  has no uncertainties; the project gives each point √I, and 1 where I < 1 (only zero counts, all in
  the excluded region), as diffraction-lib's loader does.

## Start

The start a user's own measurement would have, built by `tools/cli_projects/build_catalogue_projects.py`:
zero shift 0; U, V, W and X at the tutorial's values, already one significant figure (0.04, −0.01, 0.001,
0.1); Biso 0.5 on every site; the tutorial's free coordinates to two decimals (La z 0.004 becomes 0.0);
a flat line-segment background at the 10th percentile of the counts; scale 0.000005; the tutorial's cell
(5.5, 7.7, 5.5 Å). Free: the cell, scale, zero shift, U, V, W, X, the 53 background points, La x/z,
O1 x/z, O2 x/y/z and the Biso of La, Ti and O1 (72 parameters).

**The background.** The tutorial's automatic estimate is not capped in its number of points, so its
background follows the capillary and air scattering under the first peaks closely. Here a flat point every
0.25° from 2 to 15° (53 points) stands in for it. With 15 points the fit stopped at R<sub>wp</sub> 2.72 %
(reduced χ² 0.51), and with 27 at 2.81 %; with 40 it reached 1.60 % and with 53 1.49 %. With 79 points it
needs 580 iterations and stops at 2.58 %.

## Differences from the tutorial

- The tutorial estimates its background automatically, first without and then with the model; here it
  starts flat.
- edi's X-ray scattering uses the it1992 form factors and the sasaki1989 dispersion corrections.
- No polarization correction is declared.

## Result from this start (local diagnostic)

From this start edi converges in 26 iterations to R<sub>wp</sub> 1.49 % and reduced χ² 0.157, with
a 5.46216, b 7.73301, c 5.49025 Å, O1 x 0.5078 and scale 3.670 × 10⁻⁶. diffraction-lib's own tutorial
record reports R<sub>wp</sub> 1.51 %, reduced χ² 0.16, a 5.46225, b 7.73307, c 5.49024 Å, O1 x 0.50828
and scale 3.653 × 10⁻⁶.
