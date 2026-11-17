"""Portable trial metadata retains committed source identity without internal document paths."""

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from tests.fixtures.tutorial_cases.published_trials import assert_history

ROOT = Path(__file__).resolve().parents[3]


def git(root, *args):
    return subprocess.check_output(
        [
            'git',
            '-C',
            str(root),
            '-c',
            'user.name=Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            *args,
        ],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


@pytest.mark.parametrize(
    'change', ['none', 'dirty', 'uncommitted', 'missing-argument', 'absolute', 'parent', 'pending']
)
def test_exported_trial_provenance_requires_its_real_committed_document(tmp_path, change):
    source = tmp_path / 'source'
    source.mkdir()
    document = source / 'notes/trials.md'
    document.parent.mkdir()
    records = [{'witness': 'independent authoring protocol'}]
    raw = '# Authored trials\n```json\n' + json.dumps(records) + '\n```\n'
    document.write_text(raw, encoding='utf-8', newline='\n')
    git(source, 'init', '-q')
    git(source, 'add', '.')
    git(source, 'commit', '-qm', 'Record independent authoring protocol')
    commit = git(source, 'rev-parse', 'HEAD')
    output = tmp_path / 'export.json'
    options = ['--source-document', 'notes/trials.md']
    if change == 'dirty':
        document.write_text(raw + 'uncommitted text\n', encoding='utf-8', newline='\n')
    elif change == 'uncommitted':
        options[-1] = 'notes/unknown.md'
        (source / options[-1]).write_text(raw, encoding='utf-8', newline='\n')
    elif change == 'missing-argument':
        options = []
    elif change == 'absolute':
        options[-1] = str(document)
    elif change == 'parent':
        options[-1] = '../notes/trials.md'
    elif change == 'pending':
        options = ['--pending']
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'tests/fixtures/tutorial_cases/capture_assistant_trials.py'),
            str(source),
            str(output),
            *options,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert (result.returncode == 0) == (change in {'none', 'pending'}), (
        'Trial export admits a committed relative document or an explicit pending record only'
    )
    if change == 'none':
        evidence = json.loads(output.read_text())
        assert evidence['records'] == records, (
            'Export preserves every independently authored record'
        )
        assert evidence['source'] == {
            'document': 'assistant-prompt-trials',
            'commit': commit,
            'sha256': hashlib.sha256(raw.encode()).hexdigest(),
        }, 'Public provenance binds the real committed document bytes and source commit'
    elif change == 'pending':
        assert json.loads(output.read_text()) == {'source': None, 'records': []}, (
            'A declared pending export cannot fabricate completed authoring evidence'
        )
    else:
        assert not output.exists(), 'Refused provenance cannot publish a partial trial export'


def test_production_prompt_links_cite_the_truthful_historical_summary_outside_prompt_text():
    import re  # noqa: PLC0415 - check the actual production Markdown seam

    records = json.loads(
        (ROOT / 'tests/fixtures/tutorial_cases/assistant_trials.json').read_text()
    )
    summary = ROOT / 'docs/dev' / (records['source']['document'] + '.md')
    text = summary.read_text(encoding='utf-8')
    current = json.loads(
        (ROOT / 'tests/fixtures/tutorial_cases/published_assistant_trials.json').read_text()
    )
    assert_history(ROOT, current)
    assert 'tests/fixtures/tutorial_cases/assistant_trials.json' in text, (
        'The contributor summary must cite the immutable historical authoring receipt'
    )
    historical = [row for row in records['records'] if row['prompt_commit'] == '557d6e703']
    assert len(historical) == 2 and {row['interface'] for row in historical} == {
        'python',
        'cli',
    }, 'The public summary preserves both independently recorded initial interface attempts'
    for row in historical:
        assert (
            row['status'] == 'failed'
            and row['pin_comparison'] == 'not reached'
            and row['artifact'] is None
        ), 'Historical attempts remain failures with no fabricated scientific artifact'
        for value in [row['date'], row['model'].split(' (', 1)[0], row['prompt_commit']]:
            assert value in text, (
                'The contributor summary retains the historical date, model and prompt commit'
            )
    earlier = text.split('## Earlier attempts', 1)
    assert len(earlier) == 2, 'The contributor summary must distinguish earlier failed attempts'
    assert re.search(r'no generated artifact (?:ran|was executed)', earlier[1], re.IGNORECASE), (
        'The historical summary must not turn prerequisite failures into executed science'
    )
    for interface in ['python', 'cli']:
        checked = date.fromisoformat(
            max(row['date'] for row in current['records'] if row['interface'] == interface)
        )
        checked_text = f'{checked.day} {checked:%B %Y}'
        source = ROOT / 'website/surfaces/docs' / interface / 'tutorials/assistant.md'
        markdown = source.read_text(encoding='utf-8')
        outside = re.sub(r'```[^\n]*\n.*?```', '', markdown, flags=re.DOTALL)
        links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', outside)
        assert not any(records['source']['document'] in link for link in links), (
            'User tutorials must not link the internal prompt-trial summary'
        )
        note = re.findall(
            r'^This prompt was last checked on ([^;]+); '
            r'another assistant may take different steps[.]$',
            outside,
            flags=re.MULTILINE,
        )
        assert note == [checked_text], (
            'Both tutorials retain one plain dated note outside the unchanged prompt text'
        )
