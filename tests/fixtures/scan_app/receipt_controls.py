"""Exercise stale reuse using real host receipts and valid changed compiled inputs."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import crysta_reference_prefix, crysta_reference_source
from tests.fixtures.scan_app.build_probe import validate_current_inputs


def copy_inputs(source, destination, names):
    for name in names:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source / name, target)
    return destination


def replace_valid_source(path):
    original = path.read_bytes()
    path.unlink()
    path.write_bytes(original + b'\n// valid changed compiled input\n')


def stale_reuse(harness, receipt, backend, seam, scratch, monkeypatch, *, receipt_path):
    sdk, engine = crysta_reference_prefix(), crysta_reference_source()
    validate_current_inputs(receipt, harness.ROOT, sdk, engine)
    receipt_path = Path(receipt_path)
    assert receipt_path.is_file(), 'Stale-input controls require the actual compiled host receipt'
    assert json.loads(receipt_path.read_text()) == receipt, (
        'Stale-input controls must replay the exact original host receipt at its recorded path'
    )
    key = 'EDI_' + ('THREAD_SELECTOR' if 'thread_selector' in harness.__name__ else 'SCAN_SCREEN')
    monkeypatch.setenv(key + '_' + backend.upper() + '_RECEIPT', str(receipt_path))
    if seam == 'entry':
        private = copy_inputs(harness.ROOT, scratch / 'app', receipt['production'])
        replace_valid_source(private / 'app/main.cpp')
        monkeypatch.setattr(harness, 'ROOT', private)
    elif seam == 'sdk-source':
        private = copy_inputs(
            engine, scratch / 'engine', receipt['compiled_inputs']['sdk']['sources']
        )
        changed = next(
            name for name in receipt['compiled_inputs']['sdk']['sources'] if name.endswith('.cpp')
        )
        replace_valid_source(private / changed)
        monkeypatch.setattr(harness, 'crysta_reference_source', lambda: private)
    else:
        names = ['.crysta-sha', 'share/crysta-sdk/manifest.json', 'lib/libcrysta_core.a']
        names += ['include/' + name for name in receipt['compiled_inputs']['sdk']['headers']]
        private = copy_inputs(sdk, scratch / 'sdk', names)
        if seam == 'sdk-header':
            changed = next(iter(receipt['compiled_inputs']['sdk']['headers']))
            replace_valid_source(private / 'include' / changed)
        else:
            library = private / 'lib/libcrysta_core.a'
            library.unlink()
            shutil.copyfile(sdk / 'lib/libcrysta_core.a', library)
            compiler, ar = shutil.which('cc'), shutil.which('ar')
            assert compiler and ar, (
                'Library reuse control requires its actual native archive tools'
            )
            marker = scratch / 'receipt-control.o'
            subprocess.run(
                [compiler, '-x', 'c', '-c', '-o', str(marker), '-'],
                input='void receipt_control_unused(void) {}\n',
                text=True,
                check=True,
            )
            subprocess.run([ar, 'r', str(library), str(marker)], check=True)
        monkeypatch.setattr(harness, 'crysta_reference_prefix', lambda: private)
    with pytest.raises(RuntimeError, match='stale current production or selected SDK inputs'):
        harness.observation(backend, scratch / 'reused')
