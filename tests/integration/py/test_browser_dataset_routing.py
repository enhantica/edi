"""Actual native folder completion retains its initiating project and experiment."""

import json

import pytest

from tests.fixtures.native_ui_script.runner import run_javascript


@pytest.mark.parametrize(
    ('scenario', 'before', 'deliveries', 'loaded'),
    [
        ('accepted', '', 'deliver(41,"chosen");', True),
        ('duplicate', '', 'deliver(41,"chosen");deliver(41,"duplicate");', True),
        ('stale', '', 'deliver(40,"obsolete");deliver(41,"chosen");', True),
        ('project-replaced', 'group.project=foreign;', 'deliver(41,"chosen");', False),
        ('project-closed', 'group.project=null;', 'deliver(41,"chosen");', False),
        ('session-replaced', 'sessionProject=foreign;', 'deliver(41,"chosen");', False),
        ('target-cleared', 'group.webDataExperiment=null;', 'deliver(41,"chosen");', False),
        ('row-reindexed', 'original.currentExperiment=other;', 'deliver(41,"chosen");', True),
        (
            'cancelled',
            'ApplicationInfo.formFilesCancelled(41,true);',
            'deliver(41,"chosen");',
            False,
        ),
    ],
)
def test_browser_folder_completion_preserves_initiator_and_consumes_once(
    scenario, before, deliveries, loaded
):
    program = """
let calls=[];
const initiator={id:'initiator'};
const other={id:'other'};
const original={currentExperiment:initiator,
  loadDatasetFolder:(target,folder,copy)=>calls.push(['original',target.id,folder,copy])};
const foreign={loadDatasetFolder:(target,folder,copy)=>
  calls.push(['foreign',target.id,folder,copy])};
const group={project:original,webRequest:41,webRequestProject:original,
  webDataExperiment:initiator};
let sessionProject=original;
const Session={get project(){return sessionProject;}};
function deliver(request,folder) {
  ApplicationInfo.formDatasetFolderOpened(request,folder);
}
BEFORE
DELIVERIES
console.log(JSON.stringify({calls,pending:group.webRequest,
  targetCleared:group.webDataExperiment===null}));
""".replace('BEFORE', before).replace('DELIVERIES', deliveries)
    result = run_javascript(program)
    assert result.returncode == 0, (
        'Dataset-folder routing executes the actual native completion owner: '
        + scenario
        + ': '
        + result.stderr
    )
    observed = json.loads(result.stdout)
    expected = [['original', 'initiator', 'chosen', True]] if loaded else []
    assert observed['calls'] == expected, (
        'Dataset completion copies into its initiating project and experiment exactly once; '
        'stale, cancelled, closed or replaced owners cannot receive uploaded data'
    )
    assert observed['pending'] == 0 and observed['targetCleared'], (
        'A matching terminal folder answer consumes its pending request and retained target'
    )
