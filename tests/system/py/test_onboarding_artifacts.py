"""Artifact and launcher contracts independent of an application test host."""

import json
import os
import subprocess
from pathlib import Path

import yaml

from tests.fixtures.native_process import environment_bash

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('EDI_ONBOARDING_SOURCE_ROOT', ROOT))


def test_citation_placeholder_has_one_machine_readable_source():
    path = SOURCE / 'CITATION.cff'
    assert path.is_file(), 'The placeholder citation has one committed CITATION.cff source'
    citation = yaml.safe_load(path.read_text())
    assert isinstance(citation, dict), 'The citation source is a structured CFF document'
    for field in ['cff-version', 'message', 'title', 'authors', 'doi']:
        assert citation.get(field), (
            'The shared placeholder citation contains every required citation field'
        )
    assert str(citation['doi']).startswith('10.'), 'The placeholder DOI retains a DOI-shaped value'
    assert 'placeholder' in json.dumps(citation).lower(), (
        'The temporary citation identifies itself as a placeholder '
        'until the real citation is supplied'
    )


def test_capture_launcher_forwards_native_contract_without_a_display(tmp_path):
    launcher = SOURCE / 'tools/docs/capture-gui.sh'
    assert launcher.is_file(), (
        'The documentation capture launcher is available from the main source tree'
    )
    executable = tmp_path / 'capture-target'
    executable.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "$EDI_CAPTURE_WIDTH" "$EDI_CAPTURE_HEIGHT" "$@" '
        '> "$ONBOARDING_LAUNCH_RECEIPT"\n',
        newline='\n',
    )
    executable.chmod(0o755)
    receipt = tmp_path / 'receipt.txt'
    output = tmp_path / 'bundle with spaces'
    script = tmp_path / 'walkthrough with spaces.js'
    run = subprocess.run(
        [environment_bash(), str(launcher), str(output), '--docs-script', str(script)],
        cwd=tmp_path,
        env={
            **os.environ,
            'EDI_DOCS_APP': str(executable),
            'QT_QPA_PLATFORM': 'offscreen',
            'ONBOARDING_LAUNCH_RECEIPT': str(receipt),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert run.returncode == 0, (
        'The launcher runs the injected native executable without a display: ' + run.stderr
    )
    assert receipt.read_text().splitlines() == [
        '1480',
        '800',
        '--docs-capture',
        str(output),
        '--docs-script',
        str(script),
    ], (
        'The launcher preserves preview dimensions, mode, argument boundaries '
        'and the selected walkthrough'
    )


def test_capture_launcher_refuses_missing_app_and_missing_destination(tmp_path):
    launcher = SOURCE / 'tools/docs/capture-gui.sh'
    assert launcher.is_file(), 'The capture refusal gate requires the main-tree capture launcher'
    for arguments in [[], [str(tmp_path / 'output')]]:
        run = subprocess.run(
            [environment_bash(), str(launcher), *arguments],
            env={**os.environ, 'EDI_DOCS_APP': str(tmp_path / 'no-such-app')},
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        assert run.returncode != 0, (
            'The capture launcher rejects absent required input or an absent app'
        )


def test_tutorial_scripts_declare_isolated_project_lifecycle():
    manifest = SOURCE / 'app/tutorials/manifest.json'
    assert manifest.is_file(), (
        'All case tutorials and the auxiliary tour share a declarative manifest'
    )
    tutorials = json.loads(manifest.read_text())['tutorials']
    expected = json.loads((ROOT / 'tests/fixtures/tutorial_cases/app-tutorials.json').read_text())[
        'required'
    ]
    assert len(tutorials) == len(expected) and {item['id'] for item in tutorials} == set(
        expected
    ), 'The built-in catalogue contains exactly the Interface tour and one tutorial per app case'
    for tutorial in tutorials:
        steps = tutorial.get('steps')
        if steps is None:
            pages = json.loads((manifest.parent / tutorial['tour']).read_text())['pages']
            steps = [step for page in pages for step in page['steps']]
        assert steps, 'Every built-in tutorial contains written steps'
        for step in steps:
            assert all(
                isinstance(step.get(field), str) and step[field].strip()
                for field in (['text', 'target'])
            ), (
                'Every step describes its real control; '
                'case actions are exercised against their independent recipe gates'
            )
        assert tutorial['project'] == 'temporary', 'Every tutorial uses its own temporary project'
        assert tutorial['stop'] == 'restore-user-project', (
            'Stopping any tutorial restores the user project'
        )
        if tutorial['id'] == 'interface':
            assert tutorial['start'] == 'example:pd-neut-cwl_lbco-hrpt', (
                'The Interface tour opens the LBCO example in its temporary project'
            )
            continue
        assert tutorial['completion'] == ['keep', 'discard'], (
            'A completed scientific tutorial offers Keep this project and Discard'
        )
        assert tutorial['stop'] == 'restore-user-project', (
            'Stopping a scientific tutorial returns to the user project'
        )
