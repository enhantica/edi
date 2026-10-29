# Calculate a pattern

<p class="ed-doc-lead">See what the current structural and experimental model predicts before you refine it.</p>

## What enters the calculation

The calculated pattern combines the linked structures with the experiment's instrument, peak-profile and background model. Compare it with the measured pattern where observations are available.

## Choose your interface

=== "Application"

    Inspect the pattern on the Structure, Experiment or Analysis page. Change a cell parameter or profile term to explore its effect on peak positions or shapes.

=== "Python"

    ```python
    import edi

    project = edi.Project.load('path/to/project')
    project.analysis.calculate()
    ```

=== "Command line"

    ```bash
    python -m edi calc path/to/project
    ```

## What to inspect

Start with peak positions, scale and background. Then inspect widths and asymmetry. A refinement is easier to understand when you know which part of the model accounts for the visible mismatch.

[Refine a model →](refine.md)
