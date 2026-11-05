# Analysis workflow

A complete EasyDiffraction analysis connects the model of a sample with an experiment and keeps the decisions that produced the result. Follow these stages in any interface.

<!-- workflow-diagram -->
<ol class="ed-workflow-diagram" aria-label="Analysis workflow">
<li><a href="project/"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3h18v4H3zm1 5h16v13H4zm5.5 3a.5.5 0 0 0-.5.5V13h6v-1.5a.5.5 0 0 0-.5-.5z"/></svg><span>Project</span></a></li>
<li><a href="structure/"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 11H19V7a2 2 0 0 0-2-2h-4V3.5A2.5 2.5 0 0 0 10.5 1 2.5 2.5 0 0 0 8 3.5V5H4a2 2 0 0 0-2 2v3.8h1.5c1.5 0 2.7 1.2 2.7 2.7S5 16.2 3.5 16.2H2V20a2 2 0 0 0 2 2h3.8v-1.5c0-1.5 1.2-2.7 2.7-2.7s2.7 1.2 2.7 2.7V22H17a2 2 0 0 0 2-2v-4h1.5a2.5 2.5 0 0 0 2.5-2.5 2.5 2.5 0 0 0-2.5-2.5"/></svg><span>Structure</span></a></li>
<li><a href="experiment/"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.46 6.28 11.05 9c-2.58.26-4.55 2.41-4.55 5a5 5 0 0 0 5 5c2.05 0 3.81-1.23 4.58-3H13.5v-2h8v2h-2.25a8.05 8.05 0 0 1-2.46 4h2.71v2h-16v-2h2.71a8 8 0 0 1-2.71-6c0-3.63 2.46-6.8 5.96-7.72m3.28-4.21.76 1.3.86-.5 3.5 6.06-3.47 2-3.5-6.06.87-.5-.76-1.3z"/></svg><span>Experiment</span></a></li>
<li><a href="analysis/"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2m0 2v4h10V4zm0 6v2h2v-2zm4 0v2h2v-2zm4 0v2h2v-2zm-8 4v2h2v-2zm4 0v2h2v-2zm4 0v2h2v-2zm-8 4v2h2v-2zm4 0v2h2v-2zm4 0v2h2v-2z"/></svg><span>Analysis</span></a></li>
<li><a href="report/"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 9H7V7h10m0 6H7v-2h10m-3 6H7v-2h7M12 3a1 1 0 0 1 1 1 1 1 0 0 1-1 1 1 1 0 0 1-1-1 1 1 0 0 1 1-1m7 0h-4.18C14.4 1.84 13.3 1 12 1s-2.4.84-2.82 2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2"/></svg><span>Report</span></a></li>
</ol>
<!-- /workflow-diagram -->

<div class="ed-workflow-stage-table" markdown="1">

| Stage | Scientific task | Ready to continue when… |
| --- | --- | --- |
| [<span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true">:material-archive:</span><span class="ed-icon-text">Project</span></span>](project.md) | Organise the analysis, inputs and provenance | You can identify the measurement, model and starting conditions |
| [<span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true">:material-puzzle:</span><span class="ed-icon-text">Structure</span></span>](structure.md) | Describe the crystalline phase or phases | Symmetry, cell and atom sites represent your intended sample model |
| [<span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true">:material-microscope:</span><span class="ed-icon-text">Experiment</span></span>](experiment.md) | Describe the observations and how they are calculated | Data or a simulation range, instrument, profile, background and structure links are consistent |
| [<span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true">:material-calculator:</span><span class="ed-icon-text">Analysis</span></span>](analysis.md) | Calculate, refine and assess | The result has been inspected against the observations and physical model |
| [<span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true">:material-clipboard-text:</span><span class="ed-icon-text">Report</span></span>](report.md) | Communicate and retain the result | The report matches the saved model and the complete project is retained |

</div>

## Revisit the model

These stages are connected rather than a one-way checklist. A shifted peak may lead back to the cell or instrument calibration. An unmodelled peak may require checking the phases or measurement history. Review the starting calculation before adding more free parameters.

## Calculate or refine

A simulation uses a calculation range without measured observations. A refinement uses measured data and their uncertainties. A project can include both kinds of experiments; calculation and fitting use them according to their roles.

## Choose how to carry it out

| Interface | What its section provides |
| --- | --- |
| [<span class="ed-interface-icons" aria-hidden="true">:lucide-globe: :lucide-monitor:</span> <span class="ed-icon-text">Application</span>](../../application/index.md){ .ed-interface-link .ed-icon-label } | Workspace, imports, parameter controls, fit progress and visual inspection |
| [<span class="ed-interface-icons" aria-hidden="true">:simple-python: :simple-jupyter:</span> <span class="ed-icon-text">Python</span>](../../python/index.md){ .ed-interface-link .ed-icon-label } | Project objects, parameter access, analysis calls and result objects |
| [<span class="ed-interface-icons" aria-hidden="true">:lucide-square-terminal: :simple-python:</span> <span class="ed-icon-text">Command Line</span>](../../cli/index.md){ .ed-interface-link .ed-icon-label } | Commands for saved projects, output options and automation |

The scientific explanations belong here; the interface pages link back to them as needed.
