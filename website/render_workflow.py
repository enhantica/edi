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

    def write_diagram(filename: str, links: dict[str, str]) -> None:
        diagram = ['<ol class="ed-workflow-diagram" aria-label="Analysis workflow">']
        for title, paths in steps:
            diagram.append(
                f'<li><a href="{links[title]}">'
                f'<svg viewBox="0 0 24 24" aria-hidden="true">{paths}</svg>'
                f'<span>{title}</span></a></li>'
            )
        diagram.append('</ol>')
        replace(DOCS / filename, 'workflow-diagram', '\n'.join(diagram))

    for filename, prefix in [
        ('user-guide/analysis-workflow/index.md', ''),
        ('user-guide/index.md', 'analysis-workflow/'),
    ]:
        write_diagram(filename, {title: f'{prefix}{title.lower()}/' for title, _ in steps})
    # Each interface diagram opens the first page of that stage in its own section.
    for interface, folder in (
        ('Application', 'application'),
        ('Python', 'python'),
        ('Command Line', 'cli'),
    ):
        section = next(entry[interface] for entry in config['nav'] if interface in entry)
        workflow = next(g['Analysis workflow'] for g in section if 'Analysis workflow' in g)
        links = {}
        for stage in workflow[1:]:
            ((title, pages),) = stage.items()
            first = pages if isinstance(pages, str) else next(iter(pages[0].values()))
            links[title] = '../' + first.removeprefix(folder + '/').removesuffix('.md') + '/'
        write_diagram(f'{folder}/analysis-workflow/index.md', links)
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
