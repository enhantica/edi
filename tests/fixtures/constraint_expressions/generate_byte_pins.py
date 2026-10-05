"""Capture labelled serialization regression pins for declared relation and follower changes.

The frozen pre-change witnesses remain intact. Only the named model files may
change their regression identity; every other file keeps its previous hash.
"""

import hashlib
import json
import runpy
import subprocess
import tempfile
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]
CLI = 'repo:docs/user/cli/'
DECLARED = {
    'corpus:cosio-d20-scan-3f/project': ('', ('analysis/analysis.edi', 'structures/cosio.edi')),
    'corpus:ncaf-wish-3bank-s5/project': ('', ('structures/ncaf.edi',)),
    CLI + 'pd-neut-cwl_cosio-d20_scan-3f/project': (
        'cb4d8eb',
        ('analysis/analysis.edi', 'structures/cosio.edi'),
    ),
    CLI + 'pd-neut-cwl_cosio-d20_scan-324f/project': (
        'cb4d8eb',
        ('analysis/analysis.edi', 'structures/cosio.edi'),
    ),
    **{
        CLI + name + '/project': ('8d1edc5', ('structures/ncaf.edi',))
        for name in (
            'pd-neut-tof_ncaf-wish-3bank_start-5',
            'pd-neut-tof_ncaf-wish-5bank_start-5',
            'pd-neut-tof_ncaf-wish-5bank_start-fullprof',
        )
    },
}


def main():
    reference = runpy.run_path(str(ROOT / 'tests/fixtures/c34_t28_baseline/generate_bytes.py'))
    old = json.loads((ROOT / 'tests/fixtures/c34_t28_baseline/saved-bytes.json').read_text())[
        'cases'
    ]
    public = json.loads(
        (ROOT / 'tests/fixtures/e04_t12_public_release/saved-metadata.json').read_text()
    )
    cases = {}
    with tempfile.TemporaryDirectory() as temporary:
        for index, (case, (change, allowed)) in enumerate(DECLARED.items()):
            source = reference['inputs']()[case]
            before = public.get(case, old[case])
            inputs = reference['hashes'](source)
            if change:
                for name in inputs:
                    relative = (source / name).relative_to(ROOT).as_posix()
                    committed = subprocess.check_output([
                        'git',
                        '-C',
                        str(ROOT),
                        'show',
                        f'{change}:{relative}',
                    ])
                    if hashlib.sha256(committed).hexdigest() != inputs[name]:
                        message = 'the byte pin input must equal its declared committed model'
                        raise ValueError(message)
            saved = reference['observe'](source, Path(temporary) / str(index), calculator=True)
            for channel, hashes in (('input_sha256', inputs), ('saved_sha256', saved)):
                if set(hashes) != set(before[channel]):
                    message = 'a byte extension must retain the entire historical file inventory'
                    raise ValueError(message)
                if any(
                    hashes[name] != before[channel][name] for name in hashes if name not in allowed
                ):
                    message = (
                        'a byte extension cannot bless a change outside its declared model files'
                    )
                    raise ValueError(message)
            cases[case] = {
                'before': before,
                'after_input_sha256': inputs,
                'after_saved_sha256': saved,
                'allowed_files': list(allowed),
                'model_commit': change,
            }
    output = {
        'claim': 'REGRESSION PIN: declared relation and follower serialization.',
        'engine_extension_sha256': hashlib.sha256(
            Path(edi._edi.__file__).read_bytes()
        ).hexdigest(),
        'cases': cases,
    }
    Path(__file__).with_name('byte-pins.json').write_text(
        json.dumps(output, indent=2, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    main()
