#!/usr/bin/env python3
"""Render the shared workflow using the same bundled icons as navigation."""

from __future__ import annotations

import html
import re
from importlib.metadata import distribution
from pathlib import Path

import yaml
from defusedxml import ElementTree
from render_experiments import replace

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'surfaces/docs'


def render() -> None:
    config = yaml.load((ROOT / 'surfaces/mkdocs.yml').read_text(), Loader=yaml.BaseLoader)
    stages = config['extra']['workflow_icons']
    package = distribution('zensical')
    # Both entry pages share one responsive component and the navigation's icon paths.
    steps = []
    for title, name in stages.items():
        relative = 'zensical/templates/.icons/material/' + name + '.svg'
        source = Path(package.locate_file(relative))
        root = ElementTree.fromstring(source.read_bytes())
        paths = ''.join(
            '<path d="' + html.escape(path.attrib['d'], quote=True) + '"/>'
            for path in root
            if path.tag.endswith('path')
        )
        if not paths:
            raise ValueError('Workflow icon has no vector paths: ' + name)
        steps.append((title, paths))
    for filename, prefix in [
        ('user-guide/analysis-workflow/index.md', ''),
        ('user-guide/index.md', 'analysis-workflow/'),
    ]:
        diagram = ['<ol class="ed-workflow-diagram" aria-label="Analysis workflow">']
        for title, paths in steps:
            diagram.append(
                f'<li><a href="{prefix}{title.lower()}/">'
                f'<svg viewBox="0 0 24 24" aria-hidden="true">{paths}</svg>'
                f'<span>{title}</span></a></li>'
            )
        diagram.append('</ol>')
        replace(DOCS / filename, 'workflow-diagram', '\n'.join(diagram))
    # Broad scientific groups keep the same stage symbols as their navigation.
    group_stages = {
        'Structure model': 'Structure',
        'Experiment model': 'Experiment',
        'Analysis and refinement': 'Analysis',
        'Projects and results': 'Project',
    }
    path = DOCS / 'user-guide/features.md'
    text = path.read_text()
    for title, stage in group_stages.items():
        text = re.sub(
            r'^## (?::material-[a-z-]+: )?' + re.escape(title) + r'( \{#[^}]+\})?$',
            lambda match, stage=stage, title=title: (
                '## :material-'
                + stages[stage]
                + ': '
                + title
                + (match[1] or ' {#' + title.lower().replace(' ', '-') + '}')
            ),
            text,
            flags=re.MULTILINE,
        )
    path.write_text(text)
    # Stage links use the same identifiers in the diagram, overview table and guides.
    for path in (DOCS / 'user-guide').rglob('*.md'):
        text = path.read_text()
        for title, name in stages.items():
            text = re.sub(
                r'\['
                + title
                + r'\]\(([^)]+/'
                + title.lower()
                + r'\.md|'
                + title.lower()
                + r'\.md)\)',
                r'[:material-' + name + ': ' + title + r'](\1)',
                text,
            )
        # Table labels can wrap below their icon group without separating icons.
        text = re.sub(
            r'(?m)^(\|.*)$',
            lambda row: re.sub(
                r'\[(:material-[a-z-]+:) ([^]\n<]+)\]',
                (
                    r'[<span class="ed-icon-label"><span class="ed-icon-group" '
                    r'aria-hidden="true">\1</span><span '
                    r'class="ed-icon-text">\2</span></span>]'
                ),
                row[0],
            ),
            text,
        )
        path.write_text(text)


if __name__ == '__main__':
    render()
