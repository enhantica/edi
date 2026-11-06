# :fa5-microscope: Experiments and data

An experiment describes the measurement and the model used to calculate it. For powder diffraction, that includes instrument and peak-profile settings, background, exclusions and linked structures.

The shared [Experiment](../user-guide/analysis-workflow/experiment.md) chapter explains the scientific model; the steps below describe this interface.

## Inspect a project

```python
import edi

project = edi.Project.load('path/to/project')

for experiment in project.experiments:
    print(experiment.name)
```

Keep experimental settings with the measurement they describe. Structural parameters belong to a structure, while [wavelength and zero shift](../physics/calibration.md) and [profile parameters](../physics/profiles.md) belong to the experiment model.

## Read a measured powder pattern

For a loaded powder experiment, its data exposes measured intensities and their uncertainties. After a calculation it also carries the calculated intensities:

```python
project.analysis.calculate()

for experiment in project.experiments:
    pattern = experiment.data
    if pattern is not None:
        print(experiment.name, len(pattern.intensity_calc))
```

This snippet is limited to the powder-pattern data view. Single-crystal experiments carry reflections and require the corresponding reflection API.

## Construct an experiment from a data file

For a constant-wavelength neutron powder measurement:

```python
experiment = edi.ExperimentFactory.from_data_path(
    name='measurement',
    data_path='measurement.xye',
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
)
```

The powder reader accepts plain `x y` or `x y sigma` rows, separated by whitespace or commas. It skips nonnumeric lines, estimates uncertainty when omitted, drops nonpositive intensities, sorts the axis and keeps the first repeated-axis point. Review the resulting data when converting an unfamiliar file.

The factory creates the experiment and reads its data. You still need to choose its instrument/profile settings and link a structure before treating it as a complete model.

## Read an experiment from CIF

```python
experiment = edi.ExperimentFactory.from_cif_path('experiment.cif')
project.experiments.add_from_cif_path('experiment.cif')
```

Both read a CIF or `.edi` file with the experiment's type, instrument, peak profile, background, excluded regions, linked structures and measured points. `from_cif_str` and `add_from_cif_str` take the text instead. An experiment added to a project must link structures the project holds; otherwise the import is refused and the project is left as it was. Imported values start fixed, and items EasyDiffraction does not read come back as warnings. See [CIF files](../user-guide/data-formats.md#cif-files).

`experiment.instrument.facility` and `experiment.instrument.name` say where the measurement was made, `?` when unknown. `experiment.experiment_type.dimensionality` is `1d`, and `experiment.experiment_type.polarisation` is `unpolarised` for neutrons and `.` for X-rays; each accepts only that value.

## Measured data or a simulation range

A measured pattern supports comparison and fitting. A simulation range supports a forward calculation without observations. A project can contain both kinds; fitting uses experiments with measured data.

Read [calculate a pattern](calculate.md) or [load and fit](fit.md) for the next step.
