# SPDX-License-Identifier: BSD-3-Clause
"""Legacy settings migration exercised through the production Qt functions."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.settings_identity.prepare import identity, prepare

ROOT = Path(__file__).resolve().parents[3]


def run_probe(tmp_path, scenario):
    build = Path(os.environ.get('EDI_SETTINGS_PROBE_DIR', ROOT / 'build/settings-identity'))
    expected = tmp_path / 'provider'
    prepare(ROOT, expected)
    assert (build / 'settings_provider.inc').is_file(), (
        'ADR-0091: settings coverage requires the prepared native Qt probe'
    )
    assert (build / 'settings_provider.inc').read_bytes() == (
        expected / 'settings_provider.inc'
    ).read_bytes(), (
        'ADR-0091: the native probe must compile the current complete production functions'
    )
    binary = build / (
        'settings_identity_probe.exe' if os.name == 'nt' else 'settings_identity_probe'
    )
    assert binary.is_file(), 'ADR-0091: build the native settings prerequisite before this gate'
    assert (build / 'identity.json').is_file(), (
        'ADR-0091: native migration requires a stamped build prerequisite'
    )
    assert json.loads((build / 'identity.json').read_text()) == identity(ROOT, build), (
        'ADR-0091: the native artifact must match its current provider, fixture and binary bytes'
    )
    home = tmp_path / 'home'
    home.mkdir()
    env = {
        **os.environ,
        **{
            key: str(home)
            for key in [
                'HOME',
                'USERPROFILE',
                'APPDATA',
                'LOCALAPPDATA',
                'XDG_CONFIG_HOME',
                'XDG_DATA_HOME',
            ]
        },
    }
    result = subprocess.run(
        [str(binary), str(tmp_path / 'settings'), scenario],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, (
        'ADR-0091: migration executes against isolated settings and data folders: ' + result.stderr
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize('scenario', ['missing', 'zero-byte'])
def test_empty_destination_carries_typed_unicode_preferences(tmp_path, scenario):
    result = run_probe(tmp_path, scenario)
    assert result['organisation'] == 'EasyDiffraction', (
        'ADR-0091: persisted settings use the project-owned organisation'
    )
    assert result['values'] == {
        'edi/feedbackName': 'Zoë Example',
        'edi/feedbackEmail': 'zoe@example.invalid',
        'edi/toolTipDelay': 1739,
        'edi/autoCollapse': False,
    }, 'ADR-0091: migration retains all legacy Unicode, text, integer and boolean preferences'
    assert result['legacy_exists'] and result['legacy_name'] == 'Zoë Example', (
        'ADR-0091: migration preserves the original store for existing users'
    )


def test_any_populated_destination_wins_over_legacy(tmp_path):
    result = run_probe(tmp_path, 'populated')
    assert result['values'] == {'destination-only': 2718}, (
        'ADR-0091: a populated destination is never overwritten or merged from legacy settings'
    )


def test_migration_does_not_repeat_on_later_calls(tmp_path):
    values = run_probe(tmp_path, 'repeat')['values']
    assert values['edi/toolTipDelay'] == 1739 and values['edi/feedbackName'] == 'Current User', (
        'ADR-0091: later legacy edits cannot replace migrated values or current user choices'
    )


def test_no_legacy_store_does_not_create_settings(tmp_path):
    result = run_probe(tmp_path, 'no-legacy')
    assert result['values'] == {} and not result['current_exists'], (
        'ADR-0091: a new user with no legacy store keeps normal first-start defaults'
    )


def test_fresh_test_or_demo_does_not_migrate_user_preferences(tmp_path):
    result = run_probe(tmp_path, 'fresh')
    assert result['values'] == {} and not result['current_exists'], (
        'ADR-0091: demo and test settings isolation prevents legacy preference migration'
    )
