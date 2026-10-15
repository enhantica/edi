"""Shared manual FitJob atomicity, qualified by actual single/joint optimizer movement."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('mode', ['single', 'joint'])
@pytest.mark.parametrize('armed', [False, True], ids=['positive', 'allocation-after-live-write'])
def test_real_fit_publication_is_complete_or_preserves_exact_original_before_callback(mode, armed):
    # Accident: live writes precede allocating record/cache preparation.
    value = os.environ.get('EDI_ASSISTANT_FIT_PUBLICATION_PROBE')
    binary = (
        Path(value)
        if value
        else ROOT / 'build/assistant-core-tests/assistant_fit_publication_probe'
    )
    assert binary.is_file(), (
        'I4/I6/S5: atomic-publication witness links the real public shared FitJob'
    )
    source = (
        ROOT
        / 'docs/user/cli'
        / (
            'pd-neut-cwl_cosio-d20_start-1'
            if mode == 'single'
            else 'pd-neut-tof_ferrite-austenite-beer_joint'
        )
        / 'project'
    )
    completed = subprocess.run(
        [str(binary), str(source), 'armed' if armed else 'positive'],
        capture_output=True,
        text=True,
        timeout=12,
        check=False,
    )
    assert completed.returncode == 0, (
        'I10/S5: genuine fit and owner publication return a bounded observer result'
    )
    observed = json.loads(completed.stdout)
    assert observed['started'], (
        'I8/S5: fault monitoring follows an actual admitted native optimizer job'
    )
    assert not observed['escaped'], (
        'I4/I10/S5: publication allocation failures cannot escape owner delivery'
    )
    assert observed['finished_count'] == 1 and not observed['running'], (
        'I10/S5: real completion is reported exactly once even on a publication fault'
    )
    if not armed:
        assert observed['moved'] and observed['complete_publication'], (
            'I8/S5: positive FitJob moves real values with complete current patterns and result'
        )
        assert observed['before'] != observed['after'], (
            'I6/S5: independent exact-state observation detects genuine normal publication'
        )
    else:
        assert observed['before'] == observed['after'] or observed['complete_publication'], (
            'I4/I6/S5: allocation escape leaves exact original state or complete publication'
        )
        assert observed['fault_fired'] or observed['complete_publication'], (
            'I4/S5: post-write allocation fault fires or the illegal window is absent'
        )
