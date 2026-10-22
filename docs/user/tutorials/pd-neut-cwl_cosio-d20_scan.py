# %% [markdown]
# # Sequential fit: Co₂SiO₄, D20 temperature scan
#
# Fit Co₂SiO₄ to a cooling scan from D20 at ILL, 155 patterns from 497.4 to 52.3 K, one after another:
# each fit starts from the previous one's result. The magnetic frames at the lowest temperatures are
# left out.
#
# The project is the catalogue case `pd-neut-cwl_cosio-d20_scan`: the files the command line fits with
# `python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_scan/project` and the app opens from its
# Examples.

# %% [markdown]
# > This tutorial is not run when the documentation is built yet. It loads its project from the edi
# > repository, so it runs once a tutorial runner can provide the project elsewhere
# > (`execution-exclusions.yml`).

# %%
import edi

# %% [markdown]
# ## Load the project

# %%
project = edi.Project.load('../cli/pd-neut-cwl_cosio-d20_scan/project')
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))
print('Fitting mode:', project.fitting_mode)

# %% [markdown]
# ## The start
#
# The project starts the way your own measurement would: zero shift 0, profile terms to one
# significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the
# scale to one significant figure. Only the template pattern starts this way; each later pattern
# starts from the fit before it.
#
# The fit is free to change these parameters:

# %%
for parameter in project.free_parameters:
    print(f'{parameter.name:28} {parameter.value:12.6g} {parameter.units}')

# %% [markdown]
# ## Work on a copy
#
# A sequential fit writes one row per pattern into the project's `analysis/results.csv`, so save a
# copy first and fit that.

# %%
project.save_as('pd-neut-cwl_cosio-d20_scan')

# %% [markdown]
# ## Fit the first patterns, then stop
#
# The fit can stop between patterns. Here it stops after five; the rows it wrote stay.

# %%
fitted = []
result = project.fit_sequential(
    on_file_complete=lambda *args: fitted.append(args),
    should_cancel=lambda: len(fitted) >= 5,
)
print(result.status.name.lower(), 'after', len(fitted), 'patterns')

# %% [markdown]
# ## Resume
#
# Starting again continues with the first pattern that has no row yet, from the last fitted values.

# %%
result = project.fit_sequential(on_file_complete=lambda *args: fitted.append(args))
print(result.status.name.lower(), 'with', len(fitted), 'patterns fitted in all')

# %% [markdown]
# ## The results
#
# One row per pattern, in the order they were fitted.

# %%
import csv

with open('pd-neut-cwl_cosio-d20_scan/analysis/results.csv', newline='') as file:
    rows = list(csv.DictReader(file))
print(len(rows), 'rows; columns:', ', '.join(list(rows[0])[:6]), '...')

# %% [markdown]
# ## Patterns and report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structure and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_cosio-d20_scan.html')
