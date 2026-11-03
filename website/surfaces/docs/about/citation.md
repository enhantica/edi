# Cite and record an analysis

A software citation identifies the software you used. A reproducible analysis also identifies its inputs, model and settings.

## Identify the software

Record the exact release version or source commit of edi that produced the result. For a browser or desktop build, keep the version information shown by that build with the exported result. For a source environment, record the checkout commit and its dependency information.

If your release supplies a recommended citation or a DOI, use the citation for that exact version.

## Identify the analysis

Keep enough information for another person to run the same calculation or fit:

- the measured data and their origin;
- the structural model and its scientific source;
- instrument, background and peak-profile settings;
- excluded regions and the independent free parameters;
- fitting mode and minimizer conditions;
- the complete saved project and the exported result.

For a scan, retain the file order, template and result table. For a comparison with another program, record which model terms and observations were matched and any differences that remain.

## Keep a project and a report

The project is the state you can reopen and analyse. A [report](../application/reports.md) is a separate account of the model and result. Keep both when sharing work: the report makes the result readable, and the project makes continued analysis possible.

A figure or a single agreement factor cannot by itself preserve the starting state and fitting choices. The [fit-quality guide](../user-guide/fit-quality.md) explains the context needed to interpret those summaries.

## Cite data and reference methods

Retain the citation and provenance of external measurements, structural models and independent reference calculations. Example pages in the repository explain their sources and comparison conditions.

When reproducing a published example, consult its own reference record rather than treating the software's citation as a replacement for data or scientific-method citations.
