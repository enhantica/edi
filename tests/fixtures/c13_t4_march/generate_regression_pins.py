"""Freeze 's declared LBCO extension; regression identity, not correctness.

Run on the reviewed committed product tree. Reads committed blobs, never runs a fit.
The March physics and free-parameter gates independently cover the new behaviour.
"""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATHS = [
    'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/expected.json',
    'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project/experiments/hrpt.edi',
]


def main():
    git = shutil.which('git')
    if git is None:
        message = 'Git is required to freeze committed regression blobs'
        raise RuntimeError(message)
    pins = {}
    for path in PATHS:
        raw = subprocess.check_output([git, '-C', str(ROOT), 'show', 'HEAD:' + path])
        pins[path] = hashlib.sha256(raw).hexdigest()
    result = {
        'task': '',
        'claim': 'REGRESSION PIN: March ratio added to the existing LBCO fitting project.',
        'method': 'sha256 of committed HEAD blobs for the explicitly named extension files',
        'sha256': pins,
    }
    Path(__file__).with_name('regression-pins.json').write_text(
        json.dumps(result, indent=2, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    main()
