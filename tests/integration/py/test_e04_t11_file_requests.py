"""Browser requests retain their initiating action and project.

These fast seam checks guard every receiver, not a browser runtime substitute.
The browser harness exercises the real folder overlap and replacement transitions.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PATHS = {
    'header': 'app/src/web_files.hpp',
    'source': 'app/src/web_files.cpp',
    'folder': 'app/qml/Pages/Project/GetStartedGroup.qml',
    'structure': 'app/qml/Pages/Structure/StructuresGroup.qml',
    'experiment': 'app/qml/Pages/Experiment/ExperimentsGroup.qml',
}


def sources():
    base = os.environ.get('EDI_E04_T11_SOURCE_BASE')
    if base:
        if base != '65a31a98':
            raise ValueError('only the frozen pre-repair red control is selectable')
        return {
            key: subprocess.check_output(['git', 'show', f'{base}:{path}'], cwd=ROOT, text=True)
            for key, path in PATHS.items()
        }
    return {key: (ROOT / path).read_text() for key, path in PATHS.items()}


def violations(text, case):
    """Check request ownership independently of the signal implementation."""
    text = {key: re.sub(r'/\*[\s\S]*?\*/|//[^\n]*', '', body) for key, body in text.items()}
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
            (text['header'], r'void projectOpened\(int request,', 'folder completion identity'),
            *[
                (text['source'], re.escape(binding), 'folder root and terminal owner')
                for binding in (
                    'm_folders.insert(request, root)',
                    'm_folders.take(request)',
                    'Module._edi_web_folder_copied(request, copied)',
                    'if (!finish(request))',
                    'emit cancelled(superseded)',
                )
            ],
            (text['folder'], r'request !== group.webRequest', 'folder receiver ownership'),
        ],
        'replacement-during-upload': [
            (text[page], re.escape(binding), f'{page} initiating project')
            for page in ('folder', 'structure', 'experiment')
            for owner in ['Session.project' if page == 'folder' else 'group.project']
            for binding in (
                f'group.webRequestProject = {owner}',
                f'{owner} === group.webRequestProject',
            )
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
    return [message for body, pattern, message in specs[case] if not re.search(pattern, body)]


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
            ('source', 'm_folders.take(request)', 'pending_root'),
            ('folder', 'request !== group.webRequest', 'false'),
        ],
        'replacement-during-upload': [
            (page, '=== group.webRequestProject', '!== null')
            for page in ('folder', 'structure', 'experiment')
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
