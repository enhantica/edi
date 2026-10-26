"""Browser requests retain their initiating action and project.

These fast seam checks guard every receiver, not a browser runtime substitute.
The browser harness exercises the real folder overlap and replacement transitions.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from tests.integration.py.test_scan_app_contract import block

ROOT = Path(__file__).resolve().parents[3]
PATHS = {
    'header': 'app/src/web_files.hpp',
    'source': 'app/src/web_files.cpp',
    'folder': 'app/qml/Pages/Project/GetStartedGroup.qml',
    'structure': 'app/qml/Pages/Structure/StructuresGroup.qml',
    'experiment': 'app/qml/Pages/Experiment/ExperimentsGroup.qml',
    'session': 'app/src/session.cpp',
    'storage': 'app/src/web_storage.cpp',
}


def sources():
    base = os.environ.get('EDI_E04_T11_SOURCE_BASE')
    if base:
        if base != '65a31a98':
            raise ValueError('only the frozen pre-repair red control is selectable')
        return {
            key: subprocess.check_output(['git', 'show', f'{base}:{path}'], cwd=ROOT, text=True)
            if key not in {'session', 'storage'}
            else ''
            for key, path in PATHS.items()
        }
    return {key: (ROOT / path).read_text() for key, path in PATHS.items()}


def violations(text, case):
    """Check request ownership independently of the signal implementation."""
    text = {key: re.sub(r'/\*[\s\S]*?\*/|//[^\n]*', '', body) for key, body in text.items()}

    def section(key, marker):
        return block(text[key], marker) if marker in text[key] else ''

    opener = section('session', 'void Session::openWebProject(')
    receiver = section('session', 'WebStorage::Answer Session::webOpenAnswer(')
    picker = section('storage', 'void WebStorage::pickOpen(')
    begin = section('storage', 'int WebStorage::begin(Reply reply)')
    finish = section('storage', 'void WebStorage::finish(')
    specs = {
        'cancel-then-other-page': [
            *[
                (text['header'], rf'void {signal}\(int request[,)]', 'terminal signal identity')
                for signal in ('filesOpened', 'failed', 'cancelled')
            ],
            (text['source'], r'emit self->cancelled\(request\)', 'dismissed data picker'),
            *[
                (text[page], rf'function on{signal}\(request\b', f'{page} terminal ownership')
                for page in ('structure', 'experiment')
                for signal in ('FilesOpened', 'Failed', 'Cancelled')
            ],
            *[
                (text[page], r'request !== group.webRequest', f'{page} completion ownership')
                for page in ('structure', 'experiment')
            ],
        ],
        'overlapping-folder-uploads': [
            (
                text['folder'],
                r'Session\.openWebProject\(zip\s*\?\s*"file"\s*:\s*"folder"\)',
                'actual Open dialog route',
            ),
            (opener, r'fresh_archive_directory\("web"\)', 'separate folder root per request'),
            (opener, r'pickOpen\(kind, root, webOpenAnswer\(root\)\)', 'actual folder receiver'),
            (
                picker,
                r'edi_storage_pick_open\(begin\(std::move\(answer\)\)',
                'picker callback identity',
            ),
            (begin, re.escape('jobs_.insert(++last_, std::move(reply))'), 'unique request owner'),
            (
                finish,
                re.escape('const Reply done = jobs_.take(job)'),
                'one terminal callback per request',
            ),
            (receiver, r'\[this, root, before\]', 'receiver captures its own folder root'),
        ],
        'replacement-during-upload': [
            (
                receiver,
                re.escape('const QPointer<ProjectViewModel> before = project_'),
                'folder initiating project',
            ),
            (
                receiver,
                re.escape('if (before != project_ || !answer.ok)'),
                'folder completion project ownership',
            ),
            (
                receiver,
                r'if \(before != project_ \|\| answer.cancelled\)\s*\{\s*return;',
                'obsolete completion refuses before loading',
            ),
            (
                opener,
                re.escape('webOpenAnswer(root)'),
                'replacement guard belongs to the actual receiver',
            ),
            *[
                (text[page], re.escape(binding), f'{page} initiating project')
                for page in ('structure', 'experiment')
                for owner in ['group.project']
                for binding in (
                    f'group.webRequestProject = {owner}',
                    f'{owner} === group.webRequestProject',
                )
            ],
        ],
        'structure-cardinality': [
            (text['structure'], r'openFiles\("\.edi", false\)', 'one Structure file'),
            (text['experiment'], r'openFiles\("\.edi", true\)', 'Experiment batch'),
            (
                text['source'],
                (
                    r'multiple\s*\?\s*QWasmLocalFileAccess::FileSelectMode::MultipleFiles\s*:\s*'
                    r'QWasmLocalFileAccess::FileSelectMode::SingleFile'
                ),
                'caller chooser cardinality',
            ),
        ],
    }
    problems = [message for body, pattern, message in specs[case] if not re.search(pattern, body)]
    if case == 'replacement-during-upload':
        guard = receiver.find('if (before != project_ || !answer.ok)')
        load = receiver.find('openWebCopy(answer.path, place)')
        if guard < 0 or load < 0 or guard > load:
            problems.append('initiating-project guard precedes actual browser replacement')
    return problems


@pytest.mark.parametrize(
    'case',
    [
        'cancel-then-other-page',
        'overlapping-folder-uploads',
        'replacement-during-upload',
        'structure-cardinality',
    ],
)
def test_every_browser_file_receiver_preserves_request_ownership(case):
    text = sources()
    assert not violations(text, case), (
        'obsolete browser input must never reach the wrong action/project; '
        + '; '.join(violations(text, case))
    )
    # Every named route has an exercised escape control.
    escapes = {
        'cancel-then-other-page': [
            ('structure', 'request !== group.webRequest', 'false'),
            ('experiment', 'function onCancelled(request)', 'function onOther(request)'),
            ('source', 'emit self->cancelled(request)', 'emit self->failed(request, {})'),
        ],
        'overlapping-folder-uploads': [
            ('storage', 'jobs_.take(job)', 'jobs_.value(job)'),
            (
                'storage',
                'jobs_.insert(++last_, std::move(reply))',
                'jobs_.insert(1, std::move(reply))',
            ),
            (
                'session',
                'pickOpen(kind, root, webOpenAnswer(root))',
                'pickOpen(kind, root, unusedAnswer(root))',
            ),
            ('session', 'fresh_archive_directory("web")', 'shared_archive_directory("web")'),
        ],
        'replacement-during-upload': [
            ('session', 'before != project_ || !answer.ok', 'before == project_ || !answer.ok'),
            (
                'session',
                'if (before != project_ || !answer.ok)',
                'openWebCopy(answer.path, place); if (before != project_ || !answer.ok)',
            ),
            *[
                (page, '=== group.webRequestProject', '!== null')
                for page in ('structure', 'experiment')
            ],
        ],
        'structure-cardinality': [
            ('structure', 'openFiles(".edi", false)', 'openFiles(".edi", true)'),
            ('experiment', 'openFiles(".edi", true)', 'openFiles(".edi", false)'),
        ],
    }
    for key, old, new in escapes[case]:
        assert old in text[key], 'each escape must reach the actual production request seam'
        damaged = {**text, key: text[key].replace(old, new)}
        assert violations(damaged, case), (
            'lost ownership, project binding or cardinality must red its gate'
        )
