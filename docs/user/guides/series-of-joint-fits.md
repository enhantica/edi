# Series of joint fits

Some measurements give several patterns at every step: one file per detector bank, or one per instrument, each time a
temperature or a field changes. A **series of joint fits** fits each step, a *point*, jointly over all its patterns,
and then moves on to the next point. The structure is shared by the patterns of a point; each experiment keeps its own
scale, calibration, peak shape and background.

## Loading the files

Create the first experiment as usual: its type, its instrument and its linked structures. Then, in the Experiment
page's **Measured data** group, choose **Load measured data ▸ From file…** and select the files of every point, or
**From folder…** for a whole folder. In **Load N datasets as**, choose **Series of joint fits**.

The files are grouped by name. In each name, the first run of digits that changes between the files becomes the point;
the rest of the name says which experiment the file belongs to. For example `p001_bank1.xye`, `p001_bank2.xye`,
`p002_bank1.xye` and `p002_bank2.xye` become two experiments, `p*_bank1.xye` and `p*_bank2.xye`, with points `001` and
`002`. The experiment you started from becomes the template of the first group, and a copy of it is made for each
further group. The experiments form an experiment set, and each shows its first point's pattern.

The project saves the folder and one file pattern per experiment, never a list of files. The folder stays linked where
it is; Save as offers to copy it into the project (below).

A point that lacks a file for some experiment, or has two, is not fitted. The Measured data group says how many such
points there are, and how many points' files changed after they were fitted.

## Tying experiments together

In a series every experiment starts as an ordinary experiment with its own parameters. Two switches tie them:

- **Shared**, a column of the Parameters table on the Analysis page in the Joint mode: switched on for one
  experiment's parameter, every experiment's copy has one value. It never changes a constraint; see
  [Shared parameters and the parametric fit](shared-parameters-and-the-parametric-fit.md).
- **Phase ratios shared**, in the Linked structures group of a multi-phase experiment: the other experiments keep their
  own overall scale and follow this experiment's ratios between the phases.

Each switch is one step that Undo takes back.

## Fitting and the results

On the Analysis page choose **Sequential** and fit. Each point starts from the previous point's values as they were
written to the results, so a series that is stopped and continued gives the same results as one run straight through.

A series writes two results files in `analysis/`:

- `results.csv`, one row per point: the joint fit's χ², whether it succeeded, the shared parameters and the derived
  values that belong to the structure (a moment's size and angles);
- `results_experiments.csv`, one row per point and experiment: each experiment's own parameters, its share of χ², the
  file it read with its size and time, and its phase weight fractions.

## Looking at a series

The **Stacked** and **Map** tabs draw one row per point, on the d axis, so that patterns from different banks line up.
The **Rows** choice shows every experiment of a point merged, each divided by its fitted scale, or one experiment.

The **Evolution** tab follows a parameter across the points. Choose **Common** for the parameters in `results.csv`, or
**Per experiment** for each experiment's own parameters in `results_experiments.csv`. Derived values such as weight fractions
and moment angles are listed with the fitted ones.

## Saving

**Save as** shows a **Measured data** choice for a project that reads data from outside its folder: copy the files into
the project, or keep them linked. It starts from the project's Data on save setting.

## From the command line and Python

The same project runs with `python -m edi fit <project>` and with `project.analysis.fit()` in Python. The example
`docs/user/cli/pd-neut-tof_ncaf-wish-5bank_scan-6p` is a six-point series of the five WISH banks of
Na<sub>2</sub>Ca<sub>3</sub>Al<sub>2</sub>F<sub>14</sub>.
