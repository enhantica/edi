"""The real undo command publishes only reader-admissible scientific values."""

import re
import subprocess
import sys

import edi
import pytest

from tests.integration.py.test_report_iucr_persistence import project
from tests.integration.py.test_report_storage import inventory


@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
@pytest.mark.parametrize('angle', ['angle_alpha', 'angle_beta', 'angle_gamma'])
@pytest.mark.parametrize('uncertainty', [3.0, 0.003], ids=['endpoint', 'ordinary'])
def test_cli_snapshot_restore_cannot_publish_unreadable_cell(tmp_path, rule, angle, uncertainty):
    path = project(tmp_path, '4()', rule)
    structure = path / 'structures/phase.edi'
    structure.write_text(
        re.sub(r'(_cell\.' + angle + r'\s+)\S+', r'\g<1>90()', structure.read_text())
    )
    analysis = path / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text() + '\nloop_\n_fit_parameter.id\n_fit_parameter.start_value\n'
        '_fit_parameter.start_uncertainty\n_fit_parameter.start_tied\n'
        f'structure.cell.{angle} 179.99 {uncertainty} .\n'
    )
    loaded = edi.Project.load(path)
    parameter = getattr(loaded.structures[0].cell, angle)
    assert parameter.start_value == 179.99 and parameter.start_uncertainty == uncertainty, (
        'The loader holds the independently authored fit snapshot before the command runs'
    )
    before = inventory(path)
    result = subprocess.run(
        [sys.executable, '-m', 'edi', 'undo', str(path), '--verbosity', 'off'],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode:
        assert uncertainty == 3.0, (
            'Ordinary reader-admissible snapshot rounding must not be refused'
        )
        assert inventory(path) == before, (
            'A CLI rounded-domain refusal must occur before replacing any source bytes'
        )
        return
    try:
        restored = edi.Project.load(path)
    except (ValueError, RuntimeError, OSError) as error:
        pytest.fail(
            'A successful real CLI save must remain inside its loader domain: ' + str(error)
        )
    actual = getattr(restored.structures[0].cell, angle).value
    assert 0 < actual < 180, 'A successful CLI restore retains the strict physical angle domain'
    assert actual == 179.99, (
        'This endpoint witness uses exact fallback or its ordinary rounded value'
    )
