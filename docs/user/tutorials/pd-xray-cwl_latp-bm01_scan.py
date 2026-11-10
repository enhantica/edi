"""Sequential fit: LATP, BM01."""
# %% [markdown]
# # Sequential fit: LATP, BM01
#
# Fit three phases, LATP and two AlPO₄ forms, to 73 synchrotron X-ray patterns from BM01 at ESRF,
# one after another, with linked displacement parameters.
#
# The project is the catalogue case `pd-xray-cwl_latp-bm01_scan`, the one the command line and the
# app's Examples open. Al shares Ti's site, coordinate and displacement, and the impurity phase's
# displacements are shared, from the start.

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
project_path = edi.download_data('pd-xray-cwl_latp-bm01_scan', destination='data')
project = edi.Project.load(project_path)
project.save_as('pd-xray-cwl_latp-bm01_scan')
latp = project.structures['latp']
c2221 = project.structures['alpo4_c2221']
p63mc = project.structures['alpo4_p63mc']
experiment = project.experiments['bm01']
project.display.constraints()

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %% [markdown]
# ## Stage the template fit
#
# The template is the scan's first pattern. Fit it alone first, in stages, so the scan starts from
# a good model: switch the fitting mode to a single fit.

# %%
project.analysis.fitting_mode = 'single'

# %%
project.display.pattern('bm01')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scales, 2θ zero and cells
#
# The three phases' scales and cells and the zero shift.

# %%
experiment.linked_structures['latp'].scale.free = True
experiment.linked_structures['alpo4_c2221'].scale.free = True
experiment.linked_structures['alpo4_p63mc'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
latp.cell.length_a.free = True
latp.cell.length_c.free = True
c2221.cell.length_a.free = True
c2221.cell.length_b.free = True
c2221.cell.length_c.free = True
p63mc.cell.length_a.free = True
p63mc.cell.length_c.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('bm01')

# %% [markdown]
# ### Background

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('bm01')

# %% [markdown]
# ### Peak widths

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.mixing_eta_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('bm01')

# %% [markdown]
# ### Peak asymmetry

# %%
experiment.peak.asym_beba_a0.free = True
experiment.peak.asym_beba_b0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('bm01')

# %% [markdown]
# ### LATP positions
#
# The main phase's free coordinates; Al's follows Ti's.

# %%
latp.atom_sites['Ti1'].fract_z.free = True
latp.atom_sites['P1'].fract_x.free = True
latp.atom_sites['O1'].fract_x.free = True
latp.atom_sites['O1'].fract_y.free = True
latp.atom_sites['O1'].fract_z.free = True
latp.atom_sites['O2'].fract_x.free = True
latp.atom_sites['O2'].fract_y.free = True
latp.atom_sites['O2'].fract_z.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('bm01')

# %% [markdown]
# ### LATP displacements

# %%
latp.atom_sites['Ti1'].adp_iso.free = True
latp.atom_sites['P1'].adp_iso.free = True
latp.atom_sites['O1'].adp_iso.free = True
latp.atom_sites['O2'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('bm01')

# %%
project.display.fit.correlations()

# %%
project.display.structure('latp')

# %%
project.display.structure('alpo4_c2221')

# %%
project.display.structure('alpo4_p63mc')

# %% [markdown]
# ## Fit the scan
#
# Back to the sequential mode, with the template's free parameters. Each pattern starts from the
# fit before it.

# %%
project.analysis.fitting_mode = 'sequential'
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
# ## Save the report

# %%
project.report.save_html('pd-xray-cwl_latp-bm01_scan.html')
