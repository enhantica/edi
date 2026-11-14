"""Sequential fit: LATP, BM01."""
# %% [markdown]
# # Sequential fit: LATP, BM01
#
# Fit three phases, LATP and two AlPO₄ forms, to 73 synchrotron X-ray patterns from BM01 at ESRF,
# one after another, with linked displacement parameters.
#
# It builds the catalogue case `pd-xray-cwl_latp-bm01_scan` step by step: the same project the
# command line fits and the app's Examples open. Al shares Ti's site, coordinate and displacement,
# and the impurity phase's displacements are shared,.

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
project = edi.Project(name='pd-xray-cwl_latp-bm01_scan')

# %% [markdown]
# ## Define the structures
#
# Load the three structures from EasyDiffraction's collection. Each CIF gives its space group, cell
# and atom sites.

# %%
path = edi.download_data('pd-xray-cwl_latp-bm01_scan-latp', destination='data')
project.structures.add_from_cif_path(path)
path = edi.download_data('pd-xray-cwl_latp-bm01_scan-alpo4_c2221', destination='data')
project.structures.add_from_cif_path(path)
path = edi.download_data('pd-xray-cwl_latp-bm01_scan-alpo4_p63mc', destination='data')
project.structures.add_from_cif_path(path)
latp = project.structures['latp']
c2221 = project.structures['alpo4_c2221']
p63mc = project.structures['alpo4_p63mc']

# %%
project.display.structure('latp')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-xray-cwl_latp-bm01_scan-bm01-data', destination='data')
project.experiments.add_from_data_path(
    name='bm01',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='xray',
    scattering_type='bragg',
)
experiment = project.experiments['bm01']
experiment.xray_dispersion = 'sasaki1989'
experiment.peak.type = 'cwl-pseudo-voigt-berar-baldinozzi'
experiment.absorption.type = 'cylinder-hewat'
experiment.instrument.name = 'BM01'
experiment.instrument.facility = 'ESRF'
experiment.xray_dispersion = 'sasaki1989'
experiment.peak.broad_gauss_u = 0.019
experiment.peak.broad_gauss_v = 0.019
experiment.peak.broad_gauss_w = 0.0156
experiment.peak.mixing_eta_0 = 0.374
experiment.peak.asym_beba_a0 = 0.088
experiment.peak.asym_beba_b0 = 0.0043
experiment.peak.cutoff_fwhm = 8
experiment.instrument.setup_wavelength = 0.69687
experiment.instrument.calib_twotheta_offset = -0.0388
experiment.absorption.mu_r = 0.3
experiment.excluded_regions.create(start=0, end=3.8)
experiment.excluded_regions.create(start=62.3, end=180)
experiment.linked_structures.create(structure_id='latp', scale=4.15)
experiment.linked_structures.create(
    structure_id='alpo4_c2221',
    scale=0.54,
)
experiment.linked_structures.create(
    structure_id='alpo4_p63mc',
    scale=1.6,
)
experiment.background.create(id='4', position=4.0117, intensity=37000000)
experiment.background.create(id='5', position=5.3148, intensity=41700000)
experiment.background.create(id='7', position=7.1929, intensity=52700000)
experiment.background.create(id='8', position=8.2721, intensity=67200000)
experiment.background.create(id='9', position=8.9749, intensity=82700000)
experiment.background.create(id='10', position=10.0793, intensity=79800000)
experiment.background.create(id='12', position=12.3508, intensity=48200000)
experiment.background.create(id='14', position=13.9092, intensity=37100000)
experiment.background.create(id='16', position=15.6032, intensity=30700000)
experiment.background.create(id='18', position=18.1069, intensity=26100000)
experiment.background.create(id='20', position=20.4202, intensity=24300000)
experiment.background.create(id='23', position=22.675, intensity=22900000)
experiment.background.create(id='25', position=25.3704, intensity=22700000)
experiment.background.create(id='27', position=27.1127, intensity=25100000)
experiment.background.create(id='30', position=29.6603, intensity=24400000)
experiment.background.create(id='33', position=32.5461, intensity=25900000)
experiment.background.create(id='36', position=35.7233, intensity=19290000)
experiment.background.create(id='38', position=37.9048, intensity=15950000)
experiment.background.create(id='40', position=40.4041, intensity=16580000)
experiment.background.create(id='43', position=42.6881, intensity=18850000)
experiment.background.create(id='45', position=44.899, intensity=18080000)
experiment.background.create(id='47', position=47.0073, intensity=17900000)
experiment.background.create(id='49', position=49.2474, intensity=19470000)
experiment.background.create(id='51', position=51.0337, intensity=20370000)
experiment.background.create(id='53', position=53.2738, intensity=21920000)
experiment.background.create(id='55', position=55.2504, intensity=22390000)
experiment.background.create(id='57', position=56.9107, intensity=21830000)
experiment.background.create(id='59', position=58.6676, intensity=23840000)
experiment.background.create(id='61', position=61.4348, intensity=18960000)
experiment.background.create(id='62', position=62.25, intensity=15500000)

# %% [markdown]
# The constraints the fit keeps, each between two named parameters (aliases).

# %%
project.analysis.aliases.create(id='z_Ti1', param=latp.atom_sites['Ti1'].fract_z)
project.analysis.aliases.create(id='z_Al1', param=latp.atom_sites['Al1'].fract_z)
project.analysis.aliases.create(id='b_Ti1', param=latp.atom_sites['Ti1'].adp_iso)
project.analysis.aliases.create(id='b_Al1', param=latp.atom_sites['Al1'].adp_iso)
project.analysis.aliases.create(id='b2_Al1', param=c2221.atom_sites['Al1'].adp_iso)
project.analysis.aliases.create(id='b2_P1', param=c2221.atom_sites['P1'].adp_iso)
project.analysis.aliases.create(id='b2_O1', param=c2221.atom_sites['O1'].adp_iso)
project.analysis.aliases.create(id='b2_O2', param=c2221.atom_sites['O2'].adp_iso)
project.analysis.constraints.create(id='z_Al1', expression='z_Al1 = z_Ti1')
project.analysis.constraints.create(id='b_Al1', expression='b_Al1 = b_Ti1')
project.analysis.constraints.create(id='b2_P1', expression='b2_P1 = b2_Al1')
project.analysis.constraints.create(id='b2_O1', expression='b2_O1 = b2_Al1')
project.analysis.constraints.create(id='b2_O2', expression='b2_O2 = b2_Al1')

# %%
project.save_as('pd-xray-cwl_latp-bm01_scan')
project.display.constraints()

# %% [markdown]
# The scan's patterns come from the collection as one archive. Unpack them into the project's
# folder and declare them as the scan the sequential fit runs over, from the last file up.

# %%
scan_path = edi.download_data('pd-xray-cwl_latp-bm01_scan-scan', destination='data')
with zipfile.ZipFile(scan_path) as archive:
    archive.extractall('pd-xray-cwl_latp-bm01_scan/experiments/bm01_scan')
project.analysis.sequential_fit.data_dir = 'experiments/bm01_scan'
project.analysis.sequential_fit.file_pattern = '*.dat'
project.analysis.sequential_fit.reverse = True
project.analysis.template_file = 'latp_312.dat'
project.save()

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
for parameter in (
    latp.cell.length_a,
    latp.cell.length_c,
    c2221.cell.length_a,
    c2221.cell.length_b,
    c2221.cell.length_c,
    p63mc.cell.length_a,
    p63mc.cell.length_c,
):
    parameter.free = True

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
for parameter in (
    experiment.peak.broad_gauss_u,
    experiment.peak.broad_gauss_v,
    experiment.peak.broad_gauss_w,
    experiment.peak.mixing_eta_0,
):
    parameter.free = True

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
for parameter in (
    latp.atom_sites['Ti1'].fract_z,
    latp.atom_sites['P1'].fract_x,
    latp.atom_sites['O1'].fract_x,
    latp.atom_sites['O1'].fract_y,
    latp.atom_sites['O1'].fract_z,
    latp.atom_sites['O2'].fract_x,
    latp.atom_sites['O2'].fract_y,
    latp.atom_sites['O2'].fract_z,
):
    parameter.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('bm01')

# %% [markdown]
# ### LATP displacements

# %%
for parameter in (
    latp.atom_sites['Ti1'].adp_iso,
    latp.atom_sites['P1'].adp_iso,
    latp.atom_sites['O1'].adp_iso,
    latp.atom_sites['O2'].adp_iso,
):
    parameter.free = True

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
# ## Report

# %%
project.report.save_html('pd-xray-cwl_latp-bm01_scan.html')

# %% [markdown]
# ## Save the project
#
# The fitted template and the scan results are in the project folder already; save the
# project once more after the fits.

# %%
project.save()
