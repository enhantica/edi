# SPDX-License-Identifier: BSD-3-Clause
"""Recorded grouped flag changes after a fit and a shared-site relation."""

import importlib.util
import json
import shutil
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'native_driver', ROOT / 'tests/system/py/test_e11_t5_dev_native_integration.py'
)
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


def _calls(parameters):
    profile = [p['path'] for p in parameters if p['category'] == 'peak']
    adps = [p for p in parameters if p['field'] == 'adp_iso']
    independent = [p['path'] for p in adps if p['row_label'] in {'Ba', 'Co', 'O'}]
    assert len(profile) == 5 and len(adps) == 4 and len(independent) == 3, (
        'Grouped flag scenarios must cover all profile and independent site members.'
    )

    def flags(paths, free):
        return [{'path': path, 'free': free} for path in paths]

    return [
        DRIVER.tool_call(
            'edit_relation',
            'remove-starting-relation',
            id='biso_Ba',
            operation='constraint_remove',
        ),
        DRIVER.tool_call(
            'set_free', 'fix-starting-adps', flags=flags([p['path'] for p in adps], False)
        ),
        DRIVER.tool_call('set_free', 'fix-profile', flags=flags(profile, False)),
        DRIVER.tool_call('set_free', 'release-profile', flags=flags(profile, True)),
        DRIVER.tool_call('run_fit', 'profile-fit'),
        DRIVER.tool_call(
            'add_relations',
            'share-site',
            aliases=[],
            constraints=[
                {
                    'id': 'shared_site',
                    'expression': 'biso_La = biso_Ba',
                    'enabled': True,
                }
            ],
        ),
        DRIVER.tool_call('set_free', 'release-independent-adps', flags=flags(independent, True)),
        DRIVER.tool_call('run_fit', 'adp-fit'),
        DRIVER.tool_call('set_free', 'fix-independent-adps', flags=flags(independent, False)),
        DRIVER.tool_call('save_project', 'save-result', destination='current'),
        DRIVER.tool_call('run_fit', 'fit-before-background-followups'),
        DRIVER.tool_call(
            'edit_background',
            'position-background-ids',
            experiment='hrpt',
            operation='name_from_positions',
        ),
        DRIVER.tool_call('estimate_background', 'estimate-after-fit', experiment='hrpt'),
    ]


def _results(actor, count):
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        row = actor.command('inspect')
        responses = actor.responses()
        if len(responses) == count and row['ui']['state'] == 'idle':
            return [json.loads(r['result']['contentItems'][0]['text']) for r in responses]
        time.sleep(0.2)
    raise AssertionError('The recorded grouped flag sequence did not settle')


@contextmanager
def _project_actor(tmp_path, monkeypatch, show_actions):
    sources = ROOT / 'tests/fixtures/online_sources'
    monkeypatch.setenv(
        'EDI_ONLINE_SOURCES',
        f'cod={(sources / "cod").as_uri()}/;'
        f'easydiffraction={(sources / "easydiffraction").as_uri()}/',
    )
    project = tmp_path / 'project'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project', project)
    analysis = project / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace(
            '_minimizer.max_iterations 1000', '_minimizer.max_iterations 2'
        )
    )
    binary = ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe'
    actor = DRIVER.MainActor(binary, tmp_path, {'turns': [[]]}, show_actions)
    try:
        assert actor.command('open', path=str(project))['reply']['opened'], (
            'The grouped flag scenario must open its project before native actions.'
        )
        actor.until(lambda row: not row['ui']['project']['calculating'])
        yield actor
    finally:
        actor.close()


def _run(actor, calls):
    actor.configure_turns([calls])
    actor.connect()
    actor.until(
        lambda row: (
            DRIVER.qml(actor, 'Session.assistant.draftAdmissionReady')
            and any(
                c['name'] == 'statusBar.fit.button'
                and c['enabled']
                and c['visible']
                and c['input_reachable']
                for c in row['ui']['controls']
            )
        ),
        seconds=30,
    )
    actor.command(
        'evaluate', expression='Session.assistant.send("Execute the recorded sequence.")'
    )
    return _results(actor, len(calls))


@pytest.mark.parametrize('show_actions', [False, True], ids=['normal', 'shown'])
def test_grouped_adp_flags_after_fit_and_relation(tmp_path, monkeypatch, show_actions):
    with _project_actor(tmp_path, monkeypatch, show_actions) as actor:
        calls = _calls(actor.last['ui']['project']['parameters'])
        results = _run(actor, calls)
        assert results[4]['adopted'] and results[5]['status'] == 'edited', (
            'Grouped adp flags after fit and relation.'
        )
        assert results[6]['status'] == 'edited', (
            'Grouped adp flags after fit and relation.',
            results[6],
        )
        assert results[7]['adopted'], 'Grouped adp flags after fit and relation.'
        assert results[8]['status'] == 'edited', (
            'Grouped adp flags after fit and relation.',
            results[8],
        )
        assert results[9]['committed'], ('Grouped adp flags after fit and relation.', results[9])
        assert results[10]['adopted'], 'Grouped adp flags after fit and relation.'
        assert all(r['result']['success'] for r in actor.responses()), (
            'Grouped adp flags after fit and relation.',
            results,
        )
        parameters = actor.last['ui']['project']['parameters']
        assert all(not p['free'] for p in parameters if p['field'] == 'adp_iso'), (
            'Grouped adp flags after fit and relation.'
        )
        assert any(c['id'] == 'shared_site' for c in actor.last['ui']['project']['constraints']), (
            'Grouped adp flags after fit and relation.'
        )


@pytest.mark.parametrize('show_actions', [False, True], ids=['normal', 'shown'])
def test_prepared_controls_after_fit(tmp_path, monkeypatch, show_actions):
    with _project_actor(tmp_path, monkeypatch, show_actions) as actor:
        calls = [
            DRIVER.tool_call('run_fit', 'fit-before-normal-followups'),
            DRIVER.tool_call(
                'edit_background',
                'position-background-ids',
                experiment='hrpt',
                operation='name_from_positions',
            ),
            DRIVER.tool_call('estimate_background', 'estimate-after-fit', experiment='hrpt'),
            DRIVER.tool_call(
                'edit_experiment',
                'experiment-control-after-fit',
                experiment='hrpt',
                operation='cutoff_fwhm',
                value=9.0,
            ),
            DRIVER.tool_call(
                'edit_structure',
                'structure-control-after-fit',
                structure='lbco',
                operation='rename',
                value='renamed_lbco',
            ),
            DRIVER.tool_call('create_experiment', 'append-experiment-after-fit'),
            DRIVER.tool_call('create_structure', 'append-structure-after-fit'),
        ]
        results = _run(actor, calls)
        assert results[0]['adopted'], 'Prepared controls after fit.'
        assert all(r['result']['success'] for r in actor.responses()), (
            'Prepared controls after fit.',
            results,
        )
        assert actor.last['ui']['project']['structures'] == 2, 'Prepared controls after fit.'
