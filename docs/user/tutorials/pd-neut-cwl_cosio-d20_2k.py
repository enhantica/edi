"""Magnetic structure fit: Co₂SiO₄ at 2.3 K, D20."""
# %% [markdown]
# # Magnetic structure fit: Co₂SiO₄ at 2.3 K, D20
#
# Fit the magnetic structure of the olivine Co₂SiO₄ to constant-wavelength neutron powder data
# from D20 at ILL, measured at 2.3 K, below its ordering temperature. The cobalt moments order with
# k = 0 in the magnetic space group Pnma.1: Co1 may point in any direction, Co2 only along b.
#
# It builds the catalogue case `pd-neut-cwl_cosio-d20_2k` step by step: the same project the
# command line fits and the app's Examples open. Its two Co sites share one displacement, and the
# two FCJ asymmetry terms are tied.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='pd-neut-cwl_cosio-d20_2k')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-cwl_cosio-d20_2k-cosio', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['cosio']

# %%
project.display.structure('cosio')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-neut-cwl_cosio-d20_2k-d20-data', destination='data')
project.experiments.add_from_data_path(
    name='d20',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['d20']
experiment.peak.type = 'cwl-tch-pseudo-voigt-fcj'
experiment.absorption.type = 'cylinder-hewat'
experiment.instrument.name = 'D20'
experiment.instrument.facility = 'ILL'
experiment.peak.broad_gauss_u = 0.273527
experiment.peak.broad_gauss_v = -0.589718
experiment.peak.broad_gauss_w = 0.413007
experiment.peak.broad_lorentz_y = 0.017548
experiment.peak.cutoff_fwhm = 8
experiment.absorption.mu_r = 0.230
experiment.instrument.setup_wavelength = 1.87
experiment.instrument.calib_twotheta_offset = 0.29433
experiment.excluded_regions.create(start=0, end=6)
experiment.excluded_regions.create(start=64.65, end=64.74)
experiment.excluded_regions.create(start=150, end=180)
experiment.linked_structures.create(structure_id='cosio', scale=1.817226)
experiment.background.create(position=6, intensity=603.5)
experiment.background.create(position=6.5, intensity=585.0)
experiment.background.create(position=7, intensity=568.5)
experiment.background.create(position=7.6, intensity=528.8)
experiment.background.create(position=12.6, intensity=418.9)
experiment.background.create(position=13, intensity=420.2)
experiment.background.create(position=13.5, intensity=416.5)
experiment.background.create(position=15, intensity=416.0542)
experiment.background.create(position=25, intensity=394.7747)
experiment.background.create(position=30, intensity=373.1628)
experiment.background.create(position=50, intensity=406.3737)
experiment.background.create(position=70, intensity=408.5056)
experiment.background.create(position=90, intensity=395.9971)
experiment.background.create(position=110, intensity=345.9223)
experiment.background.create(position=130, intensity=279.0409)
experiment.background.create(position=150, intensity=230.6987)

# %% [markdown]
# The constraints the fit keeps, each between two named parameters (aliases).

# %%
project.analysis.aliases.create(id='biso_Co1', param=structure.atom_sites['Co1'].adp_iso)
project.analysis.aliases.create(id='biso_Co2', param=structure.atom_sites['Co2'].adp_iso)
project.analysis.aliases.create(id='sl', param=experiment.peak.asym_fcj_1)
project.analysis.aliases.create(id='dl', param=experiment.peak.asym_fcj_2)
project.analysis.constraints.create(id='biso_Co2', expression='biso_Co2 = biso_Co1')
project.analysis.constraints.create(id='dl', expression='dl = sl')

# %%
project.display.constraints()

# %%
project.display.pattern('d20')

# %% [markdown]
# ## Perform the analysis
#
# Everything starts fixed, and five stages each free one more group, keeping the earlier ones free:
# the scale, cell and moments, then the background, the atoms, the peak widths and last the peak
# asymmetry.
#
# ### Scale, 2θ zero, cell and magnetic moments
#
# The first stage frees the phase scale, the 2θ zero shift, the three cell lengths and the magnetic
# model: the moment components the magnetic space group allows (Co1 in any direction, Co2 only
# along b) and the j2 term of the Co²⁺ form factor, which sets how the magnetic intensities fall
# with angle.

# %%
experiment.linked_structures['cosio'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True
structure.atom_site_moment['Co1'].crystalaxis_x.free = True
structure.atom_site_moment['Co1'].crystalaxis_y.free = True
structure.atom_site_moment['Co1'].crystalaxis_z.free = True
structure.atom_site_moment['Co2'].crystalaxis_y.free = True
structure.magnetic_form_factor['Co'].j2_coefficient.free = True

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
# The second stage frees the sixteen background points, which follow the level between the peaks.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Atomic displacements and positions
#
# The third stage frees the atoms: each site's isotropic displacement (Co2's follows Co1's by the
# project's constraint) and the coordinates the symmetry leaves free. Co1 sits on a centre of
# symmetry, so it has none; the other sites lie on the mirror plane, except O3.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = not site.adp_iso.user_constrained
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Peak widths
#
# The fourth stage frees the peak profile: the Gaussian widths U, V and W and the Lorentzian Y.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.broad_lorentz_y.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Peak asymmetry
#
# The last stage frees the asymmetry: the low-angle peaks lean towards low angle. One FCJ term is
# freed; the other follows it by the project's constraint.

# %%
experiment.peak.asym_fcj_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %%
project.display.fit.correlations()

# %%
project.display.structure('cosio')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_cosio-d20_2k.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_cosio-d20_2k')
