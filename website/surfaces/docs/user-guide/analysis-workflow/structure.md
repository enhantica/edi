# :fa5-layer-group: Structure

A structure describes a crystalline phase used to calculate diffraction. It combines a symmetry setting, unit-cell geometry and atom sites. It can be imported from a structural CIF or assembled from crystallographic information.

## Symmetry and setting

The [space group and its setting](../../physics/crystallography.md#symmetry) determine which positions and cell parameters are independent. Check that the chosen setting matches the coordinate system of the structural data you are using.

A symmetry-related value is not an additional independent fitting direction. A table can display several coordinates or cell dimensions even when symmetry relates or fixes them. Symmetry is one of several reasons a fit cannot vary a value; see [free and fixed](../parameters.md#free-and-fixed).

## Unit cell

[Cell lengths and angles](../../physics/crystallography.md#eq-cell-metric) define the repeating geometry. Their units and allowed relationships depend on the crystallographic setting. Inspect the starting calculated reflection positions before fitting the cell: an instrumental calibration error can also move peaks.

## Atom sites

| Quantity | Meaning | What to inspect |
| --- | --- | --- |
| Site label and element | Identify the site and its scattering species | Consistency with the intended composition |
| Fractional coordinates | Locate the representative site in the unit cell | Coordinate setting, symmetry and plausible geometry |
| Occupancy | Describes occupation of the site | Composition and relationships between species sharing a site |
| Displacement parameters | Describe displacement around the average position | Isotropic/anisotropic convention, units and physically meaningful values |
| Wyckoff position | Describes the site's symmetry position | Restrictions on coordinates and site multiplicity |

Keep the [displacement convention](../../physics/displacement.md) used by the source structure; quantities expressed with different conventions should not be compared by name alone. Use [parameters](../parameters.md) for free/fixed values, uncertainty and constraints.

## Calculation method {#calculation-method}

Each structure has a calculation method. It says where the intensity of each reflection comes from.

| Method | Needs | Gives | Use it to |
| --- | --- | --- | --- |
| Rietveld, the default | Cell, space group, atom sites with displacements (and moments), peak profile, background | The structure, phase scales, weight fractions and R Bragg | Fit the structure |
| Le Bail | Cell, space group, peak profile, background | The cell, profile and background, and one intensity per reflection without an s.u. | Settle the cell and profile before Rietveld; test a space group or a propagation vector |
| Pawley | The same as Le Bail | The same, with an s.u. for every intensity | Extract intensities with their uncertainties, for example for structure solution |

Le Bail shares the measured counts out between the reflections after each fit step. It is fast and stable, but its intensities have no uncertainties. Pawley fits every intensity as a parameter. That gives uncertainties, but it is slower and less stable where peaks overlap; no intensity goes below zero. Neither method gives a phase scale, weight fractions or R Bragg.

A good way to start on a new pattern:

1. Load the structure, for example from a CIF with its atoms.
2. Switch it to **Le Bail** and fit the cell, peak profile, background and zero.
3. Switch back to **Rietveld**. Every atom, displacement and moment from the CIF is still there, and the phase scale gets a new start from the pattern.
4. Free the atoms you want and continue the fit from the Le Bail cell and profile.

Under Le Bail or Pawley the atoms stay saved with the structure, free marks included, and the fit leaves them out. A structure without atoms can be fitted with Le Bail or Pawley too. The method applies to powder diffraction only. Each experiment keeps its own intensities, also in a joint fit, and a sequential scan carries them from one dataset to the next. The method is saved in the structure block as `_structure.calc_method`, only when it is not Rietveld, and the intensities in the experiment file, where they start the next fit.

## A structure file

A structure is saved as one `.edi` data block. The example below is `structures/lif.edi` from the LiF project: the symmetry, unit cell and atom sites described above map directly onto its keys.

```edi
data_lif

_edi.schema_version 3

_cell.length_a 4.0267
_cell.length_b 4.0267
_cell.length_c 4.0267
_cell.angle_alpha 90.
_cell.angle_beta 90.
_cell.angle_gamma 90.

_space_group.name_h_m "F m -3 m"
_space_group.coord_system_code 1

loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.wyckoff_letter
_atom_site.occupancy
_atom_site.adp_iso
_atom_site.adp_type
Li1 Li 0. 0. 0. a 1. 1.2 Biso
F1 F 0.5 0.5 0.5 b 1. 0.8 Biso
```

A structure imported from a CIF uses the same layout. See [data formats](../data-formats.md) for how `.edi` relates to CIF.

## Phases and experiment links

A project may contain several structures. An experiment links the structures that contribute to its calculated pattern, with a scale for each link. Adding a structure to the project does not by itself establish that it contributes to every measurement.

Check which phases should contribute and whether their links are enabled. Structural quantities describe the sample; background and peak-profile terms belong to the experiment even though they also affect the calculated pattern.

Edit structures in the [<span class="ed-interface-icons" aria-hidden="true">:fa5-desktop:</span> <span class="ed-icon-text">Application</span>](../../application/structure/structures.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../../python/structures.md){ .ed-interface-link .ed-icon-label }, then [calculate the saved model from Command line](../../cli/calculate.md).
