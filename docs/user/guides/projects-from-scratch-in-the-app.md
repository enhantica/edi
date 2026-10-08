# A project from scratch in the app

You can build a project in the app without preparing any file first: create a structure, create an
experiment, load its measured pattern from a plain text file, and fit.

## A structure

On the Structure page, **Create structure** adds a structure named `structure1` (then `structure2`,
and so on) with one oxygen atom at the origin in space group P b n m, a = 10, b = 6 and c = 5 Å. Edit
its space group, cell and atom sites into the structure you need. It is linked to no experiment yet.

Removing a structure also removes every experiment's link to it, in one step that **Undo** puts back,
and the status bar's Messages names the experiments that lost the link.

## An experiment

On the Experiment page, **Create experiment** adds an experiment named `experiment1` (then
`experiment2`, and so on), linked to every structure of the project. Until it has data it is a
simulation: choose its type, and the start, end and step of the range its pattern is calculated over.

## Its data

**Load data…** in the experiment's File cell reads a plain text file with two or three columns,
`x y` or `x y σ`, separated by spaces, tabs or commas. x is 2θ in degrees for a constant-wavelength
experiment and time of flight in µs for a time-of-flight one. The file dialog shows `.xye`, `.xy`,
`.dat`, `.txt` and `.csv` files, or all files; in the web app the browser's file chooser opens.

The reader:

- skips every line that is not two or three numbers, such as headers and comments;
- takes σ = √max(y, 1) when the file has no σ column, and replaces a σ below 0.0001 with 1;
- skips rows with an intensity of zero or less;
- sorts the rows by x and keeps the first of two rows with the same x.

One message in the status bar's Messages says how many points were loaded and what was skipped or
changed. The data replaces the simulation's range, whose fields then show the data's start, end
and step, and the experiment's type can no longer change. Its instrument, peak, background and
excluded regions stay as they were. An experiment still called `experimentN` takes the file's name;
a name you gave it stays.

The File cell then shows the file's name; clicking it loads another file in place of the data.
**Undo** takes a load back, to the simulation or to the data before. Saving stores the data in the
experiment's `.edi` file, so the project no longer needs the file you loaded; the File column still
shows that file's name.

## Experiments with and without data

A project can hold experiments with data and experiments without. A calculation covers all of them;
a fit uses only the experiments with data.
