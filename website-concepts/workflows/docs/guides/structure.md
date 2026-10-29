# Define a structure

<p class="ed-doc-lead">Describe the crystal that gives rise to the diffraction pattern.</p>

## Space group and cell

The space group expresses the model's symmetry. The unit cell defines its geometry. Together with atom sites, they form the structural part of a project; instrument and peak-profile settings belong to the experiment.

## Atom sites

Inspect each site's element, fractional coordinates, occupancy and displacement parameters. Use constraints where values are linked, rather than treating dependent values as independent fit parameters.

## In the application

Open the Structure page to inspect or edit the structure. **Create structure** starts a new one; adjust its initial space group, cell and sites to your model before interpreting a calculated pattern.

## In Python and project files

Python exposes the structures loaded by `edi.Project.load()`. Project files keep a structure in `structures/<name>.edi` and each experiment declares which structures contribute to its pattern.

## Next step

[Calculate a pattern →](calculate.md)
