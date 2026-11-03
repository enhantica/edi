# :material-calculator: Calculate a pattern

A calculation predicts the data from the current model. It does not optimize the model parameters. Use it for a simulation, or to inspect the starting model before a refinement.

## Calculate the loaded project

```python
import edi

project = edi.Project.load('path/to/project')
project.analysis.calculate()
```

The calculation reads its structures, experiments and settings from the project. You do not pass a second grid or measurement alongside it.

## Inspect calculated powder intensities

```python
for experiment in project.experiments:
    if experiment.data is not None:
        calculated = experiment.data.intensity_calc
        print(experiment.name, len(calculated), 'calculated points')
```

`calculate()` returns no result object. The calculated data is stored on each experiment. The example above covers the powder-pattern view; single-crystal experiments use reflection data instead.

## Calculate without measured data

A complete simulation project declares an axis range in its experiment file. The current catalogue includes `pd-neut-cwl_lbco_simulation` and `pd-neut-tof_si_simulation`; their tutorial sources calculate from the model and inspect the experiment's calculated intensities.

The absence of observations is expected for a simulation. It also means there is no measured pattern to refine against.

## Save or present the result

```python
project.save_as('calculated-project')
project.report.save_html('calculation.html', offline=True)
```

Saving and reporting are explicit choices. A report is a presentation of the project; keep the editable project when you want to continue the analysis later.
