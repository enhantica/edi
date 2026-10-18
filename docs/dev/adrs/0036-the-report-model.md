# The report model

- **Status:** Accepted
- **Date:** 2026-10-13
- **Implementation:** 🟡 Partially implemented — the model, its JSON and the builder first; the HTML writer, the Python
  and CLI surfaces and the Report page follow
- **Priority:** High
- **Forward constraint (binding on new features):** every renderer of a report — the HTML writer, `report.js`, the
  Report page and the Python display — reads a `ReportModel` or its JSON, never the project; only `build_report` reads
  a project. A chart or scene in a report is the output of the core function the app's own view draws
  (`present_pattern`, `present_structure`, `default_view`, `scene_drawing`, `correlation_matrix`, `evolution_series`);
  no renderer decides layout, decimation, radii, bonds, orientation or colours again.

## Context

A fitted project should produce a report like diffraction-lib's: a self-contained HTML file with interactive charts
for the command line, the Python library, notebooks and the app's Save report, and a live preview on the app's Report
page, without a web view (ADR-0006, ADR-0015 §8). The owner ratified one report model built in the core, with neutral
chart and scene descriptions, a small `report.js` mapping them to plotly.js and three.js, and the app drawing the same
model with its own views (2026-10-10). The model is also the data the CIF report (later) and the app's charts and
Python plotting are built from.

diffraction-lib's HTML report (`report/data_context.py`, `templates/html/report.html.j2`) has four numbered sections:
Project summary, Analysis, Structures and Experiments. Its fitted parameters, correlation heatmap and parameter evolution
are notebook calls, not report sections; the owner asked for all three in edi's report (2026-10-12).

## Decision

1. **One versioned model.** `edi::ReportModel` (`core/include/edi/report_model.hpp`) is plain data, free of Qt and
   HTML, with `schema_version` 1. `report_to_json` and `report_from_json` (`core/src/report_json.cpp`) carry every field;
   a model read from its JSON writes the same JSON again. Doubles are written in their shortest round-trip form and
   read correctly rounded; a non-finite double is `null`. The reader also refuses a model whose indices leave their
   collections, as the builder never makes them: an atom's major part or a sphere's, bond's, label's or shared site's
   atom that does not exist, a structure the viewer draws without its three views along the axes (another may have none,
   as a report without its figures does), a measured series without one data row and one pair of bar ends per point, or
   another series' bars that are neither none nor one per point. Renderers index with these, so they are checked once,
   where the model is read.
2. **One builder.** `edi::build_report(const Project&, const ReportOptions&)` is the only function that reads a
   project. The options say which sections, all or free parameters, the correlation level (absent: the five most
   correlated, as the Correlations tab and diffraction-lib), which experiments, the x axis (native or d-spacing),
   whether to show the residual and the Bragg ticks, and the time the report states (default: now, in UTC).
3. **Sections, in order:** Project summary, Analysis (software, minimizer, fitting mode, fit result, then Parameters,
   Correlations and, for a scan, Evolution), Structures, Experiments. The options remove sections and never reorder
   them. A scan's report holds its template dataset's sections, the evolution charts and the template's correlations,
   and nothing of the other datasets. The template dataset is the declared one, else the first of the scan's files;
   its correlations are the pairs the fit record keeps for it (ADR-0034), so a report from the saved files shows the
   same pairs as one made in the app.
4. **Charts are the core's outputs.** For each experiment the builder captures the pattern (the d axis is a capture
   choice: x from `_pd_data.d_spacing`, ascending, and each tick at its `_refln.position` mapped to d as the points are,
   so it meets its peak as on the native axis, its readout keeping `_refln.d_spacing`), applies the options to that
   source (no residual: no residual column; no ticks: no phases) and stores `present_pattern`'s presentation at full
   resolution, with the core's hover text for each Bragg point and the style rows it names. For each structure it stores
   `present_structure`'s scene (default options), its `default_view` and `scene_drawing` for a report viewport of 800 ×
   600. Correlations and evolution come from the functions the Correlations and Evolution tabs then share:
   `correlation_matrix`, and `evolution_parameters` with `evolution_series`, which read a scan's results. In the JSON,
   the analysis rows are `analysis_categories`; `correlations` and, for a scan, `evolution` (per listed parameter its
   `name`, `units`, `x_title` and points with `x`, `y`, `su` and `text`, all read from the results in one pass) sit at
   the root. Each pattern carries its `title`, the experiment's Rwp and χ² (`reliability_text`), and `legend`, false:
   its y titles name the series in their colours. The evolution is one chart per listed parameter, in the Evolution
   tab's order, titled with its name and units: one to a row, the column's width, its height to its width the Evolution
   tab's at the app's default window size (1.05), so its axes keep the app's proportions. A pattern or evolution chart
   has no border round it; a structure view is framed as a table is (the owner, 2026-10-14). The preview draws each with
   the Evolution tab's chart given its series, the HTML report with plotly.js, and the PDF as images of the preview's
   charts. Every renderer colours the charts from the model's style rows alone, never from the app's settings or
   project: a scan's table has a measured row for each of its datasets and its pattern takes its template dataset's row,
   the colour the app's pages give that dataset, and the evolution charts take the first measured row in every renderer.
5. **Numbers.** Every value with a standard uncertainty carries the number, its s.u. and the text spelled by the
   project's rule, so no renderer writes a bracket itself. Units follow the value after a space, as the app's unit
   fields write them; an angle is in `deg`, never with the degree sign, in tables and axis titles alike, in the app and
   in every report (the owner, 2026-10-17).
6. **The static PDF is the app's.** The core also writes the report as static HTML in the subset Qt's rich text reads
   (`report_static_html`): the same sections and tables, each number in two cells so a column's points line up under any
   header, and each figure an image by its name. The app lays it out with `QTextDocument` on A4 pages with 2.5 cm
   margins and the page number below, keeps a heading with what follows it and a short table whole, lets a long table
   run on over pages with its header repeated on each, and draws the figures as images of copies of the preview's
   figures in the light colours, whatever the app's theme, as a PDF is for print, grabbed at twice their size. Its text
   is printed in the light theme's ink too, and its tables' borders are finer and lighter than the HTML report's, as
   they print bolder. The PDF and the HTML report show the same groups: a group the Contents include, the reflections
   and the measured data among them, is shown in full in both, the HTML's tables every row (the owner, 2026-10-14). The
   CLI and Python do not write it, as edi's core has no Qt.

7. **The report's settings are project data, kept with the page that sets them.** `reports/report.edi` holds what Save
   report writes: the formats (`_report.html`, `pdf`, `cif`; absent, the HTML only), whether the HTML embeds its
   libraries (`html_offline`; absent, online) and the groups the report leaves out (`excluded`; absent, the data are
   left out, as they are usually long; an empty list includes everything), with a `_report_file` row for each report
   Save report wrote: its format, its name, when it was saved, the project's last-modified time and the digest of what
   was written. Each file is written beside its old one and renamed over it, so a failed write leaves the old file.
   Nothing is written behind a link: a linked `reports/` is made the project's own, a folder of links to its entries,
   before the first file is renamed into it, and a link at a file's name is replaced. Every temporary file is written
   new: whatever stands at its name, a link, a second name of another file or a leftover, is removed first, never
   written through. Every surface, the app's HTML and PDF included, writes through the same core function, which keeps
   the rules of ADR-0039 for every project write. A
   format that fails stops the formats after it, the files written before it keeping their rows, and the open project's
   rows change only when `reports/report.edi` is written. The colour scheme and, in a fit of several experiments, the
   experiment whose parameters the correlation chart shows are choices of the surface, not settings of the project, and
   each surface gives them explicitly: the app its Preferences' scheme and the experiment its Analysis page shows,
   Python its `colour_scheme` and `correlation_experiment` keywords and the CLI its `--colour-scheme` and
   `--correlation-experiment` flags, by default the default scheme and the first experiment. A row's digest is of the
   report the project makes with those defaults, whatever the surface chose, and every surface judges a row by it
   (`report_file_options`), so a report is out of date only when the project changed since it was saved (the owner,
   2026-10-14). `analysis/analysis.edi` holds the correlation threshold (`_correlation_chart.threshold`; absent,
   diffraction-lib's automatic rule) and the charts' x axis (`_pattern_chart.x_axis`, `native` or `d_spacing`). crysta
   checks every value, reads and writes both files; a project save writes `reports/report.edi` only when its text
   changes and writes no report. `effective_report_options(project, overrides)` makes a report's options from them, each
   replaced by a given override for one run, writing nothing. In the app the Report page's Contents boxes and Embed
   checkbox, the Analysis page's correlation level and its chart's x axis write them as undoable edits; a count sets the
   lowest threshold that keeps at most that many parameters, a tie kept whole, and only the threshold is saved. The
   Preferences give a new project's `html_offline` only. A `_report` line in `project.edi`, diffraction-lib's, is not
   read. The Export group shows one row per format, its box and the path of the file Save report would write now
   (`reports/<name>.<ext>`, read-only; the file name alone in the browser), found by that name among the rows: normal
   while the file matches what Save report would write now, red when it does not or is gone, "not saved yet" while no
   row has that name (a renamed project's older reports keep their rows and files), dimmed while its box is unticked.
   After a project save the open project takes the values its files hold, as a reopen reads them (rounded by the IUCr
   rule), and is calculated once from them, so a report saved then is still current when the project is reopened. The
   Report page's Text tab shows `reports/report.edi` with every setting the project leaves at its default written out
   with that value (`report_settings_text`), so it shows the report settings before any is changed, as the file is left
   out until one is. In the browser Save report also downloads the files, one file as itself and several as
   `<name>-reports.zip`, and they stay in the in-browser `reports/` until a reload.

## Consequences

- The HTML report, the Report page, the PDF and a notebook show the same numbers, charts and order, and the CLI,
  Python and the app write the same HTML bytes for the same project, options and time.
- Restyled charts and edi's Python plotting take these specs as they are; a renderer that needs another viewport
  reruns the same core function on the model's data.
- The model holds full-resolution patterns, so a report of a long scan is as large as its template's data.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| Render the report from the project in each surface | Rejected: three implementations of the same sections would drift; the owner ratified one model. |
| Give `report.js` the raw pattern columns | Rejected: it would decide gaps, error bars and pane layout again, which ADR-0021 assigns to `present_pattern`. |
| A web view in the app | Rejected by ADR-0006 and ADR-0015 §8 (no WebEngine in the browser build). |
