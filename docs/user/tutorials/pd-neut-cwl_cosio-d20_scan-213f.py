"""Sequential magnetic fit: Co₂SiO₄, D20 scan from 2.3 K."""
# %% [markdown]
# # Sequential magnetic fit: Co₂SiO₄, D20 scan from 2.3 K
#
# Fit the olivine Co₂SiO₄ with its magnetic structure to the whole D20 cooling scan, 213 patterns
# from 497.4 K down to 2.3 K, one after another and from the lowest temperature up: the first fit
# is the 2.3 K example's, and each later one starts from the previous result. The cobalt moments
# stay free at every temperature and fall towards zero near the Néel temperature, about 50 K.
#
# The project is the catalogue case `pd-neut-cwl_cosio-d20_scan-213f`: the files the command line
# fits with `python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_scan-213f/project` and the app
# opens from its Examples.

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
project = edi.Project.load('../cli/pd-neut-cwl_cosio-d20_scan-213f/project')
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))
print('Fitting mode:', project.fitting_mode)

# %% [markdown]
# ## The start
#
# The template is the 2.3 K pattern with the 2.3 K example's model: the magnetic structure in
# Pnma.1, Co1's moment free in all three components and Co2's along b. The scan is fitted in
# reverse file order, so the 2.3 K file comes first. The fit is free to change these parameters:

# %%
for parameter in project.free_parameters:
    print(f'{parameter.name:28} {parameter.value:12.6g} {parameter.units}')

# %% [markdown]
# ## Work on a copy
#
# A sequential fit writes one row per pattern into the project's `analysis/results.csv`, so save a
# copy first and fit that.

# %%
project.save_as('pd-neut-cwl_cosio-d20_scan-213f')

# %% [markdown]
# ## Fit the lowest temperatures, then stop
#
# The fit can stop between patterns. Here it stops after five, all below 3 K; the rows it wrote
# stay.

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
# The whole scan takes a while.

# %%
result = project.fit_sequential(on_file_complete=lambda *args: fitted.append(args))
print(result.status.name.lower(), 'with', len(fitted), 'patterns fitted in all')

# %% [markdown]
# ## The moments against temperature
#
# One row per pattern, in the order they were fitted. The moment columns name their site and
# component.

# %%
results = Path('pd-neut-cwl_cosio-d20_scan-213f/analysis/results.csv')
with results.open(newline='', encoding='utf-8') as file:
    rows = list(csv.DictReader(file))
moments = [name for name in rows[0] if 'crystalaxis' in name and not name.endswith('_su')]
print(len(rows), 'rows; moment columns:', ', '.join(moments))

# %% [markdown]
# ## Patterns and report
#
# The HTML report draws the measured, calculated and difference patterns with the nuclear and the
# magnetic reflection positions, and lists the structure and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_cosio-d20_scan-213f.html')
