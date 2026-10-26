"""Rebind the joint receipt only when its new start reproduces the existing FullProf inputs."""

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

from finalize_fullprof import refresh_project_inputs, stopping_settings
from fullprof_inputs import ROOT

CASE = 'pd-neut-xray-cwl_pbso4-d1a-lab'


def main(evidence):
    home = ROOT / 'knowledge/fitting/fullprof' / CASE
    receipt = home / 'reference.json'
    original = receipt.read_text()
    record = json.loads(original)
    name = record['start_project'] + '/experiments/d1a.edi'
    before, after = [
        subprocess.check_output(['git', 'show', commit + ':' + name], cwd=ROOT)
        for commit in ('09a40bdc^', '09a40bdc')
    ]
    assert before.count(b'_instrument.setup_wavelength 1.91()\n') == 1, (
        'The joint correction begins with exactly one declared free D1A wavelength'
    )
    assert (
        before.replace(
            b'_instrument.setup_wavelength 1.91()\n', b'_instrument.setup_wavelength 1.91\n'
        )
        == after
        == (ROOT / name).read_bytes()
    ), 'The committed joint correction changes only the D1A wavelength free flag'
    old_hash, new_hash = [hashlib.sha256(data).hexdigest() for data in (before, after)]
    assert record['project_sha256']['experiments/d1a.edi'] == old_hash, (
        'The receipt update starts at the exact archived pre-correction D1A input'
    )
    candidate = copy.deepcopy(record)
    candidate['cycles'], candidate['epsilon'] = stopping_settings(home / 'fit.pcr')
    # This existing authoring guard compares every exported PCR and observation
    # file against the committed inputs, for both calculation and fit. It never
    # launches FullProf, and refuses before changing a receipt if any byte differs.
    refresh_project_inputs(candidate, home, CASE)
    assert candidate['project_sha256'] == {
        **record['project_sha256'],
        'experiments/d1a.edi': new_hash,
    }, 'Only the corrected D1A source digest may change in the joint start binding'
    assert original.count(old_hash) == 1, (
        'The receipt has one unambiguous source digest to update surgically'
    )
    receipt.write_text(original.replace(old_hash, new_hash))
    with (home / 'PROVENANCE.md').open('a') as stream:
        stream.write(
            '\nThe committed D1A wavelength is fixed at 1.91 A, as the FullProf input already '
            'does. Re-exporting both the start calculation and the fit reproduces every '
            'committed PCR and observation-data byte. Their authoring outputs are reused '
            'unchanged; only the source receipt digest is rebound.\n'
        )
    evidence.write_text(
        json.dumps(
            {
                'case': CASE,
                'input': name,
                'before_sha256': old_hash,
                'after_sha256': new_hash,
                'export_guard': (
                    'refresh_project_inputs: calculation and fit inputs byte-identical'
                ),
                'external_outputs_unchanged': record['artifacts_sha256'],
                'fp2k_invoked': False,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    main(parser.parse_args().evidence)
