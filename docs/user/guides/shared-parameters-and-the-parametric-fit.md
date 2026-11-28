# Shared parameters and the joint fit of a scan

Some parameters should have one value for a whole set of patterns: the instrument's peak widths over a temperature
scan, or a crystal's extinction over the banks it was measured on. A **shared** parameter is fitted once, against
every pattern it belongs to, instead of once per pattern.

## Sharing a parameter

The Parameters table on the Analysis page has a **Shared** column just left of **Free**. It is shown in the Joint fitting
mode, and the sidebar widens by its width so no other column gives way:

- **Joint**, for a project with several experiments. Sharing a parameter of one experiment gives the same parameter
  of every experiment that row's value. The row you ticked stays in the table and stands for the group; the other
  experiments' copies leave the table, as a constraint's dependents do. A parameter that is not in every experiment
  cannot be shared, and its box is disabled.
- **Joint**, for a scan. Sharing a parameter gives it one value for every pattern of the scan; the parameters you
  leave unshared are fitted per pattern, as in a sequential fit.

Shared and Free are separate: a shared parameter can be fixed, and then keeps its one value. A shared group has one
Free box, so freeing or fixing one of its parameters does it for all of them, and editing its value changes it in
every experiment. A new group starts free if any of its parameters was free, with the value of the row you ticked. Free boxes are green, Shared boxes and shared values indigo, and a value a constraint computes is
shown in magenta on the Structure and Experiment pages.

The Shared header opens a menu with **Shared**, **Not shared** and, when the rows differ, **Mixed**, as the Free header
does.

Sharing never changes a constraint. A parameter that a constraint or the symmetry sets cannot be shared, and its box
is disabled; the tooltip names the constraint.

In the other fitting modes the Shared column is hidden and the project keeps its shared names unchanged.

## The joint fit of a scan

Choose **Joint: all patterns as one fit** on the Analysis page for a project with a scan. The fit refines all the patterns at once: the
shared parameters have one value for the whole scan and the others one value per pattern. A sequential fit, by
contrast, fits the files one at a time.

While it runs, the Evolution chart and the selected pattern are redrawn after each step from the values the fit has
reached, at most four times a second. The selection stays where you put it. Stopping the fit returns the views to the
results that were there before.

When it ends, the results files are written as after a sequential fit, `analysis/results.csv` with one row per
pattern, and the uncertainties of every pattern are scaled by the reduced χ² of the whole scan. A shared parameter has
the same value and uncertainty in every row.

A joint fit of a scan keeps every pattern in memory. Before it starts it estimates how much it needs, and a scan too large
for the memory available is refused with a message saying how much it needs; fit fewer patterns, or use the
sequential mode.

## In a project file

The shared parameters are listed in `analysis/analysis.edi` by unique name:

```text
_fitting_mode.type joint

loop_
_parametric_fit_shared.parameter_unique_name
d20.peak.broad_gauss_u
d20.peak.broad_gauss_v
d20.peak.broad_gauss_w
```

With results present, the next fit starts each pattern from its own row of `analysis/results.csv`. A value you edit
then is the start of the pattern shown, for the next fit only; it is not saved, and saving says how many such edits
will not be kept.

The Co₂SiO₄ D20 joint scan example, `pd-neut-cwl_cosio-d20_parametric`, fits 213 patterns with U, V and W
shared. In Python, `parameter.shared = True` shares a parameter and `project.analysis.fit()` runs the fit of the
project's mode.
