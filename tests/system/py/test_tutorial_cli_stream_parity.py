"""Owner 53fc79e74: both real CLI entry points retain the same complete human stream."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT


def without_time(text):
    lines = text.splitlines(keepends=True)
    width = None
    result = []
    for original in lines:
        line = original
        if re.search(r'\biter\b', line) and re.search(r'\btime\b', line):
            width = re.search(r'\biter\b', line).end()
        if width is not None and line[:width].strip().isdigit():
            match = re.fullmatch(r'(\s*\d+)\s+[-+\d.eE]+\s+(.+?)(\n?)', line)
            assert match is not None, 'Gate 5: an iteration row has one identifiable time field'
            line = match[1] + ' <time> ' + match[2] + match[3]
        elif line.lstrip().startswith('done ·'):
            line = re.sub(r'(?<= · )\d+(?:\.\d+)? s(?=\n?$)', '<time> s', line)
        result.append(line)
    return ''.join(result)


def assert_human_stream(text):
    lines = text.splitlines()
    assert any(line.startswith('edi fit:') for line in lines), (
        'Gate 5: human fit output starts with the shared project/count preamble'
    )
    headers = [
        (index, line)
        for index, line in enumerate(lines)
        if re.search(r'\biter\b', line) and re.search(r'\btime\b', line)
    ]
    assert len(headers) == 1, 'Gate 5: human fit output has its iteration-table header'
    index, header = headers[0]
    width = re.search(r'\biter\b', header).end()
    assert (
        index + 1 < len(lines)
        and not lines[index + 1][:width].strip()
        and lines[index + 1].strip()
    ), 'Gate 5: the starting-value row appears immediately after the table header'
    iterations = [line for line in lines[index + 2 :] if line[:width].strip().isdigit()]
    assert iterations, 'Gate 5: the human stream includes actual per-iteration rows'
    assert all(re.match(r'\s*\d+\s+\d+\.\d{3}\s', line) for line in iterations), (
        'Gate 5/8: every iteration time has three decimal places'
    )
    summaries = [line for line in lines if line.lstrip().startswith('done ·')]
    assert len(summaries) == 1 and 'iters' in summaries[0], (
        'Gate 5: the human stream ends with its shared fit summary'
    )
    assert re.search(r' · \d+\.\d{2} s$', summaries[0]), (
        'Gate 5/8: the summary time has two decimal places'
    )


@pytest.fixture(scope='module')
def both_entry_points(tmp_path_factory):
    candidates = [
        os.environ.get('EDI_CLI_EXECUTABLE'),
        ROOT / 'build/ci-consumer/cli/easydiffraction',
        ROOT / 'build/ci/cli/easydiffraction',
    ]
    binary = next(
        (str(path) for path in candidates if path and Path(path).is_file()),
        None,
    )
    assert binary is not None, 'Gate 5 prerequisite: build the standalone easydiffraction target'
    folder = tmp_path_factory.mktemp('cli-human-parity')
    source = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project'
    project = folder / 'project'
    shutil.copytree(source, project)
    before = {
        path.relative_to(project): path.read_bytes()
        for path in project.rglob('*')
        if path.is_file()
    }
    arguments = ['fit', str(project), '--dry', '--report', 'human', '--verbosity', 'compact']
    outputs = {}
    for name, prefix in [('standalone', [binary]), ('python', [sys.executable, '-m', 'edi'])]:
        run = subprocess.run(
            prefix + arguments,
            cwd=folder,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
            env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
        )
        assert run.returncode == 0, (
            'Gate 5: each actual fit entry point completes: ' + name + run.stderr
        )
        outputs[name] = run.stdout
        (folder / (name + '.stdout')).write_text(run.stdout)
        assert before == {
            path.relative_to(project): path.read_bytes()
            for path in project.rglob('*')
            if path.is_file()
        }, 'Gate 5: both dry fits preserve the same complete starting tree'
    return outputs


def test_standalone_and_python_human_output_match_except_elapsed_time(both_entry_points):
    assert without_time(both_entry_points['standalone']) == without_time(
        both_entry_points['python']
    ), 'Gate 5: standalone and Python human output is byte-identical apart from elapsed time'


@pytest.mark.parametrize('entry', ['standalone', 'python'])
def test_each_cli_entry_really_streams_header_start_iterations_and_summary(
    entry, both_entry_points
):
    assert_human_stream(both_entry_points[entry])


@pytest.mark.parametrize('escape', ['rwp', 'iteration', 'starting-row', 'summary', 'header'])
def test_time_normalizer_never_hides_other_output_changes(escape):
    original = (
        'edi fit: project example, 42 pts fitted / 45 loaded, 2 free\n'
        '   iter   time (s)    Rwp (%)   reduced χ²\n'
        '                       12.5          2.75\n'
        '      1       0.140      7.25          1.28\n'
        '  done · converged · 1 iters · reduced χ² 1.28 · Rwp 7.25 % · 0.20 s\n'
    )
    assert_human_stream(original)
    assert without_time(original) == without_time(
        original.replace('0.140', '8.920').replace('0.20 s', '7.90 s')
    ), 'Gate 5: only actual duration fields are ignored by the parity comparison'
    changed = {
        'rwp': original.replace('7.25', '8.25'),
        'iteration': original.replace('      1 ', '      2 '),
        'starting-row': original.replace('12.5', '13.5'),
        'summary': original.replace('converged ·', 'not converged ·'),
        'header': original.replace('45 loaded', '46 loaded'),
    }[escape]
    assert without_time(original) != without_time(changed), (
        'Gate 5: all non-time human output remains part of the parity assertion'
    )


@pytest.mark.parametrize('wrong', ['0.14', '0.1400', '0.2 s', '0.200 s'])
def test_stream_shape_refuses_old_or_extra_time_precision(wrong):
    original = (
        'edi fit: project example, 42 pts fitted / 45 loaded, 2 free\n'
        '   iter   time (s)    Rwp (%)   reduced χ²\n'
        '                       12.5          2.75\n'
        '      1      0.140      7.25          1.28\n'
        '  done · converged · 1 iters · reduced χ² 1.28 · Rwp 7.25 % · 0.20 s\n'
    )
    assert_human_stream(original)
    broken = original.replace('0.20 s' if wrong.endswith(' s') else '0.140', wrong)
    with pytest.raises(AssertionError, match='Gate 5/8:'):
        assert_human_stream(broken)
