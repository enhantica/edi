"""Two-phase fit: YAlO₃ and Al₂O₃, SPODI."""
# %% [markdown]
# # Two-phase fit: YAlO₃ and Al₂O₃, SPODI
#
# Fit two phases, YAlO₃ and corundum Al₂O₃, in one constant-wavelength neutron pattern from SPODI
# at FRM II, measured at 3 K, with a shared Bérar-Baldinozzi profile and cylinder absorption.
#
# It builds the catalogue case `pd-neut-cwl_yalo3-al2o3-spodi` step by step: the same project the
# command line fits and the app's Examples open.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='pd-neut-cwl_yalo3-al2o3-spodi')

# %% [markdown]
# ## Define the structures
#
# Load the two structures from EasyDiffraction's collection. Each CIF gives its space group, cell
# and atom sites.

# %%
path = edi.download_data('pd-neut-cwl_yalo3-al2o3-spodi-YAlO3', destination='data')
project.structures.add_from_cif_path(path)
path = edi.download_data('pd-neut-cwl_yalo3-al2o3-spodi-Al2O3', destination='data')
project.structures.add_from_cif_path(path)
yalo3 = project.structures['YAlO3']
alumina = project.structures['Al2O3']

# %%
project.display.structure('YAlO3')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-neut-cwl_yalo3-al2o3-spodi-spodi-data', destination='data')
project.experiments.add_from_data_path(
    name='spodi',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['spodi']
experiment.neutron_scattering_length = 'sears1992'
experiment.peak.type = 'cwl-pseudo-voigt-berar-baldinozzi'
experiment.absorption.type = 'cylinder-hewat'
experiment.instrument.name = 'SPODI'
experiment.instrument.facility = 'FRM II'
experiment.peak.broad_gauss_u = 0.04
experiment.peak.broad_gauss_v = -0.05
experiment.peak.broad_gauss_w = 0.1
experiment.peak.mixing_eta_0 = 0.1
experiment.peak.asym_beba_limit = 160
experiment.instrument.setup_wavelength = 1.54816
experiment.absorption.mu_r = 0.0221
experiment.excluded_regions.create(start=0, end=4)
experiment.excluded_regions.create(start=153.95, end=180)
experiment.linked_structures.create(structure_id='YAlO3', scale=30)
experiment.linked_structures.create(structure_id='Al2O3', scale=0.2)
experiment.background.create(position=4.0500, intensity=2100.0)
experiment.background.create(position=4.7770, intensity=2100.0)
experiment.background.create(position=6.7860, intensity=2100.0)
experiment.background.create(position=13.2590, intensity=2100.0)
experiment.background.create(position=18.1700, intensity=2100.0)
experiment.background.create(position=23.7500, intensity=2100.0)
experiment.background.create(position=32.0090, intensity=2100.0)
experiment.background.create(position=36.4730, intensity=2100.0)
experiment.background.create(position=47.1880, intensity=2100.0)
experiment.background.create(position=52.0980, intensity=2100.0)
experiment.background.create(position=59.0180, intensity=2100.0)
experiment.background.create(position=69.9550, intensity=2100.0)
experiment.background.create(position=80.0000, intensity=2100.0)
experiment.background.create(position=90.4910, intensity=2100.0)
experiment.background.create(position=101.2050, intensity=2100.0)
experiment.background.create(position=106.3390, intensity=2100.0)
experiment.background.create(position=108.7950, intensity=2100.0)
experiment.background.create(position=112.5890, intensity=2100.0)
experiment.background.create(position=119.2860, intensity=2100.0)
experiment.background.create(position=128.2140, intensity=2100.0)
experiment.background.create(position=133.1250, intensity=2100.0)
experiment.background.create(position=140.9380, intensity=2100.0)
experiment.background.create(position=145.6250, intensity=2100.0)
experiment.background.create(position=148.0800, intensity=2100.0)
experiment.background.create(position=151.9000, intensity=2100.0)

# %%
project.display.pattern('spodi')

# %% [markdown]
# ## Perform the analysis
#
# The fit follows diffraction-lib's three cycles for this case (its YAP tutorial). diffraction-lib
# frees the Lorentzian Y and two asymmetry terms where this profile has the mixing η₀ and four.

# %% [markdown]
# ### Cells, scales and 2θ zero
#
# Both phases' cells and scales, and the zero shift, put the peaks of both phases in place.

# %%
yalo3.cell.length_a.free = True
yalo3.cell.length_b.free = True
yalo3.cell.length_c.free = True
alumina.cell.length_a.free = True
alumina.cell.length_c.free = True
experiment.linked_structures['YAlO3'].scale.free = True
experiment.linked_structures['Al2O3'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Background

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Peak widths
#
# The Gaussian widths and the mixing η₀.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.mixing_eta_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Asymmetry
#
# The four Bérar-Baldinozzi asymmetry terms.

# %%
experiment.peak.asym_beba_a0.free = True
experiment.peak.asym_beba_b0.free = True
experiment.peak.asym_beba_a1.free = True
experiment.peak.asym_beba_b1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Atom positions
#
# The coordinates the symmetry leaves free in both phases.

# %%
yalo3.atom_sites['Y'].fract_x.free = True
yalo3.atom_sites['Y'].fract_y.free = True
yalo3.atom_sites['O1'].fract_x.free = True
yalo3.atom_sites['O1'].fract_y.free = True
yalo3.atom_sites['O2'].fract_x.free = True
yalo3.atom_sites['O2'].fract_y.free = True
yalo3.atom_sites['O2'].fract_z.free = True
alumina.atom_sites['Al1'].fract_z.free = True
alumina.atom_sites['O1'].fract_x.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Displacements
#
# Every site's displacement in both phases.

# %%
for structure in (yalo3, alumina):
    for site in structure.atom_sites:
        site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %%
project.display.fit.correlations()

# %%
project.display.structure('YAlO3')

# %%
project.display.structure('Al2O3')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_yalo3-al2o3-spodi.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_yalo3-al2o3-spodi')
