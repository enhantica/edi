"""Sequential magnetic fit: Co₂SiO₄, D20 scan from 2.3 K."""
# %% [markdown]
# # Sequential magnetic fit: Co₂SiO₄, D20 scan from 2.3 K
#
# Fit the olivine Co₂SiO₄ with its magnetic structure to the whole D20 cooling scan, 213 patterns
# from 497.4 K down to 2.3 K, one after another and from the lowest temperature up. First the fit
# is staged on the 2.3 K pattern, the scan's template; then each later pattern starts from the
# previous result. The cobalt moments stay free at every temperature and fall towards zero near
# the Néel temperature, about 50 K.
#
# The project is the catalogue case `pd-neut-cwl_cosio-d20_scan-213f`, the one the command line
# and the app's Examples open. Its two Co sites share one displacement from the start.

# %%
import csv
from pathlib import Path

import easydiffraction as edi

# %% [markdown]
# ## Load the project
#
# A sequential fit writes one row per pattern into the project's `analysis/results.csv`, so work
# on a copy of the project, saved to a folder of its own.

# %%
project_path = edi.download_data('pd-neut-cwl_cosio-d20_scan-213f', destination='data')
project = edi.Project.load(project_path)
project.save_as('pd-neut-cwl_cosio-d20_scan-213f')
structure = project.structures['cosio']
experiment = project.experiments['d20']

# %% [markdown]
# ## Stage the template fit
#
# The template is the 2.3 K pattern. Fit it alone first, in stages, so the scan starts from a
# good model: switch the fitting mode to a single fit, and start with nothing free.

# %%
project.analysis.fitting_mode = 'single'
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('d20')

# %% [markdown]
# ## Perform the analysis
#
# ### Scale, 2θ zero and cell

# %%
experiment.linked_structures['cosio'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Background
#
# The sixteen background points follow the level between the peaks.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Peak widths
#
# U, V and W only: across a temperature scan the Lorentzian term and the asymmetry stay at their
# 2.3 K values, as do the form factor's j2 term.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Atom positions

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Displacements
#
# Co2's displacement follows Co1's by the project's constraint.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = not site.adp_iso.user_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Magnetic moments
#
# Last, the moments: Co1 in any direction, Co2 along b.

# %%
structure.atom_site_moment['Co1'].crystalaxis_x.free = True
structure.atom_site_moment['Co1'].crystalaxis_y.free = True
structure.atom_site_moment['Co1'].crystalaxis_z.free = True
structure.atom_site_moment['Co2'].crystalaxis_y.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ## Fit the scan
#
# Back to the sequential mode, with the template's free parameters. The fit can stop between
# patterns: here it stops after five, all below 3 K, and the rows it wrote stay.

# %%
project.analysis.fitting_mode = 'sequential'
fitted = []
result = project.fit_sequential(
    on_file_complete=lambda *args: fitted.append(args),
    should_cancel=lambda: len(fitted) >= 5,
)
print(result.status.name.lower(), 'after', len(fitted), 'patterns')

# %% [markdown]
# ## Resume
#
# Starting again continues with the first pattern that has no row yet, from the last fitted
# values. The whole scan takes a while.

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
# ## Save the report
#
# The HTML report draws the measured, calculated and difference patterns with the nuclear and the
# magnetic reflection positions, and lists the structure and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_cosio-d20_scan-213f.html')
