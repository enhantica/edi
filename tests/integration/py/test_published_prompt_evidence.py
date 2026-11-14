"""Published authoring evidence preserves real execution, numerical findings and history."""

import copy
import json
from pathlib import Path

import pytest

from tests.fixtures.tutorial_cases.published_trials import (
    assert_comparisons,
    assert_history,
    assert_published_trial,
    assert_recorded_trial,
    sha256,
)

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'tests/fixtures/tutorial_cases/published_assistant_trials.json'


def evidence():
    return json.loads(EVIDENCE.read_text())


def recapture(document, name, text):
    document['captures'][name] = {'text': text, 'sha256': sha256(text.encode())}


@pytest.mark.parametrize('interface', ['python', 'cli'])
def test_actual_published_trial_retains_execution_and_distinct_scientific_findings(interface):
    document = evidence()
    assert_history(ROOT, document)
    rows = [row for row in document['records'] if row['interface'] == interface]
    assert len(rows) == 1, 'Each current interface retains one actual independent authoring trial'
    row = rows[0]
    assert_published_trial(ROOT, document, row, interface, row['prompt_sha256'])
    assert row['scientific_reference_match'] and not row['single_fit_regression_match'], (
        'Actual reference agreement never overwrites separate single-fit regression mismatches'
    )


@pytest.mark.parametrize(
    'change',
    [
        'wrong-route',
        'wrong-url',
        'changed-prompt',
        'wrong-doc-body',
        'wrong-doc-source',
        'missing-artifact',
        'wrong-artifact-hash',
        'missing-execution',
        'failed-execution',
        'wrong-edi-source',
        'wrong-sdk-source',
        'wrong-binary',
        'false-release-claim',
        'corrupt-capture',
        'missing-comparison',
        'widened-tolerance',
        'invented-result',
        'false-regression-pass',
        'wrong-correlation-sign',
        'missing-uncertainty',
        'duplicate-machine-key',
        'wrong-stage-display',
        'inconsistent-final-capture',
    ],
)
def test_published_authoring_evidence_refuses_forged_or_incomplete_records(change):
    document = copy.deepcopy(evidence())
    interface = 'cli' if change == 'duplicate-machine-key' else 'python'
    row = next(item for item in document['records'] if item['interface'] == interface)
    digest = row['prompt_sha256']
    execution = row['execution']
    comparison = row['comparisons'][-1]
    edits = {
        'wrong-route': (row, 'publication_route', 'unpublished-local-build'),
        'wrong-url': (row, 'prompt_url', 'https://example.invalid/python/tutorials/assistant/'),
        'changed-prompt': (row, 'prompt_sha256', '0' * 64),
        'wrong-doc-body': (row, 'prompt_page_sha256', '0' * 64),
        'wrong-doc-source': (document['documentation'], 'source_commit', '0' * 40),
        'failed-execution': (execution, 'exit_code', 1),
        'wrong-edi-source': (execution, 'edi_source', '0' * 40),
        'wrong-sdk-source': (execution, 'sdk_source', '0' * 40),
        'wrong-binary': (execution, 'binary_sha256', '0' * 64),
        'false-release-claim': (execution, 'claims_released_artifact', True),
        'wrong-artifact-hash': (row['artifact'], 'sha256', '0' * 64),
        'widened-tolerance': (comparison, 'tol_abs', 1),
        'invented-result': (comparison, 'actual', comparison['value']),
        'false-regression-pass': (row, 'single_fit_regression_match', True),
        'wrong-correlation-sign': (row, 'La_Ba_Biso_correlation', 1.0),
    }
    if change in edits:
        target, key, value = edits[change]
        target[key] = value
    elif change in {'missing-artifact', 'missing-execution'}:
        row.pop(change.removeprefix('missing-'))
    elif change == 'corrupt-capture':
        document['captures']['python-result']['text'] += ' '
    elif change == 'missing-comparison':
        row['comparisons'].pop()
    elif change == 'missing-uncertainty':
        stages = json.loads(document['captures']['python-stages']['text'])
        stages[-1]['uncertainties'].pop(next(iter(stages[-1]['uncertainties'])))
        recapture(document, 'python-stages', json.dumps(stages))
    elif change == 'inconsistent-final-capture':
        raw = json.loads(document['captures']['python-result']['text'])
        raw['reduced_chi_square'] = comparison['value']
        comparison['actual'] = comparison['value']
        comparison['matches'] = True
        recapture(document, 'python-result', json.dumps(raw))
    elif change == 'duplicate-machine-key':
        name = row['execution']['stage_captures'][-1]
        recapture(document, name, document['captures'][name]['text'] + 'n_free=15\n')
    else:
        stages = json.loads(document['captures']['python-stages']['text'])
        stages[-1]['rwp'] = 0.2
        recapture(document, 'python-stages', json.dumps(stages))
    with pytest.raises(AssertionError, match='Gate 3/5:'):
        assert_published_trial(ROOT, document, row, interface, digest)


@pytest.mark.parametrize('change', ['erased-attempt', 'changed-failure', 'changed-source'])
def test_current_trials_cannot_rewrite_the_original_failed_export(change):
    document = evidence()
    path = ROOT / 'tests/fixtures/tutorial_cases/assistant_trials.json'
    historical = json.loads(path.read_text())
    if change == 'erased-attempt':
        historical['records'].pop()
    elif change == 'changed-failure':
        historical['records'][0]['status'] = 'passed'
    else:
        historical['source']['sha256'] = '0' * 64
    with pytest.raises(AssertionError, match='Gate 3/5:'):
        assert_history(ROOT, document, json.dumps(historical).encode())


def test_public_summary_cites_current_receipt_and_actual_diagnostic_artifact_sources():
    document = evidence()
    summary = ROOT / 'website/surfaces/docs' / (document['summary_document'] + '.md')
    text = summary.read_text(encoding='utf-8')
    assert sha256(EVIDENCE.read_bytes()) in text, (
        'The published summary cites the exact separately recorded current authoring evidence'
    )
    identities = [document['documentation']['source_commit']]
    for row in document['records']:
        identities.extend([
            row['artifact']['sha256'],
            row['execution']['edi_source'],
            row['execution']['sdk_source'],
        ])
    assert all(identity in text for identity in identities), (
        'The public summary distinguishes actual docs artifact Edi and SDK source identities'
    )


@pytest.mark.parametrize('change', ['missing-artifact', 'missing-execution', 'relabelled-release'])
def test_preview_metadata_cannot_bypass_the_same_real_execution_proof(change):
    from tests.fixtures.tutorial_cases.assistant_versions import (  # noqa: PLC0415 - same route
        PREVIEW_REF,
        PROMPT_BASE,
        USER_BASE,
    )
    from tests.system.py.test_tutorial_assistant_pages import (  # noqa: PLC0415 - original route
        assert_preview_trial,
    )

    document = evidence()
    row = copy.deepcopy(document['records'][0])
    row['publication_route'] = 'prerelease-preview'
    row['preview_ref'] = PREVIEW_REF
    row['address_mapping'] = {PROMPT_BASE: USER_BASE}
    assert_preview_trial(row, 'python', row['prompt_sha256'])
    if change != 'relabelled-release':
        row.pop(change.removeprefix('missing-'))
    with pytest.raises(AssertionError, match='Gate 3/5:'):
        assert_recorded_trial(ROOT, document, row, 'python', row['prompt_sha256'])


@pytest.mark.parametrize('damage', ['scientific-value', 'tolerance', 'pin-provenance'])
def test_published_trial_refuses_changes_to_the_annotated_original_reference(tmp_path, damage):
    document = evidence()
    relative = Path(document['scientific_reference']['path'])
    original = (ROOT / relative).read_bytes()
    reference = json.loads(original)
    if damage == 'pin-provenance':
        reference['source']['pins']['commit'] = '0' * 40
    else:
        pin = next(iter(reference['quantities'].values()))
        pin['value' if damage == 'scientific-value' else 'tol_abs'] = 12345
    destination = tmp_path / relative
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(reference))
    with pytest.raises(AssertionError, match='committed source byte'):
        assert_comparisons(tmp_path, document, document['records'][0])
