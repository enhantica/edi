"""Sequential fit: LATP, BM01."""
# %% [markdown]
# # Sequential fit: LATP, BM01
#
# Fit three phases, LATP and two AlPO₄ forms, to 73 synchrotron X-ray patterns from BM01 at SNBL,
# one after another, with linked displacement parameters.
#
# The project is the catalogue case `pd-xray-cwl_latp-bm01_scan`: the files the command line fits
# with `python -m edi fit docs/user/cli/pd-xray-cwl_latp-bm01_scan/project` and the app opens from
# its Examples.

# %% [markdown]
# > This tutorial is not run when the documentation is built yet. It loads its project from the edi
# > repository, so it runs once a tutorial runner can provide the project elsewhere
# > (`execution-exclusions.yml`).

# %%
import csv
from pathlib import Path

import edi

# %% [markdown]
# ## Load the project

# %%
project = edi.Project.load('../cli/pd-xray-cwl_latp-bm01_scan/project')
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))
print('Fitting mode:', project.fitting_mode)

# %% [markdown]
# ## The start
#
# The template pattern, latp_312, starts from an earlier fit of that pattern; each later pattern
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
project.save_as('pd-xray-cwl_latp-bm01_scan')

# %% [markdown]
# ## Fit every pattern
#
# Each pattern starts from the fit before it.

# %%
fitted = []
result = project.fit_sequential(on_file_complete=lambda *args: fitted.append(args))
print(result.status.name.lower(), 'after', len(fitted), 'patterns')

# %% [markdown]
# ## The results
#
# One row per pattern, in the order they were fitted.

# %%
results = Path('pd-xray-cwl_latp-bm01_scan/analysis/results.csv')
with results.open(newline='', encoding='utf-8') as file:
    rows = list(csv.DictReader(file))
print(len(rows), 'rows; columns:', ', '.join(list(rows[0])[:6]), '...')

# %% [markdown]
# ## Patterns and report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structure and the fit. Open it in a browser.

# %%
project.report.save_html('pd-xray-cwl_latp-bm01_scan.html')
