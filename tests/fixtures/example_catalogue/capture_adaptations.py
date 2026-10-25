"""Capture decided pin and metadata changes without rewriting the original retention oracle."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
PINS = (
    'pd-neut-tof_ncaf-wish-2bank_start-3',
    'pd-neut-tof_ncaf-wish-3bank_start-5',
    'pd-neut-tof_ncaf-wish-5bank_start-5',
    'pd-neut-tof_ncaf-wish-5bank_start-fullprof',
    'pd-neut-tof_si-sepd_start-2',
    'pd-neut-tof_si-sepd_start-5',
    'pd-neut-tof_cecoal-polaris_chebyshev',
    'pd-neut-tof_ceo2-pearl_polynomial',
    'pd-neut-tof_ferrite-austenite-beer_joint',
)


def committed(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


def reference_rows(value, prefix=''):
    output = {}
    if isinstance(value, dict):
        if value.get('kind') == 'reference':
            output[prefix] = value
        for key, child in value.items():
            output.update(reference_rows(child, prefix + '/' + key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            output.update(reference_rows(child, prefix + '/' + str(index)))
    return output


def main():
    files = {}
    paths = [(case + '/expected.json', 'b339d832') for case in PINS]
    paths.append(('pd-neut-cwl_y2o3_beta-adp/project/project.edi', '34168971'))
    for suffix, commit in paths:
        path = 'docs/user/cli/' + suffix
        before, after = committed('3a6b4dc8', path), committed(commit, path)
        if suffix.endswith('expected.json'):
            assert reference_rows(json.loads(before)) == reference_rows(json.loads(after)), (
                'Decided pin changes retain every correctness reference and tolerance'
            )
            reason = (
                'Decided descent recovery and out-of-range TOF tails; '
                'documented before/after regression pins'
            )
        else:
            fields = (b'_metadata.title ', b'_metadata.instrument ', b'_metadata.facility ')
            strip = lambda data, fields=fields: b''.join(  # noqa: E731 - exact byte projection
                line for line in data.splitlines(keepends=True) if not line.startswith(fields)
            )
            assert strip(before) == strip(after), 'The Y2O3 change is descriptive metadata only'
            reason = 'Main supplies SPODI at FRM II; all scientific bytes remain unchanged'
        assert (ROOT / path).read_bytes() == after, (
            'Capture only the declared committed replacement'
        )
        files[path] = {
            'source_commit': commit,
            'reason': reason,
            'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
            'before': before.decode(),
            'after': after.decode(),
        }
    (HERE / 'retention-adaptations.json').write_text(json.dumps({'files': files}, indent=2) + '\n')


if __name__ == '__main__':
    main()
