# The report

A project's report sets out its structures, its experiments, the fit and its correlations as one document. The app
shows it on the Report page and saves it; the command line and Python save the same report from the same settings.

## On the Report page

The page shows the report as it will be saved, with its charts and structure views. The sidebar has two groups.

**Export** says which formats Save report writes, two to a row: the interactive HTML and whether it embeds its chart
libraries, then the PDF and the CIF report (the CIF report is not available yet). **Save report** writes each ticked
format into the project's `reports/` folder as `<short name>.html` or `.pdf`; in the web app the files are also
downloaded. Unticking a format never deletes a report saved before.

The reports saved so far are listed under the button with the time each was saved. One is marked **out of date** when
the report the project would make now differs from it, for example after a fit or a change to the Contents, and
**missing** when its file is no longer in `reports/`. The marks are there after the project is opened again too. Save
report brings them up to date.

**Contents** has a box for each optional part: the charts, the correlations, the reflections, the data points and, for
a scan, the evolution. The data are left out at first, as they are usually long.

The HTML report keeps its charts interactive: zoom and hover on the patterns, and turn the structures, with the
Structure page's buttons. Without the embedded libraries it loads them from the web when it opens. The PDF is laid out
on A4 pages with its charts as images, always in the light colours.

## Where the settings live

The settings are part of the project and are saved with it:

- `reports/report.edi` holds what Save report writes (`_report.html`, `pdf`, `cif`), whether the HTML embeds its
  libraries (`_report.html_offline`), the parts left out (`_report.excluded`), and a `_report_file` row for each
  report saved, with the time it was saved and a digest of what was written;
- `analysis/analysis.edi` holds the correlation chart's threshold (`_correlation_chart.threshold`), which the
  Correlations tab's level or count sets, and the charts' x axis (`_pattern_chart.x_axis`), which the Analysis chart's
  x box sets.

Saving the project writes no report, and rewrites `reports/report.edi` only when a setting changed.

## From the command line

```console
python -m edi report path/to/project
python -m edi report path/to/project --check
```

The first writes the ticked formats but the PDF, which the app writes, into `reports/`, as Save report does. Flags
change a setting for that run only: `--offline` or `--online`, `--x-axis native` or `d_spacing`,
`--correlation-threshold X`, `--exclude KEY` (repeated) or `--include-all`. `--check` lists each saved report as
current, out of date or missing, writes nothing, and exits with 1 when one is not current.

## From Python

```python
import edi

project = edi.Project.load('path/to/project')
project.report.excluded = []          # include every part
project.report.save()                 # as Save report, the PDF aside
project.report.check()                # [('lbco_hrpt_s2.html', 'current'), ...]
html = project.report.as_html(offline=True)
```

`project.report.html_offline`, `correlation_threshold`, `x_axis` and `excluded` read and set the project's settings.
`model()`, `as_html()`, `save_html()` and `save()` take the same names as keywords, each changing a setting for that
call only. In a notebook, `project.report` on its own shows the report.
