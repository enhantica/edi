# :material-puzzle: Structure

A structure describes a crystalline phase used to calculate diffraction. It combines a symmetry setting, unit-cell geometry and atom sites. It can be imported from a structural CIF or assembled from crystallographic information.

## Symmetry and setting

The [space group and its setting](../../physics/crystallography.md#symmetry) determine which positions and cell parameters are independent. Check that the chosen setting matches the coordinate system of the structural data you are using.

A symmetry-related value is not an additional independent fitting direction. A table can display several coordinates or cell dimensions even when symmetry relates or fixes them. Symmetry is one of several reasons a fit cannot vary a value; see [free and fixed](../parameters.md#free-and-fixed).

## Unit cell

[Cell lengths and angles](../../physics/crystallography.md#eq-cell-metric) define the repeating geometry. Their units and allowed relationships depend on the crystallographic setting. Inspect the starting calculated reflection positions before refining the cell: an instrumental calibration error can also move peaks.

## Atom sites

| Quantity | Meaning | What to inspect |
| --- | --- | --- |
| Site label and element | Identify the site and its scattering species | Consistency with the intended composition |
| Fractional coordinates | Locate the representative site in the unit cell | Coordinate setting, symmetry and plausible geometry |
| Occupancy | Describes occupation of the site | Composition and relationships between species sharing a site |
| Displacement parameters | Describe displacement around the average position | Isotropic/anisotropic convention, units and physically meaningful values |
| Wyckoff position | Describes the site's symmetry position | Restrictions on coordinates and site multiplicity |

Keep the [displacement convention](../../physics/displacement.md) used by the source structure; quantities expressed with different conventions should not be compared by name alone. Use [parameters](../parameters.md) for free/fixed values, uncertainty and constraints.

## Phases and experiment links

A project may contain several structures. An experiment links the structures that contribute to its calculated signal, with a scale for each link. Adding a structure to the project does not by itself establish that it contributes to every measurement.

Check which phases should contribute and whether their links are enabled. Structural quantities describe the sample; background and peak-profile terms belong to the experiment even though they also affect the calculated pattern.

Edit structures in the [<span class="ed-interface-icons" aria-hidden="true">:lucide-globe: :lucide-monitor:</span> <span class="ed-icon-text">Application</span>](../../application/structures.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:simple-python: :simple-jupyter:</span> <span class="ed-icon-text">Python</span>](../../python/structures.md){ .ed-interface-link .ed-icon-label }, then [calculate the saved model from Command Line](../../cli/calculate.md).
