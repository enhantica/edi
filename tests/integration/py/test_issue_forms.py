"""Check public issue forms against the issue policy and the executable validator."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
FORMS = Path('.github/ISSUE_TEMPLATE')
POLICY = Path('docs/dev/adrs/0101-issue-labels.md')
VALIDATOR = Path('tools/checks/issue_forms.py')
EXPECTED = {
    'bug.yml': {'🐞 bug', '⚠️ priority needed'},
    'feature.yml': {'✨ enhancement', '⚠️ priority needed'},
    'question.yml': {'⚠️ scope needed', '⚠️ priority needed'},
}


def test_forms_start_with_the_approved_public_labels():
    policy = (ROOT / POLICY).read_text(encoding='utf-8')
    rows = [
        (group, name, scopes.split())
        for group, name, scopes in re.findall(
            r'^\|\s*(\w+)\s*\|\s*`([^`]+)`\s*\|\s*([EF ]+)\|', policy, re.MULTILINE
        )
    ]
    public = {name for _, name, scopes in rows if 'E' in scopes}
    priority = {name for group, name, scopes in rows if group == 'priority' and 'E' in scopes}
    assert priority == {'🔴 high', '🟠 medium', '🟡 low', '⚠️ priority needed'}, (
        'The public issue policy includes exactly three priorities and the triage placeholder'
    )
    assert {p.name for p in (ROOT / FORMS).glob('*.yml')} == {*EXPECTED, 'config.yml'}, (
        'The public tracker offers the local bug, feature and question forms and their config'
    )
    for filename, labels in EXPECTED.items():
        document = yaml.safe_load((ROOT / FORMS / filename).read_text(encoding='utf-8'))
        actual = document['labels']
        assert len(actual) == len(set(actual)) and set(actual) == labels <= public, (
            f'{filename} must start with its approved public labels exactly once: {actual!r}'
        )


def test_issue_ownership_policy_uses_the_project_column():
    policy = (ROOT / POLICY).read_text(encoding='utf-8')
    rule = re.search(r'(?ms)^4\. \*\*In progress\.\*\*.*?(?=^5\.)', policy)
    assert rule and re.search(r'\b(?:board|column)\b', rule.group(), re.IGNORECASE), (
        'The issue ownership rule must tell maintainers to move the project board column'
    )
    obsolete = r'(?i)(?:in.progress label replaces|in.progress` is set|label is removed)'
    assert not re.search(obsolete, rule.group()) and not re.search(
        r'(?i)the in.progress label replaces it', policy
    ), 'The current and dropped-label rules both retire label-based issue ownership'


@pytest.fixture
def form_repository(tmp_path):
    assert (ROOT / VALIDATOR).is_file(), 'The issue forms have an executable local validator'
    shutil.copytree(ROOT / 'tools/checks', tmp_path / 'tools/checks')
    shutil.copytree(ROOT / FORMS, tmp_path / FORMS)
    policy = tmp_path / POLICY
    policy.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / POLICY, policy)
    shutil.copyfile(ROOT / 'pyproject.toml', tmp_path / 'pyproject.toml')
    return tmp_path


@pytest.mark.parametrize(
    'defect', ['legacy-label', 'feedback-only-label', 'bad-yaml', 'bad-type', 'bad-id']
)
def test_issue_form_validator_refuses_one_damaged_field(form_repository, defect):
    def validate():
        return subprocess.run(
            [sys.executable, form_repository / VALIDATOR],
            cwd=form_repository,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )

    good = validate()
    assert good.returncode == 0, 'The checked-in form set must pass the executable validator'
    path = form_repository / FORMS / 'bug.yml'
    document = yaml.safe_load(path.read_text(encoding='utf-8'))
    if defect == 'bad-yaml':
        path.write_text('labels: [\n', encoding='utf-8')
    else:
        if defect == 'legacy-label':
            document['labels'][0] = '[scope] bug'
        elif defect == 'feedback-only-label':
            document['labels'][0] = 'likes'
        else:
            element = next(row for row in document['body'] if 'id' in row)
            if defect == 'bad-type':
                element['type'] = 'made-up'
            else:
                element['id'] = 'spaces are invalid'
        path.write_text(yaml.safe_dump(document, allow_unicode=True), encoding='utf-8')
    refused = validate()
    assert refused.returncode == 1 and 'bug' in (refused.stdout + refused.stderr).lower(), (
        f'The validator must name the damaged bug form and refuse {defect}: '
        f'{refused.stdout}{refused.stderr}'
    )
