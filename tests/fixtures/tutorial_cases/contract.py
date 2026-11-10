"""Independent ADR-0080 contract helpers; numerical expectations are REGRESSION PINS."""

import json
import subprocess
import sys
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads(Path(__file__).with_name('contract.json').read_text())
CASES = CONTRACT['cases']


def records(root=ROOT, *, json_output=True):
    return subprocess.run(
        [
            sys.executable,
            str(root / 'tools/checks/case_records.py'),
            '--root',
            str(root),
        ]
        + (['--json'] if json_output else []),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


def read_records(root=ROOT):
    run = records(root)
    assert run.returncode == 0, (
        'Gate 1: the public case-record builder must succeed and name partial cases: '
        + run.stdout
        + run.stderr
    )
    result = json.loads(run.stdout)
    assert isinstance(result, list), 'Gate 1: the record command returns the case collection'
    return result


def case_record(case, root=ROOT):
    matches = [row for row in read_records(root) if row.get('id') == case]
    assert len(matches) == 1, 'Gate 1: every owner-selected case has exactly one record: ' + case
    return matches[0]


def pin_quantities(document, *, simulation=False):
    source = document.get('calc', {}) if simulation else document
    return {
        name: row
        for name, row in source.get('quantities', {}).items()
        if row.get('kind') == 'regression-pin'
    }


INTERFACES = ('app', 'python', 'cli')
SURFACE_INTERFACE = {
    'app': 'app',
    'app_docs': 'app',
    'python': 'python',
    'script': 'python',
    'notebook': 'python',
    'cli': 'cli',
    'cli_docs': 'cli',
}


def declared_interfaces(record):
    value = record.get('interfaces', list(INTERFACES))
    assert isinstance(value, list) and value and all(isinstance(item, str) for item in value), (
        'Gate 1/3/4: declared tutorial interfaces are a nonempty list of interface names'
    )
    assert len(value) == len(set(value)) and set(value) <= set(INTERFACES), (
        'Gate 1/3/4: tutorial interfaces are unique and limited to app, python and cli'
    )
    return tuple(value)


@cache
def _registry_interfaces(payload):
    import yaml  # noqa: PLC0415 - parse the independent committed case declaration

    return yaml.safe_load(payload)['projects']


def interfaces_for(case, root=ROOT):
    rows = _registry_interfaces((root / 'docs/user/cli/projects.yml').read_text())
    matches = [row for row in rows if row['id'] == case]
    if not matches and case in CASES:
        # Missing records cannot opt out of surfaces; Gate 1 diagnoses the absence.
        return INTERFACES
    assert len(matches) == 1, 'Gate 1/3/4: each tutorial has one source interface declaration'
    return declared_interfaces(matches[0])


def cases_for(*interfaces, root=ROOT):
    return [case for case in CASES if set(interfaces) <= set(interfaces_for(case, root))]
