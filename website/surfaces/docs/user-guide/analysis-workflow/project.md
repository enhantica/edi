# :material-archive: Project

A project is the complete working record of an analysis. It keeps structures, experiments, data, fitting settings and saved results together, so the analysis can be inspected, repeated and continued.

## Establish the analysis

Start from an included example, open an existing complete project, or assemble the inputs for a new measurement. Give the analysis a useful identity and retain the provenance of its structural model and observations.

A structural CIF supplies a structure. An experiment CIF supplies an experiment, including its measured points, and a measured-pattern file supplies observations. Neither alone describes a complete analysis: the project connects them with instrument settings, structural links and analysis choices.

## What belongs together

| Part | Role |
| --- | --- |
| Structures | Sample models, including symmetry, cell and atom sites |
| Experiments | Measured observations or simulation ranges, instrument/profile/background settings and links to structures |
| Analysis | Free parameters, constraints, fitting mode and minimizer conditions |
| Results and reports | Recorded outcomes and documents for inspection and sharing |

Several experiments can share a structure while keeping different measurement settings. Several structures can contribute to one experiment. Check those links explicitly when adding phases or measurements.

## Keep a complete copy

The project folder contains `project.edi` and associated `structures/`, `experiments/`, `analysis/` and `reports/` content. A `.zip` archive packages the folder for transfer. See [data formats](../data-formats.md).

Keep the full folder or archive when moving between interfaces. Retain starting conditions separately when you want to compare them with a refined state. Saving a report is separate from saving the editable project.

## Check completeness

A runnable experiment needs valid structure links and either observations with uncertainties or a calculation range. The complete-project reader rejects ambiguous or incomplete saved inputs instead of returning a partially loaded project.

For scans, retain the declared source files and their order along with the template and results. Moving a project may require checking that the scan's external input location is still available.

Create, open and save a project in the [<span class="ed-interface-icons" aria-hidden="true">:lucide-monitor:</span> <span class="ed-icon-text">Application</span>](../../application/projects.md){ .ed-interface-link .ed-icon-label }, [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../../python/projects.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:lucide-square-terminal:</span> <span class="ed-icon-text">Command Line</span>](../../cli/files.md){ .ed-interface-link .ed-icon-label }.
