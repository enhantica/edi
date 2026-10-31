# Reading CIF files

edi reads a structure or an experiment from a CIF file wherever it reads one from a `.edi` file. This page says
where, what edi takes from the file, and what it tells you about the rest.

## Where a CIF can come in

- Python: `StructureFactory.from_cif_str` and `from_cif_path`, `ExperimentFactory.from_cif_str` and `from_cif_path`,
  and the project's collections, `project.structures.add_from_cif_str`, `add_from_cif_path`, and the same three on
  `project.experiments`.
- The app: **Load structure from file** and **Load experiments** accept `.cif` files as well as `.edi` ones.
- Project folders: a `.cif` file in `structures/` or `experiments/` is a member like a `.edi` one, the suffix in any
  case. When a folder holds `lbco.edi` and `lbco.cif`, the `.edi` file is read and the `.cif` one is named in a
  warning. A save writes every member as `.edi`, so a saved project holds no `.cif` files.
- The command line, through the project it loads.

edi decides from the names in the file, not from its suffix: a file named `x.edi` that holds only CIF names is read
as a CIF.

## What is read

The file is read as CIF 1.1. Every item and loop value it gives ends in exactly one of these outcomes:

- **taken**: the structure or experiment holds it;
- **checked**: it agrees with a value edi works out itself, such as an IT number beside a symbol, or an isotropic
  value beside a site's tensor;
- **reported**: edi tells you it is not used, and why;
- **refused**: the file is not read at all, and the error names the item.

Only a bare `?` or `.` means a value is absent. A quoted value, `''` and `'?'` included, and a text field are values
you gave, so edi never treats them as missing.

### Values start fixed

A number in a CIF is the published value. Its bracket, as in `3.8909(1)`, is the authors' standard uncertainty, not a
sign that the value should be fitted. So imported values start fixed, and one warning per block lists the items whose
uncertainty was not kept. Free the parameters you want to fit before fitting.

A bracket on a measured intensity is that point's uncertainty, and it fills the uncertainty column. If the file also
gives that column, the two must agree.

### Structures

edi reads the cell, the space group and the atom sites, with their displacement parameters in the form the site
declares. The space group's symbol, number, setting code and symmetry operations are read together. When a symbol
names several settings, as `F d -3 m` does, and the file gives no setting code, the listed operations choose the
setting. Operations that match no setting of the group stop the import.

A site may lie a little off its Wyckoff position, or on another copy of it. edi moves it onto the position and checks
your values in the file's own frame. A value that the symmetry sets otherwise is reported with the value used.

### Experiments

edi reads the experiment type, the instrument, the peak profile, the background, excluded regions, linked structures
and the measured points. A single crystal reads its measured reflections, and no powder settings are added to it.

Every value is checked against the experiment as edi will hold it. One it holds differently, such as point ids that
are renumbered in order, is reported with the value used. One it has no place for, such as a time-of-flight item in a
constant-wavelength experiment, stops the import.

An experiment added to a project must link structures that project holds. If it does not, the import is refused and
the project is left as it was. An experiment made on its own, from a factory, can link any name until it joins a
project.

## The warnings

Every report is a warning whose text starts with `crysta.schema.cif_items_not_read:` and names the block, the items and
the reason, for example:

```text
crysta.schema.cif_items_not_read: CIF block 'lbco': _audit.note not read: no crysta item has these names
```

Python shows them as warnings, the command line prints them on stderr, and the app lists them with the project's
messages. The reasons are: no item has these names; crysta calculates these values itself; a fit's settings and
results, or a project's own settings, are not read from a CIF; the measured points are read rather than a summary of
them; and a value given differently from the one used.

## Files with several blocks

A structure is read from the one block that gives a cell, and an experiment from the one block that gives
experiment items and no cell. A file with none, or with several, is refused, naming the blocks. Every other block is
named in a warning, saying what it holds.
