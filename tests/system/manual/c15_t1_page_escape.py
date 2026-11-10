"""Execute the real LiF page, then disable X-ray through its declared selector."""

import re
import runpy
from pathlib import Path
from unittest.mock import patch

import edi
import numpy as np
from edi import verification

ROOT = Path(__file__).resolve().parents[3]
page = ROOT / 'docs/dev/verification/pd-xray-cwl_LiF_single.py'
assert page.is_file(), ' missing capability: executable LiF X-ray page'
factory = edi.ExperimentFactory.from_dict
text_factory = edi.ExperimentFactory.from_cif_str
agreement = verification.assert_patterns_agree
for disabled in (False, 'radiation', 'dispersion'):
    state = {'compared': False, 'rejected': False, 'changed': False}

    def make(data, *, disabled=disabled, state=state):
        if disabled == 'radiation':
            data = {
                **data,
                'experiment_type': {**data['experiment_type'], 'radiation_probe': 'neutron'},
            }
            data['scattering_source'] = {
                key: value
                for key, value in data.get('scattering_source', {}).items()
                if key not in {'xray_form_factor', 'xray_dispersion'}
            }
            state['changed'] = True
        elif disabled == 'dispersion':
            data = {
                **data,
                'scattering_source': {
                    **data.get('scattering_source', {}),
                    'xray_dispersion': 'none',
                },
            }
            state['changed'] = True
        return factory(data)

    def make_text(text, *, disabled=disabled, state=state):
        before = text
        if disabled == 'radiation':
            text = re.sub(r'(_experiment_type.radiation_probe)\s+\S+', r'\1 neutron', text)
            text = re.sub(r'(?m)^_scattering_source\.xray_\w+.*\n?', '', text)
        elif disabled == 'dispersion':
            text = re.sub(r'(_scattering_source.xray_dispersion)\s+\S+', r'\1 none', text)
        state['changed'] = state['changed'] or before != text
        return text_factory(text)

    def compare(*args, state=state, **kwargs):
        for _label, expected, actual in args[0]:
            assert np.isfinite(expected).all() and np.isfinite(actual).all(), (
                ' disabled kernel must reach agreement with finite calculated data'
            )
        state['compared'] = True
        try:
            return agreement(*args, **kwargs)
        except AssertionError:
            state['rejected'] = True
            raise

    with (
        patch.object(edi.ExperimentFactory, 'from_dict', side_effect=make),
        patch.object(edi.ExperimentFactory, 'from_cif_str', side_effect=make_text),
        patch.object(verification, 'assert_patterns_agree', side_effect=compare),
    ):
        try:
            runpy.run_path(str(page), run_name='__main__')
        except AssertionError:
            if not (disabled and state['rejected']):
                raise
    assert state['compared'], ' actual page must execute its real agreement assertion'
    if disabled:
        assert state['changed'] and state['rejected'], (
            ' escape: disabling X-ray must fail the actual page agreement, not crash'
        )
print(' actual page green; disabled X-ray rejected at agreement')
print(' actual page green; disabled dispersion rejected at agreement')
