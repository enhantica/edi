"""Adapt catalogue identities without refreshing numerical or historical measurements.

The original project bodies are bound to before_commit. Only the decided name and
authors metadata may differ. Existing CLI records and independent model counts
keep every scientific field and their original capture/input provenance.
"""

import argparse
import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
IDENTITIES = json.loads((HERE / 'single-crystal-renames.json').read_text())
RENAMES = IDENTITIES['ids']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def renamed(value):
    if isinstance(value, dict):
        return {renamed(key): renamed(item) for key, item in value.items()}
    if isinstance(value, list):
        return [renamed(item) for item in value]
    if isinstance(value, str):
        for old, new in RENAMES.items():
            if value == old:
                return new
            value = value.replace('docs/user/cli/' + old + '/', 'docs/user/cli/' + new + '/')
    return value


def historical_path(relative):
    for old, new in RENAMES.items():
        relative = relative.replace('docs/user/cli/' + new + '/', 'docs/user/cli/' + old + '/')
    return relative


def same_science(before, after):
    pattern = rb'(?m)^_metadata\.(?:name|authors)[^\n]*\n'
    return re.sub(pattern, b'', before) == re.sub(pattern, b'', after)


def validate_inputs():
    executable = shutil.which('git')
    require(executable is not None, 'A catalogue identity capture requires git')
    for old, new in RENAMES.items():
        prefix = 'docs/user/cli/' + old + '/project/'
        names = subprocess.check_output(
            [
                executable,
                'ls-tree',
                '-r',
                '--name-only',
                IDENTITIES['before_commit'],
                '--',
                prefix,
            ],
            cwd=ROOT,
            text=True,
        ).splitlines()
        previous = {
            name.removeprefix(prefix): subprocess.check_output(
                [executable, 'show', IDENTITIES['before_commit'] + ':' + name],
                cwd=ROOT,
            )
            for name in names
        }
        folder = ROOT / 'docs/user/cli' / new / 'project'
        current = {
            path.relative_to(folder).as_posix(): path.read_bytes()
            for path in folder.rglob('*')
            if path.is_file()
        }
        require(
            previous and set(current) == set(previous),
            'A catalogue rename retains the complete scientific project file population',
        )
        for name, data in previous.items():
            require(
                same_science(data, current[name])
                if name == 'project.edi'
                else data == current[name],
                'A catalogue rename changes only the decided name/authors metadata',
            )


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def migrate_pins():
    path = ROOT / 'tests/fixtures/c34_t28_baseline/saved-bytes.json'
    data = json.loads(path.read_text())
    original_cases = copy.deepcopy(data['cases'])
    data['post_feature_fixed_points'] = renamed(data['post_feature_fixed_points'])
    data['catalogue_identity_aliases'] = RENAMES
    require(data['cases'] == original_cases, 'Every immutable pre-move byte pin stays unchanged')
    write_json(path, data)
    path = ROOT / 'tests/fixtures/project_save/input-transitions.json'
    data = json.loads(path.read_text())
    data['cases'] = renamed(data['cases'])
    data['catalogue_identity_aliases'] = RENAMES
    write_json(path, data)


def migrate_cli():
    folder = ROOT / 'tests/fixtures/e05_t1'
    path = folder / 'cli.json'
    manifest = json.loads(path.read_text())
    for row in manifest['cases']:
        if row['id'] not in RENAMES:
            continue
        old = row['id']
        previous = copy.deepcopy(row)
        row['id'] = RENAMES[old]
        row['path'] = 'docs/user/cli/' + row['id'] + '/project'
        require(
            {key: value for key, value in row.items() if key not in {'id', 'path'}}
            == {key: value for key, value in previous.items() if key not in {'id', 'path'}},
            'Identity adaptation retains every historical CLI numeric record and input digest',
        )
        original_record, current_record = (
            folder / (old + '.record'),
            folder / (row['id'] + '.record'),
        )
        if original_record.exists():
            require(
                not current_record.exists(), 'A renamed CLI record cannot replace another fixture'
            )
            original_record.rename(current_record)
    manifest['catalogue_identity_aliases'] = RENAMES
    manifest['catalogue_identity_scope'] = (
        'Identity/path aliases only. Numerical records and inputs_sha256 retain their original '
        'historical capture provenance; no fit or numerical reference was retaken.'
    )
    spec = importlib.util.spec_from_file_location('retained_cli_writer', folder / 'generate.py')
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)
    writer.write_artifacts(manifest)
    path = folder / 'model_counts.json'
    counts = json.loads(path.read_text())
    for row in counts['cases']:
        if row['id'] in RENAMES:
            row['id'] = RENAMES[row['id']]
    counts['catalogue_identity_aliases'] = RENAMES
    counts['catalogue_identity_scope'] = (
        'Case identities only; every independently captured model count/name stays unchanged.'
    )
    write_json(path, counts)


def migrate_runtime_ids():
    spec = importlib.util.spec_from_file_location(
        'catalogue_runtime_writer', ROOT / 'tools/checks/per_pr_runtimes.py'
    )
    writer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = writer
    spec.loader.exec_module(writer)
    path = ROOT / 'tests/per-pr-runtimes.tsv'
    _, measured = writer.load_manifest(path)
    holes = writer._unmeasured_reasons(path.read_text())
    original = {**measured, **holes}
    adapted = {}
    for identity, value in original.items():
        retained = value
        current = identity
        for old, new in RENAMES.items():
            current = current.replace(old, new)
        if current in adapted and adapted[current] != value:
            previous = adapted[current]
            retained = previous if isinstance(previous, str) else value
            if not isinstance(previous, str) and not isinstance(retained, str):
                retained = max(previous, retained)
        adapted[current] = retained
    measured = {
        identity: value for identity, value in adapted.items() if not isinstance(value, str)
    }
    holes = {identity: value for identity, value in adapted.items() if isinstance(value, str)}
    costs = writer.load_module_costs(path)
    output = writer.render_manifest(
        measured,
        [
            'Recorded from: metadata-only catalogue identity adaptation; no node re-measured',
            'Original durations, declared holes and module costs retained under decided case ids',
        ],
        costs,
        holes,
    )
    path.write_text(output)
    _, loaded = writer.load_manifest(path)
    require(
        loaded == measured and writer.load_unmeasured(path) == set(holes),
        'Runtime identity adaptation retains measurements and explicit holes',
    )


def main(*, runtimes=False):
    validate_inputs()
    if runtimes:
        migrate_runtime_ids()
        return
    migrate_pins()
    migrate_cli()
    print(
        'Catalogue identity fixtures migrated; scientific values and original provenance retained'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtimes', action='store_true')
    main(runtimes=parser.parse_args().runtimes)
