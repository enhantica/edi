"""Capture pre-move serialization regression pins; never a physics oracle.

Run this visible generator with the baseline build and --record. The source
closure must still equal BASE; a changed implementation cannot bless new bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

from tests.conftest import crysta_reference_source
from tests.fixtures.c34_t28_baseline.closure import require_baseline_closure
from tests.fixtures.cwl_family.historical import current_tokens, original_tokens

ROOT = Path(__file__).resolve().parents[3]
BASE = 'f3ea7afea400639f2a66d6acb8d922163f1ef128'
PACKAGE = 'edi'


def corpus_root(root=ROOT):
    if PACKAGE == 'crysta':
        return root / 'tests/fitting'
    # Before: the suite's shared mutable fit scratch was treated as committed
    # input. After: bind to the pristine source of edi's linked SDK. observe()
    # and the freshness vehicle copy it privately; all immutable pins stay.
    return crysta_reference_source() / 'tests/fitting'


def inputs(root=ROOT):
    sources = {}
    for path in sorted((root / 'docs/user').rglob('project.edi')):
        sources['repo:' + path.parent.relative_to(root).as_posix()] = path.parent
    for path in sorted(corpus_root(root).glob('*/project/project.edi')):
        sources['corpus:' + path.parent.relative_to(corpus_root(root)).as_posix()] = path.parent
    if PACKAGE == 'crysta':
        prior = root / 'tests/fixtures/c34_t26_diffraction_lib'
        for group in ('inputs', 'calculated'):
            for path in sorted((prior / group).glob('*/project.edi')):
                sources['repo:' + path.parent.relative_to(root).as_posix()] = path.parent
    return sources


def hashes(directory):
    return {
        p.relative_to(directory).as_posix(): hashlib.sha256(
            original_tokens(p.read_bytes())
        ).hexdigest()
        for p in sorted(directory.rglob('*'))
        if p.is_file()
    }


def committed_input(source, destination, revision=None):
    """Materialize retained historical inputs, or an explicit live Git revision."""
    relative = source.relative_to(ROOT).as_posix()
    destination.mkdir(parents=True)
    if revision is None:
        reference = ROOT / 'tests/fixtures/e04_t12_public_release/history'
        pins = json.loads((reference / 'manifest.json').read_text())['input']
        with zipfile.ZipFile(reference / 'input.zip') as archive:
            names = [name for name in pins if name.startswith(relative + '/')]
            if not names:
                raise ValueError('retained historical input is absent: ' + relative)
            for name in names:
                data = archive.read(name)
                if hashlib.sha256(data).hexdigest() != pins[name]:
                    raise ValueError('retained input bytes differ from the historical pin')
                target = destination / name.removeprefix(relative + '/')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(current_tokens(data))
    else:
        payload = subprocess.check_output([
            'git',
            '-C',
            str(ROOT),
            'archive',
            revision + ':' + relative,
        ])
        with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
            archive.extractall(destination, filter='data')
    return destination


#  at independently merged crysta main cf5d5253 changed exactly these
# six inputs from cryspy to crysta; every other input byte keeps its old hash.
CALCULATOR_INPUTS = {
    'corpus:cosio-d20-s1/project': ('experiments/d20.edi',),
    'corpus:cosio-d20-s4/project': ('experiments/d20.edi',),
    'corpus:ncaf-wish-2bank-s3/project': ('experiments/wish_4_7.edi', 'experiments/wish_5_6.edi'),
    'corpus:si-sepd-s2/project': ('experiments/sepd.edi',),
    'corpus:si-sepd-s5/project': ('experiments/sepd.edi',),
}


def legacy_input_hashes(directory, case):
    result = hashes(directory)
    for name in CALCULATOR_INPUTS.get(case, ()):
        contents = (directory / name).read_bytes()
        declaration = b'_calculator.type crysta\n'
        assert contents.count(declaration) == 1, (
            ' I22 inherited seed change is exactly one supported calculator declaration'
        )
        assert len(re.findall(rb'(?m)^_calculator\.', contents)) == 1, (
            ' I22 no additional seed calculator field may escape the input oracle'
        )
        old = original_tokens(contents).replace(declaration, b'_calculator.type cryspy\n', 1)
        result[name] = hashlib.sha256(old).hexdigest()
    return result


def without_saved_calculator(name, contents):
    # Exact canonical block from 's independent CIF contract and retained
    # main-tree byte witness; this is not a new engine-output regression pin.
    if not (name.startswith('experiments/') and name.endswith('.edi')):
        return contents
    declaration = b'_calculator.type crysta\n\n'
    assert contents.count(declaration) == 1, (
        ' I22 each saved experiment has exactly one canonical calculator block'
    )
    assert len(re.findall(rb'(?m)^_calculator\.', contents)) == 1, (
        ' I22 no additional saved calculator field may escape the output oracle'
    )
    return original_tokens(contents.replace(declaration, b'', 1))


def saved_hashes(directory):
    return {
        p.relative_to(directory).as_posix(): hashlib.sha256(
            without_saved_calculator(p.relative_to(directory).as_posix(), p.read_bytes())
        ).hexdigest()
        for p in sorted(directory.rglob('*'))
        if p.is_file()
    }


def observe(source, destination, *, calculator=False):
    package = importlib.import_module(PACKAGE)
    # Drive the real loader with prescribed metadata, not a masked save output.
    # last_modified advances from this future input by exactly one second.
    with tempfile.TemporaryDirectory() as temporary:
        controlled = Path(temporary) / 'input'
        shutil.copytree(source, controlled)
        project_file = controlled / 'project.edi'
        text = project_file.read_text()
        for name, value in (
            ('created', '01 Jan 2099 00:00:00'),
            ('last_modified', '01 Jan 2099 00:00:01'),
        ):
            line = f'_metadata.{name} "{value}"'
            pattern = rf'(?m)^_metadata\.{name}[^\n]*$'
            if re.search(pattern, text):
                text = re.sub(pattern, line, text)
            else:
                text += '\n' + line + '\n'
        project_file.write_text(text)
        project = package.Project.load(controlled)
    project.save_as(destination)
    return saved_hashes(destination) if calculator else hashes(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true', required=True)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.source_root.resolve()
    executable = shutil.which('git')
    if not executable:
        parser.error('real Git is required to establish the baseline source closure')
    require_baseline_closure(root)
    package = importlib.import_module(PACKAGE)
    if not Path(package.__file__).resolve().is_relative_to(root):
        parser.error('the imported pre-move package must resolve inside its source checkout')
    inventory = inputs(root)
    if not inventory or not any(name.startswith('corpus:') for name in inventory):
        message = 'the declared CLI/corpus inputs must resolve before capture'
        raise SystemExit(message)
    result = {'kind': 'pre-move serialization regression pin', 'source_commit': BASE, 'cases': {}}
    with tempfile.TemporaryDirectory() as temporary:
        for index, (name, source) in enumerate(inventory.items()):
            result['cases'][name] = {
                'input_sha256': hashes(source),
                'saved_sha256': observe(source, Path(temporary) / str(index)),
            }
            print('captured', name, flush=True)
    destination = Path(__file__).with_name('saved-bytes.json')
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('recorded', len(result['cases']), 'projects at', BASE, flush=True)


if __name__ == '__main__':
    main()
