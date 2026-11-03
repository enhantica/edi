# :material-archive: Load and save projects

A complete project brings together structures, experiments, measured data or a calculation range, and analysis settings. Python opens the same saved projects as the application and Command Line.

## Open a project

```python
import edi

project = edi.Project.load('path/to/project')
```

The same loader accepts a project entry file or a zip archive:

```python
project = edi.Project.load('path/to/project/project.edi')
project = edi.Project.load('project.zip')
```

Each statement opens a project; choose the input form you have. A `project.edi` refers to the complete project beside it, rather than being a standalone replacement for all its files.

## What a successful load means

The loader checks the project as a whole. Experiment links must resolve to the project's structures. A powder experiment declares either observed data with uncertainties or a simulation range. An incomplete, ambiguous or invalid input raises `edi.IoError` instead of returning a partially populated project.

```python
try:
    project = edi.Project.load('path/to/project')
except edi.IoError as error:
    print(error)
```

## Inspect its contents

```python
print(project.metadata.title)
print(project.location)
print([structure.name for structure in project.structures])
print([experiment.name for experiment in project.experiments])
print(project.analysis.fitting_mode)
```

Collections expose the current model. A complete project can hold several structures and experiments; it is not restricted to one crystal model and one bank.

## Save or move the project

```python
project.save()
project.save_as('refined-project')
```

`save()` writes to the project's current location. When Python opened a zip, `project.location` is the zip path and `save()` rewrites that archive. `save_as(folder)` writes to a folder and makes it the location for subsequent saves.

Saving rounds values to their output precision and recalculates the displayed model from the saved values. Small numerical changes after a save can therefore reflect the precision of the persisted project.

## Hand on an archive

```python
project.save()
project.export_zip('shared-project.zip')
```

`export_zip()` packages the project's folder **as last saved**. Save first when you want current in-memory changes included. The exported archive can be opened by the other interfaces.

Read [shared data formats](../user-guide/data-formats.md) for the project structure and [Command Line files and output](../cli/files.md) for the different archive write-back rule used by commands.
