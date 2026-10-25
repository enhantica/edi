"""Rebind LATP descriptive metadata only after replaying both FullProf input exports."""

import copy
import json

from finalize_fullprof import refresh_project_inputs, stopping_settings
from fullprof_inputs import ROOT

CASE = 'pd-xray-cwl_latp-bm01_scan'


def main():
    home = ROOT / 'knowledge/fitting/fullprof' / CASE
    receipt = home / 'reference.json'
    original = receipt.read_text()
    before = json.loads(original)
    after = copy.deepcopy(before)
    after['cycles'], after['epsilon'] = stopping_settings(home / 'fit.pcr')
    refresh_project_inputs(after, home, CASE)
    old_inputs, new_inputs = before['project_sha256'], after['project_sha256']
    if old_inputs.keys() != new_inputs.keys() or any(
        old_inputs[name] != new_inputs[name] for name in old_inputs if name != 'project.edi'
    ):
        raise ValueError('Only LATP project metadata may change in this receipt')
    if old_inputs['project.edi'] == new_inputs['project.edi']:
        raise ValueError('The LATP receipt already binds these metadata bytes')
    receipt.write_text(original.replace(old_inputs['project.edi'], new_inputs['project.edi']))
    with (home / 'PROVENANCE.md').open('a') as stream:
        stream.write(
            '\nThe source metadata now names BM01 at ESRF. Both start and fit exports '
            'reproduce every committed FullProf control and observation-data byte. '
            'The source metadata digest alone is rebound; external outputs are unchanged.\n'
        )


if __name__ == '__main__':
    main()
