"""Reviewed local producers and exact component transports retain publication ownership."""

import copy

import pytest

from tests.system.py import test_e04_t12_public_release as policy


@pytest.mark.parametrize('damage', ['other-local', 'remote', 'missing-producer', 'not-callable'])
def test_reusable_workflow_allowance_refuses_unknown_or_missing_ownership(damage):
    documents = policy.workflows()
    assert not policy.public_token_findings(documents), (
        'Reviewed producer ownership first admits before every reusable-workflow challenge'
    )
    changed = copy.deepcopy(documents)
    if damage == 'missing-producer':
        changed = [(name, doc) for name, doc in changed if name != 'crysta-sdk.yml']
    elif damage == 'not-callable':
        target = next(doc for name, doc in changed if name == 'crysta-sdk.yml')
        target['on'].pop('workflow_call')
    else:
        caller = next(doc for name, doc in changed if name == 'ci.yml')['jobs']['crysta-sdk']
        caller['uses'] = (
            './.github/workflows/other.yml'
            if damage == 'other-local'
            else 'enhantica/edi/.github/workflows/crysta-sdk.yml@main'
        )
    assert policy.public_token_findings(changed), (
        'A local producer allowance cannot admit remote, absent, uncallable or unrelated authority'
    )


@pytest.mark.parametrize(
    'damage', ['needs', 'artifact', 'foreign-run', 'optional', 'comment-only']
)
def test_each_component_publication_refuses_a_foreign_or_bypassed_transport(damage):
    baseline = dict(policy.workflows())['pages.yml']
    for component, artifact, incoming in [
        ('docs', 'pages-docs', 'documentation'),
        ('wasm', 'pages-webapp', 'webapp'),
    ]:
        policy.pages_component_boundary(baseline, component, component, artifact, incoming)
        changed = copy.deepcopy(baseline)
        job = changed['jobs']['publish-' + component]
        download = next(
            step for step in job['steps'] if 'actions/download-artifact@' in step.get('uses', '')
        )
        if damage == 'needs':
            job['needs'] = 'unrelated-build'
        elif damage == 'artifact':
            download['with']['name'] = 'foreign-component'
        elif damage == 'foreign-run':
            download['with']['run-id'] = 'other-run'
        elif damage == 'optional':
            download['continue-on-error'] = True
        else:
            placement = next(
                step for step in job['steps'] if 'tools/ci/pages_update.py' in step.get('run', '')
            )
            placement['run'] = '\n'.join('# ' + line for line in placement['run'].splitlines())
        with pytest.raises(AssertionError):
            policy.pages_component_boundary(changed, component, component, artifact, incoming)
