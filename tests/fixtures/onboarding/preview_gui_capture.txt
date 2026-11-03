"""Validate a source-matched native GUI walkthrough before publishing its assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path

SIZE = [1480, 800]
PAGES = ['project', 'structure', 'experiment', 'analysis', 'report']


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def local_file(root: Path, value: object) -> Path:
    require(isinstance(value, str) and bool(value), 'Missing artifact filename')
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()) and path.is_file(), f'Invalid artifact: {value}')
    return path


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f'Expected an object in {path.name}')
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_bundle(root: Path, *, workflow: str = 'creation') -> tuple[dict, list[dict]]:
    manifest = read_json(root / 'manifest.json')
    require(workflow in {'creation', 'reference'}, 'Unknown capture workflow')
    require(manifest.get('workflow', 'creation') == workflow, 'Wrong capture workflow')
    require(
        manifest.get('schema') == 1 and manifest.get('status') == 'complete',
        'Capture is incomplete',
    )
    require(
        bool(re.fullmatch(r'[a-z0-9][a-z0-9_-]*', manifest.get('example', ''))),
        'Invalid walkthrough example id',
    )
    fixture = manifest.get('fixture')
    if fixture is not None:
        require(fixture.get('id') == manifest['example'], 'Fixture and example id disagree')
    reference_kind = 'scan'
    if workflow == 'reference':
        modes = (fixture or {}).get('values', {}).get('fittingMode', [])
        require(
            any(mode in {'sequential', 'independent', 'joint'} for mode in modes),
            'Reference requires a scan or joint-fit fixture',
        )
        reference_kind = 'joint' if 'joint' in modes else 'scan'
    for dependency in manifest.get('dependencies', []):
        require(
            sha256(local_file(root, dependency.get('file'))) == dependency.get('sha256'),
            'A data dependency changed',
        )
    require(manifest.get('logical_size') == SIZE, 'Wrong capture size')
    revision = manifest.get('source_revision', '')
    require(bool(re.fullmatch(r'[0-9a-f]{40}', revision)), 'Capture needs a clean source revision')
    require(
        bool(re.fullmatch(r'[0-9a-f]{64}', manifest.get('binary_sha256', ''))),
        'Missing app identity',
    )
    require(
        sha256(local_file(root, 'walkthrough.js')) == manifest.get('script_sha256'),
        'Walkthrough script changed',
    )
    inputs = manifest.get('inputs', {})
    raw_inputs = 'data' in inputs
    require(
        set(inputs)
        == ({'structure', 'experiment', 'data'} if raw_inputs else {'structure', 'experiment'}),
        'Separate, declared tutorial inputs are required',
    )
    if raw_inputs:
        require(
            Path(inputs['structure']['file']).suffix == '.cif'
            and Path(inputs['data']['file']).suffix == '.xye',
            'The realistic walkthrough requires CIF and measured XYE inputs',
        )
    for item in inputs.values():
        require(
            sha256(local_file(root, item.get('file'))) == item.get('sha256'),
            'An input file changed',
        )
    actions = [item.get('action', '') for item in manifest.get('actions', [])]
    loads = [
        a
        for a in actions
        if a.startswith(('examples.open.', 'open-project:', 'open-cli-project:'))
    ]
    if workflow == 'creation':
        require(not loads, 'Walkthrough opened a whole project')
    else:
        require(
            loads == ['open-cli-project:' + manifest['example']],
            'Reference must open only its declared example',
        )
    expected = [
        'home.start',
        'project.create',
        'createProject.accept',
        'import-structure:',
        'import-experiment:',
        'statusBar.fit.button',
        'wait-fit',
        'close-fit-results',
    ]
    if raw_inputs and workflow == 'creation':
        expected = [
            'home.start',
            'project.create',
            'createProject.accept',
            'import-structure:',
            'experiments.create',
            'import-data:',
            'fill:instrument.setup_wavelength=',
            'excludedRegions.append',
            'background.estimate',
            'parameters.freeHeader.fixed',
            'parameters.freeHeader.free',
            'statusBar.fit.button',
            'wait-fit',
            'close-fit-results',
        ]
    if workflow == 'reference':
        expected = [loads[0], 'statusBar.fit.button', 'wait-fit', 'close-fit-results']
    position = -1
    for action in expected:
        candidates = [
            i
            for i, value in enumerate(actions)
            if i > position
            and (value.startswith(action) if action.endswith((':', '=')) else value == action)
        ]
        require(bool(candidates), f'Missing or out-of-order action: {action}')
        position = candidates[0]
    captured = []
    ids = set()
    for scene in manifest.get('scenes', []):
        name = scene.get('id')
        require(isinstance(name, str) and name not in ids, 'Duplicate or missing scene id')
        ids.add(name)
        require(scene.get('status') in {'captured', 'skipped'}, 'Invalid scene status')
        if scene['status'] == 'skipped':
            continue
        image = local_file(root, scene.get('image'))
        metadata = read_json(local_file(root, scene.get('metadata')))
        require(
            metadata.get('id') == name and metadata.get('source_revision') == revision,
            'Mixed capture sources',
        )
        require(
            metadata.get('script_sha256') == manifest.get('script_sha256'),
            'Mixed walkthrough scripts',
        )
        require(
            metadata.get('image') == image.name and metadata.get('image_sha256') == sha256(image),
            f'Image and metadata disagree: {name}',
        )
        header = image.read_bytes()[:24]
        require(header[:8] == b'\x89PNG\r\n\x1a\n' and len(header) == 24, 'Invalid PNG')
        pixels = list(struct.unpack('>II', header[16:24]))
        require(
            pixels == SIZE
            and metadata.get('pixel_size') == SIZE
            and metadata.get('logical_size') == SIZE,
            f'Wrong image dimensions: {name}',
        )
        state = metadata.get('state', {})
        require(
            state.get('page') == scene.get('page')
            and state.get('sidebar') == scene.get('sidebar'),
            'Scene and native state disagree',
        )
        if scene.get('sidebar'):
            selected = [t.get('label') for t in state.get('sidebar_tabs', []) if t.get('checked')]
            require(
                selected == [scene['sidebar']], 'Sidebar label does not match its native selection'
            )
        fit_phase = metadata.get('fit_phase', '')
        require(
            fit_phase in {'', 'setup'}
            and (fit_phase != 'setup' or scene.get('page') == 'analysis'),
            'Only explicit Analysis setup scenes may precede fitting',
        )
        if scene.get('page') in {'analysis', 'report'}:
            require(
                not state.get('fit_running')
                and not state.get('fit_results_open')
                and (fit_phase == 'setup' or state.get('fit_result_rows', 0) > 0),
                'Analysis setup must be idle; result scenes need a completed fit and closed popup',
            )
            if workflow == 'reference' and reference_kind == 'scan':
                require(
                    state.get('scan_total', 0) > 1
                    and state.get('scan_fitted') == state['scan_total']
                    and state.get('scan_failed') == 0,
                    'Scan reference needs a completed fit for every dataset',
                )
            if workflow == 'reference' and reference_kind == 'joint':
                require(
                    state.get('experiments', 0) > 1, 'Joint reference needs several experiments'
                )
        items = metadata.get('items', {})
        for target in metadata.get('highlights', []):
            item = items.get(target, {})
            bounds = item.get('visible_bounds', [])
            require(
                not item.get('ambiguous')
                and len(bounds) == 4
                and all(isinstance(v, (int, float)) and math.isfinite(v) for v in bounds),
                f'Invalid annotation target: {target}',
            )
            x, y, width, height = bounds
            require(
                x >= -0.1
                and y >= -0.1
                and width > 0
                and height > 0
                and x + width <= SIZE[0] + 0.1
                and y + height <= SIZE[1] + 0.1,
                f'Annotation lies outside the image: {target}',
            )
        captured.append({**scene, 'layout': metadata})
    checkpoints = (
        [
            '01-home',
            '02-project-start',
            '03-project-details',
            '04-project-created',
            '06-structure-import',
            '07-structure-loaded',
            '09-experiment-import',
            '10-experiment-loaded',
        ]
        if workflow == 'creation'
        else [reference_kind + '-experiment-before']
    )
    for name in checkpoints:
        require(any(s['id'] == name for s in captured), f'Missing workflow checkpoint: {name}')
    for page in PAGES:
        scenes = [s for s in captured if s.get('page') == page and s.get('sidebar')]
        require(bool(scenes), f'No sidebar captures for {page}')
        enabled = {
            t['label'] for t in scenes[0]['layout']['state']['sidebar_tabs'] if t['enabled']
        }
        shown = [s['sidebar'] for s in scenes]
        require(
            set(shown) == enabled and len(shown) == len(enabled),
            f'Incomplete sidebar coverage for {page}',
        )
    return manifest, captured


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--workflow', choices=['creation', 'reference'], default='creation')
    args = parser.parse_args()
    manifest, scenes = validate_bundle(args.bundle, workflow=args.workflow)
    print(
        json.dumps(
            {
                'status': 'PASS',
                'source': manifest['source_revision'],
                'scenes': [s['id'] for s in scenes],
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
