"""Hand-written nondefault experiments exercise independently sourced CIF name lists."""

import importlib
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
NAMES = json.loads((ROOT / 'tests/fixtures/dictionary_display/experiment_names.json').read_text())
CASES = [(uid, name) for uid, names in NAMES.items() for name in names]
BASE = """data_names
_easydiffraction_experiment_type.sample_form powder
_easydiffraction_experiment_type.beam_mode 'constant wavelength'
_easydiffraction_experiment_type.radiation_probe neutron
_easydiffraction_experiment_type.scattering_type bragg
_diffrn_radiation_wavelength.value 1.494
_pd_calib.2theta_offset 0.6225
_easydiffraction_peak.broad_gauss_u 0.0834
"""
COLUMNS = {
    'instrument.setup_wavelength': ('_diffrn_radiation_wavelength.value', 1.494),
    'peak.broad_gauss_u': ('_easydiffraction_peak.broad_gauss_u', 0.0834),
    'absorption.mu_r': ('_easydiffraction_absorption.mu_r', 0.0361),
    'linked_structure.scale': ('_pd_phase_block.scale', 0.71345),
    'background.intensity': ('_pd_background.line_segment_intensity', 4.12345),
    'preferred_orientation.march_r': ('_pd_pref_orient_March_Dollase.r', 0.92345),
}


def parameter(experiment, uid):
    category, member = uid.split('.')
    return getattr(getattr(experiment, category), member)


@pytest.mark.parametrize(('uid', 'name'), CASES, ids=[name for _, name in CASES])
def test_every_external_experiment_spelling_loads_its_nondefault_value(uid, name):
    old, expected = COLUMNS[uid]
    text = BASE.replace(old, name)
    api = importlib.import_module('edi')
    experiment = api.ExperimentFactory.from_cif_str(text)
    actual = parameter(experiment, uid)
    assert actual.value == pytest.approx(expected, abs=1e-12), (
        'Each official or upstream CIF name reaches its hand-written nondefault quantity'
    )


@pytest.mark.parametrize(
    ('uid', 'expected'),
    [
        ('instrument.setup_wavelength', 1.54),
        ('peak.broad_gauss_u', 0.0834),
        ('absorption.mu_r', 0.0361),
        ('linked_structure.scale', 0.71345),
        ('background.intensity', 4.12345),
        ('preferred_orientation.march_r', 0.92345),
    ],
)
@pytest.mark.parametrize('upper', [False, True])
def test_external_edi_names_reach_each_existing_category(tmp_path, uid, expected, upper):
    # The external inventory fixes the canonical EDI name; input numbers are hand-written.
    upstream = json.loads(
        (ROOT / 'tests/fixtures/dictionary_display/upstream-names.json').read_text()
    )
    external = {name for row in upstream['entries'] for name in row['edi_names']}
    tag = '_' + uid
    assert tag in external, 'The EDI input name exists in the independent upstream inventory'
    source = tmp_path / 'input'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', source)
    path = source / 'experiments/bank.edi'
    text = path.read_text().replace('_peak.broad_gauss_u 0', '_peak.broad_gauss_u 0.0834')
    text = text.replace('phase 0.7\n', 'phase 0.71345\n')
    text = text.replace('pA 10.011 4()', 'pA 10.011 4.12345')
    text = text.replace('phase 0.73 ', 'phase 0.92345 ')
    text += '\n_absorption.type cylinder-hewat\n_absorption.mu_r 0.0361\n'
    if upper:
        text = text.replace(tag, tag.upper())
    path.write_text(text)
    api = importlib.import_module('edi')
    project = api.Project.load(source)
    experiment = project.experiments['bank']
    if uid == 'linked_structure.scale':
        actual = experiment.linked_structures[0].scale
    elif uid == 'preferred_orientation.march_r':
        actual = experiment.preferred_orientation['phase'].march_r
    elif uid == 'background.intensity':
        actual = experiment.background[0].intensity
    else:
        actual = parameter(experiment, uid)
    assert actual.value == pytest.approx(expected, abs=1e-12), (
        'Each external EDI name reaches its existing category with the independent input value'
    )
