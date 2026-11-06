# Parameters

Parameters describe both the sample and the experiment. Changing a cell length moves calculated reflections; changing a scale changes their contribution to intensity; changing a background coefficient changes the signal underneath the peaks.

[Look up GUI labels, Edi keys, Python paths and CIF names](parameter-reference.md). The linked tables lead to a description of every category and field.

## A value and its context

A parameter's value needs its name, units and place in the model to be meaningful. Typical groups include:

| Group | Examples | What to check |
| --- | --- | --- |
| [Unit cell](../physics/crystallography.md#eq-cell-metric) | Lengths and angles | Units, symmetry and plausible geometry |
| [Atom sites](../physics/diffraction.md#eq-nuclear-structure-factor) | Fractional coordinates and occupancies | Site meaning, symmetry restrictions and composition |
| [Displacements](../physics/displacement.md) | Isotropic or anisotropic displacement parameters | Convention, units and physical interpretation |
| [Instrument](../physics/calibration.md) and [profile](../physics/profiles.md) | Calibration shifts and peak-width terms | Instrument geometry and profile definition |
| [Background](../physics/background.md) and [scale](../physics/diffraction.md#phase-fractions) | Background points or terms, phase scales | Baseline behaviour and how phases contribute |

The [project model](analysis-workflow/project.md) keeps structure quantities separate from experiment quantities. They may still be correlated in a fit.

## Free and fixed

A **free** parameter is allowed to change during [refinement](../physics/rietveld.md#eq-weighted-residual). An active **fixed** parameter contributes to the calculation but keeps the value you supplied. A stored-only field is different: retaining it does not establish a calculation effect. The [parameter index](../physics/parameters.md) identifies the known stored-only fields and model-specific roles.

Review the free set before fitting. Only quantities that can vary independently belong in it. A fit cannot vary a value that describes the setup, such as the crystal radius, one that symmetry or a constraint sets, one the fit's data cannot determine, such as a cell fitted only to single-crystal intensities, or one the calculation has no derivative for yet. A value saved as free that cannot be fitted is loaded as fixed, with a message saying so. Keep the chosen free set with the saved project. Edit the free set in the [<span class="ed-interface-icons" aria-hidden="true">:lucide-monitor:</span> <span class="ed-icon-text">Application</span>](../application/parameters.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../python/structures.md){ .ed-interface-link .ed-icon-label }. [<span class="ed-interface-icons" aria-hidden="true">:lucide-square-terminal:</span> <span class="ed-icon-text">Command Line</span>](../cli/fit.md){ .ed-interface-link .ed-icon-label } uses the choices saved in the project.

## Uncertainties

A fitted parameter may have a [standard uncertainty](../physics/minimization.md#eq-covariance). Interpret it together with the measurement uncertainties, the model and correlations with other parameters.

A small standard uncertainty describes precision under the fit's assumptions. It does not remove uncertainty from calibration, sample effects, missing phases, an unsuitable background, or another systematic source.

See [fit quality](fit-quality.md) for how parameter uncertainties relate to agreement factors and the residual.

## Constraints and symmetry

Some values are related by the crystallographic symmetry; others may be linked by a declared constraint. Such values are not independent fitting directions.

For example, a symmetry restriction on a coordinate cannot be treated as an arbitrary free coordinate simply because a table displays it. The application disables the free checkbox on such a value. Inspect the relationship before interpreting how many independently variable quantities the fit has.

## Bounds and starting values

Use meaningful starting values. A fit begins at the project's current parameter values, and its final state can depend on that starting point.

Model-admissibility limits describe which values the model accepts. They have a different purpose from an optimiser's search bounds. Check the applicable model and interface documentation before treating a displayed range as an editable fitting interval.

When interpreting a constrained or limited value, check the applicable model and fitting settings. A result reaching a permitted limit can be a reason to inspect the starting assumptions, observations and parameter correlations.

For scan analyses, the [fitting mode](fitting-modes.md) determines whether each dataset starts from the same template values or from the previous fit.

## Names in code and files

A parameter can have a Python access path, an Edi persistence key, and a scientific CIF report name. These have different jobs. Use the current [Python documentation](../python/index.md) for code and [data formats](data-formats.md) for saved files. The code access path and the saved-file key need not be identical.
