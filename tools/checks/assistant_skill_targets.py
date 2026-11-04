# SPDX-License-Identifier: BSD-3-Clause
"""Check bundled skills against the GUI controls they name."""

from __future__ import annotations

import re
from pathlib import Path

TARGET = re.compile(r'\bui:([A-Za-z0-9_.-]+)')
OBJECT = re.compile(r"^\s*objectName\s*:\s*[\"']([^\"']+)[\"']\s*;?\s*(?://.*)?$", re.MULTILINE)
OLD_ROUTE = re.compile(r'experiments\.(?:loadData|file)\.')


def check_targets(skills: Path, qml: Path) -> list[str]:
    """Return missing declared controls and retired file-cell routes."""
    controls = set()
    sources = list(qml.rglob('*.qml'))
    if not sources:
        return [f'No QML source files in {qml}']
    for source in sources:
        controls.update(OBJECT.findall(source.read_text(encoding='utf-8')))
    guides = sorted(skills.glob('*/SKILL.md'))
    if not guides:
        return [f'No skills in {skills}']
    errors = []
    for guide in guides:
        body = guide.read_text(encoding='utf-8')
        errors.extend(
            f'{guide.parent.name}: missing GUI control {target}'
            for target in sorted(set(TARGET.findall(body)))
            if target not in controls
        )
        if OLD_ROUTE.search(body):
            errors.append(f'{guide.parent.name}: retired experiment file-cell route')
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    errors = check_targets(root / 'data/assistant/skills', root / 'app/qml')
    for error in errors:
        print(error)
    if not errors:
        print('Assistant skill GUI targets are current')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
