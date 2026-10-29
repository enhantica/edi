<p class="ed-kicker">Guides / Build your analysis</p>

# Refine a model

<p class="ed-doc-lead">Bring the calculated pattern into agreement with your measured data — and keep the model physically meaningful.</p>

## Before you fit

Start with a complete project and inspect its calculated pattern. Check the structure, background and peak positions before freeing more parameters. The fit uses the project's measured intensities and their uncertainties.

<div class="ed-doc-note">Use one example throughout: <strong>La₀.₅Ba₀.₅CoO₃ measured on HRPT</strong>. Open <code>pd-neut-cwl_lbco-hrpt</code> from the app's catalogue, or use the same project's folder in Python and the command line.</div>

## Choose what may vary

Refinable parameters have a current value and a choice of whether they vary. Consider the scientific role of a parameter before adding it to the free set. A fit that improves numerically can still describe an inappropriate model.

The project's declared analysis settings determine the fitting mode and minimizer conditions. Keep those settings with the project so another interface runs the same analysis.

## Run the refinement

=== "Application"

    1. Open **Analysis** and inspect the parameters for your experiment.
    2. Select which parameters may vary.
    3. Choose **Start fitting**.
    4. Inspect the updated pattern, fit results and uncertainties.

    Desktop and browser use the same fitting model. Opening and saving files follows the host's file dialogs or browser downloads.

=== "Python"

    ```python
    import edi

    project = edi.Project.load('path/to/project')
    result = project.analysis.fit()

    print(result.rwp)
    print(result.reduced_chi_square)
    ```

    `analysis.fit()` follows the fitting mode declared by the project. The same call handles the declared single, joint, sequential or independent workflow.

=== "Command line"

    ```bash
    python -m edi fit path/to/project --dry
    python -m edi fit path/to/project
    ```

    The first command runs the fit without writing changes back to the project. The second runs and saves it. Refinement conditions live in the project rather than being restated as command-line flags.

## Read the result

Look at the residual across the whole pattern. Check that the refined values make sense, inspect uncertainties and correlations, and consider systematic differences that the current model does not explain.

| Look at | Ask yourself |
| --- | --- |
| Peak positions | Is the structure or calibration consistent with the data? |
| Peak shapes and background | Does the experiment model explain the pattern? |
| Parameter uncertainties | Are the values supported by this measurement? |
| Agreement factors | How much mismatch remains under the chosen weighting? |

## Several experiments or a scan

**Joint** refinement combines experiments in one fit. **Sequential** refinement carries the converged starting point from one scan pattern to the next; **independent** refinement uses the same initial parameters for each pattern. These are different scientific workflows, even though the project is the common entry point.

## Save your analysis

Save the refined project and prepare a report so the model and its results travel together.

[Understand fit results →](results.md){ .md-button }
[Save and share →](export.md){ .md-button }
