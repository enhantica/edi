"""LBCO/HRPT structure Rietveld fit — a diffraction-lib tutorial port."""
# %% [markdown]
# # Structure Refinement: LBCO, HRPT
#
# This minimalistic example is designed to show how Rietveld refinement
# can be performed when both the crystal structure and experiment are
# defined directly in code. Only the experimentally measured data is
# loaded from an external file. It also shows how to switch calculation
# engine.
#
# For this example, constant-wavelength neutron powder diffraction data
# for La0.5Ba0.5CoO3 from HRPT at PSI is used.
#
# It does not contain any advanced features or options, and includes no
# comments or explanations — these can be found in the other tutorials.
# Default values are used for all parameters if not specified. Only
# essential and self-explanatory code is provided.
#
# The example is intended for users who are already familiar with the
# EasyDiffraction library and want to quickly get started with a simple
# refinement. It is also useful for those who want to see what a
# refinement might look like in code. For a more detailed explanation of
# the code, please refer to the other tutorials.

# %% [markdown]
# > ⛔ **Execution-disabled**: this tutorial is committed ahead of the API it
# > exercises and stays out of notebook execution until **tutorial-runner** lands — see
# > `execution-exclusions.yml`, whose list shrinks to empty as unblocking tasks land.

# %% [markdown]
# ## 🛠️ Import Library

# %%
import edi

# %% [markdown]
# ## 📦 Define Project

# %%
project = edi.Project(name='lbco_hrpt')

# %% [markdown]
# ## 🧩 Define Structure

# %%
project.structures.create(name='lbco')

# %%
structure = project.structures['lbco']

# %%
structure.space_group.name_h_m = 'P m -3 m'
structure.space_group.coord_system_code = '1'

# %%
structure.cell.length_a = 3.88

# %%
structure.atom_sites.create(
    id='La',
    type_symbol='La',
    fract_x=0,
    fract_y=0,
    fract_z=0,
    adp_iso=0.5,
    occupancy=0.5,
)
structure.atom_sites.create(
    id='Ba',
    type_symbol='Ba',
    fract_x=0,
    fract_y=0,
    fract_z=0,
    adp_iso=0.5,
    occupancy=0.5,
)
structure.atom_sites.create(
    id='Co',
    type_symbol='Co',
    fract_x=0.5,
    fract_y=0.5,
    fract_z=0.5,
    adp_iso=0.5,
)
structure.atom_sites.create(
    id='O',
    type_symbol='O',
    fract_x=0,
    fract_y=0.5,
    fract_z=0.5,
    adp_iso=0.5,
)

# %%
project.display.structure(struct_name='lbco')

# %% [markdown]
# ## 🔬 Define Experiment

# %%
data_path = edi.download_data('meas-lbco-hrpt', destination='data')

# %%
project.experiments.add_from_data_path(
    name='hrpt',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
)

# %%
experiment = project.experiments['hrpt']

# %%
experiment.instrument.setup_wavelength = 1.494
experiment.instrument.calib_twotheta_offset = 0.6

# %%
experiment.peak.broad_gauss_u = 0.1
experiment.peak.broad_gauss_v = -0.1
experiment.peak.broad_gauss_w = 0.1
experiment.peak.broad_lorentz_y = 0.1

# %%
experiment.excluded_regions.create(id='1', start=0, end=5)
experiment.excluded_regions.create(id='2', start=165, end=180)

# %%
experiment.background.auto_estimate()

# %%
experiment.linked_structures.create(structure_id='lbco', scale=10.0)

# %% [markdown]
# ## 🚀 Perform Analysis

# %% [markdown]
# ### Without Constraints

# %%
structure.cell.length_a.free = True

structure.atom_sites['La'].adp_iso.free = True
structure.atom_sites['Ba'].adp_iso.free = True
structure.atom_sites['Co'].adp_iso.free = True
structure.atom_sites['O'].adp_iso.free = True

# %%
experiment.instrument.calib_twotheta_offset.free = True

experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.broad_lorentz_y.free = True

for point in experiment.background:
    point.intensity.free = True

experiment.linked_structures['lbco'].scale.free = True

# %%
project.analysis.fit()

# %%
project.display.fit.results()

# %%
# project.display.fit.correlations()
# ⛔ WIP PLACEHOLDER — not yet in edi
print('[WIP] project.display.fit.correlations is not implemented in edi yet — skipped')

# %%
project.display.pattern(expt_name='hrpt')

# %% [markdown]
# ### With Constraints

# %%
# As can be seen from the parameter-correlation plot, the isotropic
# displacement parameters of La and Ba are highly correlated. Because
# La and Ba share the same mixed-occupancy site, their contributions to
# the neutron diffraction pattern are difficult to separate, especially
# since their coherent scattering lengths are not very different.
# Therefore, it is necessary to constrain them to be equal. First we
# define aliases and then use them to create a constraint.
project.analysis.aliases.create(
    id='biso_La',
    param=project.structures['lbco'].atom_sites['La'].adp_iso,
)
project.analysis.aliases.create(
    id='biso_Ba',
    param=project.structures['lbco'].atom_sites['Ba'].adp_iso,
)
project.analysis.constraints.create(expression='biso_Ba = biso_La')

# %%
# project.analysis.minimizer.show_supported()
# project.analysis.minimizer.type = 'lmfit'
# ⛔ TASK-SCOPED PLACEHOLDER — the minimizer and calculator selectors are DEFERRED to a
# later milestone (owner
# ruling 2026-09-22, unfiled at porting time); this placeholder expires when that milestone lands.
print('[PLACEHOLDER] the fitting-backend selector is deferred to a later milestone — skipped')

# %%
project.analysis.fit()

# %%
project.display.fit.results()

# %%
# project.display.fit.correlations()
# ⛔ WIP PLACEHOLDER — not yet in edi
print('[WIP] project.display.fit.correlations is not implemented in edi yet — skipped')

# %%
project.display.pattern(expt_name='hrpt')

# %% [markdown]
# ### Switch Calculator

# %%
# experiment.calculator.show_supported()
# ⛔ TASK-SCOPED PLACEHOLDER — the calculator and minimizer selectors are DEFERRED to a
# later milestone (owner
# ruling 2026-09-22, unfiled at porting time); this placeholder expires when that milestone lands.
print('[PLACEHOLDER] the pattern-engine selector is deferred to a later milestone — skipped')

# %%
# experiment.calculator.type = 'crysfml'
# ⛔ TASK-SCOPED PLACEHOLDER — the calculator and minimizer selectors are DEFERRED to a
# later milestone (owner
# ruling 2026-09-22, unfiled at porting time); this placeholder expires when that milestone lands.
print('[PLACEHOLDER] the pattern-engine selector is deferred to a later milestone — skipped')

# %%
project.analysis.fit()

# %%
project.display.fit.results()

# %%
# project.display.fit.correlations()
# ⛔ WIP PLACEHOLDER — not yet in edi
print('[WIP] project.display.fit.correlations is not implemented in edi yet — skipped')

# %%
project.display.pattern(expt_name='hrpt')

# %% [markdown]
# ## 💾 Save Project

# %%
project.save_as(dir_path='projects/refine-lbco-hrpt-from-data')
