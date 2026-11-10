"""The CLI permits saved Auto fit flags and refuses structural or value edits."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import edi as engine
import pytest

from tests.fixtures.background_estimate.readonly import KINDS, edit_saved, snapshot
from tests.fixtures.background_estimate.series import project as series_project
from tests.fixtures.background_estimate.settings import (
    DEFAULTS,
    configured_project,
    write_settings,
)

ROOT = Path(__file__).resolve().parents[3]


def files(project):
    return {
        str(path.relative_to(project)): path.read_bytes()
        for path in project.rglob('*')
        if path.is_file()
    }


def calculate(project):
    command = [sys.executable, '-m', 'edi', 'calc', str(project)]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=2,
        check=False,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('field', ['id', 'coordinate', 'value', 'free', 'add', 'remove'])
def test_cli_allows_saved_auto_free_toggles_and_requires_manual_for_other_edits(
    tmp_path, kind, field
):
    source = (
        configured_project(tmp_path / 'input')
        if kind == 'line-segment'
        else series_project(tmp_path / 'input', kind)
    )
    write_settings(
        source,
        {
            **DEFAULTS,
            'mode': 'manual',
            'method': 'arpls',
            'width': 6,
            'smoothness': 1000,
            'max_terms': 6,
            'n_points': 9,
        },
    )
    project = engine.Project.load(source)
    project.experiment.background_estimate.mode = 'auto'
    project.analysis.calculate()
    saved = tmp_path / 'saved'
    project.save_as(saved)
    text = (saved / 'experiments/bank.edi').read_text()
    assert '_background_estimate.points_digest' in text, (
        'The external-edit control must carry independently exercised saved point provenance'
    )
    assert len(snapshot(project)) >= 2, (
        'The CLI edit control must retain multiple actual saved rows'
    )
    original = snapshot(project)
    edit_saved(saved, kind, field)
    before = files(saved)
    result = calculate(saved)
    # Before: a saved free-flag change was refused. After: it remains valid in Auto.
    if field == 'free':
        assert result.returncode == 0, (
            'The ordinary CLI must accept an Auto free/fixed toggle: ' + result.stderr
        )
        accepted_auto = engine.Project.load(saved)
        expected_auto = [(*original[0][:-1], not original[0][-1]), *original[1:]]
        assert snapshot(accepted_auto) == expected_auto, (
            'CLI calculation must keep the Auto flag change, ids, coordinates and values'
        )
        assert accepted_auto.experiment.background_estimate.mode == 'auto', (
            'An accepted CLI free/fixed toggle must keep the stored estimation mode Auto'
        )
    else:
        assert result.returncode > 0, (
            'The CLI must refuse an edited Auto row value or structure before calculation or save'
        )
        assert 'manual' in (result.stdout + result.stderr).lower(), (
            'CLI refusal must say to select Manual before changing background values or rows'
        )
        assert files(saved) == before, (
            'A refused Auto CLI edit must preserve every input and output byte'
        )
    manual = tmp_path / 'manual'
    shutil.copytree(saved, manual)
    path = manual / 'experiments/bank.edi'
    path.write_text(
        path.read_text().replace(
            '_background_estimate.mode auto', '_background_estimate.mode manual'
        )
    )
    expected = snapshot(engine.Project.load(manual))
    accepted = calculate(manual)
    assert accepted.returncode == 0, (
        'The same authored row change must calculate after explicit Manual selection: '
        + accepted.stderr
    )
    assert snapshot(engine.Project.load(manual)) == expected, (
        'The Manual CLI must preserve edited row ids, coordinates, values and free flags'
    )
