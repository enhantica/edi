"""Run deliberately wrong inputs through the actual Qt instruments, expecting red."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
APP_TESTS = ROOT / 'tests/unit/app'


def runner():
    override = os.environ.get('EDI_APP_TEST_RUNNER')
    candidates = (
        [Path(override)]
        if override
        else [
            ROOT / 'build/app/app/edi_app_tests',
            ROOT / 'build/app/edi_app_tests',
        ]
    )
    binary = next((path for path in candidates if path.is_file()), None)
    assert binary is not None, 'I3/I10: app-build must produce the Qt Quick Test runner'
    return binary


@pytest.fixture(scope='module')
def owner_amendment_run():
    # One real Qt host supplies all independently required boundary receipts.
    # Record its launch and GUI exercise once with the module-cost instrument.
    return subprocess.run(
        [str(runner()), '-input', str(APP_TESTS / 'tst_e04_t1_amendments.qml'), '-o', '-,txt'],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_owner_amendments_execute_in_the_production_qml_host(owner_amendment_run):
    run = owner_amendment_run
    output = run.stdout + run.stderr
    assert run.returncode == 0, (
        f'owner amendments: editability, X-rays and categories work in the real app: {output}'
    )
    assert 'E04T1OwnerAmendments' in output and '0 failed' in output, (
        'owner amendments: a zero-test run cannot attest the new QML acceptance cases'
    )


@pytest.mark.parametrize(
    'boundary',
    [
        'test_library_settable_scalars_and_derived_readonly',
        'test_library_settable_table_columns_reach_core',
        'test_settable_fields_are_editable_in_the_page',
        'test_visible_xray_and_background_selectors_and_no_split_groups',
    ],
)
def test_owner_amendment_receipts_cover_every_original_gui_boundary(owner_amendment_run, boundary):
    output = owner_amendment_run.stdout + owner_amendment_run.stderr
    assert f'PASS   : edi_app::E04T1OwnerAmendments::{boundary}()' in output, (
        'each original GUI boundary must actually execute and pass in the production host: '
        + boundary
    )


@pytest.mark.parametrize('escape', ['missing_property', 'broad_notifications'])
def test_runtime_escape_reaches_the_same_assertions(tmp_path, escape):
    (tmp_path / 'escapes').mkdir()
    shutil.copy(APP_TESTS / 'SignalContract.js', tmp_path / 'SignalContract.js')
    shutil.copy(APP_TESTS / 'escapes' / (escape + '.qml'), tmp_path / 'escapes/tst_escape.qml')
    run = subprocess.run(
        [str(runner()), '-input', str(tmp_path / 'escapes'), '-o', '-,txt'],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = run.stdout + run.stderr
    assert run.returncode != 0, (
        'I3/I10: the intentionally broken fixture must fail the real Qt test'
    )
    assert 'FAIL!' in output and 'E04' in output, (
        'I3/I10: refusal must reach the Qt assertion, not fail to launch'
    )
    if escape == 'missing_property':
        assert 'e04MissingProperty' in output or 'Unable to assign' in output, (
            'I10: the missing view-model property reaches the warning channel'
        )
    else:
        assert 'test_every_property' in output and 'test_whole_object' in output, (
            'I3: both broad-notification escape channels execute'
        )
        assert 'I3 unexpected signal set' in output, (
            'I3: production signal predicate detects the widened notification set'
        )


def test_missing_property_fails_the_production_qmllint_import_context():
    override = os.environ.get('EDI_APP_QMLLINT')
    candidates = (
        [Path(override)]
        if override
        else [
            ROOT / '.pixi/envs/app/bin/qmllint',
            ROOT / '.pixi/envs/app/lib/qt6/bin/qmllint',
            ROOT / '.pixi/envs/default/bin/qmllint',
        ]
    )
    binary = next((path for path in candidates if path.is_file()), None)
    assert binary is not None, 'I10: app environment supplies qmllint'
    imports = os.environ.get('QML_IMPORT_PATH', str(ROOT / 'build/app/qml'))
    command = [str(binary), '-E']
    for directory in imports.split(os.pathsep):
        command += ['-I', directory]
    command.append(str(APP_TESTS / 'escapes/missing_property_lint.qml'))
    run = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    output = run.stdout + run.stderr
    assert run.returncode != 0, 'I10: qmllint must fail on an unknown registered view-model member'
    assert 'e04MissingProperty' in output, 'I10: lint failure names the missing member'
    assert 'Failed to import edi.app' not in output, (
        'I10: the negative control must resolve the actual app module'
    )
