#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Render captured outputs and the shared initial/refined comparison without copied results."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from render_experiments import replace
from render_interfaces import preview

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'surfaces/docs'


def comparison(folder: Path) -> tuple[str, dict]:
    metadata = json.loads((folder / 'capture.json').read_text())
    example = json.loads((DOCS / 'assets/gui/y2o3/manifest.json').read_text())['example']
    if metadata['example'] != example:
        raise ValueError('Learning comparison must use the selected GUI example')
    for filename, digest in metadata['assets_sha256'].items():
        if hashlib.sha256((folder / filename).read_bytes()).hexdigest() != digest:
            raise ValueError('Learning figure differs from its captured source')
    if 'gui_capture' in metadata:
        bundle = DOCS / 'assets/gui/y2o3'
        if (
            hashlib.sha256((bundle / 'manifest.json').read_bytes()).hexdigest()
            != metadata['gui_capture']['manifest_sha256']
        ):
            raise ValueError('GUI comparison and screenshot capture disagree')
        for phase, field in [('starting', 'input_sha256'), ('refined', 'refined_input_sha256')]:
            source = bundle / 'checkpoints' / phase
            actual = {
                str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in source.rglob('*')
                if path.is_file()
            }
            if actual != metadata[field]:
                raise ValueError('GUI comparison checkpoints changed')
    panes = ['<div class="gui-viewer" markdown="1">', '']
    for title, filename, description in [
        (
            'Starting model',
            'initial.svg',
            (
                'Compare the starting calculation with the measured pattern. The residual '
                'shows their difference.'
            ),
        ),
        (
            'Fitted model',
            'refined.svg',
            (
                'After the fit, compare the same peaks and residual on exactly the same '
                'axes and scale.'
            ),
        ),
    ]:
        panes += [
            '=== "' + title + '"',
            '',
            '    <p class="gui-view-description">' + description + '</p>',
            '',
        ]
        panes += [
            '    ' + line
            for line in preview(
                folder.relative_to(DOCS / 'assets').as_posix() + '/' + filename, title
            ).splitlines()
        ]
        panes += ['']
    panes += ['</div>', '']
    comparison = '\n'.join(panes)
    ranges = metadata['axis_ranges']
    if ranges['initial'] != ranges['refined'] or any(
        not isinstance(value, (int, float)) or not math.isfinite(value)
        for bounds in ranges['initial'].values()
        for value in bounds
    ):
        raise ValueError('Comparison axes must be finite and identical')
    return comparison, metadata


def render() -> None:
    folder = DOCS / 'assets/learning'
    if not (folder / 'capture.json').exists():
        return
    prepared, _ = comparison(folder)
    gui_folder = folder / 'gui'
    application = comparison(gui_folder)[0] if (gui_folder / 'capture.json').exists() else prepared
    # The Y2O3 case's Application tutorial, three folders below the docs root.
    page = DOCS / 'application/tutorials/cases/pd-neut-cwl_y2o3-spodi.md'
    if page.is_file():
        replace(page, 'learning-comparison', application.replace('../assets/', '../../../assets/'))


if __name__ == '__main__':
    render()
