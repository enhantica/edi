---
template: gui.html
---

# Example refinement in Python

Download the [notebook](../assets/interfaces/refinement.ipynb) and [example project](../assets/interfaces/example-project.zip). Extract the project beside the notebook, then select a kernel from your [edi environment](setup.md).

## Load the project

<!-- example:python -->
```python
import edi

project = edi.Project.load('pd-neut-cwl_y2o3-spodi')
```
<!-- /example -->

## Refine and inspect

```python
result = project.analysis.fit()
print(f'Rwp: {100 * result.rwp:.2f}%')
print(f'Reduced chi-square: {result.reduced_chi_square:.2f}')
```

For the supplied starting project:

```text
Rwp: 1.34%   ·   Reduced χ²: 1.20
```

The notebook plots measured and calculated arrays with Plotly. Expand its plotting cell to see or change the code. [Inspect results](results.md) describes parameter values and uncertainties.

<!-- learning-comparison -->
<div class="gui-viewer" markdown="1">

=== "Starting model"

    <p class="gui-view-description">Compare the starting calculation with the measured pattern. The residual shows their difference.</p>

    <figure class="ed-interface-preview" data-interface-hero>
    <a class="gui-image-link" href="../assets/learning/initial.svg?v=f06fa4f9ee38" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Starting model"><svg class="gui-capture" viewBox="0 0 1000 540" width="1000" height="540" role="img" aria-label="Starting model"><title>Starting model</title><defs><clipPath id="interface-initial"><rect y="0" width="1000" height="540" rx="12" /></clipPath></defs><image href="../assets/learning/initial.svg?v=f06fa4f9ee38" width="1000" height="540" clip-path="url(#interface-initial)" /><rect class="gui-image-frame" y="0" width="1000" height="540" rx="12" /></svg></a>
    </figure>

=== "Refined model"

    <p class="gui-view-description">After refinement, compare the same peaks and residual on exactly the same axes and scale.</p>

    <figure class="ed-interface-preview" data-interface-hero>
    <a class="gui-image-link" href="../assets/learning/refined.svg?v=8c5fe4e476e6" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Refined model"><svg class="gui-capture" viewBox="0 0 1000 540" width="1000" height="540" role="img" aria-label="Refined model"><title>Refined model</title><defs><clipPath id="interface-refined"><rect y="0" width="1000" height="540" rx="12" /></clipPath></defs><image href="../assets/learning/refined.svg?v=8c5fe4e476e6" width="1000" height="540" clip-path="url(#interface-refined)" /><rect class="gui-image-frame" y="0" width="1000" height="540" rx="12" /></svg></a>
    </figure>

</div>

<!-- /learning-comparison -->

## Keep the result

```python
project.save_as('refined-project')
project.report.save_html('refinement.html', offline=True)
```

The starting files stay unchanged until you save. See [load and save](projects.md) for other input and output forms.
