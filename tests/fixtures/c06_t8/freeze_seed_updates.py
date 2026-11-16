"""Seal decided seed updates before the unchanged historical source-byte gates."""

import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

from tests.fixtures.c06_t8.variant_name_projection import restore_variant_name

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
RETIRED = {'fast-descent-linear-snap', 'fast-descent-guarded-linear-snap'}


def pin_changes(old, new, trail=()):
    if isinstance(old, dict) and isinstance(new, dict):
        removed = old.keys() - new.keys()
        assert not new.keys() - old.keys() and removed <= RETIRED, (
            'Only the two explicitly retired strategy branches may leave a retained seed'
        )
        for name in removed:
            assert all(
                row.get('kind') == 'regression-pin' for row in old[name]['quantities'].values()
            ), 'A retired strategy branch cannot conceal an independent physical reference'
        return [list(trail + (name,)) for name in sorted(removed)] + [
            change for name in new for change in pin_changes(old[name], new[name], trail + (name,))
        ]
    if old == new:
        return []
    assert trail[-1:] == ('value',) or trail == ('edi', 'quantities', 'iterations', 'kind'), (
        'Seed updates preserve every schema field, reference kind and tolerance except the named '
        'iteration classification'
    )
    return [list(trail)]


def stop_entry(analysis_name, stop_row):
    current_analysis = (ROOT / analysis_name).read_bytes()
    with zipfile.ZipFile(ROOT / 'tests/fixtures/metadata_transition/task-inputs.zip') as archive:
        legacy_analysis = archive.read(stop_row['after_sha256'])
    assert hashlib.sha256(legacy_analysis).hexdigest() == stop_row['after_sha256'], (
        'The stop-rule set transition authenticates the complete existing legacy source'
    )
    assert legacy_analysis == subprocess.check_output(
        ['git', 'show', 'a452ce5^:' + analysis_name], cwd=ROOT
    ), (
        'The retained legacy source must equal the complete committed parent of the selector '
        'migration'
    )
    legacy_tag = b'_minimizer.stop_rule shift_su\n'
    assert (
        legacy_analysis.count(legacy_tag) == 1
        and legacy_analysis.replace(legacy_tag, b'') == current_analysis
    ), (
        'The current default-set declaration removes only its legacy scalar; all other source '
        'bytes remain'
    )
    assert current_analysis == subprocess.check_output(
        ['git', 'show', 'a452ce5:' + analysis_name], cwd=ROOT
    ), 'The default-set transition is exactly the committed selector migration'
    return {
        'kind': 'default-stop-rule-set',
        'current_sha256': hashlib.sha256(current_analysis).hexdigest(),
        'previous_sha256': stop_row['after_sha256'],
        'source_commit': 'a452ce52ec19ba696412af61f21ddb36699c5a2f',
        'effective_rules': ['chi_square_change', 'shift_su'],
    }


def verify(a, b, trail=()):
    if isinstance(a, dict) and isinstance(b, dict):
        if a.get('kind') == 'reference' and trail != (
            'edi',
            'quantities',
            'iterations',
        ):
            assert a == b, (
                'Every independent physical reference and its tolerance remains unchanged'
            )
        for key in a.keys() & b.keys():
            verify(a[key], b[key], trail + (key,))


def seed_entry(name, historical):
    current = restore_variant_name(name, (ROOT / name).read_bytes())
    old = historical.encode()
    if current != old:
        left, right = json.loads(old), json.loads(current)
        changes = pin_changes(left, right)

        verify(left, right)
        return {
            'kind': 'regression-and-retired-strategy-update',
            'current_sha256': hashlib.sha256(current).hexdigest(),
            'previous_sha256': hashlib.sha256(old).hexdigest(),
            'changed_paths': changes,
            'source_commits': subprocess.check_output(
                ['git', 'log', '-5', '--format=%H', '--', name], cwd=ROOT, text=True
            ).splitlines(),
        }
    return None


def main():
    source = json.loads(
        (ROOT / 'tests/fixtures/c34_t23_cli_projects/source-objects.json').read_text()
    )['projects']
    ids = json.loads((ROOT / 'tests/fixtures/c34_t23_cli_projects/project-ids.json').read_text())[
        'source_to_project'
    ]
    history = json.loads(
        (ROOT / 'tests/fixtures/example_catalogue/retention-adaptations.json').read_text()
    )['files']
    metadata = json.loads((ROOT / 'tests/fixtures/metadata_transition/sources.json').read_text())[
        'files'
    ]
    removed_paths = set(
        subprocess.check_output(
            ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'de09a36'],
            cwd=ROOT,
            text=True,
        ).splitlines()
    )
    stop_inputs = json.loads(
        (ROOT / 'tests/fixtures/metadata_transition/task-inputs.json').read_text()
    )['files']
    entries = {}
    for seed in source:
        analysis_name = f'docs/user/cli/{ids[seed]}/project/analysis/analysis.edi'
        entries[analysis_name] = stop_entry(analysis_name, stop_inputs[analysis_name])

        name = f'docs/user/cli/{ids[seed]}/expected.json'
        if name in history:
            entry = seed_entry(name, history[name]['after'])
            if entry is not None:
                entries[name] = entry

        for path in (ROOT / f'docs/user/cli/{ids[seed]}/project').rglob('*.edi'):
            name = path.relative_to(ROOT).as_posix()
            row = metadata.get(name)
            if name not in removed_paths:
                continue
            current = path.read_bytes()
            # The absorption retirement removed one exact zero scalar;
            # no live compatibility member is restored.
            old = subprocess.check_output(['git', 'show', 'de09a36^:' + name], cwd=ROOT)
            if row is not None:
                assert hashlib.sha256(old).hexdigest() == row['after_sha256'], (
                    'The absorption comparison retains the authenticated complete descriptive '
                    'source'
                )
            removed = re.findall(rb'(?m)^_absorption\.abscor2[^\n]*\n', old)
            assert (
                removed == [b'_absorption.abscor2 0.0\n']
                and old.replace(removed[0], b'') == current
            ), (
                'Only the exact retired zero absorption scalar may differ from the historical '
                'source'
            )
            entries[name] = {
                'kind': 'removed-zero-absorption-scalar',
                'current_sha256': hashlib.sha256(current).hexdigest(),
                'previous_sha256': hashlib.sha256(old).hexdigest(),
                'removed': removed[0].decode(),
                'source_commit': 'de09a36',
            }
    output = {
        'claim': 'Exact source-only stages; historical captures and every scientific '
        'reference/tolerance retained',
        'files': entries,
    }
    committed = json.loads(
        subprocess.check_output(
            ['git', 'show', 'HEAD:tests/fixtures/c06_t8/seed-updates.json'], cwd=ROOT, text=True
        )
    )['files']
    for name, row in output['files'].items():
        previous = committed.get(name)
        if previous is not None and {
            key: value for key, value in row.items() if key != 'source_commits'
        } == {key: value for key, value in previous.items() if key != 'source_commits'}:
            # A merge's history simplification cannot rewrite an unchanged source receipt.
            output['files'][name] = previous
    (HERE / 'seed-updates.json').write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
