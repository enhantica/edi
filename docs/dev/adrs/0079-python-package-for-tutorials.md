# 0079. The Python package for tutorials

- **Status:** Accepted
- **Date:** 2026-11-08
- **Implementation:** 🟡 Partially implemented — the empty named project, explicit links, excluded-region rows and the
  display namespace first; the module name, the wheel's dependencies and the one-line install follow
- **Priority:** High
- **Forward constraint (binding on new features):** a notebook chart or table is a view of the report model drawn by
  the report's own writer and `report.js` (ADR-0036); no Python code draws a chart, lays out a table or picks a colour
  itself. A new display call adds a view kind to `report_view_html`, never a second renderer.

## Context

The owner asked for Jupyter tutorials that install with one plain cell and show the analysis step by step, with charts
and tables after each step, as diffraction-lib's tutorials do (2026-11-08). Four things in the Python package stand in
the way:

- A new project is not empty. `Project()` holds one blank structure and one blank experiment, so the single-block
  scripts (`p.structure.cell...`) work, and a new experiment links one unnamed structure. A tutorial that builds its
  structure and experiment from code then fits a project with a blank structure in it, which crysta refuses ("space
  group '' is not in the table").
- The module is `edi`. diffraction-lib's tutorials start with `import easydiffraction as edi`, and the owner ruled
  that edi's do too, the distribution staying `easydiffraction`.
- The wheel declares numpy only, so a notebook needs a long setup cell.
- There is no per-step display. The only output is the whole HTML report (`project.report`).

The owner also ruled that the notebook charts and the HTML report share one basis, the same model and the same drawing
code, and that every name follows the edi app (2026-11-08).

## Decision

1. **A named project starts empty.** `Project(name=...)` is the app's New project (`empty_project`): no structure, no
   experiment, and the app's minimizer defaults. Reading a collection never creates anything.
2. **An experiment made from code links nothing.** `experiments.create`, `experiments.add_from_data_path` and
   `ExperimentFactory.from_scratch`/`from_data_path` give an experiment with no linked structure.
   `experiment.linked_structures.create(structure_id=..., scale=...)` links one, as the app's Linked structures table
   does. An experiment read from a file or a dictionary keeps the links it states.
3. **The single-block flow keeps working.** `Project()` without a name is the single-block shortcut: it holds one
   structure and one experiment, so `p.structure` and `p.experiment` work at once, as before. The singular setters
   (`p.structure = s`, `p.experiment = e`) add the first one to an empty project, and an experiment set that way
   without a link gets one link to the project's only structure, which is what the blank link did. The native
   `Project()` is unchanged; the loader and `empty_project` already replace its placeholders.
4. **Excluded regions are rows, as in the app.** `experiment.excluded_regions` is still the tuple of `(start, end)`
   pairs, and its `create(start=..., end=...)` adds a region, as a row added in the app's Excluded regions table;
   assigning a list of pairs still replaces them all.
5. **The module is `easydiffraction`.** The distribution stays `easydiffraction` and tutorials write
   `import easydiffraction as edi`. First `easydiffraction` is the public name of the one module the package holds
   (`lib/easydiffraction` gives the same module object as `edi`, so the extension is never loaded twice), and the
   wheel carries both names. Then the package itself moves to `easydiffraction`, every caller with it, and `edi`
   stays only as long as something still imports it.
6. **The wheel carries what a tutorial needs**, so the notebook's only setup is one cell, diffraction-lib's with
   EasyDiffraction's index added: it runs `%pip install easydiffraction --extra-index-url <EasyDiffraction's index>`
   only when `importlib.util.find_spec('easydiffraction')` finds no package, so a user's own environment is never
   reinstalled or upgraded. The display needs no Python package beyond numpy: its views are HTML with plotly.js and
   three.js, loaded from their pinned addresses as the report's are.
7. **`project.display` shows views of the report model.** Each call builds the report model as `project.report.model()`
   does and writes one part of it with the report's writer and `report.js` (`report_view_html`), in a notebook frame of
   its own, so the chart, table or structure is the one the HTML report shows:

   | call | what it shows | report part |
   |---|---|---|
   | `pattern(expt_name=None, x_min=None, x_max=None)` | the measured, calculated and difference pattern with Bragg ticks, or a single crystal's F² chart; `x_min`/`x_max` zoom the x axis | the experiment's figure |
   | `structure(struct_name=None)` | the structure view | the structure's figure |
   | `fit.results()` | the fit result: status, iterations, reduced χ², R factors | the Analysis `fit_result` category |
   | `fit.correlations()` | the correlation chart | Correlations |
   | `fit.series()` | each fitted parameter across a scan's datasets | Evolution |
   | `parameters.free()` | the free parameters with their values and s.u. | the parameter list, free ones |
   | `parameters.fittable()` | the parameters a fit can free | the parameter list, those without a fit blocker (ADR-0053) |
   | `parameters.all()` | every parameter | the parameter list |
   | `constraints()` | the aliases and constraints | the Analysis relations |

   A name left out is the project's only experiment or structure, and several refuse, naming them. In IPython the view
   is shown at once, as diffraction-lib's display calls are; elsewhere the call returns the view, whose `html` is the
   frame's document.
8. **The report gains the tables the views need.** The parameter list keeps whether a fit can free each parameter
   (`fittable`, written only when false), and the Analysis section lists the project's aliases and constraints
   (`relations`, written only when there are some). The HTML report shows the relations after the fit result, so a
   view and the report never show different tables.

## Consequences

- A tutorial builds its structure and experiment from code and fits them, with nothing blank in the project.
- The notebook and the report cannot drift apart: a fix to a chart reaches both.
- A view embeds the report's model and `report.js`, so each frame is as large as the report's data for that project.
- Scripts that relied on a new experiment's blank link without the singular setter now link the structure themselves.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Draw the notebook charts in Python with plotly | Rejected: a second renderer, which the owner ruled out |
| Make the native `Project()` empty too | Rejected: native callers and the loader rely on, or already replace, its placeholders; the change belongs to the Python constructor |
| Keep the module `edi` | Rejected by the owner (2026-11-08) |
