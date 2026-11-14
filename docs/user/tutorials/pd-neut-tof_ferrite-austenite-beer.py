"""Joint fit: ferrite and austenite, BEER."""
# %% [markdown]
# # Joint fit: ferrite and austenite, BEER
#
# Calibrate the BEER instrument at ESS with two McStas-simulated banks of a ferrite and austenite
# duplex steel, fitted together: each bank has its own zero and resolution.
#
# It builds the catalogue case `pd-neut-tof_ferrite-austenite-beer` step by step: the same project
# the command line fits and the app's Examples open. Austenite's displacement follows ferrite's,
# and each phase's scale in bank n2 follows bank s2.

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
project = edi.Project(name='ferrite-austenite-beer')
project.analysis.fitting_mode = 'joint'

# %% [markdown]
# ## Define the structures
#
# Load the two structures from EasyDiffraction's collection. Each CIF gives its space group, cell
# and atom sites.

# %%
path = edi.download_data('pd-neut-tof_ferrite-austenite-beer-ferrite', destination='data')
project.structures.add_from_cif_path(path)
path = edi.download_data('pd-neut-tof_ferrite-austenite-beer-austenite', destination='data')
project.structures.add_from_cif_path(path)
ferrite = project.structures['ferrite']
austenite = project.structures['austenite']

# %%
project.display.structure('ferrite')

# %% [markdown]
# ## Define the experiments
#
# Create the two experiments from their measured data in EasyDiffraction's collection, then
# describe each one's instrument, peak profile, background and the structures it links.

# %%
data_path = edi.download_data(
    'pd-neut-tof_ferrite-austenite-beer-expt_s2-data', destination='data'
)
project.experiments.add_from_data_path(
    name='expt_s2',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
bank_s2 = project.experiments['expt_s2']
bank_s2.neutron_scattering_length = 'sears1992'
bank_s2.peak.type = 'tof-pseudo-voigt'
bank_s2.absorption.type = 'none'
bank_s2.instrument.name = 'BEER'
bank_s2.instrument.facility = 'ESS'
bank_s2.peak.cutoff_fwhm = 12
bank_s2.peak.broad_gauss_sigma_0 = 900
bank_s2.peak.broad_gauss_sigma_1 = 1000
bank_s2.peak.broad_gauss_sigma_2 = 300
bank_s2.peak.broad_lorentz_gamma_0 = 5
bank_s2.instrument.setup_twotheta_bank = 90.0
bank_s2.instrument.calib_d_to_tof_linear = 54902.1875
bank_s2.excluded_regions.create(start=20000.0, end=40158.2305)
bank_s2.excluded_regions.create(start=130000.0, end=180000.0)
bank_s2.linked_structures.create(structure_id='ferrite', scale=400)
bank_s2.linked_structures.create(structure_id='austenite', scale=100)
bank_s2.background.create(position=40111.8789, intensity=0.18)
bank_s2.background.create(position=41193.5664, intensity=0.18)
bank_s2.background.create(position=42041.3750, intensity=0.18)
bank_s2.background.create(position=42713.7734, intensity=0.18)
bank_s2.background.create(position=44409.3945, intensity=0.18)
bank_s2.background.create(position=45198.7344, intensity=0.18)
bank_s2.background.create(position=46251.1875, intensity=0.18)
bank_s2.background.create(position=49350.0742, intensity=0.18)
bank_s2.background.create(position=51289.6836, intensity=0.18)
bank_s2.background.create(position=55245.1992, intensity=0.18)
bank_s2.background.create(position=55679.7070, intensity=0.18)
bank_s2.background.create(position=56383.9102, intensity=0.18)
bank_s2.background.create(position=58956.1797, intensity=0.18)
bank_s2.background.create(position=61536.4570, intensity=0.18)
bank_s2.background.create(position=63768.0469, intensity=0.18)
bank_s2.background.create(position=65581.2109, intensity=0.18)
bank_s2.background.create(position=70183.8516, intensity=0.18)
bank_s2.background.create(position=71787.8203, intensity=0.18)
bank_s2.background.create(position=78343.1094, intensity=0.18)
bank_s2.background.create(position=80016.8047, intensity=0.18)
bank_s2.background.create(position=98141.8516, intensity=0.18)
bank_s2.background.create(position=99262.2344, intensity=0.18)
bank_s2.background.create(position=100985.8516, intensity=0.18)
bank_s2.background.create(position=101933.8516, intensity=0.18)
bank_s2.background.create(position=108656.0312, intensity=0.18)
bank_s2.background.create(position=110896.7500, intensity=0.18)
bank_s2.background.create(position=113137.4844, intensity=0.18)
bank_s2.background.create(position=114430.2031, intensity=0.18)
bank_s2.background.create(position=116929.4844, intensity=0.18)
bank_s2.background.create(position=119428.7422, intensity=0.18)
bank_s2.background.create(position=134506.3438, intensity=0.18)

# %%
data_path = edi.download_data(
    'pd-neut-tof_ferrite-austenite-beer-expt_n2-data', destination='data'
)
project.experiments.add_from_data_path(
    name='expt_n2',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
bank_n2 = project.experiments['expt_n2']
bank_n2.neutron_scattering_length = 'sears1992'
bank_n2.peak.type = 'tof-pseudo-voigt'
bank_n2.absorption.type = 'none'
bank_n2.instrument.name = 'BEER'
bank_n2.instrument.facility = 'ESS'
bank_n2.peak.cutoff_fwhm = 12
bank_n2.peak.broad_gauss_sigma_0 = 900
bank_n2.peak.broad_gauss_sigma_1 = 1000
bank_n2.peak.broad_gauss_sigma_2 = 300
bank_n2.peak.broad_lorentz_gamma_0 = 5
bank_n2.instrument.setup_twotheta_bank = 90.0
bank_n2.instrument.calib_d_to_tof_linear = 54902.1875
bank_n2.excluded_regions.create(start=20000.0, end=40158.2305)
bank_n2.excluded_regions.create(start=130000.0, end=180000.0)
bank_n2.linked_structures.create(structure_id='ferrite', scale=400)
bank_n2.linked_structures.create(structure_id='austenite', scale=100)
bank_n2.background.create(position=40111.8789, intensity=0.19)
bank_n2.background.create(position=41193.5664, intensity=0.19)
bank_n2.background.create(position=42041.3750, intensity=0.19)
bank_n2.background.create(position=42713.7734, intensity=0.19)
bank_n2.background.create(position=44409.3945, intensity=0.19)
bank_n2.background.create(position=45198.7344, intensity=0.19)
bank_n2.background.create(position=46251.1875, intensity=0.19)
bank_n2.background.create(position=49350.0742, intensity=0.19)
bank_n2.background.create(position=51289.6836, intensity=0.19)
bank_n2.background.create(position=55245.1992, intensity=0.19)
bank_n2.background.create(position=55679.7070, intensity=0.19)
bank_n2.background.create(position=56383.9102, intensity=0.19)
bank_n2.background.create(position=58956.1797, intensity=0.19)
bank_n2.background.create(position=61536.4570, intensity=0.19)
bank_n2.background.create(position=63768.0469, intensity=0.19)
bank_n2.background.create(position=65581.2109, intensity=0.19)
bank_n2.background.create(position=70183.8516, intensity=0.19)
bank_n2.background.create(position=71787.8203, intensity=0.19)
bank_n2.background.create(position=78343.1094, intensity=0.19)
bank_n2.background.create(position=80016.8047, intensity=0.19)
bank_n2.background.create(position=98141.8516, intensity=0.19)
bank_n2.background.create(position=99262.2344, intensity=0.19)
bank_n2.background.create(position=100985.8516, intensity=0.19)
bank_n2.background.create(position=101933.8516, intensity=0.19)
bank_n2.background.create(position=108656.0312, intensity=0.19)
bank_n2.background.create(position=110896.7500, intensity=0.19)
bank_n2.background.create(position=113137.4844, intensity=0.19)
bank_n2.background.create(position=114430.2031, intensity=0.19)
bank_n2.background.create(position=116929.4844, intensity=0.19)
bank_n2.background.create(position=119428.7422, intensity=0.19)
bank_n2.background.create(position=134506.3438, intensity=0.19)

# %% [markdown]
# The constraints the fit keeps, each between two named parameters (aliases).

# %%
project.analysis.aliases.create(id='biso_ferrite', param=ferrite.atom_sites['Fe'].adp_iso)
project.analysis.aliases.create(id='biso_austenite', param=austenite.atom_sites['Fe'].adp_iso)
project.analysis.aliases.create(
    id='s2_ferrite_scale', param=bank_s2.linked_structures['ferrite'].scale
)
project.analysis.aliases.create(
    id='s2_austenite_scale', param=bank_s2.linked_structures['austenite'].scale
)
project.analysis.aliases.create(
    id='n2_ferrite_scale', param=bank_n2.linked_structures['ferrite'].scale
)
project.analysis.aliases.create(
    id='n2_austenite_scale', param=bank_n2.linked_structures['austenite'].scale
)
project.analysis.constraints.create(id='1', expression='biso_austenite = biso_ferrite')
project.analysis.constraints.create(id='2', expression='n2_ferrite_scale = s2_ferrite_scale')
project.analysis.constraints.create(id='3', expression='n2_austenite_scale = s2_austenite_scale')

# %%
project.display.constraints()

# %%
project.display.pattern('expt_s2')

# %% [markdown]
# ## Perform the analysis
#
# The cells stay fixed: this is a calibration, and the two phases are the standards.

# %% [markdown]
# ### Scales and time-of-flight calibration
#
# Both phases' scales and each bank's DIFC offset put the peaks in place and at the right height.

# %%
bank_s2.linked_structures['ferrite'].scale.free = True
bank_s2.linked_structures['austenite'].scale.free = True
bank_s2.instrument.calib_d_to_tof_offset.free = True
bank_n2.instrument.calib_d_to_tof_offset.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('expt_s2')

# %%
project.display.pattern('expt_n2')

# %% [markdown]
# ### Background
#
# Each bank's background points; the last, past the end of the data, stays fixed.

# %%
for point in bank_s2.background:
    point.intensity.free = True
for point in bank_n2.background:
    point.intensity.free = True
bank_s2.background[30].intensity.free = False
bank_n2.background[30].intensity.free = False

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('expt_s2')

# %%
project.display.pattern('expt_n2')

# %% [markdown]
# ### Peak widths
#
# Each bank's widths.

# %%
bank_s2.peak.broad_gauss_sigma_0.free = True
bank_s2.peak.broad_gauss_sigma_1.free = True
bank_s2.peak.broad_gauss_sigma_2.free = True
bank_s2.peak.broad_lorentz_gamma_0.free = True
bank_n2.peak.broad_gauss_sigma_0.free = True
bank_n2.peak.broad_gauss_sigma_1.free = True
bank_n2.peak.broad_gauss_sigma_2.free = True
bank_n2.peak.broad_lorentz_gamma_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('expt_s2')

# %%
project.display.pattern('expt_n2')

# %% [markdown]
# ### Displacement
#
# Last, ferrite's displacement; austenite's follows it.

# %%
ferrite.atom_sites['Fe'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('expt_s2')

# %%
project.display.pattern('expt_n2')

# %%
project.display.fit.correlations()

# %%
project.display.structure('ferrite')

# %%
project.display.structure('austenite')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-tof_ferrite-austenite-beer.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_ferrite-austenite-beer')
