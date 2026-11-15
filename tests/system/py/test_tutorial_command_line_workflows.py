"""Owner 4cf15ae54: execute visible Command line stages against Python and regression pins."""

import json
import os
import subprocess
import sys
from itertools import accumulate

import pytest

from tests.fixtures.tutorial_cases.command_line import (
    actions,
    compare_staged_regression_pin,
    delete_loop,
    edit_project,
    loop_schemas,
    setup_action,
    visible_flag_edits,
    write_project,
)
from tests.fixtures.tutorial_cases.contract import ROOT, interfaces_for
from tests.fixtures.tutorial_cases.notebook_fit import local_collection
from tests.fixtures.tutorial_cases.pins import machine_values, pinned_start
from tests.fixtures.tutorial_cases.stages import group, observe
from tests.integration.py.test_tutorial_empty_project import api
from tests.integration.py.test_tutorial_fit_stages import FITTING, source


@pytest.fixture(scope='module')
def collection(tmp_path_factory):
    return local_collection(tmp_path_factory.mktemp('visible-cli-collection'))


@pytest.mark.parametrize('case', [case for case in FITTING if 'cli' in interfaces_for(case)])
def test_visible_command_line_edits_and_fits_match_python_stages_and_final_pin(  # noqa: PLR0912, PLR0914, PLR0915 - whole visible workflow
    case, tmp_path, collection
):
    page = ROOT / 'website/surfaces/docs/cli/tutorials/cases' / (case + '.md')
    assert page.is_file(), (
        'Gate 5: the executable Command line lesson is a local user page: ' + case
    )
    text = page.read_text()
    steps = actions(text)
    fits = [step for step in steps if step[0] == 'fit']
    assert len(fits) >= 2 and any(
        step[0] == 'download' for step in steps[: steps.index(fits[0])]
    ), 'Gate 5: the visible lesson gets its case and runs successive actual edi fit stages'
    assert any(step[0] in {'edit', 'free-rows'} and '()' in step[2] for step in steps), (
        'Gate 5: the Command line lesson teaches selecting free parameters with empty brackets'
    )
    assert {'mkdir', 'write', 'move', 'download'} <= {
        step[0] for step in steps[: steps.index(fits[0])]
    }, 'Gate 5: the lesson constructs its project from visible files and downloaded blocks'
    quantities = pinned_start(case)
    first_arguments = fits[0][1]
    assert first_arguments and not first_arguments[0].startswith('-'), (
        'Gate 5: each visible fit names its project'
    )
    project = tmp_path / first_arguments[0]
    assert project.resolve().is_relative_to(tmp_path), (
        'Gate 5: tutorial commands stay in their fresh work folder'
    )
    expected = (
        observe(source(case, 'script'))['cycles'] if 'python' in interfaces_for(case) else None
    )
    totals = list(accumulate(cycle['constraints'] for cycle in expected)) if expected else None
    actual = []
    final = None
    schemas = {}
    for operation, argument, body in steps:
        if operation in {'mkdir', 'move', 'unpack'}:
            setup_action(tmp_path, operation, argument)
        elif operation == 'write':
            write_project(project, argument, body)
        elif operation == 'download':
            run = subprocess.run(
                [sys.executable, '-m', 'edi', *argument],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
                env={**os.environ, 'EDI_COLLECTION': str(collection)},
            )
            assert run.returncode == 0, (
                'Gate 5: the displayed download obtains its actual collection member: '
                + run.stderr
            )
        elif operation == 'delete-loop':
            delete_loop(project, argument, body)
        elif operation == 'edit':
            schemas.setdefault(argument, loop_schemas((project / argument).read_text()))
            edit_project(project, argument, body, schemas=schemas[argument])
        elif operation in {'clear-free', 'free-rows'}:
            schemas.setdefault(argument, loop_schemas((project / argument).read_text()))
            visible_flag_edits(
                project,
                argument,
                body if operation == 'free-rows' else None,
                schemas=schemas[argument],
            )
        elif operation in {'fit', 'calc'}:
            for path in sorted(project.rglob('*.edi')):
                schemas.setdefault(
                    path.relative_to(project).as_posix(), loop_schemas(path.read_text())
                )
            if operation == 'fit':
                loaded = api().Project.load(project)
                parameters = json.loads(
                    loaded.report.model(excluded=['data', 'reflections']).to_json()
                )['parameters']
                active = sorted({group(row['unique_name']) for row in parameters if row['free']})
                actual.append({'active': active, 'constraints': len(loaded.analysis.constraints)})
            # Report selection only changes presentation. Preserve every scientific option
            # and execute exactly one real fit per displayed stage, retaining full precision.
            arguments = list(argument)
            assert (tmp_path / arguments[0]).resolve() == project.resolve(), (
                'Gate 5: every stage fits the same progressively edited project'
            )
            arguments[0] = str(project.resolve())
            for option in ['--report', '--verbosity']:
                if option in arguments:
                    at = arguments.index(option)
                    del arguments[at : at + 2]
            run = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'edi',
                    operation,
                    *arguments,
                    '--report',
                    'machine',
                    '--verbosity',
                    'full',
                ],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=3600,
                env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
            )
            assert run.returncode == 0, (
                'Gate 5: every visible stage executes successfully: ' + run.stderr
            )
            if operation == 'fit':
                final = run.stdout
    if expected is not None:
        assert actual == [
            {'active': cycle['active'], 'constraints': total}
            for cycle, total in zip(expected, totals, strict=True)
        ], 'Gate 5: declared Command line and Python lessons share their exact stage sequence'
    compare_staged_regression_pin(machine_values(final), quantities)
