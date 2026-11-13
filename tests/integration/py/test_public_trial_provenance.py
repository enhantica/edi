"""Portable trial metadata retains committed source identity without internal document paths."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

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
    document.write_text(raw, encoding='utf-8')
    git(source, 'init', '-q')
    git(source, 'add', '.')
    git(source, 'commit', '-qm', 'Record independent authoring protocol')
    commit = git(source, 'rev-parse', 'HEAD')
    output = tmp_path / 'export.json'
    options = ['--source-document', 'notes/trials.md']
    if change == 'dirty':
        document.write_text(raw + 'uncommitted text\n', encoding='utf-8')
    elif change == 'uncommitted':
        options[-1] = 'notes/unknown.md'
        (source / options[-1]).write_text(raw, encoding='utf-8')
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
    summary = ROOT / 'website/surfaces/docs' / (records['source']['document'] + '.md')
    text = summary.read_text(encoding='utf-8')
    assert records['source']['commit'] in text and records['source']['sha256'] in text, (
        'The production summary cites the exact independently recorded authoring source'
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
        for field in ['date', 'model', 'prompt_commit', 'prompt_sha256']:
            assert row[field] in text, (
                'The truthful public summary retains each original model/date/prompt identity'
            )
    assert (
        'No preview trial is recorded' in text and 'no generated artifact was executed' in text
    ), 'The summary clearly distinguishes historical prerequisite failure from executed science'
    for interface in ['python', 'cli']:
        source = ROOT / 'website/surfaces/docs' / interface / 'tutorials/assistant.md'
        markdown = source.read_text(encoding='utf-8')
        outside = re.sub(r'```[^\n]*\n.*?```', '', markdown, flags=re.DOTALL)
        links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', outside)
        assert any(
            (source.parent / link).resolve() == summary.resolve()
            for link in links
            if not link.startswith(('http:', 'https:'))
        ), 'Both prompt pages link the public summary outside their immutable prompt fences'
