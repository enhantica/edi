"""Disposable metadata-only completeness controls; these authored placeholders are never fitted."""

import copy
import json
import subprocess
from pathlib import Path

import yaml

from tests.fixtures.tutorial_cases.contract import CASES, CONTRACT, ROOT


def overlay(source, destination):
    destination.mkdir()
    for path in source.iterdir():
        Path(destination / path.name).symlink_to(path.resolve(), target_is_directory=path.is_dir())
    return destination


def writable(root, relative):
    path = Path(relative)
    current = root
    for part in path.parts[:-1]:
        current /= part
        if current.is_symlink():
            source = current.resolve()
            current.unlink()
            overlay(source, current)
        else:
            current.mkdir(exist_ok=True)
    result = root / path
    if result.is_symlink():
        original = result.read_bytes()
        result.unlink()
        result.write_bytes(original)
    return result


def write_json(root, relative, document):
    writable(root, relative).write_text(json.dumps(document, indent=2) + '\n')


def control_rows(registry):
    by_id = {row['id']: row for row in registry['projects']}
    for row in by_id.values():
        if 'user-facing' in row:
            row['user-facing'] = row['id'] in CASES
    return by_id


def complete_metadata_tree(destination):
    root = overlay(ROOT, destination)
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())
    by_id = control_rows(registry)
    manifest = json.loads((ROOT / 'app/tutorials/manifest.json').read_text())
    metadata = json.loads((ROOT / 'app/examples/metadata.json').read_text())
    commit = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
    ).strip()
    for case in CASES:
        row = by_id.setdefault(case, {'id': case, 'executing': False})
        row['user-facing'] = True
        if not any(key in row for key in ['diffraction-lib', 'follows-diffraction-lib']):
            row['follows-diffraction-lib'] = 'simulate-lbco-cwl'
        row['structure-by-hand'] = case == 'pd-neut-cwl_lbco-hrpt'
        row['data-from-file'] = case == 'pd-neut-tof_si-sepd'
        directory = 'docs/user/cli/' + case
        project = writable(root, directory + '/project/project.edi')
        lines = project.read_text().splitlines()
        project.write_text(
            '\n'.join(
                '_metadata.name ' + case if line.startswith('_metadata.name ') else line
                for line in lines
            )
            + '\n'
        )
        expected_path = root / directory / 'expected.json'
        expected = (
            json.loads(expected_path.read_text()) if expected_path.exists() else {'schema': 1}
        )
        expected.setdefault('source', {})['pins'] = {
            'commit': commit,
            'reason': 'Authored metadata-only fixture: no fitted values are produced or claimed',
        }
        if not expected.get('quantities') and not expected.get('calc'):
            expected['calc'] = {
                'quantities': {
                    'n_points': {
                        'value': 1,
                        'kind': 'regression-pin',
                        'tol_abs': 0,
                        'tol_rel': None,
                    },
                }
            }
        write_json(root, directory + '/expected.json', expected)
        if not (root / directory / 'PROVENANCE.md').is_file():
            writable(root, directory + '/PROVENANCE.md').write_text(
                '# Authored metadata control\n\n## Sources\n\nCalculation without measured data.\n'
            )
        for key, pattern in CONTRACT['tutorials'].items():
            if key == 'app':
                continue
            path = pattern.format(case=case)
            if not (root / path).is_file():
                if key == 'python':
                    write_json(
                        root,
                        path,
                        {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {}, 'cells': []},
                    )
                else:
                    writable(root, path).write_text('# Authored metadata-only tutorial control\n')
        if case not in {entry['id'] for entry in manifest['tutorials']}:
            manifest['tutorials'].append({
                'id': case,
                'steps': [{'title': 'Authored control', 'target': 'home.start'}],
            })
        if case not in metadata['examples']:
            template = (
                'sc-neut-cwl_tb2ti2o7-heidi'
                if case.startswith('sc-')
                else 'pd-neut-cwl_yalo3-al2o3-spodi'
            )
            metadata['examples'][case] = copy.deepcopy(metadata['examples'][template])
            if case in CONTRACT['simulations']:
                metadata['examples'][case]['values']['purpose'] = ['simulation']
    registry['projects'] = list(by_id.values())
    writable(root, 'docs/user/cli/projects.yml').write_text(
        yaml.safe_dump(registry, sort_keys=False)
    )
    write_json(root, 'app/tutorials/manifest.json', manifest)
    write_json(root, 'app/examples/metadata.json', metadata)
    return root
