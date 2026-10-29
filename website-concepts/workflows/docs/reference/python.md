# Python

<p class="ed-doc-lead">The <code>edi</code> library exposes the same project model for scripts and notebooks.</p>

## Load a complete project

```python
import edi

project = edi.Project.load('path/to/project')
```

`Project.load()` returns a complete project or raises an input error. Its structures, experiments, observations and analysis settings travel together.

## Calculate or fit

```python
project.analysis.calculate()
result = project.analysis.fit()
print(result.rwp, result.reduced_chi_square)
```

The project's fitting mode selects single, joint, sequential or independent analysis.

## Save the model and report

```python
project.save_as('refined-project')
project.report.save_html('refinement.html')
```

## Learn by doing

The [shared refinement guide](../guides/refine.md) puts these calls in context. [Current source and examples](https://github.com/enhantica/edi) contain the full evolving API; this concept page demonstrates how its reference would be organized.
