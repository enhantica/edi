---
icon: fa5/file-code
---

# Data formats

EasyDiffraction keeps a saved analysis as an **Edi project**. It reads crystal structures and experiments from **CIF**, imports measured patterns from plain text, and exports reports as readable documents. Use the complete project to continue an analysis; use the other formats to bring data in or to share a result.

## Edi and CIF

**Edi** is EasyDiffraction's own format for saved project state, written with a `.edi` suffix. It uses CIF-like syntax — named data items, data blocks and `loop_` tables. Most of its keys match the IUCr CIF names, and it adds EasyDiffraction-owned keys where no official CIF key is defined, which happens most often for experiment settings.

**CIF** (Crystallographic Information File) is the crystallographic exchange format maintained by the [International Union of Crystallography](https://www.iucr.org/resources/cif). It is human-readable, and its dictionaries define the meaning of each name: **coreCIF** covers common crystallographic quantities, **pdCIF** covers powder diffraction, and **magCIF** covers magnetic structures. EasyDiffraction follows these names for CIF import and report output where they fit.

In short, Edi round-trips the whole project — structures, experiments, data, analysis settings and results — while CIF is the standard way to exchange a single crystal structure or to export a strict report. The [Parameters](parameters.md) section lists the Python path, Edi key and CIF key side by side.

## In a project, only Edi

A saved project contains only `.edi` files:

```text
project/
├── project.edi
├── structures/
├── experiments/
├── analysis/
└── reports/
```

`project.edi` carries the project-level information; the other folders hold the structures, experiments and fitting settings, and the reports when you ask for them. The folder can be packaged as a `.zip` archive, and the app, Python and Command Line all accept a project folder, its `project.edi`, or an archive.

You can still bring in data from other formats for convenience — a crystal structure or an experiment from CIF, and measured points from a text file — but EasyDiffraction writes everything back as `.edi` when it saves. If a folder holds both `lbco.edi` and `lbco.cif`, the `.edi` file is read and a warning names the `.cif` one, so a saved project never keeps CIF files.

| Format | What you use it for |
| --- | --- |
| Edi project | Reopen and continue the analysis with its structures, experiments, data, settings and results |
| Structure from CIF or `.edi` | Import one crystal structure into the project, for convenience |
| Experiment from CIF or `.edi` | Import one experiment with its settings and any stored data, for convenience |
| Measured-pattern text file | Supply observations to an experiment, for convenience |
| HTML, PDF or CIF report | Export a readable account of the analysis to share |

A structure imported from CIF is a starting point. It still needs an experiment, instrument settings and measured data or a calculation range before it describes a complete analysis.

## Format comparison

Edi and CIF share the same readable, line-based layout. The example below shows a crystal structure as it appears in a `.edi` or CIF file, and the same data as JSON. JSON suits structured data in programming, but for crystallographic data the CIF-style layout is easier to read.

```text
data_lbco

_space_group.name_h_m "P m -3 m"
_space_group.coord_system_code 1

_cell.length_a 3.8909
_cell.length_b 3.8909
_cell.length_c 3.8909
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90

loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
La La 0   0   0   0.5 0.4958
Ba Ba 0   0   0   0.5 0.4943
Co Co 0.5 0.5 0.5 1.0 0.2567
O  O   0   0.5 0.5 1.0 1.4041
```

The unit-cell parameters are grouped under the `_cell` category and the atom positions under `_atom_site`. The `loop_` keyword introduces a table whose rows follow the listed names. The same structure as JSON is more verbose:

```json
{
  "lbco": {
    "space_group": { "name_h_m": "P m -3 m", "coord_system_code": 1 },
    "cell": {
      "length_a": 3.8909, "length_b": 3.8909, "length_c": 3.8909,
      "angle_alpha": 90, "angle_beta": 90, "angle_gamma": 90
    },
    "atom_site": [
      { "id": "La", "type_symbol": "La", "fract_x": 0,   "fract_y": 0,   "fract_z": 0,   "occupancy": 0.5, "adp_iso": 0.4958 },
      { "id": "Ba", "type_symbol": "Ba", "fract_x": 0,   "fract_y": 0,   "fract_z": 0,   "occupancy": 0.5, "adp_iso": 0.4943 },
      { "id": "Co", "type_symbol": "Co", "fract_x": 0.5, "fract_y": 0.5, "fract_z": 0.5, "occupancy": 1.0, "adp_iso": 0.2567 },
      { "id": "O",  "type_symbol": "O",  "fract_x": 0,   "fract_y": 0.5, "fract_z": 0.5, "occupancy": 1.0, "adp_iso": 1.4041 }
    ]
  }
}
```

## Importing a CIF {#cif-files}

A CIF file can bring in a structure or an experiment wherever a `.edi` file can. EasyDiffraction reads both CIF 1.1 and CIF 2.0, and goes by the names inside the file rather than by its suffix.

- A structure gives its cell, space group and atom sites, with their displacement parameters.
- An experiment gives its type, instrument, peak profile, background, excluded regions, linked structures and measured points. An experiment added to a project must link structures the project already holds.

Imported values start **fixed** unless they carry a standard uncertainty: a value written as `3.8909(1)` is read as free, while a bare `3.8909` is read as fixed. Free the remaining parameters you want to fit before fitting.

Every item in the file is either used, checked against what EasyDiffraction derives itself, reported as not read, or stops the import with an error that names it. Items that are not read come back as warnings beginning with `crysta.schema.cif_items_not_read`, each with a reason, so you can see exactly what was ignored.

A structure is read from the one block that gives a cell, and an experiment from the one block that gives experiment items and no cell. A file with several such blocks is refused. Magnetic and modulated structures and mmCIF files are not supported.

### Structure files {#structure-edi}

A saved structure — `.edi` or CIF — adds one crystal structure to the current project. It imports the structure model only; it does not open a complete project. The [:fa5-layer-group: Structure](analysis-workflow/structure.md) stage shows the file contents.

### Experiment files {#experiment-edi}

A saved experiment — `.edi` or CIF — adds one experiment with its measurement settings and any stored data. Check its linked structures after import. A measured-data text file such as `.xye` instead supplies observations to an existing experiment. The [:fa5-microscope: Experiment](analysis-workflow/experiment.md) stage shows the file contents.

## Measured-pattern text files

Powder observations can be supplied as plain text columns for `x`, intensity, and optionally the standard uncertainty of the intensity:

- For constant-wavelength data, `x` is 2θ in degrees.
- For time-of-flight data, `x` is time of flight in microseconds.
- A supplied uncertainty is used as the observation's standard uncertainty. Check it as carefully as the intensity.

After loading, the measured data are stored in the experiment's `.edi` file. The project keeps the source filename as context but does not depend on that original text file to reopen the stored measurement.

!!! note "Check the imported pattern"

    Inspect the units, range, retained observations and any import messages. A readable file is not evidence that its columns or units describe the measurement you intended.

## Observations and calculation ranges

A fit-ready experiment declares its observations and uncertainties; a simulation experiment declares a calculation range instead. A project may contain both kinds: calculation covers all of its experiments, while fitting uses those with observations.

## Saving and sharing a project

Hand on the complete project folder or archive to keep its saved model, embedded observations and analysis choices, and keep any external scan inputs as well. A report is a separate output, and saving a project does not create one automatically.

The exact file dialogs, import messages and write-back behaviour are interface-specific:

- [Application: measured-data import](../application/experiment/experiments.md) and [saving projects](../application/project/index.md).
- [Python: experiment input](../python/experiments.md) and [project loading and saving](../python/projects.md).
- [Command Line: accepted project inputs and output destinations](../cli/files.md).

See the shared [:fa5-clipboard-list: Report](analysis-workflow/report.md) stage for document formats and provenance.
