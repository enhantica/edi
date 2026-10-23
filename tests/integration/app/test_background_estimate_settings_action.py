"""Saved automatic projects agree across actual app, CLI and Python entry points."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tests.fixtures.background_estimate.settings import (
    app_cases,
    points,
    read_settings,
    saved_points,
)

ROOT = Path(__file__).resolve().parents[3]


PROVENANCE = {'inputs_digest', 'points_digest'}


def require_settings_receipt(actual, expected):
    # Before: exactly the line-segment user settings. After: the same values,
    # a blank series-only max_terms, plus the
    # two saved provenance digests; no unknown fields or filled-in blank defaults.
    assert set(actual) == set(expected) | PROVENANCE, (
        'The saved estimate category must contain exactly its user settings '
        'and both provenance digests'
    )
    assert {key: actual[key] for key in expected} == expected, (
        'Saving provenance must preserve every user setting, including blank derived overrides'
    )
    provenance = {key: actual[key] for key in PROVENANCE}
    assert all(
        isinstance(value, str) and re.fullmatch(r'[0-9a-f]{16}', value) and int(value, 16) != 0
        for value in provenance.values()
    ), 'Both saved provenance digests must be nonzero fixed-width hexadecimal strings'
    return provenance


def persisted_provenance(project, expected):
    text = (project / 'experiments/bank.edi').read_text()
    pairs = re.findall(r'(?m)^_background_estimate\.([a-z_]+)\s+(\S+)', text)
    raw = dict(pairs)
    assert len(raw) == len(pairs), (
        'A saved estimate category must not contain duplicate setting or provenance tags'
    )
    assert set(raw) <= set(expected) | PROVENANCE, (
        'The saved file must not introduce unknown estimate settings or provenance tags'
    )
    assert set(raw) >= PROVENANCE, (
        'The saved file must retain both provenance tags even when blank overrides are omitted'
    )
    return require_settings_receipt(
        {**read_settings(project), **{key: raw[key] for key in PROVENANCE}}, expected
    )


@pytest.fixture(scope='module')
def settings_actor():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Saved-settings acceptance requires the built production Qt host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_estimate_settings.qml'),
            'BackgroundEstimateSettings::test_saved_auto_project_matches_reference',
            'BackgroundEstimateSettings::test_main_choice_and_extra_overrides_are_real_saved_controls',
            'BackgroundEstimateSettings::test_blank_defaults_and_derived_hint_survive_save_reload',
            'BackgroundEstimateSettings::test_point_keyboard_edit_sets_manual',
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


@pytest.mark.parametrize('case', ['auto-derived', 'auto-overrides'])
def test_saved_auto_app_cli_python_points_are_identical(settings_actor, case, tmp_path):
    status, output = settings_actor
    assert status == 0, (
        'Saved auto mode, Main/Extra controls and manual point edits must pass in the Qt host:\n'
        + output
    )
    receipts = [
        json.loads(row) for row in re.findall(r'BACKGROUND_SETTINGS_RECEIPT (\{[^\n]+\})', output)
    ]
    matches = [row for row in receipts if row['case'] == case]
    assert len(matches) == 1, (
        'Each saved auto input must produce one completed app calculation receipt'
    )
    settings = app_cases()[case]['settings']
    provenance = require_settings_receipt(matches[0]['settings'], settings)
    source = ROOT / 'tests/fixtures/background_estimate/projects' / case
    project = edi.Project.load(source)
    project.analysis.calculate()
    expected = [list(row[:2]) for row in points(project)]
    assert matches[0]['points'] == expected, (
        'The app and Python must calculate exactly the same saved automatic points'
    )
    python_save = tmp_path / 'python'
    project.save_as(python_save)
    assert persisted_provenance(python_save, settings) == provenance, (
        'App and Python must persist identical input and point provenance for the same estimate'
    )
    cli = tmp_path / 'cli'
    import shutil  # noqa: PLC0415

    shutil.copytree(source, cli)
    result = subprocess.run(
        [sys.executable, '-m', 'edi', 'calc', str(cli)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, (
        'The existing CLI must consume the same saved automatic project: ' + result.stderr
    )
    assert [list(row) for row in saved_points(cli)] == expected, (
        'App, CLI and Python must produce identical points from one saved project'
    )
    assert persisted_provenance(cli, settings) == provenance, (
        'CLI, Python and app must retain identical settings and both provenance digests'
    )


def test_main_extra_controls_and_hand_edit_reach_saved_state(settings_actor):
    status, output = settings_actor
    assert status == 0, (
        'Actual Main/Extra settings and point edits must complete in the app:\n' + output
    )
    assert 'BACKGROUND_SETTINGS_UI ' in output, (
        'The actor must commit every Main and Extra setting through real input'
    )
    ui = re.findall(r'BACKGROUND_SETTINGS_UI (\{[^\n]+\})', output)
    assert len(ui) == 1, 'The Extra controls must produce one completed saved-settings receipt'
    assert json.loads(ui[0])['tolerance'] == pytest.approx(0.75, rel=0, abs=0), (
        'The real Extra tolerance editor must save the nondefault noise multiplier exactly'
    )
    controls = re.findall(r'BACKGROUND_MODEL_CONTROL (\{[^\n]+\})', output)
    assert len(controls) == 1, (
        'The real saved policy selector must emit one completed control receipt'
    )
    control = json.loads(controls[0])
    assert (
        control['objectName'] == 'background_estimate.use_model'
        and control['use_model'] == 'subtract'
    ), 'The stable background_estimate.use_model selector must write the canonical saved policy'
    assert control['label'].strip().lower() == 'calculated peaks', (
        'The stable policy selector must carry the public Calculated peaks label'
    )
    assert 'BACKGROUND_SETTINGS_MANUAL true' in output, (
        'The actor must save manual mode after a real point edit'
    )


def test_blank_app_defaults_and_derived_hint_survive_two_saves(settings_actor):
    status, output = settings_actor
    assert status == 0, (
        'The real app must save and reload blank twice-noise/automatic-model defaults: ' + output
    )
    assert (
        'BACKGROUND_BLANK_DEFAULTS tolerance=2 use_model=auto in_peaks=move saves=2' in output
    ), (
        'The app must display whole-number hint 2, automatic calculated-peak selection and move, '
        'while retaining blank tolerance through both saves'
    )


@pytest.mark.parametrize(
    'damage',
    [
        'missing-inputs',
        'missing-points',
        'zero',
        'bad-hex',
        'short',
        'number',
        'extra',
        'changed-option',
        'filled-blank',
    ],
)
def test_saved_settings_receipt_refuses_partial_or_weakened_categories(damage):
    expected = app_cases()['auto-derived']['settings']
    receipt = {
        **expected,
        'inputs_digest': '1234567890abcdef',
        'points_digest': 'fedcba0987654321',
    }
    if damage == 'missing-inputs':
        del receipt['inputs_digest']
    elif damage == 'missing-points':
        del receipt['points_digest']
    elif damage == 'zero':
        receipt['inputs_digest'] = '0' * 16
    elif damage == 'bad-hex':
        receipt['points_digest'] = 'g' * 16
    elif damage == 'short':
        receipt['points_digest'] = '1234'
    elif damage == 'number':
        receipt['points_digest'] = 123
    elif damage == 'extra':
        receipt['unreviewed'] = 'extra'
    elif damage == 'changed-option':
        receipt['method'] = 'snip' if receipt['method'] != 'snip' else 'arpls'
    else:
        receipt['width'] = 7.25
    with pytest.raises(AssertionError, match=r'saved|Saving|Both'):
        require_settings_receipt(receipt, expected)
