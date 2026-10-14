"""Freeze independent FullProf and published form-factor inputs at authoring time."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = Path(sys.argv[1])
LIBRARIES = Path(sys.argv[2])
REVISION = '0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf'
LIB_REVISION = 'b37f9f3148d2771c6d84ee91f57331676d93746f'
GIT = shutil.which('git')
if GIT is None:
    message = 'The reference generator requires git'
    raise RuntimeError(message)


def committed(repo, revision, path):
    return subprocess.check_output([GIT, '-C', str(repo), 'show', f'{revision}:{path}'])


manifest = {'upstream': 'https://github.com/easyscience/diffraction-lib', 'revision': REVISION}
for case, stem, folder in [
    ('doublet', 'lif_doublet_unpolarized', 'pd-xray-cwl_lif'),
    ('absorption', 'lif_single_absorption', 'pd-xray-cwl_lif'),
    ('round-robin', 'pbsox', 'pd-xray-cwl_pbso4_round-robin'),
]:
    target = ROOT / case
    target.mkdir(exist_ok=True)
    files = {}
    for extension in ('pcr', 'prf', 'sum', 'bac', 'dat'):
        name = f'{stem}.{extension}'
        raw = committed(UPSTREAM, REVISION, f'docs/docs/verification/fullprof/{folder}/{name}')
        (target / name).write_bytes(raw)
        files[name] = hashlib.sha256(raw).hexdigest()
    manifest[case] = {'stem': stem, 'files': files}

sources = {
    'wk1995': 'periodictable/periodictable/f0_WaasKirf.dat',
    'it1992': 'cctbx/cctbx/eltbx/xray_scattering/it1992.cpp',
}
tables = {}
for name, path in sources.items():
    raw = committed(LIBRARIES, LIB_REVISION, path)
    manifest[name] = {
        'libraries_revision': LIB_REVISION,
        'path': path,
        'sha256': hashlib.sha256(raw).hexdigest(),
    }
    rows = {}
    if name == 'wk1995':
        for block in raw.decode().split('#S ')[1:]:
            key = block.splitlines()[0].split()[1]
            values = [float(value) for value in block.splitlines()[3].split()]
            rows[key] = {'a': values[:5], 'b': values[6:], 'c': values[5]}
    else:
        cleaned = re.sub(r'//[^\n]*|/\*.*?\*/', '', raw.decode(), flags=re.DOTALL)
        for key, a, b, c in re.findall(
            r'\{\s*"([^"]+)"\s*,\s*\{([^}]+)\}\s*,\s*\{([^}]+)\}\s*,\s*([-\d.eE+]+)\s*\}', cleaned
        ):
            rows[key] = {
                'a': [float(v) for v in a.split(',')],
                'b': [float(v) for v in b.split(',')],
                'c': float(c),
            }
    tables[name] = rows
(ROOT / 'published-f0.json').write_text(json.dumps(tables, indent=2, sort_keys=True) + '\n')
manifest['published-f0.json'] = hashlib.sha256(
    (ROOT / 'published-f0.json').read_bytes()
).hexdigest()
(ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')

MODEL = """data_structure
_edi.schema_version 3
_cell.length_a 4.026700
_cell.length_b 4.026700
_cell.length_c 4.026700
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "F m -3 m"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
Li1 a Li Biso 0 0 0 1 1.2
F1 b F Biso 0.5 0.5 0.5 1 0.8

data_experiment
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe xray
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0.048457
_peak.broad_gauss_v -0.083053
_peak.broad_gauss_w 0.04
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0.049268
_peak.cutoff_fwhm 48
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength 1.540560
loop_
_linked_structure.structure_id
_linked_structure.scale
structure 0.01

_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion sasaki1989
"""
(ROOT / 'lif.edi').write_text(MODEL)
