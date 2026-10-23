"""Retained temporary entries never share an inode with bytes a writer does not own."""

import subprocess
import sys

import edi
import pytest

from tests.fixtures.report_storage import temporary_aliases as alias_fixtures
from tests.fixtures.report_storage.temporary_aliases import (
    ROOT,
    environment,
    plant,
)
from tests.integration.py.test_report_storage import inventory, put, source

alias_failure = alias_fixtures.alias_failure


@pytest.mark.parametrize(
    'surface', ['save', 'save-as', 'core-save', 'python-html', 'cli-save', 'cli-output', 'calc']
)
@pytest.mark.parametrize('alias', ['symbolic', 'hard', 'none'])
@pytest.mark.parametrize('parent', ['owned', 'linked'])
@pytest.mark.parametrize('target', ['outside', 'published'])
@pytest.mark.parametrize('failed', [False, True], ids=['complete', 'refused'])
def test_every_temporary_writer_detaches_retained_aliases(
    tmp_path, alias_failure, surface, alias, parent, target, failed
):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    put(path, 'reports/carried.html', 'carried artifact, independent bytes\n')
    selected_name = edi.Project.load(path).name + '.html'
    if surface == 'calc':
        selected = next((path / 'experiments').glob('*.edi'))
    else:
        selected = (
            path / 'reports' / ('report.edi' if surface in {'save', 'save-as'} else selected_name)
        )
    external, _temporary = plant(path, selected, alias, parent, target)
    outside = inventory(external)
    previous = selected.read_bytes()
    receipt = tmp_path / 'receipt'
    env = environment(alias_failure, selected, receipt, failed)
    if surface in {'core-save', 'python-html'}:
        arguments = [
            sys.executable,
            str(ROOT / 'tests/fixtures/report_storage/temporary_driver.py'),
            surface,
            str(path),
        ]
    elif surface in {'cli-save', 'cli-output'}:
        arguments = [sys.executable, '-m', 'edi', 'report', str(path)]
        if surface == 'cli-output':
            arguments.extend(['--output', str(selected), '--online'])
    elif surface == 'calc':
        arguments = [sys.executable, '-m', 'edi', 'calc', str(path)]
    else:
        code = 'import edi,sys;p=edi.Project.load(sys.argv[1]);p.report.html_offline=True;' + (
            'p.save()' if surface == 'save' else 'p.save_as(sys.argv[2])'
        )
        destination = path if surface == 'save' else tmp_path / 'destination'
        arguments = [sys.executable, '-c', code, str(path), str(destination)]
        # Full staging generates fresh entries; its final swap is the later failure boundary.
        if failed:
            env = environment(alias_failure, destination, receipt, failed=True)
    result = subprocess.run(
        arguments, capture_output=True, text=True, check=False, env=env, timeout=20
    )
    assert inventory(external) == outside, (
        'Every temporary-file write must detach symbolic and hard aliases '
        'before opening, in both parent-placement branches'
    )
    refused = result.returncode != 0 or result.stdout.startswith('refused')
    assert failed or alias != 'none' or not refused, (
        'An unaliased writer completes ordinary successful publication'
    )
    if failed or refused:
        if alias == 'none' and failed:
            assert receipt.exists(), (
                'The unaliased refusal reaches rename after writing the output'
            )
        assert refused, 'An actual replacement failure is reported to its caller'
        assert selected.read_bytes() == previous, (
            'A failed replacement preserves the previously published inode '
            'bytes even when its temporary name aliases them'
        )
    else:
        assert result.returncode == 0, (
            'The ordinary detached publication reaches success: ' + result.stderr
        )
        assert selected.is_file(), 'A successful output is a regular file'
        assert not selected.is_symlink(), 'A successful output owns its final entry'
        if surface != 'save-as':
            assert not selected.parent.is_symlink(), 'A successful writer owns its output parent'
    assert (
        path / 'reports/carried.html'
    ).read_text() == 'carried artifact, independent bytes\n', (
        'Temporary-entry detachment preserves carried artifacts'
    )
