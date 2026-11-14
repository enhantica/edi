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
# It builds the catalogue case `pd-neut-cwl_cosio-d20_scan-213f` step by step: the same project the
# command line fits and the app's Examples open. Its two Co sites share one displacement.

# %% [markdown]
# ## Import the library

# %%
import csv
import zipfile
from pathlib import Path

import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='pd-neut-cwl_cosio-d20_scan-213f')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-cwl_cosio-d20_scan-213f-cosio', destination='data')
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
data_path = edi.download_data('pd-neut-cwl_cosio-d20_scan-213f-d20-data', destination='data')
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
experiment.peak.broad_lorentz_y = 0.0114
experiment.peak.asym_fcj_1 = 0.0619
experiment.peak.asym_fcj_2 = 0.0619
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

# %%
project.save_as('pd-neut-cwl_cosio-d20_scan-213f')

# %% [markdown]
# The scan's patterns come from the collection as one archive. Unpack them into the project's
# folder and declare them as the scan the sequential fit runs over, from the last file up; it reads
# each pattern's temperature from its header.

# %%
scan_path = edi.download_data('pd-neut-cwl_cosio-d20_scan-213f-scan', destination='data')
with zipfile.ZipFile(scan_path) as archive:
    archive.extractall('pd-neut-cwl_cosio-d20_scan-213f/experiments/d20_scan')
project.analysis.sequential_fit.data_dir = 'experiments/d20_scan'
project.analysis.sequential_fit.file_pattern = '*.dat'
project.analysis.sequential_fit.reverse = True
project.analysis.sequential_fit_extract.create(
    id='temperature', target='diffrn.ambient_temperature', pattern=r'^TEMP\s+([0-9.]+)'
)
project.save()

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
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the nuclear and the
# magnetic reflection positions, and lists the structure and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_cosio-d20_scan-213f.html')

# %% [markdown]
# ## Save the project
#
# The fitted template and the scan results are in the project folder already; save the
# project once more after the fits.

# %%
project.save()
