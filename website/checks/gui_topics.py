"""Keep workflow how-to headings and native screenshot coverage in sync."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from import_gui_captures import native_options
from render_interfaces import screenshot_radius

from checks.gui_capture import require


def validate_topics(root: Path, config: dict, scenes: list[dict]) -> None:
    docs = root / 'surfaces/docs'
    registry = json.loads((root / 'gui-guide-scenes.json').read_text())
    navigation = next(
        section['Application'] for section in config['nav'] if 'Application' in section
    )
    workflow = next(
        group['Analysis workflow']
        for group in navigation
        if isinstance(group, dict) and 'Analysis workflow' in group
    )
    for stage in workflow:
        if not isinstance(stage, dict):
            continue
        pages = next(iter(stage.values()))
        for filename in (
            [pages]
            if isinstance(pages, str)
            else [page if isinstance(page, str) else next(iter(page.values())) for page in pages]
        ):
            require(filename in registry, f'{filename}: missing screenshot coverage declaration')
    by_id = {scene['id']: scene for scene in scenes}
    require(len(by_id) == len(scenes), 'Capture bundles reuse a scene id')
    for filename, sections in registry.items():
        path = (docs / filename).resolve()
        require(
            path.is_relative_to(docs.resolve()) and path.is_file(), f'Invalid guide: {filename}'
        )
        text = path.read_text()
        headings = set(re.findall(r'^## (.+)$', text, re.MULTILINE)) - {'Related Physics'}
        # A text-only page declares no scene, because the capture run does not reach its group.
        require(
            not sections or headings == set(sections),
            f'{filename}: practical headings and capture map differ',
        )
        for heading, references in sections.items():
            identities = references.values() if isinstance(references, dict) else references
            if isinstance(identities, str):
                identities = [identities]
            slug = re.sub(r'[^a-z0-9]+', '-', heading.lower()).strip('-')
            markers = re.findall(
                r'<!-- gui-guide:' + re.escape(slug) + r' -->(.*?)<!-- /gui-guide -->',
                text,
                flags=re.DOTALL,
            )
            require(len(markers) == 1, f'{filename}: {heading} needs one generated illustration')
            for identity in identities:
                require(identity in by_id, f'{filename}: missing native scene {identity}')
                require(
                    by_id[identity]['image'] in markers[0],
                    f'{filename}: stale illustration for {identity}',
                )
        root = '../' * filename.count('/')
        require(
            native_options(text, by_id, root) == text, f'{filename}: stale native selector options'
        )
        if not sections:
            continue
        radii = re.findall(r'<rect width="1480" height="800" rx="([0-9.]+)"', text)
        require(
            radii
            and all(abs(float(radius) - screenshot_radius(1480)) < 0.001 for radius in radii),
            f'{filename}: stale screenshot corner radius',
        )
