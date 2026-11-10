# SPDX-License-Identifier: BSD-3-Clause
"""GUI workflows transcribed from the guides, and independently authored load inputs."""

import hashlib
import json
import re

MEASURED = b'17.5 31.25 0.75\n22.75 47.125 1.25\n28.125 19.625 0.875\n'
STRUCTURE = b"""data_gui_reference
_chemical_formula_sum Al
_space_group_name_H-M_alt 'P m -3 m'
_cell_length_a 4.125
_cell_length_b 4.125
_cell_length_c 4.125
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
Al1 Al 0 0 0 1
"""
EXPERIMENT = (
    b"""data_gui_reference
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.beam_mode 'constant wavelength'
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.dimensionality 1d
_experiment_type.polarisation unpolarised
_instrument.setup_wavelength 1.731
_instrument.calib_twotheta_offset 0.125
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0.064
_peak.broad_gauss_v -0.013
_peak.broad_gauss_w 0.087
_peak.broad_lorentz_x 0.017
_peak.broad_lorentz_y 0.023
_peak.cutoff_fwhm 30
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
"""
    + MEASURED
)

# Indices refer to the guide's ordered ui: annotations, not the QObject tree.
# A reordered or replaced annotation therefore changes the action that is replayed.
ROUTES = {
    'measured-file': ('experiment', [0, 1, 2], 'measured'),
    'experiment-file': ('experiment', [1, 3], 'experiment'),
    'structure-file': ('structure', [4, 5], 'structure'),
    'structure-create': ('structure', [6], None),
    'experiment-web': ('experiment', [1, 7, 10, 11, 12, 13], None),
    'measured-web': ('experiment', [0, 1, 8, 10, 11, 12, 13], None),
    'structure-web': ('structure', [4, 9, 10, 11, 12, 13], None),
}


def inventory(guides):
    documents = {
        path.parent.name: path.read_text(encoding='utf-8') for path in guides.glob('*/SKILL.md')
    }
    assert documents, 'The per-skill GUI replay must discover a nonempty guide inventory'
    owner = 'project-assistance'
    assert owner in documents, 'The documented shared GUI route guide must exist'
    shared = re.findall(r'\bui:([A-Za-z0-9_.-]+)', documents[owner])
    assert len(shared) == 14, (
        'Every current GUI route annotation needs its ordered replay role; removed or new '
        'annotations require an explicit workflow update'
    )
    result = {}
    for name, text in documents.items():
        own = re.findall(r'\bui:([A-Za-z0-9_.-]+)', text)
        delegated = 'For GUI operations use project-assistance' in text
        asks = bool(re.search(r'show\s+assistant\s+before\s+asking', text, re.IGNORECASE))
        assert own or delegated or asks, (
            'Every skill must declare executable GUI steps or its explicit GUI delegate: ' + name
        )
        targets = own or (shared if delegated else [])
        if targets:
            assert len(targets) == 14, 'Every delegated skill must retain the complete GUI routes'
        result[name] = {
            'targets': targets,
            'routes': list(ROUTES) if targets else [],
            'show_assistant': True,
            'source': owner if delegated else name,
        }
    assert all(row['routes'] or row['show_assistant'] for row in result.values()), (
        'Every skill must have a nonempty executable step inventory'
    )
    return result


def build(root):
    payloads = {
        'structure': ('structures/reference.cif', STRUCTURE, 'cif'),
        'experiment': ('experiments/reference.edi', EXPERIMENT, 'edi'),
        'measured': ('data/reference.xye', MEASURED, 'xye'),
    }
    entries = []
    paths = {}
    for kind, (relative, content, format_name) in payloads.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        paths[kind] = path
        entries.append({
            'id': kind + '-reference',
            'kind': 'data' if kind == 'measured' else kind,
            'name': 'Independent GUI ' + kind,
            'description': 'Authored GUI route fixture',
            'files': [
                {
                    'path': relative,
                    'format': format_name,
                    'bytes': len(content),
                    'sha256': hashlib.sha256(content).hexdigest(),
                }
            ],
        })
    (root / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': entries}), encoding='utf-8'
    )
    return paths
