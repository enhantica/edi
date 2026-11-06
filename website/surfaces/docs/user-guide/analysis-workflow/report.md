# :fa5-clipboard-list: Report

A report brings the model and analysis outcome into a document for inspection and sharing. It complements the complete project, which retains the editable analysis.

## What to retain

A useful scientific account identifies the structures, experiments, observations, analysis choices and outcome. Inspect the refined values, uncertainties and agreement factors together with the observed/calculated patterns and residuals.

Report settings select optional material such as charts, correlations, reflection information, data points and scan evolution. Include what the reader needs to assess the result, and retain the complete project when a report omits large data tables.

## Choose an output

| Output | Purpose | Current interface support |
| --- | --- | --- |
| Interactive HTML | Share a readable document with interactive figures | Application, Python and Command Line |
| Offline HTML | Embed chart libraries so the document can be opened without fetching them | Application, Python and Command Line |
| PDF | Share a paginated document with static figures | Application |
| CIF report | Exchange a scientific account of structures, experiments and results | Application, Python and Command Line |

A structural CIF used as input and a CIF report serve different purposes. Neither replaces the complete project; see [data formats](../data-formats.md).

## Save the model and the report

Saving a project and writing its report are separate actions. A model or report-settings change can make a previously saved report out of date. A file that has been removed can be marked missing.

Check report state before sharing it. Keep the report together with the matching project, measured data provenance and software version. For a scan, include the template, file order and information about failed or incomplete results.

## Generate the document

- [Application: Report page, export formats and saved-state indicators](../../application/reports.md).
- [Python: report rendering and save methods](../../python/reports.md).
- [Command Line: report output and freshness checks](../../cli/reports.md).

Use [citation and reproducibility](../../about/citation.md) when preparing a publication or handing an analysis to a collaborator.
