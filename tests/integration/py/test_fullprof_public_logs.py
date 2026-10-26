"""Capture stdout privately enough to publish, retaining the independent numerical evidence."""

import importlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def capture(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tests/fixtures/example_catalogue'))
    return importlib.import_module('run_fullprof')


def test_authoring_capture_scrubs_paths_and_preserves_program_evidence(
    tmp_path, monkeypatch, capture
):
    case = tmp_path / 'example'
    logs = tmp_path / 'logs'
    case.mkdir()
    logs.mkdir()
    executable = Path.home() / 'Applications/fullprof/fp2k'
    numeric = 'Convergence reached at this CYCLE\nRwp: 1.70\n'

    def program(argv, **kwargs):
        assert argv == [str(executable)] and kwargs['cwd'] == case, (
            'The capture must execute the requested program in its case directory'
        )
        kwargs['stdout'].write(f'Executable: {executable}\n' + numeric)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, 'run', program)
    assert capture.execute(executable, case, 'fit', logs) == 0, (
        'Sanitizing a capture must preserve the actual program exit status'
    )
    text = (logs / 'example-fit.log').read_text()
    assert str(executable) not in text and str(case) not in text, (
        'A captured program log must not expose absolute executable or case paths'
    )
    assert 'fit.pcr' in text and 'fp2k' in text and numeric in text, (
        'Public logs must retain the input name, executable name and numerical output'
    )
    assert (logs / 'example-fit.exit').read_text() == '0\n', (
        'Public capture must keep its separate exit receipt'
    )
    older = logs / 'older.log'
    older.write_text(f'Executable: {executable}\n' + numeric)
    published = logs / 'published.log'
    importlib.import_module('capture_logs').copy_public_log(older, published)
    assert str(executable) not in published.read_text() and numeric in published.read_text(), (
        'Publishing an older capture must scrub its paths and preserve its program evidence'
    )


def test_every_committed_fullprof_log_is_scrubbed_and_its_receipt_matches(capture, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools/public-release'))
    scrub = importlib.import_module('scrub')
    markers = importlib.import_module('patterns').RESIDUE_LITERALS['personal path']
    homes = [ROOT / f'knowledge/{kind}/fullprof' for kind in ['fitting', 'verification']]
    logs = [path for home in homes for path in home.rglob('*.log')]
    assert logs, 'The publication check must reach the retained FullProf capture logs'
    for path in logs:
        text = path.read_text()
        sanitized = scrub.personal(text) if any(marker in text for marker in markers) else text
        assert sanitized == text, (
            'Every retained FullProf log must already satisfy the canonical public scrub'
        )
    for home in homes:
        for receipt in home.rglob('reference.json'):
            record = json.loads(receipt.read_text())
            for field in ['artifacts_sha256', 'twin_artifacts_sha256', 'fixed_twin_sha256']:
                if field not in record:
                    continue
                folder = receipt.parent
                if field in {'twin_artifacts_sha256', 'fixed_twin_sha256'}:
                    folder = (
                        ROOT / 'knowledge/verification/fullprof' / folder.relative_to(homes[0])
                    )
                for name, expected in record.get(field, {}).items():
                    if name.endswith('.log'):
                        assert capture.digest(folder / name) == expected, (
                            'Sanitized logs must retain an exact digest in their reference receipt'
                        )
