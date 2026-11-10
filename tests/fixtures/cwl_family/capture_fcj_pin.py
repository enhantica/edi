"""Retake only the FCJ regression pin for crysta's continuous axial-offset integral.

Run with the qualified edi extension and --engine-source pointing to its crysta
checkout. This is an engine regression pin, never an independent physics oracle.
Historical captures and the dispatch-only rounding contract remain immutable.
"""

import argparse
import base64
import hashlib
import json
import os
import platform
import subprocess
import tempfile
from pathlib import Path

import edi
import edi.verification
import numpy as np

from tests.fixtures.cwl_family import profiles
from tests.fixtures.cwl_family.regression_comparison import (
    FCJ_MODEL_SEAL,
    read_reference,
    rename_project,
)

ROOT = Path(__file__).resolve().parents[3]
HOME = Path(__file__).resolve().parent
ALGORITHM = 'b2022d22'
CAUSE = "crysta continuous FCJ integral, intentionally distinct from FullProf's Prof_Val"


def capture(source):
    linked = edi.verification._crysta_provenance_path().read_text().strip()
    selected = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    if selected != linked:
        raise ValueError('Retake requires the actual linked engine source')
    subprocess.run(
        ['git', 'merge-base', '--is-ancestor', ALGORITHM, selected], cwd=source, check=True
    )
    if os.environ.get('CRYSTA_SIMD_LANES') is not None:
        raise ValueError('Retake requires default native dispatch')
    manifest = json.loads(
        (ROOT / 'build/crysta-prefix/share/crysta-sdk/manifest.json').read_text()
    )
    if manifest['source_sha'] != linked:
        raise ValueError('Retake requires the manifest of the linked SDK')
    hashes = {
        p.relative_to(HOME / 'rename_inputs').as_posix(): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in sorted((HOME / 'rename_inputs').rglob('*.edi'))
    }
    if hashes != json.loads((HOME / 'rename-input-sha256.json').read_text()):
        raise ValueError('Retake must keep every historical physical input byte')
    native = platform.system()
    historical = read_reference(HOME, native)
    with tempfile.TemporaryDirectory() as tmp:
        directory = rename_project(HOME, Path(tmp) / 'fcj', 'fcj', profiles.TOKENS[5], historical)
        project = edi.Project.load(directory)
        project.analysis.calculate()
        actual = np.asarray(project.experiments[0].data.intensity_calc, dtype='<f8')
    old = base64.b64decode(historical['pins']['fcj'], validate=True)
    if actual.nbytes != len(old) or not np.isfinite(actual).all():
        raise ValueError('Retake requires every finite historical sample')
    return {
        'kind': 'regression-pin',
        'cause': CAUSE,
        'algorithm_commit': subprocess.check_output(
            ['git', 'rev-parse', ALGORITHM], cwd=source, text=True
        ).strip(),
        'platform': native,
        'machine': platform.machine(),
        'edi_source': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'engine_source': linked,
        'sdk_manifest': manifest,
        'module_sha256': hashlib.sha256(Path(edi._edi.__file__).read_bytes()).hexdigest(),
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'input_sha256': hashes,
        'historical_fcj_sha256': hashlib.sha256(old).hexdigest(),
        'pin': base64.b64encode(actual.tobytes()).decode(),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-source', type=Path)
    parser.add_argument(
        '--refresh-description',
        action='store_true',
        help='Update only the description and generator digest of the existing sealed capture',
    )
    args = parser.parse_args()
    output = HOME / 'fcj-adr0110.json'
    if args.refresh_description:
        record = json.loads(output.read_text())
        sealed = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if hashlib.sha256(sealed.encode()).hexdigest() != FCJ_MODEL_SEAL:
            raise ValueError('Description refresh requires the existing sealed capture')
        record['cause'] = CAUSE
        record['generator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    else:
        if args.engine_source is None:
            parser.error('--engine-source is required to capture a new profile')
        record = capture(args.engine_source)
    output.write_text(json.dumps(record, indent=2) + '\n')
