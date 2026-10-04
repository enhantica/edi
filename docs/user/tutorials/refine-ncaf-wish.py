"""NCAF/WISH joint multi-bank fit — a diffraction-lib tutorial port."""
# %% [markdown]
# # Structure Refinement: NCAF, WISH
#
# This example demonstrates a Rietveld refinement of Na2Ca3Al2F14
# crystal structure using time-of-flight neutron powder diffraction data
# from WISH at ISIS.
#
# Two datasets from detector banks 5+6 and 4+7 are used for joint
# fitting.

# %% [markdown]
# > ⛔ **Execution-disabled**: this tutorial is committed ahead of the API it
# > exercises and stays out of notebook execution until **tutorial-runner** lands — see
# > `execution-exclusions.yml`, whose list shrinks to empty as unblocking tasks land.
# > Upstream's minimizer/calculator selector switches are deferred to a later milestone
# >.

# %% [markdown]
# ## 🛠️ Import Library

# %%
from edi import ExperimentFactory, Project, StructureFactory, download_data

# %% [markdown]
# ## 🧩 Define Structure
#
# This section covers how to add structures and modify their
# parameters.
#
# ### Create Structure

# %%
structure = StructureFactory.from_scratch(name='ncaf')

# %% [markdown]
# ### Set Space Group

# %%
structure.space_group.name_h_m = 'I 21 3'
structure.space_group.coord_system_code = '1'

# %% [markdown]
# ### Set Unit Cell

# %%
structure.cell.length_a = 10.250256

# %% [markdown]
# ### Set Atom Sites

# %%
structure.atom_sites.create(
    id='Ca',
    type_symbol='Ca',
    fract_x=0.4663,
    fract_y=0.0,
    fract_z=0.25,
    adp_iso=0.92,
)
structure.atom_sites.create(
    id='Al',
    type_symbol='Al',
    fract_x=0.2521,
    fract_y=0.2521,
    fract_z=0.2521,
    adp_iso=0.73,
)
structure.atom_sites.create(
    id='Na',
    type_symbol='Na',
    fract_x=0.0851,
    fract_y=0.0851,
    fract_z=0.0851,
    adp_iso=2.08,
)
structure.atom_sites.create(
    id='F1',
    type_symbol='F',
    fract_x=0.1377,
    fract_y=0.3054,
    fract_z=0.1195,
    adp_iso=0.90,
)
structure.atom_sites.create(
    id='F2',
    type_symbol='F',
    fract_x=0.3625,
    fract_y=0.3633,
    fract_z=0.1867,
    adp_iso=1.37,
)
structure.atom_sites.create(
    id='F3',
    type_symbol='F',
    fract_x=0.4612,
    fract_y=0.4612,
    fract_z=0.4612,
    adp_iso=0.88,
)

# %% [markdown]
# ## 🔬 Define Experiment
#
# This section shows how to add experiments, configure their parameters,
# and link the structures defined in the previous step.
#
# ### Download Data

# %%
data_path56 = download_data('meas-ncaf-wish-b56', destination='data')

# %%
data_path47 = download_data('meas-ncaf-wish-b47', destination='data')

# %% [markdown]
# ### Create Experiment

# %%
expt56 = ExperimentFactory.from_data_path(
    name='wish_5_6',
    data_path=data_path56,
    beam_mode='time-of-flight',
)

# %%
expt47 = ExperimentFactory.from_data_path(
    name='wish_4_7',
    data_path=data_path47,
    beam_mode='time-of-flight',
)

# %% [markdown]
# ### Set Instrument

# %%
expt56.instrument.setup_twotheta_bank = 152.827
expt56.instrument.calib_d_to_tof_offset = -13.5
expt56.instrument.calib_d_to_tof_linear = 20773.0
expt56.instrument.calib_d_to_tof_quadratic = -1.08308

# %%
expt47.instrument.setup_twotheta_bank = 121.660
expt47.instrument.calib_d_to_tof_offset = -15.0
expt47.instrument.calib_d_to_tof_linear = 18660.0
expt47.instrument.calib_d_to_tof_quadratic = -0.47488

# %% [markdown]
# ### Set Peak Profile

# %%
expt56.peak.show_supported()
expt56.peak.broad_gauss_sigma_0 = 0.0
expt56.peak.broad_gauss_sigma_1 = 0.0
expt56.peak.broad_gauss_sigma_2 = 15.5
expt56.peak.decay_beta_0 = 0.007
expt56.peak.decay_beta_1 = 0.01
expt56.peak.rise_alpha_0 = -0.0094
expt56.peak.rise_alpha_1 = 0.1
expt56.peak.cutoff_fwhm = 20

# %%
expt47.peak.broad_gauss_sigma_0 = 0.0
expt47.peak.broad_gauss_sigma_1 = 29.8
expt47.peak.broad_gauss_sigma_2 = 18.0
expt47.peak.decay_beta_0 = 0.006
expt47.peak.decay_beta_1 = 0.015
expt47.peak.rise_alpha_0 = -0.0115
expt47.peak.rise_alpha_1 = 0.1
expt47.peak.cutoff_fwhm = 20

# %% [markdown]
# ### Set Background

# %%
expt56.background.show_supported()
expt56.background.type = 'line-segment'
for idx, (x, y) in enumerate(
    [
        (9162, 465),
        (11136, 593),
        (13313, 497),
        (14906, 546),
        (16454, 533),
        (17352, 496),
        (18743, 428),
        (20179, 452),
        (21368, 397),
        (22176, 468),
        (22827, 477),
        (24644, 380),
        (26439, 381),
        (28257, 378),
        (31196, 343),
        (34034, 328),
        (37265, 310),
        (41214, 323),
        (44827, 283),
        (49830, 273),
        (52905, 257),
        (58204, 260),
        (62916, 261),
        (70186, 262),
        (74204, 262),
        (82103, 268),
        (91958, 268),
        (102712, 262),
    ],
    start=1,
):
    expt56.background.create(id=str(idx), position=x, intensity=y)

# %%
expt47.background.type = 'line-segment'
for idx, (x, y) in enumerate(
    [
        (9090, 488),
        (10672, 566),
        (12287, 494),
        (14037, 559),
        (15451, 529),
        (16764, 445),
        (18076, 460),
        (19456, 413),
        (20466, 511),
        (21880, 396),
        (23798, 391),
        (25447, 385),
        (28073, 349),
        (30058, 332),
        (32583, 309),
        (34804, 355),
        (37160, 318),
        (40324, 290),
        (46895, 260),
        (50631, 256),
        (54602, 246),
        (58439, 264),
        (66520, 250),
        (75002, 258),
        (83649, 257),
        (92770, 255),
        (101524, 260),
    ],
    start=1,
):
    expt47.background.create(id=str(idx), position=x, intensity=y)

# %% [markdown]
# ### Set Linked Structures

# %%
expt56.linked_structures.create(structure_id='ncaf', scale=78.0)

# %%
expt47.linked_structures.create(structure_id='ncaf', scale=37.0)

# %% [markdown]
# ### Set Excluded Regions

# %%
expt56.excluded_regions.create(id='1', start=0, end=10010)
expt56.excluded_regions.create(id='2', start=100010, end=200000)

# %%
expt47.excluded_regions.create(id='1', start=0, end=10006)
expt47.excluded_regions.create(id='2', start=100004, end=200000)

# %% [markdown]
# ## 📦 Define Project
#
# The project object is used to manage the structure, experiments,
# and analysis
#
# ### Create Project

# %%
project = Project(name='ncaf_wish')

# %% [markdown]
# ### Add Structure

# %%
project.structures.add(structure)

# %% [markdown]
# ### Add Experiment

# %%
project.experiments.add(expt56)
project.experiments.add(expt47)

# %% [markdown]
# ## 🚀 Perform Analysis
#
# This section shows the analysis process, including how to set up
# calculation and fitting engines.
#
# ### Set Fit Mode

# %%
project.analysis.fitting_mode.show_supported()
project.analysis.fitting_mode.type = 'joint'

# %% [markdown]
# ### Set Free Parameters

# %%
structure.atom_sites['Ca'].adp_iso.free = True
structure.atom_sites['Al'].adp_iso.free = True
structure.atom_sites['Na'].adp_iso.free = True
structure.atom_sites['F1'].adp_iso.free = True
structure.atom_sites['F2'].adp_iso.free = True
structure.atom_sites['F3'].adp_iso.free = True

# %%
expt56.linked_structures['ncaf'].scale.free = True
expt56.instrument.calib_d_to_tof_offset.free = True
expt56.instrument.calib_d_to_tof_linear.free = True
expt56.peak.broad_gauss_sigma_2.free = True
expt56.peak.decay_beta_0.free = True
expt56.peak.decay_beta_1.free = True
expt56.peak.rise_alpha_1.free = True

expt47.linked_structures['ncaf'].scale.free = True
expt47.instrument.calib_d_to_tof_linear.free = True
expt47.instrument.calib_d_to_tof_offset.free = True
expt47.peak.broad_gauss_sigma_2.free = True
expt47.peak.decay_beta_0.free = True
expt47.peak.decay_beta_1.free = True
expt47.peak.rise_alpha_1.free = True

# %% [markdown]
# ### Display Structure

# %%
project.display.structure(struct_name='ncaf')

# %% [markdown]
# ### Display Pattern

# %%
project.display.pattern(expt_name='wish_5_6')

# %%
project.display.pattern(expt_name='wish_4_7')

# %% [markdown]
# ### Run Fitting

# %%
project.analysis.fit()
project.display.fit.results()
# project.display.fit.correlations()
# ⛔ WIP PLACEHOLDER — not yet in edi
print('[WIP] project.display.fit.correlations is not implemented in edi yet — skipped')

# %% [markdown]
# ### Display Pattern

# %%
project.display.pattern(expt_name='wish_5_6')

# %%
project.display.pattern(expt_name='wish_4_7')

# %% [markdown]
# ## 📊 Report
#
# The HTML report is written automatically when the project is saved;
# enable `project.report.pdf` as well for a PDF version.

# %% [markdown]
# ## 💾 Save Project

# %%
project.save_as(dir_path='projects/refine-ncaf-wish')
