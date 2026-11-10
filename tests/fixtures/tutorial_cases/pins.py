"""Regression agreement and start custody, never a correctness oracle for diffraction."""

import json
import math
import re
import subprocess

from tests.fixtures.tutorial_cases.contract import CONTRACT, ROOT, pin_quantities


def git(root, *args):
    return subprocess.run(
        ['git', '-C', str(root), *args],
        capture_output=True,
        check=False,
    )


def project_at_commit(root, case, commit):
    prefix = 'docs/user/cli/' + case + '/project/'
    listing = git(root, 'ls-tree', '-r', '-z', commit, '--', prefix)
    assert listing.returncode == 0 and listing.stdout, (
        'Gate 2: the regression pin source commit contains the entire starting project'
    )
    result = {}
    for item in listing.stdout.split(b'\0'):
        if not item:
            continue
        header, path = item.split(b'\t', 1)
        mode, kind, oid = header.split()
        assert kind == b'blob' and mode in {b'100644', b'100755'}, (
            'Gate 2: a pinned start is a regular committed file tree, not an external symlink'
        )
        blob = git(root, 'cat-file', 'blob', oid.decode())
        assert blob.returncode == 0, 'Gate 2: every pinned start blob must be readable'
        result[path.decode().removeprefix(prefix)] = blob.stdout
    return result


def pinned_start(case, root=ROOT):
    directory = root / 'docs/user/cli' / case
    path = directory / 'expected.json'
    assert path.is_file(), 'Gate 2: every case has a committed regression-pin document: ' + case
    expected = json.loads(path.read_text())
    source = expected.get('source', {}).get('pins')
    assert isinstance(source, dict), (
        'Gate 2: regression pins name their source commit and re-pin reason'
    )
    commit = source.get('commit', '')
    reason = source.get('reason', '')
    assert isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{7,40}', commit), (
        'Gate 2: regression pins identify a concrete source commit'
    )
    assert isinstance(reason, str) and reason.strip(), (
        'Gate 2: a re-pin requires an explicit nonblank reason'
    )
    assert git(root, 'merge-base', '--is-ancestor', commit, 'HEAD').returncode == 0, (
        'Gate 2: the regression pin source commit is reachable task history'
    )
    project = directory / 'project'
    actual = {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in sorted(project.rglob('*'))
        if path.is_file()
    }
    assert actual == project_at_commit(root, case, commit), (
        'Gate 2: changing any starting file fails until the start is re-pinned with a reason: '
        + case
    )
    simulation = case in CONTRACT['simulations']
    quantities = pin_quantities(expected, simulation=simulation)
    assert quantities, 'Gate 2: every example has explicitly labelled regression-pin quantities'
    for row in quantities.values():
        assert type(row.get('value')) in {int, float} and math.isfinite(row['value']), (
            'Gate 2: a regression pin is a finite numeric expectation'
        )
        tolerances = [row.get('tol_abs'), row.get('tol_rel')]
        assert any(value is not None for value in tolerances) and all(
            value is None or (type(value) in {int, float} and math.isfinite(value) and value >= 0)
            for value in tolerances
        ), 'Gate 2: every cross-platform comparison has stated finite nonnegative bounds'
    require_explicit_repin(root, case, expected, simulation=simulation)
    return quantities


def require_explicit_repin(root, case, document, *, simulation):
    relative = 'docs/user/cli/' + case + '/expected.json'
    history = git(root, 'log', '--format=%H', '--', relative)
    assert history.returncode == 0, 'Gate 2: regression-pin change history must be readable'
    current = document
    for commit in history.stdout.decode().splitlines():
        previous = git(root, 'show', commit + ':' + relative)
        assert previous.returncode == 0, (
            'Gate 2: the previous committed regression pin is readable'
        )
        old = json.loads(previous.stdout)
        before = old.get('source', {}).get('pins')
        if not isinstance(before, dict):
            break  # Earlier pins predate ADR-0080's source-provenance contract.
        if pin_quantities(old, simulation=simulation) != pin_quantities(
            current, simulation=simulation
        ):
            after = current['source']['pins']
            assert after.get('reason', '').strip() and after['commit'] != before.get('commit'), (
                'Gate 2: changing pin values or tolerance requires '
                'fresh source provenance and a re-pin reason'
            )
        current = old


def machine_values(text):
    result = {}
    for line in text.splitlines():
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        assert key not in result, (
            'Gate 2: an actual machine result cannot overwrite a duplicate key'
        )
        result[key] = value
    return result


def compare_regression_pin(actual, quantities):
    for name, row in quantities.items():
        assert name in actual, (
            'Gate 2: every pinned quantity must be observed on each interface: ' + name
        )
        value = float(actual[name])
        assert math.isfinite(value), (
            'Gate 2: a nonfinite result never agrees with a regression pin'
        )
        assert math.isclose(
            value, row['value'], abs_tol=row.get('tol_abs') or 0, rel_tol=row.get('tol_rel') or 0
        ), (
            'Gate 2: each real result agrees with its labelled regression pin '
            'within only its stated tolerance: ' + name
        )
