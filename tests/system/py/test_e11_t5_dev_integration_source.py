"""Source deliverables only; these gates make no native/runtime/science claim.

Baseline hashes come from frozen dev, not the assistant implementation. Real Main
actors and native OFF/ON observations separately qualify integrated behavior.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BASELINE = json.loads(
    (ROOT / 'tests/fixtures/assistant_dev_integration/baseline.json').read_text()
)


def test_port_retains_current_gui_and_sdk_identities():
    gui = (ROOT / 'cmake/EdiGuiBase.cmake').read_text()
    pins = re.findall(r'(?m)^set\(EDI_GUI_COMPONENTS_SHA\s+([0-9a-f]{40})\)', gui)
    assert pins == [BASELINE['gui_commit']], 'Assistant integration retains the current GUI pin'
    config = tomllib.loads((ROOT / 'pixi.toml').read_text())
    platforms = config['target']
    observed = {
        name: target['activation']['env']['CRYSTA_SDK_TAG']
        for name, target in platforms.items()
        if 'CRYSTA_SDK_TAG' in target.get('activation', {}).get('env', {})
    }
    assert observed, 'The real platform SDK identities must remain declared'
    assert set(observed.values()) == {BASELINE['sdk_tag']}, (
        'Assistant integration consumes the current dev SDK on every declared platform'
    )


@pytest.mark.parametrize('relative,expected', BASELINE['preserved_files'].items())
def test_port_preserves_current_estimator_and_existing_adr_identities(relative, expected):
    path = ROOT / relative
    assert path.is_file(), f'Current dev source is retained: {relative}'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, (
        f'{relative} is frozen dev source from {BASELINE["source_commit"]}; '
        'assistant ADRs need distinct identities and native Estimate reuses its current algorithm'
    )


def test_port_does_not_restore_retired_local_gui_or_optional_folder_dialog():
    excluded = [
        'app/qml/Base/Gui/Components/ListView.qml',
        'app/qml/Components/TableViewParameter.qml',
        'app/qml/Components/ProjectFolderDialog.qml',
    ]
    present = [relative for relative in excluded if (ROOT / relative).exists()]
    assert not present, f'The selective port excludes these old manual UI surfaces: {present}'


def test_shipped_skills_have_exact_self_contained_content_identity():
    folder = ROOT / 'data/assistant/skills'
    index = folder / 'index.json'
    assert index.is_file(), 'The integrated assistant must ship its actual versioned skills'
    manifest = json.loads(index.read_text())
    assert manifest['schema'] == 'edi.assistant.skills/1'
    rows = manifest['skills']
    assert rows, 'The shipped skill manifest cannot be an empty availability claim'
    names = [row['id'] for row in rows]
    assert len(names) == len(set(names)), 'Every shipped skill has one unambiguous identity'
    resolved_paths = []
    for row in rows:
        assert re.fullmatch(r'\d+\.\d+\.\d+', row['version']), (
            'A reportable shipped skill version must be explicit'
        )
        path = (folder / row['path']).resolve()
        assert path.is_relative_to(folder.resolve()) and path.name == 'SKILL.md', (
            'Skill registration cannot escape its shipped resource root'
        )
        assert path.is_file(), f'Skill {row["id"]} must resolve to actual packaged content'
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == row['sha256'], (
            f'Skill {row["id"]} must disclose the identity of its actual current content'
        )
        assert content.strip(), 'An empty resource is not usable skill guidance'
        resolved_paths.append(path)
    assert len(resolved_paths) == len(set(resolved_paths)), (
        'Distinct skill identities cannot silently alias the same resource'
    )
