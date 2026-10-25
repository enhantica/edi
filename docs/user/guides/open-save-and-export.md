# Opening, saving and exporting projects

A project is one folder: `project.edi`, `structures/`, `experiments/`, `analysis/` and `reports/`. Every part of edi
opens the same folder, and every part can hand it on as one `.zip` file that the others open again.

## In the desktop app

- **Open project…** opens a `project.edi` (its folder opens) or a `.zip`. You can also drop a project folder, a
  `project.edi` or a `.zip` onto the window.
- A project opened from a `.zip` is unpacked into a temporary folder. It counts as unsaved: the first **Save** asks
  where to keep it, and later saves go there. Its reports come along.
- **Save project as…** asks first for the format, **Folder** or **Zip archive**, and whether to **Save a copy**, then
  where. A project saved as a zip archive keeps that `.zip` as its location, and later saves rewrite it. A copy is
  written as the project stands now, and you keep working where you were.

## In the web app

- **Open project…** takes a project folder or a `.zip` from your computer.
- **Save** and **Save project as…** download the project as a `.zip`.

## On the command line

```sh
python -m edi calc project.zip --output kept-project   # calculate, keep the result in a folder
python -m edi fit path/to/project/project.edi          # a project.edi opens its folder
python -m edi export path/to/project -o project.zip
```

`fit` and `calc` take a folder, a `project.edi` or a `.zip`. A `.zip` is never changed: without `--output` nothing is
written back.

## In Python

```python
import edi

project = edi.Project.load('project.zip')   # or the folder, or its project.edi
project.save_as('kept-project')             # a project from a .zip has no folder until this
project.export_zip('handed-on.zip')
```

## What a save writes

Values are rounded when they are saved: each value with an uncertainty to the uncertainty's last digit, the
uncertainty with two digits (or by the IUCr rule, if the project says so), and values without an uncertainty to six
significant digits. After a save the open project holds exactly the saved values, and its calculated pattern and R
factors are recalculated from them, so what you see, what the file holds and what a reopened project shows agree.
