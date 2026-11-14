"""Rietveld fit: high-entropy perovskite, P02.1."""
# %% [markdown]
# # Rietveld fit: high-entropy perovskite, P02.1
#
# Fit the high-entropy perovskite La(Ti,Cr,Mn,Fe,Co,Ni,Cu)O₃, seven cations on one site, to
# synchrotron X-ray powder data from P02.1 at PETRA III.
#
# It builds the catalogue case `pd-xray-cwl_lam7o3-p021` step by step: the same project the command
# line fits and the app's Examples open. The seven metals sharing one site have one displacement,
# held by constraints.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='pd-xray-cwl_lam7o3-p021')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-xray-cwl_lam7o3-p021-lam7o3', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['lam7o3']

# %%
project.display.structure('lam7o3')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-xray-cwl_lam7o3-p021-p021-data', destination='data')
project.experiments.add_from_data_path(
    name='p021',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='xray',
    scattering_type='bragg',
)
experiment = project.experiments['p021']
experiment.xray_form_factor = 'it1992'
experiment.xray_dispersion = 'sasaki1989'
experiment.peak.type = 'cwl-tch-pseudo-voigt'
experiment.instrument.name = 'P02.1'
experiment.instrument.facility = 'PETRA III'
experiment.peak.broad_gauss_u = 0.04
experiment.peak.broad_gauss_v = -0.01
experiment.peak.broad_gauss_w = 0.001
experiment.peak.broad_lorentz_x = 0.1
experiment.peak.cutoff_fwhm = 30
experiment.instrument.setup_wavelength = 0.207109
experiment.excluded_regions.create(start=0, end=2)
experiment.excluded_regions.create(start=15, end=20)
experiment.linked_structures.create(structure_id='lam7o3', scale=0.000005)
experiment.background.create(id='2.0', position=2.0033379, intensity=300)
experiment.background.create(id='2.3', position=2.297792, intensity=300)
experiment.background.create(id='2.7', position=2.7079241, intensity=300)
experiment.background.create(id='2.9', position=2.8761833, intensity=300)
experiment.background.create(id='3.0', position=2.9813454, intensity=300)
experiment.background.create(id='3.1', position=3.1180563, intensity=300)
experiment.background.create(id='3.7', position=3.7174802, intensity=300)
experiment.background.create(id='4.1', position=4.1381288, intensity=300)
experiment.background.create(id='4.3', position=4.2748394, intensity=300)
experiment.background.create(id='4.4', position=4.3905177, intensity=300)
experiment.background.create(id='4.5', position=4.5482607, intensity=300)
experiment.background.create(id='4.9', position=4.9268441, intensity=300)
experiment.background.create(id='5.1', position=5.1371684, intensity=300)
experiment.background.create(id='7', position=7.4086699, intensity=300)
experiment.background.create(id='8', position=8.0922232, intensity=300)
experiment.background.create(id='10', position=9.7748175, intensity=300)
experiment.background.create(id='11', position=10.910567, intensity=300)
experiment.background.create(id='12', position=12.498515, intensity=300)
experiment.background.create(id='14.7', position=14.70692, intensity=300)
experiment.background.create(id='15.0', position=14.990857, intensity=300)

# %% [markdown]
# The constraints the fit keeps, each between two named parameters (aliases).

# %%
project.analysis.aliases.create(id='biso_Ti', param=structure.atom_sites['Ti'].adp_iso)
project.analysis.aliases.create(id='biso_Cr', param=structure.atom_sites['Cr'].adp_iso)
project.analysis.aliases.create(id='biso_Mn', param=structure.atom_sites['Mn'].adp_iso)
project.analysis.aliases.create(id='biso_Fe', param=structure.atom_sites['Fe'].adp_iso)
project.analysis.aliases.create(id='biso_Co', param=structure.atom_sites['Co'].adp_iso)
project.analysis.aliases.create(id='biso_Ni', param=structure.atom_sites['Ni'].adp_iso)
project.analysis.aliases.create(id='biso_Cu', param=structure.atom_sites['Cu'].adp_iso)
project.analysis.aliases.create(id='biso_O1', param=structure.atom_sites['O1'].adp_iso)
project.analysis.aliases.create(id='biso_O2', param=structure.atom_sites['O2'].adp_iso)
project.analysis.constraints.create(id='1', expression='biso_Cr = biso_Ti')
project.analysis.constraints.create(id='2', expression='biso_Mn = biso_Ti')
project.analysis.constraints.create(id='3', expression='biso_Fe = biso_Ti')
project.analysis.constraints.create(id='4', expression='biso_Co = biso_Ti')
project.analysis.constraints.create(id='5', expression='biso_Ni = biso_Ti')
project.analysis.constraints.create(id='6', expression='biso_Cu = biso_Ti')
project.analysis.constraints.create(id='7', expression='biso_O2 = biso_O1')

# %%
project.display.constraints()

# %%
project.display.pattern('p021')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale, 2θ zero and cell
#
# The scale, the zero shift and the cell put the peaks in place and at the right height.

# %%
experiment.linked_structures['lam7o3'].scale.free = True
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
project.display.pattern('p021')

# %% [markdown]
# ### Background

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

# %% [markdown]
# ### Peak widths
#
# The Gaussian widths and the Lorentzian X.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.broad_lorentz_x.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

# %% [markdown]
# ### Background from the fitted model
#
# With a fitted peak model, estimate the background again with the calculated peaks subtracted,
# which follows the low-angle background better, then free the new points and fit again.

# %%
experiment.background.auto_estimate(use_model='subtract', n_points=20)
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

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
project.display.pattern('p021')

# %% [markdown]
# ### Displacements
#
# La's, the mixed site's (through Ti) and O1's; O2's follows O1's.

# %%
structure.atom_sites['La'].adp_iso.free = True
structure.atom_sites['Ti'].adp_iso.free = True
structure.atom_sites['O1'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

# %%
project.display.fit.correlations()

# %%
project.display.structure('lam7o3')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-xray-cwl_lam7o3-p021.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-xray-cwl_lam7o3-p021')
