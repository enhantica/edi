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
   read correctly rounded; a non-finite double is `null`.
2. **One builder.** `edi::build_report(const Project&, const ReportOptions&)` is the only function that reads a
   project. The options say which sections, all or free parameters, the correlation level (absent: the five most
   correlated, as the Correlations tab and diffraction-lib), which experiments, the x axis (native or d-spacing),
   whether to show the residual and the Bragg ticks, and the time the report states (default: now, in UTC).
3. **Sections, in order:** Project summary, Analysis (software, minimizer, fitting mode, fit result, then Parameters,
   Correlations and, for a scan, Evolution), Structures, Experiments. The options remove sections and never reorder
   them. A scan's report holds its template dataset's sections, the evolution charts and the template's correlations,
   and nothing of the other datasets.
4. **Charts are the core's outputs.** For each experiment the builder captures the pattern (the d axis is a capture
   choice: x from `_pd_data.d_spacing` and the ticks from `_refln.d_spacing`, ascending), applies the options to that
   source (no residual: no residual column; no ticks: no phases) and stores `present_pattern`'s presentation at full
   resolution, with the core's hover text for each Bragg point and the style rows it names. For each structure it
   stores `present_structure`'s scene (default options), its `default_view` and `scene_drawing` for a report viewport
   of 800 × 600. Correlations and evolution come from the functions the Correlations and Evolution tabs then share.
5. **Numbers.** Every value with a standard uncertainty carries the number, its s.u. and the text spelled by the
   project's rule, so no renderer writes a bracket itself.
6. **The static PDF is the app's.** The core also writes the report as static HTML in the subset Qt's rich text reads
   (`report_static_html`): the same sections and tables, each number in two cells so a column's points line up under
   any header, and each figure an image by its name. The app lays it out with `QTextDocument` on A4 pages with 2.5 cm
   margins and the page number below, keeps a heading with what follows it and a short table whole, and draws the
   figures as the preview's images, grabbed at twice their size. The CLI and Python do not write it, as edi's core
   has no Qt.

## Consequences

- The HTML report, the Report page, the PDF and a notebook show the same numbers, charts and order, and the CLI,
  Python and the app write the same HTML bytes for the same project, options and time. The PDF's figures follow the
  app's theme, as the preview draws them.
- Restyled charts and edi's Python plotting take these specs as they are; a renderer that needs another viewport
  reruns the same core function on the model's data.
- The model holds full-resolution patterns, so a report of a long scan is as large as its template's data.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| Render the report from the project in each surface | Rejected: three implementations of the same sections would drift; the owner ratified one model. |
| Give `report.js` the raw pattern columns | Rejected: it would decide gaps, error bars and pane layout again, which ADR-0021 assigns to `present_pattern`. |
| A web view in the app | Rejected by ADR-0006 and ADR-0015 §8 (no WebEngine in the browser build). |
