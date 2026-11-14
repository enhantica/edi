"""Joint fit: Na₂Ca₃Al₂F₁₄, WISH."""
# %% [markdown]
# # Joint fit: Na₂Ca₃Al₂F₁₄, WISH
#
# Fit Na₂Ca₃Al₂F₁₄ to time-of-flight neutron powder data from WISH at ISIS, all five detector bank
# pairs at once. Each bank has its own calibration and profile; the structure is shared.
#
# It builds the catalogue case `pd-neut-tof_ncaf-wish` step by step: the same project the command
# line fits and the app's Examples open.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them. The joint
# fitting mode fits every experiment at once, against one set of structures.

# %%
project = edi.Project(name='pd-neut-tof_ncaf-wish')
project.analysis.fitting_mode = 'joint'

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-tof_ncaf-wish-ncaf', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['ncaf']

# %%
project.display.structure('ncaf')

# %% [markdown]
# ## Define the experiments
#
# Create the five experiments from their measured data in EasyDiffraction's collection, then
# describe each one's instrument, peak profile, background and the structures it links.

# %%
data_path = edi.download_data('pd-neut-tof_ncaf-wish-wish_1_10-data', destination='data')
project.experiments.add_from_data_path(
    name='wish_1_10',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
wish_1_10 = project.experiments['wish_1_10']
wish_1_10.neutron_scattering_length = 'sears1992'
wish_1_10.peak.type = 'tof-jorgensen-von-dreele'
wish_1_10.absorption.type = 'cylinder'
wish_1_10.instrument.name = 'WISH'
wish_1_10.instrument.facility = 'ISIS'
wish_1_10.peak.cutoff_fwhm = 8
wish_1_10.peak.broad_gauss_sigma_2 = 15.4063
wish_1_10.peak.broad_lorentz_gamma_1 = 8.2904
wish_1_10.peak.decay_beta_0 = 0.004707
wish_1_10.peak.decay_beta_1 = 0.137368
wish_1_10.peak.rise_alpha_0 = 0.014439
wish_1_10.peak.rise_alpha_1 = 0.05507
wish_1_10.instrument.setup_twotheta_bank = 27.081
wish_1_10.instrument.calib_d_to_tof_linear = 4985.32
wish_1_10.instrument.calib_d_to_tof_quadratic = 1.85733
wish_1_10.excluded_regions.create(start=0, end=7000)
wish_1_10.excluded_regions.create(start=240000, end=300000)
wish_1_10.linked_structures.create(structure_id='ncaf', scale=40)
wish_1_10.background.create(position=6056.0952, intensity=210.0)
wish_1_10.background.create(position=7099.4761, intensity=210.0)
wish_1_10.background.create(position=8008.2271, intensity=210.0)
wish_1_10.background.create(position=8816.0059, intensity=210.0)
wish_1_10.background.create(position=9724.7568, intensity=210.0)
wish_1_10.background.create(position=10532.5352, intensity=210.0)
wish_1_10.background.create(position=11710.5459, intensity=210.0)
wish_1_10.background.create(position=12619.2969, intensity=210.0)
wish_1_10.background.create(position=13393.4180, intensity=210.0)
wish_1_10.background.create(position=14470.4561, intensity=210.0)
wish_1_10.background.create(position=15614.8096, intensity=210.0)
wish_1_10.background.create(position=17264.0254, intensity=210.0)
wish_1_10.background.create(position=19283.4707, intensity=210.0)
wish_1_10.background.create(position=20192.2207, intensity=210.0)
wish_1_10.background.create(position=22346.2969, intensity=210.0)
wish_1_10.background.create(position=24433.0586, intensity=210.0)
wish_1_10.background.create(position=27563.2012, intensity=210.0)
wish_1_10.background.create(position=30356.7695, intensity=210.0)
wish_1_10.background.create(position=33049.3672, intensity=210.0)
wish_1_10.background.create(position=35203.4414, intensity=210.0)
wish_1_10.background.create(position=38826.4766, intensity=210.0)
wish_1_10.background.create(position=44447.2695, intensity=210.0)
wish_1_10.background.create(position=50068.0625, intensity=210.0)
wish_1_10.background.create(position=55587.8828, intensity=210.0)
wish_1_10.background.create(position=63586.3867, intensity=210.0)
wish_1_10.background.create(position=74289.4531, intensity=210.0)
wish_1_10.background.create(position=86385.1953, intensity=210.0)
wish_1_10.background.create(position=98097.9844, intensity=210.0)
wish_1_10.background.create(position=114791.3281, intensity=210.0)
wish_1_10.background.create(position=128630.5156, intensity=210.0)
wish_1_10.background.create(position=147091.2500, intensity=210.0)
wish_1_10.background.create(position=167026.9219, intensity=210.0)
wish_1_10.background.create(position=187448.0156, intensity=210.0)
wish_1_10.background.create(position=208808.5312, intensity=210.0)
wish_1_10.background.create(position=231077.7812, intensity=210.0)
wish_1_10.background.create(position=252332.8281, intensity=210.0)

# %%
data_path = edi.download_data('pd-neut-tof_ncaf-wish-wish_2_9-data', destination='data')
project.experiments.add_from_data_path(
    name='wish_2_9',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
wish_2_9 = project.experiments['wish_2_9']
wish_2_9.neutron_scattering_length = 'sears1992'
wish_2_9.peak.type = 'tof-jorgensen-von-dreele'
wish_2_9.absorption.type = 'cylinder'
wish_2_9.instrument.name = 'WISH'
wish_2_9.instrument.facility = 'ISIS'
wish_2_9.peak.cutoff_fwhm = 8
wish_2_9.peak.broad_gauss_sigma_1 = 34
wish_2_9.peak.broad_gauss_sigma_2 = 11
wish_2_9.peak.broad_lorentz_gamma_1 = 1
wish_2_9.peak.decay_beta_0 = 0.0061
wish_2_9.peak.decay_beta_1 = 0.096
wish_2_9.peak.rise_alpha_0 = 0.053
wish_2_9.peak.rise_alpha_1 = 0.031
wish_2_9.instrument.setup_twotheta_bank = 58.33
wish_2_9.instrument.calib_d_to_tof_linear = 10389.9
wish_2_9.instrument.calib_d_to_tof_quadratic = 1.85233
wish_2_9.excluded_regions.create(start=0, end=7000)
wish_2_9.excluded_regions.create(start=134000, end=300000)
wish_2_9.linked_structures.create(structure_id='ncaf', scale=40)
wish_2_9.background.create(position=7246.0732, intensity=220.0)
wish_2_9.background.create(position=9265.5195, intensity=220.0)
wish_2_9.background.create(position=11097.9795, intensity=220.0)
wish_2_9.background.create(position=13080.0303, intensity=220.0)
wish_2_9.background.create(position=15473.4473, intensity=220.0)
wish_2_9.background.create(position=16931.9355, intensity=220.0)
wish_2_9.background.create(position=18614.8086, intensity=220.0)
wish_2_9.background.create(position=20596.8594, intensity=220.0)
wish_2_9.background.create(position=22504.1133, intensity=220.0)
wish_2_9.background.create(position=26169.0332, intensity=220.0)
wish_2_9.background.create(position=28113.6875, intensity=220.0)
wish_2_9.background.create(position=30320.1172, intensity=220.0)
wish_2_9.background.create(position=34770.3828, intensity=220.0)
wish_2_9.background.create(position=40155.5703, intensity=220.0)
wish_2_9.background.create(position=48341.8086, intensity=220.0)
wish_2_9.background.create(position=58540.0156, intensity=220.0)
wish_2_9.background.create(position=69139.8672, intensity=220.0)
wish_2_9.background.create(position=80953.6328, intensity=220.0)
wish_2_9.background.create(position=94214.6562, intensity=220.0)
wish_2_9.background.create(position=107677.6328, intensity=220.0)
wish_2_9.background.create(position=120889.3047, intensity=220.0)
wish_2_9.background.create(position=132602.0938, intensity=220.0)

# %%
data_path = edi.download_data('pd-neut-tof_ncaf-wish-wish_3_8-data', destination='data')
project.experiments.add_from_data_path(
    name='wish_3_8',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
wish_3_8 = project.experiments['wish_3_8']
wish_3_8.neutron_scattering_length = 'sears1992'
wish_3_8.peak.type = 'tof-jorgensen-von-dreele'
wish_3_8.absorption.type = 'cylinder'
wish_3_8.instrument.name = 'WISH'
wish_3_8.instrument.facility = 'ISIS'
wish_3_8.peak.cutoff_fwhm = 8
wish_3_8.peak.broad_gauss_sigma_1 = 30
wish_3_8.peak.broad_gauss_sigma_2 = 8.3
wish_3_8.peak.broad_lorentz_gamma_1 = 0.0002
wish_3_8.peak.decay_beta_0 = 0.0069
wish_3_8.peak.decay_beta_1 = 0.032
wish_3_8.peak.rise_alpha_0 = -0.016
wish_3_8.peak.rise_alpha_1 = 0.16
wish_3_8.instrument.setup_twotheta_bank = 90
wish_3_8.instrument.calib_d_to_tof_linear = 15105.5
wish_3_8.instrument.calib_d_to_tof_quadratic = 1.00785
wish_3_8.excluded_regions.create(start=0, end=9000)
wish_3_8.excluded_regions.create(start=116000, end=300000)
wish_3_8.linked_structures.create(structure_id='ncaf', scale=40)
wish_3_8.background.create(position=9089.7529, intensity=240.0)
wish_3_8.background.create(position=11580.4033, intensity=240.0)
wish_3_8.background.create(position=13667.1650, intensity=240.0)
wish_3_8.background.create(position=15551.9824, intensity=240.0)
wish_3_8.background.create(position=17739.7168, intensity=240.0)
wish_3_8.background.create(position=20364.9961, intensity=240.0)
wish_3_8.background.create(position=22653.7031, intensity=240.0)
wish_3_8.background.create(position=24740.4648, intensity=240.0)
wish_3_8.background.create(position=27130.1406, intensity=240.0)
wish_3_8.background.create(position=29957.3672, intensity=240.0)
wish_3_8.background.create(position=32616.3047, intensity=240.0)
wish_3_8.background.create(position=36150.3359, intensity=240.0)
wish_3_8.background.create(position=40963.3516, intensity=240.0)
wish_3_8.background.create(position=47265.5195, intensity=240.0)
wish_3_8.background.create(position=53391.1758, intensity=240.0)
wish_3_8.background.create(position=62005.2383, intensity=240.0)
wish_3_8.background.create(position=71866.8672, intensity=240.0)
wish_3_8.background.create(position=82913.9922, intensity=240.0)
wish_3_8.background.create(position=90385.9375, intensity=240.0)
wish_3_8.background.create(position=99649.2188, intensity=240.0)
wish_3_8.background.create(position=107356.7656, intensity=240.0)
wish_3_8.background.create(position=115337.3203, intensity=240.0)

# %%
data_path = edi.download_data('pd-neut-tof_ncaf-wish-wish_4_7-data', destination='data')
project.experiments.add_from_data_path(
    name='wish_4_7',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
wish_4_7 = project.experiments['wish_4_7']
wish_4_7.neutron_scattering_length = 'sears1992'
wish_4_7.peak.type = 'tof-jorgensen-von-dreele'
wish_4_7.absorption.type = 'cylinder'
wish_4_7.instrument.name = 'WISH'
wish_4_7.instrument.facility = 'ISIS'
wish_4_7.peak.cutoff_fwhm = 8
wish_4_7.peak.broad_gauss_sigma_1 = 14
wish_4_7.peak.broad_gauss_sigma_2 = 8.9
wish_4_7.peak.decay_beta_0 = 0.0074
wish_4_7.peak.decay_beta_1 = 0.017
wish_4_7.peak.rise_alpha_0 = -0.015
wish_4_7.peak.rise_alpha_1 = 0.16
wish_4_7.instrument.setup_twotheta_bank = 121.66
wish_4_7.instrument.calib_d_to_tof_linear = 18660.1
wish_4_7.instrument.calib_d_to_tof_quadratic = -0.47488
wish_4_7.excluded_regions.create(start=0, end=9000)
wish_4_7.excluded_regions.create(start=108000, end=300000)
wish_4_7.linked_structures.create(structure_id='ncaf', scale=40)
wish_4_7.background.create(position=9089.7529, intensity=250.0)
wish_4_7.background.create(position=10671.6523, intensity=250.0)
wish_4_7.background.create(position=12287.2100, intensity=250.0)
wish_4_7.background.create(position=14037.3975, intensity=250.0)
wish_4_7.background.create(position=15451.0088, intensity=250.0)
wish_4_7.background.create(position=16763.6504, intensity=250.0)
wish_4_7.background.create(position=18076.2910, intensity=250.0)
wish_4_7.background.create(position=19456.2461, intensity=250.0)
wish_4_7.background.create(position=20465.9688, intensity=250.0)
wish_4_7.background.create(position=21879.5801, intensity=250.0)
wish_4_7.background.create(position=23798.0566, intensity=250.0)
wish_4_7.background.create(position=25447.2715, intensity=250.0)
wish_4_7.background.create(position=28072.5508, intensity=250.0)
wish_4_7.background.create(position=30058.3418, intensity=250.0)
wish_4_7.background.create(position=32582.6504, intensity=250.0)
wish_4_7.background.create(position=34804.0391, intensity=250.0)
wish_4_7.background.create(position=37160.0625, intensity=250.0)
wish_4_7.background.create(position=40323.8594, intensity=250.0)
wish_4_7.background.create(position=46894.5391, intensity=250.0)
wish_4_7.background.create(position=50630.5156, intensity=250.0)
wish_4_7.background.create(position=54602.0938, intensity=250.0)
wish_4_7.background.create(position=58439.0430, intensity=250.0)
wish_4_7.background.create(position=66519.8203, intensity=250.0)
wish_4_7.background.create(position=75001.5000, intensity=250.0)
wish_4_7.background.create(position=83649.2188, intensity=250.0)
wish_4_7.background.create(position=92770.3828, intensity=250.0)
wish_4_7.background.create(position=101524.3047, intensity=250.0)
wish_4_7.background.create(position=107313.3906, intensity=250.0)

# %%
data_path = edi.download_data('pd-neut-tof_ncaf-wish-wish_5_6-data', destination='data')
project.experiments.add_from_data_path(
    name='wish_5_6',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
wish_5_6 = project.experiments['wish_5_6']
wish_5_6.neutron_scattering_length = 'sears1992'
wish_5_6.peak.type = 'tof-jorgensen-von-dreele'
wish_5_6.absorption.type = 'cylinder'
wish_5_6.instrument.name = 'WISH'
wish_5_6.instrument.facility = 'ISIS'
wish_5_6.peak.cutoff_fwhm = 8
wish_5_6.peak.broad_gauss_sigma_2 = 7.7
wish_5_6.peak.broad_lorentz_gamma_1 = 0.0019
wish_5_6.peak.decay_beta_0 = 0.0077
wish_5_6.peak.decay_beta_1 = 0.012
wish_5_6.peak.rise_alpha_0 = -0.012
wish_5_6.peak.rise_alpha_1 = 0.14
wish_5_6.instrument.calib_d_to_tof_linear = 20772.9
wish_5_6.instrument.calib_d_to_tof_quadratic = -1.08308
wish_5_6.excluded_regions.create(start=0, end=9000)
wish_5_6.excluded_regions.create(start=104000, end=300000)
wish_5_6.linked_structures.create(structure_id='ncaf', scale=40)
wish_5_6.background.create(position=11136.8740, intensity=260.0)
wish_5_6.background.create(position=13313.3877, intensity=260.0)
wish_5_6.background.create(position=9162.3037, intensity=260.0)
wish_5_6.background.create(position=14906.5078, intensity=260.0)
wish_5_6.background.create(position=16454.7500, intensity=260.0)
wish_5_6.background.create(position=17352.2812, intensity=260.0)
wish_5_6.background.create(position=18743.4551, intensity=260.0)
wish_5_6.background.create(position=20179.5078, intensity=260.0)
wish_5_6.background.create(position=21368.7363, intensity=260.0)
wish_5_6.background.create(position=22176.0391, intensity=260.0)
wish_5_6.background.create(position=22827.2266, intensity=260.0)
wish_5_6.background.create(position=24644.7285, intensity=260.0)
wish_5_6.background.create(position=26439.7910, intensity=260.0)
wish_5_6.background.create(position=28257.2930, intensity=260.0)
wish_5_6.background.create(position=31196.7109, intensity=260.0)
wish_5_6.background.create(position=34034.4062, intensity=260.0)
wish_5_6.background.create(position=37265.5195, intensity=260.0)
wish_5_6.background.create(position=41214.6602, intensity=260.0)
wish_5_6.background.create(position=44827.2266, intensity=260.0)
wish_5_6.background.create(position=49830.9648, intensity=260.0)
wish_5_6.background.create(position=52905.0117, intensity=260.0)
wish_5_6.background.create(position=58204.9375, intensity=260.0)
wish_5_6.background.create(position=62916.9805, intensity=260.0)
wish_5_6.background.create(position=70186.9844, intensity=260.0)
wish_5_6.background.create(position=74204.9375, intensity=260.0)
wish_5_6.background.create(position=82103.2188, intensity=260.0)
wish_5_6.background.create(position=91958.8672, intensity=260.0)
wish_5_6.background.create(position=102712.0391, intensity=260.0)

# %%
project.display.pattern('wish_1_10')

# %% [markdown]
# ## Perform the analysis
#
# Five banks fit together. diffraction-lib's tutorial of this case fits two banks at once with
# everything free; this one has five, so it stages them.

# %% [markdown]
# ### Scales and time-of-flight calibration
#
# Each bank's scale and DIFC offset and linear term put its peaks in place and at the right
# height.

# %%
wish_1_10.linked_structures['ncaf'].scale.free = True
wish_1_10.instrument.calib_d_to_tof_offset.free = True
wish_1_10.instrument.calib_d_to_tof_linear.free = True
wish_2_9.linked_structures['ncaf'].scale.free = True
wish_2_9.instrument.calib_d_to_tof_offset.free = True
wish_2_9.instrument.calib_d_to_tof_linear.free = True
wish_3_8.linked_structures['ncaf'].scale.free = True
wish_3_8.instrument.calib_d_to_tof_offset.free = True
wish_3_8.instrument.calib_d_to_tof_linear.free = True
wish_4_7.linked_structures['ncaf'].scale.free = True
wish_4_7.instrument.calib_d_to_tof_offset.free = True
wish_4_7.instrument.calib_d_to_tof_linear.free = True
wish_5_6.linked_structures['ncaf'].scale.free = True
wish_5_6.instrument.calib_d_to_tof_offset.free = True
wish_5_6.instrument.calib_d_to_tof_linear.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Background
#
# Each bank's background points; bank 1-10's first and last stay fixed, as its source has them.

# %%
for point in wish_1_10.background:
    point.intensity.free = True
for point in wish_2_9.background:
    point.intensity.free = True
for point in wish_3_8.background:
    point.intensity.free = True
for point in wish_4_7.background:
    point.intensity.free = True
for point in wish_5_6.background:
    point.intensity.free = True
wish_1_10.background[0].intensity.free = False
wish_1_10.background[35].intensity.free = False

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Peak asymmetry
#
# Each bank's back-to-back exponentials, the terms its data determine; bank 1-10 keeps its
# instrument values.

# %%
wish_2_9.peak.rise_alpha_0.free = True
wish_2_9.peak.rise_alpha_1.free = True
wish_2_9.peak.decay_beta_0.free = True
wish_2_9.peak.decay_beta_1.free = True
wish_3_8.peak.rise_alpha_0.free = True
wish_3_8.peak.rise_alpha_1.free = True
wish_3_8.peak.decay_beta_0.free = True
wish_3_8.peak.decay_beta_1.free = True
wish_4_7.peak.rise_alpha_0.free = True
wish_4_7.peak.rise_alpha_1.free = True
wish_4_7.peak.decay_beta_0.free = True
wish_4_7.peak.decay_beta_1.free = True
wish_5_6.peak.rise_alpha_0.free = True
wish_5_6.peak.rise_alpha_1.free = True
wish_5_6.peak.decay_beta_0.free = True
wish_5_6.peak.decay_beta_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_2_9')

# %% [markdown]
# ### Gaussian widths
#
# The Gaussian width terms the banks' data determine.

# %%
wish_2_9.peak.broad_gauss_sigma_1.free = True
wish_2_9.peak.broad_gauss_sigma_2.free = True
wish_3_8.peak.broad_gauss_sigma_1.free = True
wish_3_8.peak.broad_gauss_sigma_2.free = True
wish_4_7.peak.broad_gauss_sigma_1.free = True
wish_4_7.peak.broad_gauss_sigma_2.free = True
wish_5_6.peak.broad_gauss_sigma_2.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_2_9')

# %% [markdown]
# ### Lorentzian width
#
# Bank 2-9's Lorentzian term.

# %%
wish_2_9.peak.broad_lorentz_gamma_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Absorption
#
# Banks 2-9 to 5-6 each fit their absorption.

# %%
wish_2_9.absorption.abscor1.free = True
wish_3_8.absorption.abscor1.free = True
wish_4_7.absorption.abscor1.free = True
wish_5_6.absorption.abscor1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Atom positions
#
# The coordinates the cubic symmetry leaves free.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Displacements

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %%
project.display.fit.correlations()

# %%
project.display.structure('ncaf')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-tof_ncaf-wish.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_ncaf-wish')
