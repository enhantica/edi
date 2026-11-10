"""Two-phase fit: La₀.₅Ba₀.₅CoO₃ and Si, McStas."""
# %% [markdown]
# # Two-phase fit: La₀.₅Ba₀.₅CoO₃ and Si, McStas
#
# Fit two phases, La₀.₅Ba₀.₅CoO₃ and silicon, to a time-of-flight pattern simulated with McStas.
#
# The project is the catalogue case `pd-neut-tof_lbco-si-mcstas`, the one the command line and the
# app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-tof_lbco-si-mcstas', destination='data')
project = edi.Project.load(project_path)
lbco = project.structures['lbco']
si = project.structures['si']
experiment = project.experiments['mcstas']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scales and cells
#
# Both phases' scales and cells put the peaks in place and at the right height; the DIFC stays
# fixed, as in diffraction-lib's tutorial.

# %%
experiment.linked_structures['lbco'].scale.free = True
experiment.linked_structures['si'].scale.free = True
lbco.cell.length_a.free = True
si.cell.length_a.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ### Background

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ### Peak widths

# %%
experiment.peak.broad_gauss_sigma_0.free = True
experiment.peak.broad_gauss_sigma_1.free = True
experiment.peak.broad_gauss_sigma_2.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ### Rise and decay

# %%
experiment.peak.rise_alpha_1.free = True
experiment.peak.decay_beta_0.free = True
experiment.peak.decay_beta_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ### Displacements
#
# Co's and O's; La's, Ba's and Si's stay fixed, as the case's project keeps them.

# %%
lbco.atom_sites['Co'].adp_iso.free = True
lbco.atom_sites['O'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %%
project.display.fit.correlations()

# %%
project.display.structure('lbco')

# %%
project.display.structure('si')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_lbco-si-mcstas')
project.report.save_html('pd-neut-tof_lbco-si-mcstas.html')
