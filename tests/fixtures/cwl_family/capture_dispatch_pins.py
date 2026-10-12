"""Record a native default-dispatch regression pin while retaining the historical capture."""

import argparse
import ast
import base64
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import edi
import edi.verification
import numpy as np

from tests.fixtures.cwl_family import profiles
from tests.fixtures.cwl_family.regression_comparison import read_reference, rename_project

ENGINE_SOURCE = 'c2353f8f6414e4346c0701ca7018c7e615de9495'
SOURCE_OBJECTS = {
    'src': '19211cee65ebdce24101bdcbf9a62e7db4fb7cf5',
    'include': 'ec93638aadf6b3659754b47c409d8db2a6567bf5',
    'cmake': 'ac12bd000e51742ef00f8be01cab35839f81dafa',
    'data': 'c439f774d0ddf6d848f268b3aab6fc994e3e3481',
    'lib': 'db261becb2c2dfa6a32cbe8159e377ea10ce5236',
    'CMakeLists.txt': '6671771daf67ceba3ee5d3be06e5feb56f29f301',
    'pyproject.toml': 'e641f08f52a4e830304734be5d3f62ef4a3dc9c8',
}
ROOT = Path(__file__).resolve().parents[3]
HOME = Path(__file__).resolve().parent


def capture():
    native = platform.system()
    historical = read_reference(HOME, native)
    linked = edi.verification._crysta_provenance_path().read_text().strip()
    source = ROOT / 'build/crysta-src'
    selected = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    objects = {
        key: subprocess.check_output(
            ['git', 'rev-parse', 'HEAD:' + key], cwd=source, text=True
        ).strip()
        for key in SOURCE_OBJECTS
    }
    if selected != linked or objects != SOURCE_OBJECTS:
        raise ValueError('Capture requires the reviewed production source objects and linked SDK')
    inputs = json.loads((HOME / 'rename-input-sha256.json').read_text())
    actual_inputs = {
        p.relative_to(HOME / 'rename_inputs').as_posix(): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in sorted((HOME / 'rename_inputs').rglob('*.edi'))
    }
    if inputs != actual_inputs:
        raise ValueError('Capture requires every unchanged historical input byte')
    if os.environ.get('CRYSTA_SIMD_LANES') is not None:
        raise ValueError('Capture requires native default dispatch without an override')
    output = {
        'kind': 'regression-pin',
        'platform': native,
        'machine': platform.machine(),
        'host': socket.gethostname(),
        'source': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'engine_source': linked,
        'reviewed_engine_source': ENGINE_SOURCE,
        'source_objects': objects,
        'capture_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'sdk_manifest': json.loads(
            (ROOT / 'build/crysta-prefix/share/crysta-sdk/manifest.json').read_text()
        ),
        'module_sha256': hashlib.sha256(Path(edi._edi.__file__).read_bytes()).hexdigest(),
        'historical_sha256': hashlib.sha256(
            (HOME / f'tch-regression-{native}.json').read_bytes()
        ).hexdigest(),
        'input_sha256': actual_inputs,
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
        'pins': {},
        'moves': {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        for name, token in [('tch', profiles.TOKENS[4]), ('fcj', profiles.TOKENS[5])]:
            directory = rename_project(HOME, Path(tmp) / name, name, token, historical)
            project = edi.Project.load(directory)
            project.analysis.calculate()
            actual = np.asarray(project.experiments[0].data.intensity_calc, dtype='<f8')
            old = np.frombuffer(
                base64.b64decode(historical['pins'][name], validate=True), dtype='<f8'
            )
            if actual.shape != old.shape or not np.isfinite(actual).all():
                raise ValueError('Capture must retain all finite historical samples')
            delta = float(np.max(np.abs(actual - old)))
            scale = max(float(np.max(np.abs(old))), sys.float_info.min)
            if delta > 2**-34 * scale:
                raise ValueError('A reviewed dispatch move must retain the unchanged value norm')
            output['pins'][name] = base64.b64encode(actual.tobytes()).decode()
            output['moves'][name] = {
                'changed_samples': int(np.count_nonzero(actual != old)),
                'max_absolute': delta,
                'normwise': delta / scale,
                'before_sha256': hashlib.sha256(old.tobytes()).hexdigest(),
                'after_sha256': hashlib.sha256(actual.tobytes()).hexdigest(),
            }
    return output


def capture_ci_log(log, job, manifest):
    """Recover complete native byte arrays already emitted by a finished macOS test job."""
    context = json.loads(job.read_text())
    sdk = json.loads(manifest.read_text())
    if context['name'] != 'core · macOS' or context['status'] != 'completed':
        raise ValueError('Log capture requires the completed native macOS job')
    if sdk['source_sha'] != ENGINE_SOURCE or sdk['platform'] != 'osx-arm64':
        raise ValueError('Log capture requires the actual reviewed macOS SDK manifest')
    text = log.read_text()
    if 'CRYSTA_SOURCE_SHA: ' + ENGINE_SOURCE not in text:
        raise ValueError('The native job must name its actual reviewed SDK source')
    lines = [re.sub(r'^\S+Z ', '', line) for line in text.splitlines()]
    actual = [
        ast.literal_eval(line.removeprefix('actual = '))
        for line in lines
        if line.startswith('actual = b')
    ]
    expected = [
        ast.literal_eval(line.removeprefix('expected = '))
        for line in lines
        if line.startswith('expected = b')
    ]
    native = [line for line in lines if line.startswith("native_platform = 'Darwin'")]
    if len(actual) != 2 or len(expected) != 2 or len(native) != 2:
        raise ValueError('Both complete native profile byte captures must be present exactly once')
    historical = read_reference(HOME, 'Darwin')
    result = {
        'kind': 'regression-pin',
        'platform': 'Darwin',
        'machine': 'arm64',
        'host': context['runner_name'],
        'source': context['head_sha'],
        'checkout_source': re.search(r'^([0-9a-f]{40})$', '\n'.join(lines), re.MULTILINE)[1],
        'engine_source': ENGINE_SOURCE,
        'reviewed_engine_source': ENGINE_SOURCE,
        'source_objects': SOURCE_OBJECTS,
        'sdk_manifest': sdk,
        'historical_sha256': hashlib.sha256(
            (HOME / 'tch-regression-Darwin.json').read_bytes()
        ).hexdigest(),
        'input_sha256': json.loads((HOME / 'rename-input-sha256.json').read_text()),
        'run_id': context['run_id'],
        'job_id': context['id'],
        'capture_method': 'complete actual native byte literals from the finished pytest job log',
        'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
        'job_context_sha256': hashlib.sha256(job.read_bytes()).hexdigest(),
        'capture_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'pins': {},
        'moves': {},
    }
    for name, before, after in zip(('tch', 'fcj'), expected, actual, strict=True):
        old = base64.b64decode(historical['pins'][name], validate=True)
        if before != old or len(after) != len(old) or not isinstance(after, bytes):
            raise ValueError('Log capture must match the complete retained native before bytes')
        a, b = np.frombuffer(after, dtype='<f8'), np.frombuffer(old, dtype='<f8')
        if not np.isfinite(a).all():
            raise ValueError('Log capture must retain every finite native sample')
        delta = float(np.max(np.abs(a - b)))
        scale = max(float(np.max(np.abs(b))), sys.float_info.min)
        if delta > 2**-34 * scale:
            raise ValueError('The actual native move must retain the unchanged value norm')
        result['pins'][name] = base64.b64encode(after).decode()
        result['moves'][name] = {
            'changed_samples': int(np.count_nonzero(a != b)),
            'max_absolute': delta,
            'normwise': delta / scale,
            'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ci-log', type=Path)
    parser.add_argument('--ci-job', type=Path)
    parser.add_argument('--sdk-manifest', type=Path)
    args = parser.parse_args()
    if any((args.ci_log, args.ci_job, args.sdk_manifest)):
        if not all((args.ci_log, args.ci_job, args.sdk_manifest)):
            parser.error('Log capture requires the log, job context and actual SDK manifest')
        result = capture_ci_log(args.ci_log, args.ci_job, args.sdk_manifest)
    else:
        result = capture()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(result['platform'], result['engine_source'], result['moves'], flush=True)


if __name__ == '__main__':
    main()
